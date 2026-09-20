# LLF 扩展

本文件收录**不属于 LLF 本体**、但值得标准化的约定。实现可以只支持其中一部分；不支持任何扩展都不影响 LLF 本体的互操作。

## 1. 帧流（`--LLF-BEGIN` … `--LLF-END`）

LLF 本体只定义**单条消息**。模型的实际输出里，消息往往夹在别的文本中（解释、Markdown、多个调用……）。本扩展给"把消息框出来"一个**可选**的统一约定，面向"一次生成里输出多个工具调用"这类场景。

**约定**

- *frame* = 单独一行 `--LLF-BEGIN`，随后是一条完整的 LLF 消息（键值对或顶层单独值都可以），以单独一行 `--LLF-END` 结束。
- *帧流* = 任意文本中夹着零个或多个 frame；frame 之外的内容不属于帧流，解析时忽略。
- frame 之间允许空行，忽略。
- frame 内再出现 `--LLF-BEGIN`，或到流末尾仍没有 `--LLF-END`，视为截断（E02）。

**为什么是 `--LLF-BEGIN` 而不是 `--LLF-CALL`**

框架层只负责"从哪里开始、到哪里结束"，不解释里面是什么——这与本体"格式不解释内容"一致。是不是一次工具调用，由 frame 里的内容说明；同一个约定因此也能装工具结果、错误或任何别的 LLF 消息，不必为每种语义新增一个标记。

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

## 2. 调用与字面值的区分

LLF 本体分不出"模型想**调用**"还是"模型想**输出**字符串 `call - x`"——两者在字节上完全一样。这不是缺陷：**意图不属于字面格式**。

- **首选：用通道/角色。** 主流 API 把调用放在 assistant 消息的独立字段/块里（OpenAI 的 `tool_calls`、Anthropic 的 `tool_use`、Gemini 的 `functionCall`），只有 `arguments` / `input` 里才是参数字符串；结果走 tool 角色或 `tool_result` 块。LLF 只负责把参数序列化成字面值。**注意**：这是 API 层的视图——模型原始输出常常仍是带特殊 token / 标签的文本（Llama 3 的 `<|python_tag|>`、Hermes/Qwen 的 `<tool_call>…</tool_call>`、Mistral 的 `[TOOL_CALLS]`），由服务端的 tool parser 或 chat template 切出来。自己跑裸模型、没有这层 parser 时，这条边界得自己给。
- **只有纯文本时：frame 只给位置，payload 的形状给意图。** 不能把"顶格 frame"直接当成调用——否则模型展示一段调用示例时会被真的执行。约定：
  - frame 的消息是**调用形状的字典**（顶层含 `call`，且通过调用 schema 校验）→ 执行；
  - frame 的消息是其它任何值（顶层字符串、列表、null……）→ 字面值，只展示/存放，**永不执行**。
  - 要展示一个调用示例，就把它放进**字符串**里（文本块）；`|` 前缀保证里面变不成结构：

    ```
    --LLF-BEGIN
    -
    |call - write_file
    |args {}
    |  path - /etc/passwd
    --LLF-END
    ```

  这样"展示"和"执行"在结构上不相交：`|` 里的东西永远只是内容，和本体里"内容行必带 `|`、变不成结构"是同一个机制。
- **别用启发式猜意图。** 是否执行只由两个机械条件决定：**在帧内**，且 **payload 是通过 schema 校验的调用形状字典**。看到 `call - rm -rf` 出现在正文或 `|` 内容里就当调用执行，正是注入。

## 3. 其它

类型解释（第 6 节）、约束解码语法（`grammars/`）也属于"围绕本体的约定"，但各有专门的文档位置，不在这里重复。
