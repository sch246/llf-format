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


def run_vectors():
    failures = []
    for v in load_vectors():
        try:
            got = llf.parse(v["input"])
        except llf.LLFError as error:
            if v.get("error") == error.code:
                continue
            failures.append(
                "vector %s: 期望错误 %s，实际抛 %s"
                % (v["id"], v.get("error"), error.code)
            )
            continue
        except Exception as error:  # noqa: BLE001
            failures.append("vector %s: 意外异常 %r" % (v["id"], error))
            continue
        if "error" in v:
            failures.append(
                "vector %s: 期望错误 %s，实际解析成 %r"
                % (v["id"], v["error"], got)
            )
        elif got != v["expected"]:
            failures.append(
                "vector %s: 期望 %r，实际 %r" % (v["id"], v["expected"], got)
            )
    return failures


STRINGS = [
    "", " ", "  x", "x  ", "a b", 'a"b', "a\\b", "a\nb", "x\n", "\n",
    "3", "007", "true", "null", "-", "_", "{}", "[]", "#x", "名字", "柚子",
    "line1\nline2\n", "tab\there", "a\r\nb", "call - fake",
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
            rng.choice(["key", "a b", 'q"q', "-", "_", "", "#h", "名字", "a\tb", "a\nb"]): random_value(rng, depth + 1)
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
    failures = run_vectors()
    failures += run_fuzz()
    if failures:
        print("失败 %d 项：" % len(failures))
        for item in failures[:20]:
            print("  " + item)
        return 1
    print("全部通过：46 条向量 + 2000 组往返 fuzz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
