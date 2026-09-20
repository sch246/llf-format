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

```

## 特点

- **零转义**：多行文本每行以 `|` 开头，之后的内容原样保留。
- **不可注入**：内容永远在 `|` 之后；由符合规范的编码器写出的内容不可能变成结构行。
- **无类型**：格式只存字典、列表、字符串、null；类型解释全部发生在 JSON Schema 侧，格式里没有类型标记。
- **键名逃生口**：普通键名不能含空格、tab、双引号；需要时用 JSON 风格的 `"…"` 加常规转义，于是空键、含空格的键、含引号的键、甚至恰好叫 `-` 的键都能表示。
- **可流式**：每行的含义只由环境、缩进和首字符决定，可以边生成边解析。
- **可检测截断**：消息以空行结束，中途断开会被识别。

## 状态

v0.6 草案，欢迎讨论。完整规范见 [SPEC.md](SPEC.md)；命名与版本变化见 SPEC.md 第 12 节。

## 参考实现

- [llf.py](llf.py)：纯标准库的解析器与编码器；`python3 llf.py < message.llf` 可直接试。
- [vectors.json](vectors.json)：46 条机器可读测试向量（输入字节 + 期望值或错误码）。
- [tests/test_llf.py](tests/test_llf.py)：跑向量并做 2000 组 `decode(encode(x)) == x` 往返 fuzz，`python3 tests/test_llf.py`。
- [tools/build_vectors.py](tools/build_vectors.py)：从 Python 字面量重新生成 `vectors.json`。
- [tools/check_docs.py](tools/check_docs.py)：检查 Markdown 表格列数一致，防止单元格里的 `|` 把表切坏。

## 相关项目

[NestedText](https://nestedtext.org) 同样用行前缀免除转义，也把标量类型交给应用层。两者最直接的区别在**字典与列表的表示**：NestedText 靠子行的形状推断容器类型，于是空字典、空列表与空字符串容易纠缠；LLF 把 `{}` / `[]` 显式写出，嵌套与空容器都没有歧义。LLF 另加了流式语义与截断检测，定位于机器生成。
