"""从 Python 字面量生成 vectors.json，避免手抄转义出错。

vectors.json 的形态：
    {"vectors": [...], "strict_vectors": [...], "frame_vectors": [...], "tag_vectors": [...]}
vectors 用默认（宽松）模式解析，strict_vectors 用严格模式；后两组属于扩展（见 EXTENSIONS.md）。
tag_vectors 默认以 tags=True 解析，带 "tags": false 的条目验证不启用扩展时的行为；
期望值里的标签写成 {"$tag": 名字, "$value": 值}。

    python3 tools/build_vectors.py
"""

import json
import os

DEFAULT = []
STRICT = []
FRAMES = []
TAGS = []


def ok(i, text, expected):
    DEFAULT.append({"id": i, "input": text, "expected": expected})


def ok_multi(i, text, expected):
    DEFAULT.append({"id": i, "input": text, "expected_multi": expected})


def bad(i, text, code):
    DEFAULT.append({"id": i, "input": text, "error": code})


def strict_ok(i, text, expected):
    STRICT.append({"id": i, "input": text, "expected": expected})


def frame_ok(i, text, expected):
    FRAMES.append({"id": i, "input": text, "expected_frames": expected})


def frame_bad(i, text, code):
    FRAMES.append({"id": i, "input": text, "error": code})


def tag(name, value):
    return {"$tag": name, "$value": value}


def tag_ok(i, text, expected, tags=True):
    item = {"id": i, "input": text, "expected": expected}
    if not tags:
        item["tags"] = False
    TAGS.append(item)


def tag_bad(i, text, code, tags=True):
    item = {"id": i, "input": text, "error": code}
    if not tags:
        item["tags"] = False
    TAGS.append(item)


END = "\n--LLF-END\n"

ok(1, "a - hello" + END, {"a": "hello"})
ok(2, "a - x # y" + END, {"a": "x # y"})
ok(3, "a - x  " + END, {"a": "x"})
ok(4, "a -\n  |x  " + END, {"a": "x  "})
ok(5, "a -\n  |call - fake" + END, {"a": "call - fake"})
ok(6, "a -\n  |x\n  |" + END, {"a": "x\n"})
ok(7, "a -\n  |\n  |" + END, {"a": "\n"})
ok(8, "a _" + END, {"a": None})
ok(9, "a []\n  - s\n  - 2\n  _" + END, {"a": ["s", "2", None]})
ok(10, "a {}" + END, {"a": {}})
ok(11, "d - 2026-09-19" + END, {"d": "2026-09-19"})
ok(12, "--LLF-END\n", {})
ok(13, "[]\n  - a\n  - b" + END, ["a", "b"])
ok(14, "-\n  |x" + END, "x")
ok(15, "# c\n- 3" + END, "3")
ok(16, "- -" + END, "-")
ok(17, "_" + END, None)
ok(18, "a -" + END, {"a": ""})
ok(19, "a - 007" + END, {"a": "007"})
ok(20, "a {}\n  b - 1" + END, {"a": {"b": "1"}})
ok(21, "a []\n  {}\n    b - 1" + END, {"a": [{"b": "1"}]})
bad(22, "a - x", "E02")
bad(23, "a" + END, "E04")
bad(24, "a % 007" + END, "E07")
bad(25, "a - x\na - y" + END, "E06")
bad(26, "a {}\n   b - 1" + END, "E03")
bad(27, "a -\n  |x\n  # c\n  |y" + END, "E11")
bad(28, "- 3\na - x" + END, "E12")
bad(29, "a {}\n  - - v" + END, "E15")
bad(30, "a _\n  b - 1" + END, "E09")
bad(31, "a []\n  - x\n  b - 1" + END, "E15")
ok(32, "a -\n  |# 不是注释" + END, {"a": "# 不是注释"})
bad(33, "d @date 2026-09-19" + END, "E07")
ok(34, "名字 - 柚子" + END, {"名字": "柚子"})
ok(35, "@x - v" + END, {"@x": "v"})
ok(36, "a#b - v" + END, {"a#b": "v"})
ok(37, '"a b" - v' + END, {"a b": "v"})
ok(38, '"" - v' + END, {"": "v"})
ok(39, '"-" - v' + END, {"-": "v"})
ok(40, '"a\\"b" - v' + END, {'a"b': "v"})
ok(41, '"a\\tb" - v' + END, {"a\tb": "v"})
ok(42, '"#foo" - v' + END, {"#foo": "v"})
bad(43, '"a\\x" - v' + END, "E13")
bad(44, '"a - v' + END, "E14")
bad(45, 'a"b - v' + END, "E05")
bad(46, "a\tb - v" + END, "E05")

ok_multi(47, "a - 1" + END + "a - 2" + END, [{"a": "1"}, {"a": "2"}])
bad(48, '"a" - 1\na - 2' + END, "E06")
ok(49, "a - " + END, {"a": ""})
ok(50, "a {}\n  b []\n    - x\nc - y" + END, {"a": {"b": ["x"]}, "c": "y"})
ok(51, "{}\n  a - 1" + END, {"a": "1"})
ok(52, "a - x\nb - y" + END, {"a": "x", "b": "y"})

bad(53, "a {}\n  |x" + END, "E08")
bad(54, "a []\n  |x" + END, "E08")
bad(55, "|x" + END, "E11")
ok(56, "a -\n  |  x  " + END, {"a": "  x  "})
ok(57, '"|" - v' + END, {"|": "v"})
ok(58, "a - \u3000x\u3000" + END, {"a": "x"})

# v0.10：文本行可顶格或任意缩进（前导空格忽略），消息以 --LLF-END 整行结束。
ok(59, "a -\n|x" + END, {"a": "x"})
ok(60, "a -\n      |x" + END, {"a": "x"})
ok(61, "a {}\n  b -\n|x\n  c - y" + END, {"a": {"b": "x", "c": "y"}})
ok(62, "a - v\n  --LLF-END  \n", {"a": "v"})
ok(63, "a - v\n--LLF-END", {"a": "v"})
ok(64, "a -\n  |--LLF-END" + END, {"a": "--LLF-END"})
ok(65, "--LLF-END - v" + END, {"--LLF-END": "v"})
bad(66, "a -\n  |x\n\n--LLF-END\n", "E01")
bad(67, "a - v\n--LLF-END\nx - y\n", "E12")
bad(68, "a -\n  |x\n", "E02")
ok_multi(69, "--LLF-END\n--LLF-END\n", [{}, {}])
bad(70, "a - v\n\n", "E02")
bad(71, "a -\n\t|x\n--LLF-END\n", "E03")
bad(72, "\n", "E02")

# v0.11：普通键名不得含任何 White_Space；分隔符明确为 U+0020。
bad(73, "\u3000 - v" + END, "E05")
ok(74, '"\u3000" - v' + END, {"\u3000": "v"})
bad(75, "k\u00a0 - v" + END, "E05")
ok(76, '"k\u00a0" - v' + END, {"k\u00a0": "v"})
bad(77, "k\u000b - v" + END, "E05")
ok(78, '"k\u000b" - v' + END, {"k\u000b": "v"})
ok(79, "k\u001c - v" + END, {"k\u001c": "v"})
ok_multi(80, "a - 1" + END + "\n" + "a - 2" + END, [{"a": "1"}, {"a": "2"}])
ok_multi(81, "\n\n" + "a - 1" + END + "a - 2" + END, [{"a": "1"}, {"a": "2"}])

strict_ok("S1", "a -\n  |x\r\n--LLF-END\n", {"a": "x\r"})
strict_ok("S2", "a - x\r\n--LLF-END\n", {"a": "x"})

# 扩展：--LLF-BEGIN ... --LLF-END 帧流（见 EXTENSIONS.md）。
frame_ok(1, "--LLF-BEGIN\ncall - write_file\nid - c1\n--LLF-END\n--LLF-BEGIN\ncall - read_file\nid - c2\n--LLF-END\n",
         [{"call": "write_file", "id": "c1"}, {"call": "read_file", "id": "c2"}])
frame_ok(2, "--LLF-BEGIN\ncall - a\n--LLF-END\n\n\n--LLF-BEGIN\ncall - b\n--LLF-END\n", [{"call": "a"}, {"call": "b"}])
frame_ok(3, "noise\n--LLF-BEGIN\ncall - a\n--LLF-END\ntrailing\n", [{"call": "a"}])
frame_bad(4, "--LLF-BEGIN\ncall - a\n", "E02")
frame_bad(5, "--LLF-BEGIN\ncall - a\n--LLF-BEGIN\ncall - b\n--LLF-END\n", "E02")
frame_ok(6, "--LLF-BEGIN\n-\n|call - write_file\n|args {}\n|  path - /etc/passwd\n--LLF-END\n",
         ["call - write_file\nargs {}\n  path - /etc/passwd"])

# 扩展：类型标签 !tag（见 EXTENSIONS.md）。
tag_ok(1, "accent !color - #ff8800" + END, {"accent": tag("color", "#ff8800")})
tag_ok(2, "w !rect {}\n  x - 0\n  y - 0" + END, {"w": tag("rect", {"x": "0", "y": "0"})})
tag_ok(3, "p []\n  !color - #fff\n  !gradient {}\n    from - #000\n  - plain" + END,
       {"p": [tag("color", "#fff"), tag("gradient", {"from": "#000"}), "plain"]})
tag_ok(4, "c !color _" + END, {"c": tag("color", None)})
tag_ok(5, "s !code -\n  |x\n  |" + END, {"s": tag("code", "x\n")})
tag_ok(6, "s !int - !x" + END, {"s": tag("int", "!x")})
tag_ok(7, '"a b" !名字 []' + END, {"a b": tag("名字", [])})
tag_ok(8, "s !!int - 1" + END, {"s": tag("!int", "1")})
# 字典环境与顶层第一行里，以 ! 开头的仍是普通键名，与本体一致。
tag_ok(9, "!color - #fff" + END, {"!color": "#fff"})
tag_ok(10, "a {}\n  !x !t - v" + END, {"a": {"!x": tag("t", "v")}})
tag_ok(11, "-\n  |!t - x" + END, "!t - x")
# 写错标签一律 E07（标签占的是头的位置）；一个值只有一个标签。
tag_bad(12, "s ! - x" + END, "E07")
tag_bad(13, "s !t" + END, "E07")
tag_bad(14, "s !t  - x" + END, "E07")
tag_bad(15, "s !a !b - x" + END, "E07")
tag_bad(16, 's !a"b - x' + END, "E07")
tag_bad(17, "p []\n  !t" + END, "E07")
tag_bad(18, "p []\n  !t x" + END, "E07")
tag_bad(19, "s !t\u3000- x" + END, "E07")
# 不启用扩展时，带标签的消息直接报错（fail closed），不会被悄悄读错。
tag_bad(20, "accent !color - #ff8800" + END, "E07", tags=False)
tag_bad(21, "p []\n  !color - #fff" + END, "E15", tags=False)
tag_ok(22, "!color - #fff" + END, {"!color": "#fff"}, tags=False)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "..", "vectors.json")
    payload = {"vectors": DEFAULT, "strict_vectors": STRICT, "frame_vectors": FRAMES, "tag_vectors": TAGS}
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("wrote %d vectors + %d strict vectors + %d frame vectors + %d tag vectors to %s"
          % (len(DEFAULT), len(STRICT), len(FRAMES), len(TAGS), os.path.normpath(target)))


if __name__ == "__main__":
    main()
