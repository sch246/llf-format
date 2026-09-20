"""从同一份定义生成 LLF 的 GBNF（llama.cpp / XGrammar）与 Lark（outlines）语法。

    python3 tools/build_grammars.py

生成 grammars/llf.gbnf 与 grammars/llf.lark。结构缩进按层级展开到 MAX_LEVEL。
"""

import os

MAX_LEVEL = 6

# ---- GBNF 片段（用 \xXX，避免转义歧义）----
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

# ---- Lark 片段（Python re；每个正则都非零宽）----
L_PLAIN_CHAR = r'[^\x20\t\n\r"]'
L_PLAIN_START = r'[^\x20\t\n\r"#|]'
L_PLAIN_START1 = r'[^\x20\t\n\r"#|\-_]'
L_PLAIN_START2 = r'[^\x20\t\n\r"#|{\[]'
L_LEN2_BRACE = r'[^\x20\t\n\r"}]'
L_LEN2_BRACKET = r'[^\x20\t\n\r"\]]'
L_QCHAR = r'[^"\\]'
L_BSLASH = r'\\'
L_ESC = r'["\\\/bfnrt]'
L_NL = r'\n'
L_NOT_NL = r'[^\n]'
L_WS = r'[ \t]'


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


def build_lark(max_level):
    out = []
    w = out.append
    w("// LLF v0.11 tool-call grammar for outlines / Lark.")
    w("// 结构行严格 2 空格缩进，最多 %d 层；文本行可任意缩进；消息以 --LLF-END 结束。" % max_level)
    w("// 与 grammars/llf.gbnf 同源；用 Earley（dynamic lexer）解析，所有正则均非零宽。")
    w("")
    w("start: map0 end | value0 end")
    w(f'end: "--LLF-END" /{L_NL}/')
    w("")
    for d in range(max_level + 1):
        w(f"value{d}: str | null_line | dict{d} | array{d}")
    w("")
    w(f'str: "-" " "* /{L_NL}/ textblock? | "-" " " /{L_NOT_NL}/ * /{L_NL}/')
    w("textblock: textline+")
    w(f'textline: " "* "|" /{L_NOT_NL}/ * /{L_NL}/')
    w(f'null_line: "_" /{L_WS}/ * /{L_NL}/')
    w("")
    for d in range(max_level + 1):
        ind = f'"{" " * (2 * d)}" ' if d else ""
        w(f"map{d}: entry{d}*")
        w(f'entry{d}: {ind}key " " value{d}')
        w(f"items{d}: item{d}*")
        w(f"item{d}: {ind}value{d}")
        if d < max_level:
            w(f'dict{d}: "{{}}" /{L_WS}/ * /{L_NL}/ map{d + 1}')
            w(f'array{d}: "[]" /{L_WS}/ * /{L_NL}/ items{d + 1}')
        else:
            w(f'dict{d}: "{{}}" /{L_WS}/ * /{L_NL}/')
            w(f'array{d}: "[]" /{L_WS}/ * /{L_NL}/')
        w("")
    w("key: plain_key | quoted_key")
    w("plain_key: plain_len1 | plain_len2 | plain_len3plus")
    w(f"plain_len1: /{L_PLAIN_START1}/")
    w(rf'plain_len2: /\{{/ /{L_LEN2_BRACE}/ | /\[/ /{L_LEN2_BRACKET}/ | plain_start2 plain_char')
    w("plain_len3plus: plain_start plain_char plain_char+")
    w(f"plain_char: /{L_PLAIN_CHAR}/")
    w(f"plain_start: /{L_PLAIN_START}/")
    w(f"plain_start2: /{L_PLAIN_START2}/")
    w('quoted_key: /"/ qchar* /"/')
    w(f'qchar: /{L_QCHAR}/ | /{L_BSLASH}/ /{L_ESC}/ | /{L_BSLASH}/ "u" hex hex hex hex')
    w("hex: /[0-9a-fA-F]/")
    return "\n".join(out) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    grammars = os.path.join(root, "grammars")
    os.makedirs(grammars, exist_ok=True)
    for name, text in (("llf.gbnf", build_gbnf(MAX_LEVEL)), ("llf.lark", build_lark(MAX_LEVEL))):
        with open(os.path.join(grammars, name), "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote grammars/%s" % name)


if __name__ == "__main__":
    main()
