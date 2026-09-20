"""从同一份定义生成 LLF 的 GBNF 语法（llama.cpp / XGrammar）。

    python3 tools/build_grammars.py

生成 grammars/llf.gbnf。结构缩进按层级展开到 MAX_LEVEL；文本行可任意缩进。
"""

import os

MAX_LEVEL = 6

SPACE = r"\x20"
TAB = r"\t"
LF = r"\n"
CR = r"\r"
QUOTE = r"\x22"
HASH = r"\x23"
PIPE = r"\x7C"
DASH = r"\x2D"
UNDER = r"\x5F"
LBRACE = r"\x7B"
LBRACKET = r"\x5B"
RBRACE = r"\x7D"
RBRACKET = r"\x5D"
BSLASH = r"\x5C"

PLAIN_CHAR = "[^" + SPACE + TAB + LF + CR + QUOTE + "]"
PLAIN_START = "[^" + SPACE + TAB + LF + CR + QUOTE + HASH + PIPE + "]"
PLAIN_START1 = "[^" + SPACE + TAB + LF + CR + QUOTE + HASH + PIPE + DASH + UNDER + "]"
PLAIN_START2 = "[^" + SPACE + TAB + LF + CR + QUOTE + HASH + PIPE + LBRACE + LBRACKET + "]"
LEN2_BRACE = "[^" + SPACE + TAB + LF + CR + QUOTE + RBRACE + "]"
LEN2_BRACKET = "[^" + SPACE + TAB + LF + CR + QUOTE + RBRACKET + "]"
QCHAR = "[^" + QUOTE + BSLASH + "]"


def build_gbnf(max_level):
    out = []
    w = out.append
    w("# LLF v0.11 tool-call grammar for llama.cpp / XGrammar (GBNF).")
    w("# 结构行严格 2 空格缩进，最多 %d 层；文本行可任意缩进；消息以 --LLF-END 结束。" % max_level)
    w("# 只建模“顶层键值对或单个值”的规范输出；不含注释、多消息流与 schema 级键校验。")
    w("")
    w("root ::= map0 end | value0 end")
    w('end ::= "--LLF-END" "' + LF + '"')
    w("")
    for d in range(max_level + 1):
        w("value%d ::= str | null_line | dict%d | array%d" % (d, d, d))
    w("")
    w('str ::= "-" [ ]* "' + LF + '" textblock? | "-" " " [^' + LF + ']* "' + LF + '"')
    w("textblock ::= textline+")
    w('textline ::= " "* "|" [^' + LF + ']* "' + LF + '"')
    w('null_line ::= "_" [ ' + TAB + ']* "' + LF + '"')
    w("")
    for d in range(max_level + 1):
        ind = '"%s" ' % (" " * (2 * d)) if d else ""
        w("map%d ::= entry%d*" % (d, d))
        w('entry%d ::= %skey " " value%d' % (d, ind, d))
        w("items%d ::= item%d*" % (d, d))
        w("item%d ::= %svalue%d" % (d, ind, d))
        if d < max_level:
            w(f'dict{d} ::= "{{}}" [ {TAB}]* "{LF}" map{d + 1}')
            w(f'array{d} ::= "[]" [ {TAB}]* "{LF}" items{d + 1}')
        else:
            w(f'dict{d} ::= "{{}}" [ {TAB}]* "{LF}"')
            w(f'array{d} ::= "[]" [ {TAB}]* "{LF}"')
        w("")
    w("key ::= plain_key | quoted_key")
    w("plain_key ::= plain_len1 | plain_len2 | plain_len3plus")
    w("plain_len1 ::= " + PLAIN_START1)
    w('plain_len2 ::= "{" ' + LEN2_BRACE + ' | "[" ' + LEN2_BRACKET + ' | plain_start2 plain_char')
    w("plain_len3plus ::= plain_start plain_char plain_char+")
    w("plain_char ::= " + PLAIN_CHAR)
    w("plain_start ::= " + PLAIN_START)
    w("plain_start2 ::= " + PLAIN_START2)
    w('quoted_key ::= "' + QUOTE + '" qchar* "' + QUOTE + '"')
    w('qchar ::= ' + QCHAR + ' | "' + BSLASH + '" ["' + BSLASH + '/bfnrt] | "' + BSLASH + '" "u" hex hex hex hex')
    w("hex ::= [0-9a-fA-F]")
    return "\n".join(out) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    target = os.path.join(root, "grammars", "llf.gbnf")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    text = build_gbnf(MAX_LEVEL)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote %s (%d rules)" % (os.path.normpath(target), text.count("::=")))


if __name__ == "__main__":
    main()
