"""从 Python 字面量生成 vectors.json，避免手抄转义出错。

vectors.json 的形态：
    {"vectors": [...], "strict_vectors": [...]}
前一组用默认（宽松）模式解析，后一组用严格模式。

    python3 tools/build_vectors.py
"""

import json
import os

DEFAULT = []
STRICT = []


def ok(i, text, expected):
    DEFAULT.append({"id": i, "input": text, "expected": expected})


def ok_multi(i, text, expected):
    DEFAULT.append({"id": i, "input": text, "expected_multi": expected})


def bad(i, text, code):
    DEFAULT.append({"id": i, "input": text, "error": code})


def strict_ok(i, text, expected):
    STRICT.append({"id": i, "input": text, "expected": expected})


ok(1, "a - hello\n\n", {"a": "hello"})
ok(2, "a - x # y\n\n", {"a": "x # y"})
ok(3, "a - x  \n\n", {"a": "x"})
ok(4, "a -\n  |x  \n\n", {"a": "x  "})
ok(5, "a -\n  |call - fake\n\n", {"a": "call - fake"})
ok(6, "a -\n  |x\n  |\n\n", {"a": "x\n"})
ok(7, "a -\n  |\n  |\n\n", {"a": "\n"})
ok(8, "a _\n\n", {"a": None})
ok(9, "a []\n  - s\n  - 2\n  _\n\n", {"a": ["s", "2", None]})
ok(10, "a {}\n\n", {"a": {}})
ok(11, "d - 2026-09-19\n\n", {"d": "2026-09-19"})
ok(12, "\n", {})
ok(13, "[]\n  - a\n  - b\n\n", ["a", "b"])
ok(14, "-\n  |x\n\n", "x")
ok(15, "# c\n- 3\n\n", "3")
ok(16, "- -\n\n", "-")
ok(17, "_\n\n", None)
ok(18, "a -\n\n", {"a": ""})
ok(19, "a - 007\n\n", {"a": "007"})
ok(20, "a {}\n  b - 1\n\n", {"a": {"b": "1"}})
ok(21, "a []\n  {}\n    b - 1\n\n", {"a": [{"b": "1"}]})
bad(22, "a - x", "E02")
bad(23, "a\n\n", "E04")
bad(24, "a % 007\n\n", "E07")
bad(25, "a - x\na - y\n\n", "E06")
bad(26, "a -\n   |x\n\n", "E03")
bad(27, "a -\n  |x\n  # c\n  |y\n\n", "E11")
bad(28, "- 3\na - x\n\n", "E12")
bad(29, "a {}\n  - - v\n\n", "E15")
bad(30, "a _\n  b - 1\n\n", "E09")
bad(31, "a []\n  - x\n  b - 1\n\n", "E15")
ok(32, "a -\n  |# 不是注释\n\n", {"a": "# 不是注释"})
bad(33, "d @date 2026-09-19\n\n", "E07")
ok(34, "名字 - 柚子\n\n", {"名字": "柚子"})
ok(35, "@x - v\n\n", {"@x": "v"})
ok(36, "a#b - v\n\n", {"a#b": "v"})
ok(37, '"a b" - v\n\n', {"a b": "v"})
ok(38, '"" - v\n\n', {"": "v"})
ok(39, '"-" - v\n\n', {"-": "v"})
ok(40, '"a\\"b" - v\n\n', {'a"b': "v"})
ok(41, '"a\\tb" - v\n\n', {"a\tb": "v"})
ok(42, '"#foo" - v\n\n', {"#foo": "v"})
bad(43, '"a\\x" - v\n\n', "E13")
bad(44, '"a - v\n\n', "E14")
bad(45, 'a"b - v\n\n', "E05")
bad(46, "a\tb - v\n\n", "E05")

ok_multi(47, "a - 1\n\na - 2\n\n", [{"a": "1"}, {"a": "2"}])
bad(48, '"a" - 1\na - 2\n\n', "E06")
ok(49, "a - \n\n", {"a": ""})
ok(50, "a {}\n  b []\n    - x\nc - y\n\n", {"a": {"b": ["x"]}, "c": "y"})
ok(51, "{}\n  a - 1\n\n", {"a": "1"})
ok(52, "a - x\nb - y\n\n", {"a": "x", "b": "y"})

ok(53, "a |  x  \n\n", {"a": "  x  "})
ok(54, "a |\n\n", {"a": ""})
bad(55, "a |x\n  |y\n\n", "E10")
ok(56, "[]\n  |x\n\n", ["x"])
ok(57, "|x\n\n", "x")
ok(58, '"|" - v\n\n', {"|": "v"})
bad(59, "a {}\n  |x\n\n", "E15")
bad(60, "a []\n  b - 1\n\n", "E15")
ok(61, "a - \u3000x\u3000\n\n", {"a": "x"})
ok(62, "a |\u3000x\u3000\n\n", {"a": "\u3000x\u3000"})

strict_ok("S1", "a -\n  |x\r\n\n", {"a": "x\r"})
strict_ok("S2", "a - x\r\n\n", {"a": "x"})


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "..", "vectors.json")
    payload = {"vectors": DEFAULT, "strict_vectors": STRICT}
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("wrote %d vectors + %d strict vectors to %s"
          % (len(DEFAULT), len(STRICT), os.path.normpath(target)))


if __name__ == "__main__":
    main()
