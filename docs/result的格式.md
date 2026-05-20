# result的格式

`result` 是 Whisper 模型 `transcribe()` 方法返回的**字典（dict）**对象，包含以下主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 完整的转录文本 |
| `segments` | `list` | 分段列表，每段包含时间戳、文本等详细信息 |
| `language` | `str` | 检测到的语言代码（如 `"zh"` 表示中文） |

可以通过 `result["text"]` 获取完整文本，也可以遍历 `result["segments"]` 获取每个片段的详细信息，例如：

```python
# 查看每个片段的起始时间、结束时间和文本
for segment in result["segments"]:
    print(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}")
```
