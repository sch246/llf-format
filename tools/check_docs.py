#!/usr/bin/env python3
r"""检查文档里的 Markdown 表格：同一张表的列数必须一致。

单元格里的字面 | 必须转义成 \|，否则会被当成列分隔符把表切坏。

    python3 tools/check_docs.py
"""

import os
import sys
from collections import Counter

FILES = ("SPEC.md", "README.md")


def _cells_of(line):
    s = line.rstrip("\n")
    cells = []
    cur = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            cur.append(s[i:i + 2])
            i += 2
            continue
        if ch == "|":
            cells.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    cells.append("".join(cur))
    return cells


def _flush(block):
    if len(block) < 2:
        return []
    counts = [len(_cells_of(line)) for _n, line in block]
    if len(set(counts)) == 1:
        return []
    mode = Counter(counts).most_common(1)[0][0]
    return [(n, c, mode) for (n, _line), c in zip(block, counts) if c != mode]


def check(path):
    problems = []
    block = []
    with open(path, encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if line.lstrip().startswith("|"):
                block.append((number, line))
            else:
                problems += _flush(block)
                block = []
        problems += _flush(block)
    return problems


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = 0
    for name in FILES:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        for number, count, mode in check(path):
            print("%s:%d 列数 %d，同表其它行为 %d" % (name, number, count, mode))
            bad += 1
    if bad:
        print("发现 %d 处表格列数不一致" % bad)
        return 1
    print("表格列数一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
