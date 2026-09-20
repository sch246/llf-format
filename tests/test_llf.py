"""LLF 参考实现的测试：机器可读向量 + 往返 fuzz。

    python3 tests/test_llf.py
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import llf  # noqa: E402


def load_vectors():
    with open(os.path.join(ROOT, "vectors.json"), encoding="utf-8") as fh:
        return json.load(fh)


def check_one(v, strict):
    if "expected_multi" in v:
        try:
            got = llf.parse_multi(v["input"], strict=strict)
        except llf.LLFError as error:
            return "期望多条消息，实际抛 %s" % error.code
        if got != v["expected_multi"]:
            return "期望 %r，实际 %r" % (v["expected_multi"], got)
        return None
    try:
        got = llf.parse(v["input"], strict=strict)
    except llf.LLFError as error:
        if v.get("error") == error.code:
            return None
        return "期望错误 %s，实际抛 %s" % (v.get("error"), error.code)
    except Exception as error:  # noqa: BLE001
        return "意外异常 %r" % (error,)
    if "error" in v:
        return "期望错误 %s，实际解析成 %r" % (v["error"], got)
    if got != v["expected"]:
        return "期望 %r，实际 %r" % (v["expected"], got)
    return None


def run_vectors():
    data = load_vectors()
    failures = []
    counts = []
    for key, strict in (("vectors", False), ("strict_vectors", True)):
        items = data[key]
        counts.append(len(items))
        for v in items:
            message = check_one(v, strict)
            if message:
                failures.append("%s %s: %s" % (key, v["id"], message))
    return failures, counts


STRINGS = [
    "", " ", "  x", "x  ", "a b", 'a"b', "a\\b", "a\nb", "x\n", "\n",
    "3", "007", "true", "null", "-", "_", "{}", "[]", "#x", "名字", "柚子",
    "line1\nline2\n", "tab\there", "a\r\nb", "x\r", "call - fake",
    "\u00a0x", "x\u3000", "\u3000", "|x", "|", "--LLF-END", "--LLF-END\n",
]


def random_value(rng, depth=0):
    choices = ["str", "none"]
    if depth < 3:
        choices += ["dict", "list"]
    kind = rng.choice(choices)
    if kind == "str":
        return rng.choice(STRINGS)
    if kind == "none":
        return None
    if kind == "dict":
        return {
            rng.choice(["key", "a b", 'q"q', "-", "_", "", "#h", "名字", "a\tb", "a\nb", "--LLF-END",
                        "\u3000", "\u00a0", "\u000b", "k\u001c"]): random_value(rng, depth + 1)
            for _ in range(rng.randint(0, 4))
        }
    return [random_value(rng, depth + 1) for _ in range(rng.randint(0, 4))]


def run_fuzz(count=2000, seed=20260921):
    rng = random.Random(seed)
    failures = []
    for i in range(count):
        value = random_value(rng)
        text = llf.dumps(value)
        try:
            back = llf.parse(text, strict=True)
        except llf.LLFError as error:
            failures.append("fuzz %d: %s\n输入值 %r\n文本:\n%s" % (i, error, value, text))
            continue
        if back != value:
            failures.append(
                "fuzz %d: 往返不一致\n原值 %r\n解回 %r\n文本:\n%s"
                % (i, value, back, text)
            )
    return failures


def main():
    failures, counts = run_vectors()
    failures += run_fuzz()
    if failures:
        print("失败 %d 项：" % len(failures))
        for item in failures[:20]:
            print("  " + item)
        return 1
    print("全部通过：%d 条默认模式向量 + %d 条严格模式向量 + 2000 组往返 fuzz"
          % (counts[0], counts[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
