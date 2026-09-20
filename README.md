# LLF — Literal Line Format

一种零转义、格式上不可注入、可流式的数据格式。**格式不写类型、不做类型判断**：它只存储字典、列表、字符串、null（写 `_`），标量一律是字符串；某段字符串该被读成整数、浮点、布尔还是别的类型，由使用者的 JSON Schema 解释。主要面向大模型的工具调用，也适合手写。

```
# 工具调用：类型由 schema 解释，消息里只有字符串
call - write_file
id - c1
args {}
  path - src/main.py
  mode - 644
  overwrite - true
  backup _
  content -
    |def f():
    |    return "call - fake"   # 不需要任何转义
    |
--LLF-END
```

## 特点

- **零转义**：多行文本每行以 `|` 开头，之后的内容原样保留。
- **不可注入**：内容永远在 `|` 之后；由符合规范的编码器写出的内容不可能变成结构行。
- **无类型**：格式只存字典、列表、字符串、null；类型解释全部发生在 JSON Schema 侧，格式里没有类型标记。
- **键名逃生口**：普通键名不能含空格、tab、双引号；需要时用 JSON 风格的 `"…"` 加常规转义，于是空键、含空格的键、含引号的键、甚至恰好叫 `-` 或 `|` 的键都能表示。
- **空白处理**：`-` 的行内载荷按 Unicode `White_Space` 两端 strip；需要保留首尾空白或换行时用文本块，文本块里 `|` 之后逐字节保留。
- **文本块缩进自由**：`|` 之前的空格一律忽略，文本行可以顶格写，手写时不必再数两层缩进。
- **可流式**：每行的含义只由环境和首字符决定，可以边生成边解析。
- **明确结束符**：消息以单独一行 `--LLF-END` 结束；它是可见 token，不会被“清理行尾空白”的工具弄丢。

## 状态

v0.11 草案，欢迎讨论。完整规范见 [SPEC.md](SPEC.md)；命名与版本变化见 SPEC.md 第 12 节。

## 参考实现

- [llf.py](llf.py)：纯标准库的解析器与编码器；`python3 llf.py < message.llf` 可直接试。
- [vectors.json](vectors.json)：79 条机器可读测试向量 + 2 条严格模式用例（输入字节 + 期望值或错误码）。
- [tests/test_llf.py](tests/test_llf.py)：跑向量，并做 2000 组定长词汇 + 5000 组随机字节的 `decode(encode(x)) == x` 往返 fuzz，`python3 tests/test_llf.py`。
- [tools/build_vectors.py](tools/build_vectors.py)：从 Python 字面量重新生成 `vectors.json`。
- [tools/check_docs.py](tools/check_docs.py)：检查 Markdown 表格列数一致，防止单元格里的 `|` 把表切坏。
- [grammars/llf.gbnf](grammars/llf.gbnf)：GBNF 语法，供 llama.cpp / XGrammar 等约束解码直接使用；结构缩进建模到 6 层，文本行不限缩进。
- [grammars/llf.lark](grammars/llf.lark)：同源的 Lark 语法，供 outlines 使用（Earley / dynamic lexer）。
- [tools/build_grammars.py](tools/build_grammars.py)：重新生成两份语法，`python3 tools/build_grammars.py`。
- [tools/check_grammar.py](tools/check_grammar.py)：用一个小型 GBNF 识别器验证 GBNF，无需第三方依赖。
- [tools/check_lark.py](tools/check_lark.py)：用真正的 Lark 验证 Lark 语法，需 `pip install lark`；没装就跳过。
- [EXTENSIONS.md](EXTENSIONS.md)：不属于本体的可选约定；当前有帧流 `--LLF-BEGIN` … `--LLF-END` 与 `llf.parse_frames`。

语法保证结构缩进、头、文本块与 `--LLF-END` 的合法性；它**不**校验键是否符合调用方的 schema，也不含注释与多消息流。

## 相关项目

[YAML](https://yaml.org) 与 LLF 的块标量用同一个 `|` 记号，但处理方式恰好相反：YAML 靠缩进界定块、会把内容重新缩进、并且有著名的隐式类型推断（`NO`、`on`、`1.0` 会被读成布尔或数字，即 “Norway problem”）；LLF 用行首 `|` 标记界定块、不碰缩进、也完全不做类型推断。想要“一段可读的结构化文本”时，LLF 想避开的正是 YAML 的这类歧义。

[NestedText](https://nestedtext.org) 同样用行前缀免除转义，也把标量类型交给应用层。两者最直接的区别在**字典与列表的表示**：NestedText 靠子行的形状推断容器类型，于是空字典、空列表与空字符串容易纠缠；LLF 把 `{}` / `[]` 显式写出，嵌套与空容器都没有歧义。LLF 另加了流式语义与明确的截断检测，定位于机器生成。

## 许可证

MIT，见 [LICENSE](LICENSE)。
