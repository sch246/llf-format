# LLF 扩展

本文件收录**不属于 LLF 本体**、但值得标准化的约定。实现可以只支持其中一部分；不支持任何扩展都不影响 LLF 本体的互操作。

## 1. 帧流（`--LLF-BEGIN` … `--LLF-END`）

LLF 本体只定义**单条消息**。模型的实际输出里，消息往往夹在别的文本中（解释、Markdown、多个调用……）。本扩展给"把消息框出来"一个**可选**的统一约定，面向"一次生成里输出多个工具调用"这类场景。

**约定**

- *frame* = 单独一行 `--LLF-BEGIN`，随后是一条完整的 LLF 消息，以单独一行 `--LLF-END` 结束。
- *帧流* = 任意文本中夹着零个或多个 frame；frame 之外的内容不属于帧流，解析时忽略。
- frame 之间允许空行，忽略。
- frame 内再出现 `--LLF-BEGIN`，或到流末尾仍没有 `--LLF-END`，视为截断（E02）。

**为什么是 `--LLF-BEGIN` 而不是 `--LLF-CALL`**

框架层只负责"从哪里开始、到哪里结束"，不解释里面是什么——这与本体"格式不解释内容"一致。是不是一次工具调用，由 frame 里的内容说明（例如 `call - write_file`）；同一个约定因此也能装工具结果、错误或任何别的 LLF 消息，不必为每种语义新增一个标记。

**示例**

```
先读一下文件，再改：

--LLF-BEGIN
call - read_file
id - c1
args {}
  path - README.md
--LLF-END

--LLF-BEGIN
call - write_file
id - c2
args {}
  path - README.md
  content -
    |# LLF
--LLF-END

改好了。
```

**参考实现**

- `llf.parse_frames(text, strict=False) -> list`：见 [llf.py](llf.py)，忽略 frame 之外的内容与空行，frame 内仍按单条消息解析。
- 测试向量：`vectors.json` 的 `frame_vectors`。

## 2. 其它

类型解释（第 6 节）、约束解码语法（`grammars/`）也属于"围绕本体的约定"，但各有专门的文档位置，不在这里重复。
