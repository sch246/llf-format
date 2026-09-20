"""LLF — Literal Line Format 参考解析器与编码器。

实现 SPEC.md v0.11 定义的格式，只依赖标准库。

    from llf import parse, dumps, LLFError
    value = parse(text)
    text = dumps(value)

命令行：
    python3 llf.py < message.llf
"""

import json
import sys


class LLFError(Exception):
    """格式错误，携带规范第 11 节的错误码。"""

    def __init__(self, code, message, line=None):
        self.code = code
        self.line = line
        suffix = "" if line is None else " (line %d)" % line
        super().__init__("%s: %s%s" % (code, message, suffix))


def _err(code, message, line=None):
    raise LLFError(code, message, line)


HEADS = ("-", "_", "{}", "[]")

# 消息结束符：整行去掉首尾空白后等于这个字面量。
TERMINATOR = "--LLF-END"

# Unicode White_Space 属性为真的码点；按属性定义，不按某个语言库的实现定义。
_WS = frozenset(
    [0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0x85, 0xA0, 0x1680]
    + list(range(0x2000, 0x200B))
    + [0x2028, 0x2029, 0x202F, 0x205F, 0x3000]
)


def _strip_ws(s):
    i, j = 0, len(s)
    while i < j and ord(s[i]) in _WS:
        i += 1
    while j > i and ord(s[j - 1]) in _WS:
        j -= 1
    return s[i:j]


def _indent_of(raw, lineno):
    n = 0
    while n < len(raw) and raw[n] == " ":
        n += 1
    if n < len(raw) and raw[n] == "\t":
        _err("E03", "缩进中含 tab", lineno)
    return n


def _starts_with_head(content):
    return content.split(" ", 1)[0] in HEADS


def _classify(content):
    if content.startswith('"'):
        return "map"
    return "single" if _starts_with_head(content) else "map"


class _Parser:
    def __init__(self, lines):
        self.lines = lines
        self.i = 0

    def peek(self):
        while self.i < len(self.lines) and self.lines[self.i][2].startswith("#"):
            self.i += 1
        if self.i >= len(self.lines):
            return None
        return self.lines[self.i]

    def parse_message(self):
        first = self.peek()
        if first is None:
            return {}
        lineno, indent, content, _raw = first
        if indent != 0:
            _err("E03", "顶层缩进必须为 0", lineno)
        if content.startswith("|"):
            _err("E11", "文本行出现在不允许的位置", lineno)
        if _classify(content) == "single":
            self.i += 1
            head, payload = self._head(content, lineno)
            value = self._value(0, head, payload, lineno)
            leftover = self.peek()
            if leftover is not None:
                _err("E12", "顶层单独值之后又出现非注释行", leftover[0])
            return value
        value = self._map(0)
        leftover = self.peek()
        if leftover is not None:
            _err("E12", "顶层之后又出现非注释行", leftover[0])
        return value

    def _map(self, indent):
        result = {}
        while True:
            nxt = self.peek()
            if nxt is None:
                break
            lineno, li, content, _raw = nxt
            if content.startswith("|"):
                _err("E11", "文本行出现在不允许的位置", lineno)
            if li < indent:
                break
            if li > indent:
                _err("E03", "缩进不是恰好多 2 格", lineno)
            self.i += 1
            if _starts_with_head(content):
                _err("E15", "环境不匹配：字典环境里出现了项行", lineno)
            if content.startswith('"'):
                key, rest = self._quoted_key(content, lineno)
            else:
                key, rest = self._plain_key(content, lineno)
            head, payload = self._head(rest, lineno)
            if key in result:
                _err("E06", "同一层键名重复：%r" % key, lineno)
            result[key] = self._value(indent, head, payload, lineno)
        return result

    def _list(self, indent):
        result = []
        while True:
            nxt = self.peek()
            if nxt is None:
                break
            lineno, li, content, _raw = nxt
            if content.startswith("|"):
                _err("E11", "文本行出现在不允许的位置", lineno)
            if li < indent:
                break
            if li > indent:
                _err("E03", "缩进不是恰好多 2 格", lineno)
            self.i += 1
            if not _starts_with_head(content):
                _err("E15", "环境不匹配：列表环境里出现了不以头开头的行", lineno)
            head, payload = self._head(content, lineno)
            result.append(self._value(indent, head, payload, lineno))
        return result

    def _plain_key(self, content, lineno):
        sp = content.find(" ")
        if sp == -1:
            _err("E04", "条目行只有键、没有头", lineno)
        key = content[:sp]
        rest = content[sp + 1:]
        if key == "":
            _err("E05", "键名为空", lineno)
        if '"' in key:
            _err("E05", "普通键名不能含双引号，需用引号键", lineno)
        if any(ord(c) in _WS for c in key):
            _err("E05", "普通键名不能含空白，需用引号键", lineno)
        if rest == "":
            _err("E04", "条目行只有键、没有头", lineno)
        if rest[0] == " ":
            _err("E05", "键与头之间必须恰好一个空格", lineno)
        return key, rest

    def _quoted_key(self, content, lineno):
        out = []
        i = 1
        while i < len(content):
            c = content[i]
            if c == '"':
                rest = content[i + 1:]
                if rest == "":
                    _err("E04", "条目行只有键、没有头", lineno)
                if rest[0] != " ":
                    _err("E05", "键与头之间必须恰好一个空格", lineno)
                if len(rest) > 1 and rest[1] == " ":
                    _err("E05", "键与头之间必须恰好一个空格", lineno)
                return "".join(out), rest[1:]
            if c == "\\":
                i += 1
                if i >= len(content):
                    _err("E13", "引号键转义不完整", lineno)
                e = content[i]
                simple = {
                    '"': '"', "\\": "\\", "/": "/", "b": "\b",
                    "f": "\f", "n": "\n", "r": "\r", "t": "\t",
                }
                if e in simple:
                    out.append(simple[e])
                    i += 1
                elif e == "u":
                    ch, i = self._unicode_escape(content, i + 1, lineno)
                    out.append(ch)
                else:
                    _err("E13", "非法转义 \\%s" % e, lineno)
            else:
                out.append(c)
                i += 1
        _err("E14", "引号键没有闭合引号", lineno)

    def _unicode_escape(self, content, i, lineno):
        hexs = content[i:i + 4]
        if len(hexs) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hexs):
            _err("E13", "\\u 后必须是 4 位十六进制", lineno)
        cp = int(hexs, 16)
        i += 4
        if 0xD800 <= cp <= 0xDBFF:
            if content[i:i + 2] != "\\u":
                _err("E13", "高位代理必须跟低位代理", lineno)
            low = content[i + 2:i + 6]
            if len(low) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in low):
                _err("E13", "\\u 后必须是 4 位十六进制", lineno)
            lo = int(low, 16)
            if not 0xDC00 <= lo <= 0xDFFF:
                _err("E13", "低位代理不合法", lineno)
            cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
            i += 6
        elif 0xDC00 <= cp <= 0xDFFF:
            _err("E13", "孤立的低位代理", lineno)
        return chr(cp), i

    def _head(self, rest, lineno):
        token = rest.split(" ", 1)[0]
        if token not in HEADS:
            _err("E07", "未知的头符号：%r" % rest[:4], lineno)
        payload = rest[len(token):]
        if token == "-":
            payload = _strip_ws(payload)
            return "-", (payload if payload != "" else None)
        if _strip_ws(payload) != "":
            _err("E08", "%s 后不能有载荷" % token, lineno)
        return token, None

    def _value(self, indent, head, payload, lineno):
        if head == "-":
            if payload is not None:
                nxt = self.peek()
                if nxt is not None and (nxt[2].startswith("|") or nxt[1] > indent):
                    _err("E10", "字符串既有同行载荷又有子层", nxt[0])
                return payload
            nxt = self.peek()
            if nxt is None:
                return ""
            if nxt[2].startswith("|"):
                return self._text_block()
            if nxt[1] <= indent:
                return ""
            if nxt[1] != indent + 2:
                _err("E03", "缩进不是恰好多 2 格", nxt[0])
            _err("E10", "字符串的子层只能是文本行", nxt[0])
        if head == "_":
            nxt = self.peek()
            if nxt is not None and (nxt[2].startswith("|") or nxt[1] > indent):
                _err("E09", "null 下不能有子层", nxt[0])
            return None
        if head == "{}":
            nxt = self.peek()
            if nxt is None:
                return {}
            if nxt[2].startswith("|"):
                _err("E08", "字典下不能有文本行", nxt[0])
            if nxt[1] <= indent:
                return {}
            if nxt[1] != indent + 2:
                _err("E03", "缩进不是恰好多 2 格", nxt[0])
            return self._map(indent + 2)
        if head == "[]":
            nxt = self.peek()
            if nxt is None:
                return []
            if nxt[2].startswith("|"):
                _err("E08", "列表下不能有文本行", nxt[0])
            if nxt[1] <= indent:
                return []
            if nxt[1] != indent + 2:
                _err("E03", "缩进不是恰好多 2 格", nxt[0])
            return self._list(indent + 2)
        _err("E07", "未知的头符号：%r" % head, lineno)

    def _text_block(self):
        out = []
        while self.i < len(self.lines):
            _lineno, _li, content, _raw = self.lines[self.i]
            if not content.startswith("|"):
                break
            out.append(content[1:])
            self.i += 1
        return "\n".join(out)


def _normalize(text, strict):
    if text.startswith("\ufeff"):
        _err("E01", "带 BOM")
    if not strict:
        text = text.replace("\r\n", "\n")
    return text


def _raw_lines(text):
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _lines_from(raw_lines):
    lines = []
    for idx, raw in enumerate(raw_lines, start=1):
        if _strip_ws(raw) == "":
            _err("E01", "只含空白的行", idx)
        ind = _indent_of(raw, idx)
        lines.append((idx, ind, raw[ind:], raw))
    return lines


def _split_message(text, strict):
    """返回 (消息体行, 结束符之后的行)。找不到结束符就报 E02。"""
    raw_lines = _raw_lines(_normalize(text, strict))
    for idx, raw in enumerate(raw_lines):
        if _strip_ws(raw) == TERMINATOR:
            return raw_lines[:idx], raw_lines[idx + 1:]
    _err("E02", "缺少结束符（截断）")


def parse(text, strict=False):
    """解析一条 LLF 消息，返回 Python 的 dict / list / str / None。"""
    body, rest = _split_message(text, strict)
    if rest:
        _err("E12", "结束符之后还有内容")
    return _Parser(_lines_from(body)).parse_message()


def parse_multi(text, strict=False):
    """解析一个消息流，返回消息列表。消息之间的空行忽略。"""
    raw_lines = _raw_lines(_normalize(text, strict))
    out = []
    start = 0
    while start < len(raw_lines):
        if _strip_ws(raw_lines[start]) == "":
            start += 1
            continue
        end = None
        for idx in range(start, len(raw_lines)):
            if _strip_ws(raw_lines[idx]) == TERMINATOR:
                end = idx
                break
        if end is None:
            _err("E02", "缺少结束符（截断）")
        out.append(_Parser(_lines_from(raw_lines[start:end])).parse_message())
        start = end + 1
    return out


def _sp(n):
    return " " * n


def _plain_key_ok(key):
    return (
        key != ""
        and not any(ord(c) in _WS for c in key)
        and '"' not in key
        and key not in HEADS
        and not key.startswith("#")
        and not key.startswith("|")
    )


def _encode_key(key):
    if not isinstance(key, str):
        raise TypeError("键必须是字符串")
    if _plain_key_ok(key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _string_lines(s):
    if s == "":
        return ["-"]
    if "\n" in s or s != _strip_ws(s):
        parts = ["-"]
        for line in s.split("\n"):
            parts.append("|" + line)
        return parts
    return ["- " + s]


def _emit(key, value, indent, lines):
    prefix = _sp(indent)
    if key is not None:
        prefix += _encode_key(key) + " "
    if value is None:
        lines.append(prefix + "_")
        return
    if isinstance(value, str):
        parts = _string_lines(value)
        lines.append(prefix + parts[0])
        for extra in parts[1:]:
            lines.append(_sp(indent + 2) + extra)
        return
    if isinstance(value, dict):
        lines.append(prefix + "{}")
        if value:
            for k, v in value.items():
                _emit(k, v, indent + 2, lines)
        return
    if isinstance(value, list):
        lines.append(prefix + "[]")
        if value:
            for item in value:
                _emit(None, item, indent + 2, lines)
        return
    raise TypeError("不支持的值的类型：%s" % type(value).__name__)


def dumps(value):
    """把 dict / list / str / None 编码成一条 LLF 消息。"""
    lines = []
    if isinstance(value, dict):
        if value:
            for k, v in value.items():
                _emit(k, v, 0, lines)
    else:
        _emit(None, value, 0, lines)
    return "".join(line + "\n" for line in lines) + TERMINATOR + "\n"


def _main():
    data = sys.stdin.read()
    try:
        value = parse(data)
    except LLFError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
