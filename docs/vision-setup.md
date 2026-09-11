# 视觉能力部署指南（Qwen3.8-27B VLM）

> 本文档对应 2026-09-11 的视觉功能实测：从组件量化到「视觉 + 长上下文」的最优平衡点。

## 一、组件获取与自行量化

Qwen3.8-27B 是 VLM（视觉语言模型），但 GGUF 的视觉组件（mmproj）需要单独下载：

| 文件 | 大小 | 来源 |
|---|---|---|
| `mmproj-BF16.gguf` | 888 MB | esatapedico / unsloth 的 Qwen3.8-27B repo |

**可自行量化省显存**（llama.cpp 自带工具）：

```powershell
llama-quantize.exe mmproj-BF16.gguf mmproj-Q8_0.gguf Q8_0
# 888 MB → 600 MB（省 32%），实测识别质量与 BF16 完全相同
```

> ⚠️ llama.cpp 的量化器**不提供** mmproj 的 NVFP4/FP4 类型（唯一 FP4 类型 `MXFP4_MOE` 专用于 MoE 层）。视觉编码器在 GPU 上以 FP16/BF16 计算，没有 FP4 张量核加速。

## 二、★ 关键发现：视觉加载后的速度-上下文曲线

加载 mmproj 后，生成速度与上下文长度呈**非线性关系**（实测数据，Q8 视觉组件）：

| 上下文 | 显存余量 | 生成速度 | 视觉识别耗时 | 判定 |
|---|---|---|---|---|
| 192K | 179 MiB | **3.9 tok/s** | 47 s | ❌ 不可用 |
| 160K | 202 MiB | 20.8 tok/s | — | ❌ 太慢 |
| 160K + `--ctx-checkpoints 4` | — | 37.2 tok/s | — | ⚠️ 勉强 |
| **152K + `--ctx-checkpoints 4`** | 158 MiB | **63.6 tok/s** | **6.1 s** | ✅ **最优** |

**机制**：显存贴边时（mmproj 额外占用 ~0.6-1GB），引擎进入"极慢共享内存回退模式"——**不是 OOM 报错，而是静默降速 10~20 倍**。152K 和 160K 的剩余显存只差几十 MB，速度却差 3 倍，这是个非线性悬崖。

**缓解手段**：`--ctx-checkpoints 4`（默认值 32 浪费内存；实测让 160K 从 20.8 → 37.2 tok/s，+79%）。

## 三、推荐配置（视觉模式）

```powershell
llama-server.exe `
  -m Qwen3.8-27B-NVFP4-MTP-LOW.gguf `
  --mmproj mmproj-Q8_0.gguf `
  -ngl 99 -fa on -fit off `
  -c 152000 `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --ctx-checkpoints 4 `
  --spec-type draft-mtp --spec-draft-n-max 3 `
  --host 127.0.0.1 --port 8082 --load-mode none --jinja
```

| 配置 | 纯文本模式 | 视觉模式 |
|---|---|---|
| 上下文 | 192K | **152K** |
| 生成速度 | 79.6 tok/s | **63.6 tok/s** |
| 图像识别 | — | **6.1 秒/张**（640×420 测试图）|
| 识别准确率 | — | 形状 / 颜色 / 计数 / OCR 全部正确 ✓ |

## 四、API 调用示例（图像输入）

```python
import json, base64, urllib.request

b64 = base64.b64encode(open("image.png", "rb").read()).decode()
body = {
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述这张图片的内容，并读出图中的文字。"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
        ],
    }],
    "chat_template_kwargs": {"reasoning_effort": "medium"},
    "max_tokens": 1500, "temperature": 0.3,
}
# POST → http://127.0.0.1:8082/v1/chat/completions
```

## 五、已知限制与提示

1. **无 FP4 加速**：视觉编码器只能用 Q8/Q5/Q4 系量化
2. **七段数码管字体有 OCR 歧义**：实测"7392"被读成"1992"；换成点阵/常规字体后完全正确
3. 服务日志会建议 `--image-min-tokens 1024`（grounding 类任务更准，代价是图像 token 数增加）
4. 视觉 + 上下文**必须做平衡**：想要 192K 就只能牺牲视觉（或者等未来优化）
