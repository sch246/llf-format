"""用一个小型 GBNF 子集识别器验证 grammars/llf.gbnf。

    python3 tools/check_grammar.py

只支持本仓库语法用到的 GBNF 子集：字面量、字符类（含取反与范围）、规则引用、
分组、|、*、+、?。用集合式回溯匹配，能处理歧义。
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import llf  # noqa: E402


class _Tok:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def peek(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1
        return self.s[self.i] if self.i < len(self.s) else ""

    def get(self):
        c = self.peek()
        if c == "":
            return ("EOF", None)
        if c == '"':
            return ("STRING", self._string())
        if c == "[":
            return ("CLASS", self._class())
        if c in "()|*+?":
            self.i += 1
            return (c, None)
        j = self.i
        while j < len(self.s) and (self.s[j].isalnum() or self.s[j] in "_-"):
            j += 1
        if j == self.i:
            raise ValueError("unexpected %r" % c)
        name = self.s[self.i:j]
        self.i = j
        return ("IDENT", name)

    def _string(self):
        self.i += 1
        out = []
        while self.i < len(self.s) and self.s[self.i] != '"':
            out.append(self._escape())
        if self.i >= len(self.s):
            raise ValueError("unterminated string")
        self.i += 1
        return "".join(out)

    def _escape(self):
        c = self.s[self.i]
        if c != "\\":
            self.i += 1
            return c
        self.i += 1
        e = self.s[self.i]
        self.i += 1
        m = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/", "[": "[", "]": "]"}
        if e in m:
            return m[e]
        if e == "x":
            h = self.s[self.i:self.i + 2]
            self.i += 2
            return chr(int(h, 16))
        if e == "u":
            h = self.s[self.i:self.i + 4]
            self.i += 4
            return chr(int(h, 16))
        raise ValueError("bad escape \\%s" % e)

    def _class(self):
        self.i += 1
        neg = False
        if self.s[self.i] == "^":
            neg = True
            self.i += 1
        chars = set()
        while self.i < len(self.s) and self.s[self.i] != "]":
            lo = self._class_char()
            if self.i < len(self.s) and self.s[self.i] == "-" and self.i + 1 < len(self.s) and self.s[self.i + 1] != "]":
                self.i += 1
                hi = self._class_char()
                chars.update(chr(cp) for cp in range(ord(lo), ord(hi) + 1))
            else:
                chars.add(lo)
        if self.i >= len(self.s):
            raise ValueError("unterminated class")
        self.i += 1
        return (neg, frozenset(chars))

    def _class_char(self):
        c = self.s[self.i]
        if c == "\\":
            return self._escape()
        self.i += 1
        return c


def _parse_alt(tk):
    items = [_parse_seq(tk)]
    while tk.peek() == "|":
        tk.get()
        items.append(_parse_seq(tk))
    return ("alt", tuple(items)) if len(items) > 1 else items[0]


def _parse_seq(tk):
    items = []
    while tk.peek() not in ("", "|", ")"):
        items.append(_parse_postfix(tk))
    return ("seq", tuple(items)) if len(items) != 1 else items[0]


def _parse_postfix(tk):
    node = _parse_atom(tk)
    while tk.peek() in ("*", "+", "?"):
        node = (tk.get()[0], node)
    return node


def _parse_atom(tk):
    t, v = tk.get()
    if t == "STRING":
        return ("lit", v)
    if t == "CLASS":
        return ("cls", v[0], v[1])
    if t == "IDENT":
        return ("ref", v)
    if t == "(":
        node = _parse_alt(tk)
        if tk.get()[0] != ")":
            raise ValueError("missing )")
        return node
    raise ValueError("bad atom %r" % t)


def parse_gbnf(text):
    rules = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "::=" not in line:
            continue
        name, _, rhs = line.partition("::=")
        tk = _Tok(rhs.strip())
        node = _parse_alt(tk)
        if tk.peek() != "":
            raise ValueError("trailing in %r" % line)
        rules[name.strip()] = node
    return rules


class Matcher:
    def __init__(self, rules, text):
        self.rules = rules
        self.text = text
        self.memo = {}

    def match(self, node, pos):
        key = (node, pos)
        if key in self.memo:
            return self.memo[key]
        result = self._match(node, pos)
        self.memo[key] = result
        return result

    def _match(self, node, pos):
        t = node[0]
        if t == "lit":
            return {pos + len(node[1])} if self.text.startswith(node[1], pos) else set()
        if t == "cls":
            if pos >= len(self.text):
                return set()
            inside = self.text[pos] in node[2]
            return {pos + 1} if inside != node[1] else set()
        if t == "ref":
            return self.match(self.rules[node[1]], pos)
        if t == "seq":
            cur = {pos}
            for child in node[1]:
                nxt = set()
                for p in cur:
                    nxt |= self.match(child, p)
                cur = nxt
                if not cur:
                    break
            return cur
        if t == "alt":
            out = set()
            for child in node[1]:
                out |= self.match(child, pos)
            return out
        if t == "*":
            return self._star(node[1], pos)
        if t == "+":
            out = set()
            for p in self.match(node[1], pos):
                out |= self._star(node[1], p)
            return out
        if t == "?":
            return {pos} | self.match(node[1], pos)
        raise ValueError(t)

    def _star(self, child, pos):
        result = {pos}
        frontier = {pos}
        while frontier:
            new = set()
            for p in frontier:
                for q in self.match(child, p):
                    if q not in result:
                        result.add(q)
                        new.add(q)
            frontier = new
        return result

    def accepts(self, text):
        return len(text) in self.match(self.rules["root"], 0)


POOL = list('ab0 \t\n\r-_|#"\\{}[]') + ["\u3000", "\u00a0", "\u000b", "\u001c", ":", ".", "/"]


def random_value(rng, depth=0):
    kinds = ["str", "none"]
    if depth < 5:
        kinds += ["dict", "list"]
    k = rng.choice(kinds)
    if k == "str":
        return "".join(rng.choice(POOL) for _ in range(rng.randint(0, 6)))
    if k == "none":
        return None
    if k == "dict":
        return {"".join(rng.choice(POOL) for _ in range(rng.randint(0, 5))): random_value(rng, depth + 1)
                for _ in range(rng.randint(0, 3))}
    return [random_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]


def main():
    with open(os.path.join(ROOT, "grammars", "llf.gbnf"), encoding="utf-8") as fh:
        rules = parse_gbnf(fh.read())
    undefined = set()

    def walk(node):
        if node[0] == "ref":
            if node[1] not in rules:
                undefined.add(node[1])
        elif node[0] == "cls":
            return
        elif node[0] in ("seq", "alt"):
            for c in node[1]:
                walk(c)
        elif node[0] in ("*", "+", "?"):
            walk(node[1])

    for rule in rules.values():
        walk(rule)
    print("rules: %d, undefined refs: %s" % (len(rules), sorted(undefined) or "none"))

    data = json.load(open(os.path.join(ROOT, "vectors.json"), encoding="utf-8"))
    corpus = []
    for group in ("vectors", "strict_vectors"):
        for v in data[group]:
            if "expected" in v:
                corpus.append(v["expected"])
            if "expected_multi" in v:
                corpus.extend(v["expected_multi"])
    rng = random.Random(20260921)
    corpus.extend(random_value(rng) for _ in range(3000))

    fails = []
    for value in corpus:
        text = llf.dumps(value)
        if not Matcher(rules, text).accepts(text):
            fails.append((value, text))
    print("canonical dumps accepted: %d/%d" % (len(corpus) - len(fails), len(corpus)))
    for value, text in fails[:5]:
        print("  REJECT value=%r text=%r" % (value, text))

    rejects = ["a - v\n", "a {}\n b - 1\n--LLF-END\n", "a -\tvalue\n--LLF-END\n", "--LLF-END\nEXTRA"]
    bad = [s for s in rejects if Matcher(rules, s).accepts(s)]
    print("invalid strings accepted (should be 0): %d" % len(bad))
    for s in bad:
        print("  ACCEPTED %r" % (s,))
    return 1 if fails or undefined or bad else 0


if __name__ == "__main__":
    sys.exit(main())
