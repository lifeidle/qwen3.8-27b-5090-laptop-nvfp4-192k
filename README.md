# Qwen3.8-27B · 单卡 24GB 极限调优实录

**从 53 个社区量化变体中筛出最优解，并逐层压榨到硬件极限的完整实测**

[English →](./README_EN.md) ｜ [工具脚本 →](./scripts) ｜ [原始数据 →](./data)

[![Model](https://img.shields.io/badge/model-Qwen3.8--27B-7c3aed)](https://huggingface.co/Qwen/Qwen3.8-27B)
[![Platform](https://img.shields.io/badge/platform-RTX%205090%20Laptop%2024GB-76b900)]()
[![Throughput](https://img.shields.io/badge/throughput-79.6%20tok%2Fs-d97706)]()
[![Context](https://img.shields.io/badge/context-192K%20(q8__0%20KV)-2563eb)]()
[![Engine](https://img.shields.io/badge/llama.cpp-b10889-0ea5e9)](https://github.com/ggml-org/llama.cpp/releases)
[![License](https://img.shields.io/badge/license-MIT%20%2B%20CC%20BY%204.0-059669)](#许可)

---

## 🏆 最佳选择（直接看这里）

**NVFP4-MTP-LOW + 192K 上下文 + q8_0 KV + MTP n-max 3 + llama.cpp b10889**

```powershell
# 一键启动（先改脚本顶部的两个路径变量）
.\scripts\start-nvfp4-low.ps1        # → http://127.0.0.1:8082
```

### 三方终极对决（各自最优配置 · 同一台机器 · 同条件）

| | 🥇 **NVFP4-LOW** | 🥈 IQ3_S | 🥉 UD-Q4_K_S |
|---|---|---|---|
| **生成速度** | **79.6 tok/s** | 64.4 tok/s | 51.7 tok/s |
| **15.6K 长输入** | **9.7 s** | 14.9 s | 19.9 s |
| **最大上下文** | 200K（推荐 192K） | **212K**（极限 240K） | 200K |
| **模型体积** | 14.47 GiB | **11.29 GiB** | 14.30 GiB |
| **量化方式** | 全 NVFP4 + 轻量头部 | GSQ-RCO 混合（~3.5 bpw） | 动态 Q4_K_S（~4.4 bpw） |
| **质量** | 打平 | 打平（**任务无损**，有学术验证） | 打平（细节最严谨） |
| **定位** | **日常主力** ✅ | 超长材料备胎 | 存档 |

> **一句话**：NVFP4-LOW 在三方中速度双冠（生成 +24%、长输入 −35% vs 次优），质量与 BF16 的差距在社区 4,800 任务受控测试中不可测。IQ3_S 仅在你需要 21 万+ token 上下文时才值得切换。

![速度对决](assets/chart1-speed-duel.svg)

---

## 📌 三条核心结论

1. **q8_0 KV 是最被低估的优化**——零速度代价，容量直接 +56%（212K），质量近无损。而 q4_0 系 KV 虽然能开到满血 262K，却会让长输入慢 **28 倍**（内核回退），完全不可用。
2. **MTP 参数不必调**——n-max 3 就是 24GB 卡的最优（扫过 2/3/4/5 与 p-min）。接受率高 ≠ 速度快。
3. **引擎版本的影响力与量化类型强相关**——b10840 → b10889 给 NVFP4 白送 +6.6% 速度与 +48K 容量，给 K-quant 却是 −11%。**升级引擎后必须重测容量。**

---

## 📊 完整测试结果

### 1️⃣ 上下文容量：KV 量化是关键

![上下文容量](assets/chart2-context-capacity.svg)

| 模型 | F16 KV 上限 | **q8_0 KV 上限** | q4_0 系 KV |
|---|---|---|---|
| IQ3_S | 136K | **212K**（极限 240K） | 262K ⚠️ 慢 28× |
| NVFP4-LOW | 96K | **200K** | — |
| NVFP4-MID-HIGH | 88K | ~160K（估算） | — |
| UD-Q4_K_S | 96K | 200K | — |

**慢路径证据**（同一段 15.6K 输入的处理耗时）：

| 配置 | 耗时 | 判定 |
|---|---|---|
| 32K + F16 KV | 13.6 s | 基准 |
| 136K + F16 KV | 15.2 s | 无惩罚 |
| 200K + **q8_0** | **15.1 s** | **无惩罚** ✅ |
| 262K + **q4_0 系** | **~420 s 仍未完成** | ❌ 内核回退，吞吐从 286 衰减到 29 tok/s |

### 2️⃣ 速度对决（两代引擎交叉验证）

| 模型 | 引擎 b10840（旧） | 引擎 b10889（新） | 变化 |
|---|---|---|---|
| **NVFP4-LOW** | 74.7 tok/s / 152K / 10.1s | **79.6 / 200K / 9.7s** | **+6.6%、+48K** |
| IQ3_S | 61.9 / 212K / 15.5s | 64.4 / 212K / 14.9s | +4% |
| UD-Q4_K_S | 58.3 / 152K / 15.2s | 51.7 / 200K / 19.9s | **−11%**（无益） |

**机制解释**：
- **LOW 为什么最快**——轻量头部（Q5_0 输出层 + IQ4_XS MTP 头）让每次 MTP 验证/草稿读取成本最低。社区在桌面 5090 上观察到同样规律。
- **UD 接受率最高（73%）却最慢**——K-quant 每轮验证成本最贵（反量化开销）且无 FP4 加速。
- **NVFP4 的 FP4 优势只在 prefill 兑现**（10 s vs 15–20 s 级）；decode 优势来自头部设计而非文件大小。

### 3️⃣ MTP 参数全扫描（三方交叉验证）

| 配置 | NVFP4-LOW | IQ3_S | UD-Q4_K_S | 判定 |
|---|---|---|---|---|
| **n-max 3** | **74.4** | **63.2** | **59.3** | 🏆 三方共同最优 |
| n-max 2 | 66.7 | 61.0 | 54.7 | 慢 7–10% |
| n-max 4 | 启动崩（差 594 MiB） | 63.5（无收益） | 未测 | 不可用/无收益 |
| n-max 3 + p-min 0.75 | 64.6（接受率虚高至 85%） | — | — | 吞吐 −13% |

> 关键洞察：**n-max 4 的验证批次需要额外 ~594 MiB 显存**，在 24GB 卡的贴边配置下不可用；即使可用也无收益。

### 4️⃣ 代码质量：三方打平

**同题对决**（单文件贪吃蛇，5 项明确需求）：

| 维度 | IQ3_S | NVFP4-MID-HIGH | UD-Q4_K_S |
|---|---|---|---|
| 完整可运行 / 需求覆盖 / 防反向 / 食物避蛇身 | ✅ | ✅ | ✅ |
| **尾节排除**（高级细节） | ✗ | ✗ | **✅ 唯一** |
| 输出长度 | 3,985 字符 | 5,624 字符 | 4,164 字符 |
| 长文召回（12K/70% 与 150K/80% 深度） | ✅ | ✅ | ✅ |

### 5️⃣ 散热压测：12 分钟满载零衰减

![散热压测](assets/chart3-thermal-stress.svg)

| 指标 | 第 1 轮 | 第 100 轮 |
|---|---|---|
| 生成速度 | 78.7 tok/s | **83.7 tok/s（无衰减）** |
| GPU 温度 | 55 °C | 77 °C（稳定平台） |
| 功耗 | 132 W | 145 W |
| SM 时钟 | 1830 MHz | 1740 MHz（−5%） |

**结论：笔记本散热完全扛得住长时间 agent 负载。** 速度波动（±10%）来自 MTP 接受率的内容随机性，与温度无关。

---

## 🔍 筛选过程：53 → 1

![筛选漏斗](assets/chart4-selection-funnel.svg)

| 阶段 | 数量 | 说明 |
|---|---|---|
| 生态扫描 | **53** | 8 个来源家族（esatapedico NVFP4 系 9+2+8+10 档、unsloth UD 系 20 档、DASLab GSQ-RCO 3 档、QUASAR 等） |
| 硬约束排除 | ~15 | 剔除：装不下（ORIG 33GB / HIGHEST 23GB / Q8 系）、实验性修补（SSMFIX 8 档）、第三方融合权重（TURBO-Fable 10 档）、无 MTP 头（BUDGET 系）、过低精度（IQ1/IQ2） |
| 入围实测 | 4 | IQ3_S · NVFP4-MID-HIGH · NVFP4-LOW · UD-Q4_K_S |
| 深度对决 | 3 | IQ3_S · NVFP4-LOW · UD-Q4_K_S |
| **胜出** | **1** | **NVFP4-MTP-LOW** |

**排除的两个典型**（值得说明，因为它们在 HF 上很显眼）：
- **SSMFIX 系列**：社区对 8 个晚期 SSM 层 conv1d 权重做缩放修补（假说：修复长上下文退化）。证据混杂（TruthfulQA +6~8pp 但 CMMLU −1.8、无长上下文验证），README 自标 "EXPERIMENT, NOT AN IMPROVEMENT"。
- **TURBO-Fable-Cold-Fusion 系列**：第三方融合调教版（去审查 + 减思考），非官方权重，基准为作者自报口径。

---

## ⚙️ 八条可复用经验

1. **`reasoning_effort` 是必设项** — 默认档（xhigh）实测 8,000 token 全烧在思考里、正文零输出。必须传 `{"chat_template_kwargs":{"reasoning_effort":"medium"}}`。社区 4,800 任务测试：xhigh 比 low 多烧 7–11 倍 token，只换 0–4.7 分。**永远不要关闭 reasoning**（NVFP4 关闭时 HumanEval+ 从 90 掉到 13/30）。
2. **q4_0 系 KV 有隐藏性能悬崖** — 容量看似最优（262K），实际长输入慢 28×。
3. **MTP 在 dense 模型是纯收益** — n-max 3 提速 +73~79%（MoE 模型上"MTP 减速"的经验不适用）。
4. **接受率高 ≠ 速度快** — 速度 = 每 pass 成本 × 每 pass 收益；轻头部设计比高接受率更重要。
5. **NVFP4 的 FP4 加速只在 prefill 兑现** — decode 是带宽受限，看的是头部设计。
6. **引擎收益与量化类型强相关** — 升级后必须重测容量（NVFP4 +48K，K-quant 反而退化）。
7. **大上下文对 K-quant 不友好** — LOW 在 200K 的 prefill 仍 9.7 s；UD 从 15.2 s 掉到 19.9 s。
8. **prompt cache 是最大的免费加速** — 同一段 15.6K 输入：冷启 15 s → 命中缓存 **2.3 s（6.5×）**。agent 长会话保持前缀稳定即可持续受益。

---

## 🛠 工具箱

`scripts/` 三个启动脚本（PowerShell，路径已参数化，**保存为 UTF-8 with BOM**）：

| 脚本 | 用途 | 关键参数 |
|---|---|---|
| `start-nvfp4-low.ps1` | 🏆 日常主力 | `-c 192000` + q8_0 KV + MTP n-max 3 |
| `start-iq3s.ps1` | 超长材料备胎 | `-c 212000`（可到 240K） |
| `start-nvfp4-midhigh.ps1` | 对比组 | `-c 84000` |

**使用前修改脚本顶部两个变量**：`$ENGINE_DIR`（llama.cpp 目录）、`$MODELS_DIR`（模型目录）。

> ⚠️ 两个已知坑（脚本已规避）：
> 1. **脚本必须 UTF-8 with BOM** — 否则 PowerShell 5.1 按 ANSI 解码中文注释会报"字符串缺少终止符"。
> 2. **b10889+ 移除了 `--no-mmap`** — 替代参数是 `--load-mode none`。

**API 调用要求（三个配置通用）**：
```json
{ "messages": [], "chat_template_kwargs": { "reasoning_effort": "medium" } }
```
思考模式采样 `temp 1.0 / top_p 0.95 / top_k 20`；非思考模式 `temp 0.7 / top_p 0.80 / top_k 20`。

---

## ❓ FAQ

**Q：为什么不直接开 262K（模型原生最大值）？**
A：能开，但要牺牲速度——262K 只有 q4_0 系 KV 装得下，而它会让长输入慢 28 倍（内核回退）。192K + q8_0 是"容量 / 速度 / 质量"三者的最佳平衡点。

**Q：q8_0 KV 会损失质量吗？**
A：实测与业界共识均为"近无损"。本项目的长文召回测试（12K/70% 与 150K/80% 深度）在 q8_0 KV 下全部通过。

**Q：为什么不选更高精度的 Q6/Q8 量化？**
A：它们在 24GB 卡上装不下（Q8_0 为 27 GiB）。4bit 已经是这个硬件等级的质量天花板——社区受控测试显示 4bit 与 FP8 在任务级统计打平。

**Q：LOW 的头部精度（Q5_0 / IQ4_XS）比 MID-HIGH（全 Q8_0）低，质量真的没差吗？**
A：作者的 PPL 数据：LOW 3.2761 / MEDIUM 3.2858 / MID-HIGH 3.2903（差异在误差范围内，LOW 甚至略优）；实测代码对决三方打平。头部精度对 PPL 的影响远小于骨干。

**Q：桌面版 5090 会快多少？**
A：本测试的 145 W 功耗墙是 Laptop 专属限制；桌面 5090（575 W）在 prefill 上通常快 2–3 倍，decode 快 1.5–2 倍。但**容量结论（KV 量化、上下文上限）可直接参考**。

**Q：16GB 卡怎么办？**
A：换成更小的档（如 NVFP4 家族 COMPACT-LOW 15.2 GB，或无 MTP 的 BUDGET/STARVED 14.6 GB），KV 用 q8_0，上下文压到 ~96K；或用 IQ3_S（11.3 GB）配更大上下文。

**Q：模型支持图像输入吗？**
A：支持（原生 VLM）。需另下 `mmproj-BF16.gguf`（~0.87 GB）并加 `--mmproj`，额外占用约 1 GB 显存。

**Q：可以同时跑多个实例吗？**
A：24GB 装不下两个 27B 实例。建议单实例切换（三种配置脚本已备，切换约 30 秒）。

**Q：为什么不用 vLLM / SGLang？**
A：在这类 Blackwell Laptop 上，它们的显存管理与 GGUF 量化生态不如 llama.cpp 灵活；且社区 NVFP4 权重主要以 GGUF 形式分发。vLLM 更适合服务端多并发场景。

---

## 📚 参考资料与延伸阅读

**模型与量化**
- [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) — 基座模型（Apache-2.0）
- [esatapedico/Qwen3.8-27B-NVFP4-MTP-GGUF](https://huggingface.co/esatapedico/Qwen3.8-27B-NVFP4-MTP-GGUF) — 主力模型所在家族（9 档）
- [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) — UD 动态量化家族
- DASLab GSQ-RCO — HuggingFace 搜索 `DASLab Qwen3.8-27B GSQ-RCO`

**引擎**
- [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) — 需 Windows CUDA 包（主程序 + cudart 两个 zip 解压到同一目录）
- MTP 支持：启动加 `--spec-type draft-mtp`

**相关项目**
- [Qwen3.8-Flash-Next 177B 部署实录](https://github.com/lifeidle/qwen3.8-flash-next-5090-laptop-256k) — 同平台 MoE 大模型部署（三层内存分配 + 256K 上下文）

---

## 🔧 故障排查

| 症状 | 原因与解法 |
|---|---|
| 启动即退出、日志无内容 | 参数不兼容。新版引擎已移除 `--no-mmap`，用 `--load-mode none` |
| `failed to allocate buffer for kv cache` | 上下文超出显存。降 `-c` 或改用 q8_0 KV |
| 启动成功但推理卡死 | 显存贴边（余量 <200 MiB）。降 8–16K 上下文 |
| 生成全是思考、没有正文 | 未传 `reasoning_effort`；默认 xhigh 会烧光 token |
| 脚本报"字符串缺少终止符" | 脚本编码问题，另存为 UTF-8 with BOM |
| 输出乱码 | 请求体未按 UTF-8 编码（写 JSON 文件 + `curl --data-binary @file`） |

---

## 复现指南

```powershell
# 1. 引擎：下载 llama.cpp 官方 Windows CUDA 包（主程序 + cudart），解压到同一目录
# 2. 模型：从上方链接下载 GGUF（国内可用 hf-mirror.com 镜像）
# 3. 启动：修改脚本顶部两个路径变量后执行
.\scripts\start-nvfp4-low.ps1
# 4. 验证
curl http://127.0.0.1:8082/health     # 期望 {"status":"ok"}
```

**验收基线**：256-token 生成应达 **75–85 tok/s**（波动来自 MTP 接受率）；15.6K 输入 prefill 约 10 秒。

---

## 数据说明

- 所有速度为多轮采样值，±10% 波动属正常（MTP 接受率依赖生成内容）
- 容量为"启动成功 + 推理验证通过"的实测极值；"启动成功但推理崩溃"的情况已单独标注
- 测试时间：2026 年 9 月 · 平台：RTX 5090 Laptop 24GB · Windows 11 · llama.cpp b10840 / b10889
- 原始散热数据（100 轮）与全部速度数据见 [`data/`](./data)

## 许可

- 文档：CC BY 4.0 ｜ 脚本：MIT（详见 [LICENSE](./LICENSE)）
- 模型权重遵循上游许可（Qwen3.8-27B 系列为 Apache-2.0）

## 致谢

**Alibaba / Qwen 团队**（基座模型）· **unsloth**（NVFP4 量化方法、动态量化家族）· **DASLab**（GSQ-RCO 学术量化）· **esatapedico**（NVFP4-MTP GGUF 家族打包与透明模型卡）· **llama.cpp 社区**（引擎与 MTP 支持）
