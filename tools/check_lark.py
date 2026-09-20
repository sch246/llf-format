"""用 Lark（如果装了）验证 grammars/llf.lark。

    python3 tools/check_lark.py

没装 lark 时打印跳过信息。生成端用 Earley（默认 dynamic lexer），因为缩进靠
按层展开的空格字面量区分。
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import llf  # noqa: E402

try:
    from lark import Lark
except ImportError:
    print("skip: lark 未安装（python3 -m pip install lark）")
    sys.exit(0)

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
    with open(os.path.join(ROOT, "grammars", "llf.lark"), encoding="utf-8") as fh:
        grammar = fh.read()
    parser = Lark(grammar, parser="earley")

    data = json.load(open(os.path.join(ROOT, "vectors.json"), encoding="utf-8"))
    corpus = []
    for group in ("vectors", "strict_vectors"):
        for v in data[group]:
            if "expected" in v:
                corpus.append(v["expected"])
            if "expected_multi" in v:
                corpus.extend(v["expected_multi"])
    rng = random.Random(20260921)
    corpus.extend(random_value(rng) for _ in range(1500))

    fails = []
    for value in corpus:
        text = llf.dumps(value)
        try:
            parser.parse(text)
        except Exception as error:  # noqa: BLE001
            fails.append((value, text, str(error).splitlines()[0][:120]))
    print("lark: canonical dumps accepted %d/%d" % (len(corpus) - len(fails), len(corpus)))
    for value, text, err in fails[:5]:
        print("  REJECT value=%r" % (value,))
        print("         text=%r" % (text,))
        print("         err=%s" % err)

    rejects = ["a - v\n", "a {}\n b - 1\n--LLF-END\n", "a -\tvalue\n--LLF-END\n"]
    accepted = []
    for s in rejects:
        try:
            parser.parse(s)
            accepted.append(s)
        except Exception:  # noqa: BLE001
            pass
    print("lark: invalid strings accepted (should be 0): %d" % len(accepted))
    for s in accepted:
        print("  ACCEPTED %r" % (s,))
    return 1 if fails or accepted else 0


if __name__ == "__main__":
    sys.exit(main())
