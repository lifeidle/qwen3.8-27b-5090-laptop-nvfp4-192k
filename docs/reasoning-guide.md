# 思考档位（reasoning_effort）完整指南

> Qwen3.8 默认思考档是 **xhigh**，在 API 场景下是陷阱。本文是全部三档 + 预算参数的实测报告（2026-09-11）。

## 一、档位定义（从模型的 chat template 源码确认）

| 档位 | 实际行为 |
|---|---|
| **xhigh**（默认）| 往 system prompt 注入"Reasoning effort is set to xhigh. Please think carefully..." |
| **medium** | **不注入任何内容**（模型的原生行为）|
| **low** | 高效模式 |
| `enable_thinking: false` | 完全关闭思考（另有独立开关）|

> `high` 是 xhigh 的别名。所谓"档位"本质是**一句系统提示的注入与否**——这是 post-training 的产物，不是架构开关。

## 二、同题实测（题目：写 LRU 缓存，max_tokens=6000）

| 配置 | 耗时 | 总 token | 思考量 | 正文 | 结果 |
|---|---|---|---|---|---|
| **xhigh 无预算** | 114 s | 6000（撞上限）| 22,021 字符 | **0 字符** | ❌ **正文全空** |
| **xhigh + 顶层预算 3000** | 103 s | 5,498 | 10,059 | 6,386 | ✅ 能出结果 |
| xhigh + 把预算放错位置 | 117 s | 6000 | 22,207 | 0 | ❌ 参数被静默忽略 |
| **medium** | 37 s | 2,115 | 826 | 4,274 | ✅ **推荐** |
| **low** | 27 s | 2,157 | 692 | — | ✅ 最快 |

## 三、★ 关键坑：`reasoning_budget_tokens` 必须放在请求顶层

给思考设**硬上限**，防止 xhigh 失控：

```json
{
  "messages": [...],
  "chat_template_kwargs": {"reasoning_effort": "xhigh"},
  "reasoning_budget_tokens": 3000
}
```

**⚠️ 放进 `chat_template_kwargs` 里会被静默忽略**（实测：xhigh 依旧烧掉 22,207 字符思考、正文 0 输出）。必须放**请求 JSON 顶层**。

## 四、推荐用法

| 场景 | 配置 |
|---|---|
| 日常对话 / 代码（推荐）| `medium` |
| 复杂推理任务 | `xhigh` + 顶层 `reasoning_budget_tokens: 3000~5000` |
| 追求极致速度 | `low` |
| 批量/成本敏感 | `medium`（或 low），**永远不要依赖默认值** |

**max_tokens 建议**：它是"思考 + 正文"的总上限，必须大于 `reasoning_budget + 期望正文长度`。做开发建议 `max_tokens: 16000~32000`。

## 五、完整请求示例

```python
import json, urllib.request

body = {
    "messages": [{"role": "user", "content": "实现一个 LRU 缓存并解释设计选择。"}],
    "chat_template_kwargs": {"reasoning_effort": "xhigh"},
    "reasoning_budget_tokens": 4000,     # ★ 顶层参数
    "max_tokens": 16000,
    "temperature": 0.7,
}
data = json.dumps(body, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8082/v1/chat/completions",
                             data=data, headers={"Content-Type": "application/json; charset=utf-8"})
with urllib.request.urlopen(req, timeout=900) as r:
    resp = json.loads(r.read().decode("utf-8"))
print(resp["choices"][0]["message"]["content"])
```

> 社区共识（Simon Willison 等）同样建议：medium 或 low + 预算 ~5000 是最稳的起点。
