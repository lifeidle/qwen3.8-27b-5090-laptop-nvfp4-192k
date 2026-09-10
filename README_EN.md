# Qwen3.8-27B on a Single 24GB GPU: A Complete Quantization & Tuning Study

> **A systematic selection from 50+ community quantization variants, optimized layer-by-layer to the hardware limit**
>
> Platform: RTX 5090 Laptop 24GB · Windows 11 · llama.cpp
> TL;DR: **NVFP4-MTP-LOW + 192K context + q8_0 KV + MTP n-max 3 + llama.cpp b10889 = 79.6 tok/s**

[中文版 →](./README.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Test Platform](#2-test-platform)
3. [Candidate Landscape & Selection Funnel](#3-candidate-landscape--selection-funnel)
4. [Methodology](#4-methodology)
5. [Results](#5-results)
6. [Key Findings](#6-key-findings-eight-reusable-lessons)
7. [Final Recommended Configuration](#7-final-recommended-configuration)
8. [Toolbox](#8-toolbox)
9. [Reproduction Guide](#9-reproduction-guide)

---

## 1. Overview

**Background**: Qwen3.8-27B is a 27.8B dense multimodal model (Gated DeltaNet + Gated Attention hybrid, 262,144 native context, embedded MTP speculative head, Apache-2.0). Its BF16 weights total ~55.6 GB — far beyond any consumer single GPU — so deployment on a 24GB laptop requires community quantization.

**Problem**: Within weeks of release, the ecosystem produced **50+ quantization variants** (multiple families × precision tiers) with contradictory quality/performance claims and no cross-platform comparison on the same hardware.

**What this project does**:
- Systematically surveys all major quantization families (53 variants)
- Benchmarks the finalists under unified methodology (speed / capacity / quality)
- Optimizes the winner layer-by-layer (KV quantization, MTP parameters, context ceiling, engine version, thermals)
- Provides a reproducible final configuration and tooling

**Outcome**: Found the dual-optimal (speed + capacity) solution under a "no quality loss" constraint on this machine, and verified its stability under sustained load.

---

## 2. Test Platform

| Item | Specification |
|---|---|
| **GPU** | NVIDIA GeForce RTX 5090 Laptop GPU, **24 GB GDDR7**, Blackwell (sm_120) |
| CPU | Intel Core Ultra 9 275HX (24 threads) |
| RAM | 64 GB DDR5 |
| OS | Windows 11 |
| **Inference Engine** | llama.cpp (two builds tested) |
| Build A | **b10840** (unsloth build, MSVC 19.44, CUDA 12.8) |
| Build B | **b10889** (official build, Clang 20.1.8, CUDA 13.3) |
| Desktop VRAM baseline | ~500–680 MiB (without inference server) |
| Model storage | NVMe SSD (`--load-mode none`, no mmap) |

> ⚠️ The Laptop 5090 has a ~145–150 W power ceiling (far below the desktop part). All numbers here are measured on this platform and are **not directly comparable to desktop-GPU results**.

---

## 3. Candidate Landscape & Selection Funnel

### 3.1 Ecosystem Survey (53 variants)

| Source family | Tiers | Size range | Notes |
|---|---|---|---|
| **esatapedico NVFP4-MTP** | 9 | 14.9 – 33.1 GB | All-NVFP4 backbone family: ORIG / VERY-LOW / COMPACT-LOW / LOW / MEDIUM / MID-HIGH / HIGH / VERY-HIGH / HIGHEST |
| esatapedico NVFP4-BUDGET | 2 | 14.6 – 14.7 GB | MTP head stripped, 16GB-card oriented (BUDGET / STARVED) — **excluded** |
| esatapedico SSMFIX | 8 | 14.9 – 23.2 GB | Experimental community patch (rescales 8 late-layer SSM conv1d weights); mixed evidence — **excluded** |
| esatapedico TURBO-Fable series | 10 | 15.2 – 21.3 GB | Third-party fused tune (DavidAU TURBO Cold-Fusion, decensored); non-official weights — **excluded** |
| **unsloth UD family** | 20 | 5.8 – 29.3 GiB | Full gradient from UD-IQ1_M to UD-Q8_K_XL |
| **DASLab GSQ-RCO** | 3 | 11.5 – 13+ GB | Academic second-order quantization (Gumbel-Softmax / rate-constrained), incl. IQ3_S / IQ4_XS / IQ4_NL |
| QUASAR NVFP4 (QAD) | 1+ | ~17 GB | Quantization-aware-distillation NVFP4 |
| Other community conversions | several | — | e.g., multiple SSMFIX conversions |

**Total: 53 variants entered the initial screening.**

### 3.2 Selection Funnel

```
53 quantization variants (ecosystem survey)
        │
        │  Stage 1 — Hard constraints
        │    ✗ Too large (ORIG 33GB / HIGHEST 23GB / Q8 series)
        │    ✗ Experimental patches (8 SSMFIX tiers)
        │    ✗ Third-party fused weights (10 TURBO-Fable tiers)
        │    ✗ No MTP head (BUDGET / STARVED)
        │    ✗ Too low precision (IQ1/IQ2 — unusable for agents)
        ▼
   ~15 structurally qualified candidates
        │
        │  Stage 2 — Paper precision + community data review
        ▼
   4 finalists benchmarked: DASLab IQ3_S · NVFP4-MID-HIGH · NVFP4-LOW · unsloth UD-Q4_K_S
        │
        │  Stage 3 — Unified head-to-head benchmarking
        ▼
   3 deep-dive contenders: IQ3_S · NVFP4-LOW · UD-Q4_K_S
        │
        │  Stage 4 — Speed / capacity / quality / stability
        ▼
   🏆 Winner: NVFP4-MTP-LOW
```

### 3.3 Finalist Profiles

| | DASLab GSQ-RCO IQ3_S-MTP | **esatapedico NVFP4-MTP-LOW** | unsloth UD-Q4_K_S |
|---|---|---|---|
| Size | 11.29 GiB | 14.47 GiB | 14.30 GiB |
| Method | GSQ-RCO mixed precision (~3.5 bpw avg) | All-NVFP4 backbone + light heads (Q5_0 / IQ4_XS) | Dynamic Q4_K_S (~4.4 bpw) |
| Validation | ✅ Task-lossless (AIME/GPQA/LCB match BF16) | Community controlled test: all 4-bit quants tie FP8 | No semantic benchmarks |
| MTP head | Embedded | Embedded | Embedded |

---

## 4. Methodology

All tests use llama.cpp's `/completion` and `/v1/chat/completions` endpoints plus server-side timing logs:

| # | Test | Method |
|---|---|---|
| 1 | **KV VRAM calibration** | Two-point difference method: run ctx=8192 and ctx=32768 instances, read `nvidia-smi` deltas → per-token KV cost (weights and fixed overhead factored out) |
| 2 | **Context ceiling scan** | Stepwise launches (F16 / q8_0 / q4_0 / mixed KV); exact threshold located via `cudaMalloc` failure sizes |
| 3 | **Generation speed** | Fixed 256-token prompt (temp 0.7), multi-run averaging; records `predicted_per_second` + MTP draft acceptance |
| 4 | **Long-prompt processing** | 15,614-token Chinese document (needle-in-haystack construction); end-to-end time + `prompt eval` throughput |
| 5 | **MTP parameter sweep** | n-max ∈ {2,3,4,5} × p-min ∈ {none, 0.75}, all combinations |
| 6 | **Code quality** | Same-prompt duel: single-file Snake game (5 explicit requirements); checks completeness, feature coverage, hidden bugs |
| 7 | **Long-context recall** | Needle tests at 12K tokens (needle at 70% depth) and 150K tokens (80% depth) |
| 8 | **Engine comparison** | Same model/params on b10840 vs b10889 |
| 9 | **Thermal stress** | 12 minutes of continuous 512-token generation; per-round tok/s + temp + power + SM clock |
| 10 | **Quality baseline** | `reasoning_effort` comparison (default xhigh vs medium) |

**Discipline**: every comparison holds model / context / KV type / MTP params / engine constant; speed tests are multi-run; VRAM is confirmed clean (<700 MiB baseline) after each server switch.

---

## 5. Results

### 5.1 Context Capacity: KV Quantization Is the Key

**Physical ceiling** (IQ3_S example; two-point method gives ~65 KiB per token @ F16):

| KV type | IQ3_S max context | Capacity gain vs F16 |
|---|---|---|
| F16 (default) | 136K | — |
| **q8_0 (K/V)** | **212K** | **+56%** |
| K q8_0 + V q4_0 | 262K (full) | +93% |
| q4_0 (K/V) | 262K (full) | +93% |

**⚠️ Major finding — q4_0-class KV has a hidden performance cliff**: it reaches the full 262K, but long-prompt processing collapses:

| Config | 15.6K prompt latency | Verdict |
|---|---|---|
| 32K + F16 | 13.6 s | ✅ Baseline |
| 136K + F16 | 15.2 s | ✅ No penalty |
| **200K + q8_0** | **15.1 s** | ✅ **No penalty** |
| 262K + q4_0-class | **~420 s (never finished)** | ❌ **28× slower** (attention kernel fallback; throughput decays from 286 to 29 tok/s) |

**Conclusion**: **q8_0 is the sweet spot for KV quantization** (zero speed penalty, near-lossless, +56% capacity). q4_0-class KV is effectively unusable for long prompts.

### 5.2 Three-Way Speed Duel (same conditions: own max context + q8_0 KV + MTP n-max 3)

**Engine b10840 (older)**:

| Model | Config | Gen avg | 15.6K prefill | Acceptance |
|---|---|---|---|---|
| **NVFP4-LOW** | 152K | **74.7 tok/s** | **10.1 s** | 63% |
| IQ3_S | 212K | 61.9 tok/s | 15.5 s | 65% |
| UD-Q4_K_S | 152K | 58.3 tok/s | 15.2 s | 73% (highest) |

**Engine b10889 (newer)**:

| Model | Config | Gen avg | 15.6K prefill | Max context |
|---|---|---|---|---|
| **NVFP4-LOW** | **192K (recommended) / 200K (max)** | **79.6 tok/s** | **9.7 s** | 200K |
| IQ3_S | 212K (up to 240K) | 64.4 tok/s | 14.9 s | 240K |
| UD-Q4_K_S | 200K | 51.7 tok/s | 19.9 s | 200K |

**Why the differences**:
- **Why NVFP4-LOW is fastest**: its head design (Q5_0 output + IQ4_XS MTP head) minimizes read cost on every MTP verification/draft pass — the community found the same pattern on a desktop RTX 5090 (LOW is the family's throughput champion).
- **Why UD has the highest acceptance (73%) yet is slowest**: K-quant's per-pass verification cost is the heaviest (dequant overhead) with no FP4 acceleration — net effect: last place.
- **NVFP4's FP4 tensor-core advantage only materializes in prefill**: both NVFP4 models prefill in ~10 s, K-quants take 15–20 s.

### 5.3 Quality Verification: A Three-Way Tie

**Code quality** (identical Snake-game prompt):

| Dimension | IQ3_S | NVFP4-MID-HIGH | UD-Q4_K_S |
|---|---|---|---|
| Complete & runnable | ✅ | ✅ | ✅ |
| All 5 requirements | ✅ | ✅ | ✅ |
| Anti-reverse buffering | ✅ | ✅ | ✅ |
| Food avoids snake body | ✅ | ✅ | ✅ |
| **Tail exclusion** (advanced detail) | ✗ | ✗ | **✅ (only one)** |
| Output length | 3,985 chars | 5,624 chars | 4,164 chars |

**Long-context recall**: all three passed (needles accurately retrieved at 12K/70% and 150K/80% depth).

**Conclusion: the three quants tie on quality.** UD-Q4_K_S is the most rigorous on classic details (a small manifestation of its 4.4 bpw paper advantage), but not enough to form a generational gap.

### 5.4 MTP Parameter Sweep: Current Settings Are Already Optimal

| Config | LOW avg | IQ3_S | UD | Verdict |
|---|---|---|---|---|
| **n-max 3** | **74.4** | **63.2** | **59.3** | 🏆 Best for all three |
| n-max 2 | 66.7 | 61.0 | 54.7 | 7–10% slower |
| n-max 4 | launch crash (short 594 MiB) | 63.5 (@200K, no gain) | untested | Unusable / no gain |
| n-max 3 + p-min 0.75 | 64.6 (acceptance inflated to 85%) | — | — | Throughput −13% |

**Key insight**: **n-max 4 needs ~594 MiB extra VRAM** for its verification batch — unusable at the edge of a 24GB card, and even when usable, it brings no gain. **High acceptance ≠ high speed** (p-min 0.75 raised acceptance from 63% to 85% while throughput dropped 13%).

### 5.5 Engine Version Comparison (b10840 → b10889)

| Model | Old engine | New engine | Delta |
|---|---|---|---|
| **NVFP4-LOW** | 74.7 / 152K / 10.1s | **79.6 / 200K / 9.7s** | **+6.6% speed, +48K capacity** |
| IQ3_S | 61.9 / 212K / 15.5s | 64.4 / 212K / 14.9s | +4% |
| UD-Q4_K_S | 58.3 / 152K / 15.2s | 51.7 / 200K / 19.9s | **−11% (no benefit)** |

**Conclusion**: the newer engine's optimizations **mainly benefit NVFP4 models** (FP4 path + better VRAM management — the latter directly gave LOW +48K usable context); K-quants saw no benefit.

**⚠️ Migration note**: the newer build removed `--no-mmap`; the replacement is **`--load-mode none`**.

### 5.6 Thermal Stress Test (12 min / 100 rounds sustained load)

| Metric | First round | Last round | Verdict |
|---|---|---|---|
| Generation speed | 78.7 tok/s | 83.7 tok/s | **Zero decay** |
| GPU temp | 55 °C | 77 °C (stable plateau) | Safe |
| Power | 132 W | 145 W | Stable |
| SM clock | 1830 MHz | 1740 MHz | −5% (minor) |

**Conclusion: laptop thermals easily handle sustained agent workloads** — no systematic speed decay, no thermal throttling concerns.

---

## 6. Key Findings (Eight Reusable Lessons)

1. **`reasoning_effort` is mandatory**: Qwen3.8-27B's default effort (xhigh) burns astonishingly many tokens — measured **8,000 tokens of pure thinking with zero output**. You must pass `{"chat_template_kwargs":{"reasoning_effort":"medium"}}` (medium converges in 11 s with complete code). A community 4,800-task controlled test confirms: xhigh burns 7–11× more tokens than low for 0–4.7 points. **Never disable reasoning** (NVFP4 collapses to 13/30 on HumanEval+ with reasoning off).

2. **q4_0-class KV has a hidden performance cliff**: capacity looks best (262K), but an attention kernel fallback makes long prompts **28× slower**. **q8_0 KV is the sweet spot** (zero penalty + near-lossless + +56% capacity).

3. **MTP is pure win on dense models**: n-max 3 measured **+79% (IQ3_S) / +73% (NVFP4)**, acceptance 60–80%. This contradicts the "MTP slows MoE down" experience (MoE's expert-read penalty doesn't exist on dense). But n-max 4+ needs ~594 MiB extra VRAM — unsuitable for small-VRAM cards.

4. **High MTP acceptance ≠ high speed**: speed = per-pass cost × per-pass yield. A light-head design (LOW's Q5_0 lm_head + IQ4_XS MTP head) makes every pass cheaper, so it wins even without the top acceptance rate. p-min filtering raises acceptance while lowering throughput.

5. **NVFP4's FP4 acceleration only materializes in prefill**: decode is bandwidth-bound — NVFP4 models are larger files (14.5 GiB vs IQ3_S's 11.3 GiB) and should theoretically be slower at decode; yet the light-head NVFP4-LOW is fastest in practice. **On prefill, NVFP4 leads across the board (10 s vs 15 s class)**.

6. **New-engine gains depend heavily on quantization type**: b10840→b10889 gave NVFP4 +6.6% speed and +48K capacity (VRAM management), while K-quant lost 11%. **Always re-measure capacity after an engine upgrade**.

7. **Large contexts are unfriendly to K-quants**: NVFP4-LOW's prefill at 200K is still 9.7 s (same as at 152K), while UD-Q4_K_S degrades from 15.2 s to 19.9 s at 200K. KV quantization + large allocation hits K-quant's dequant path harder.

8. **Prompt cache is the biggest free speedup**: the same 15.6K input takes 15 s cold and **2.3 s warm (6.5×)**. In long agent sessions, keep the conversation prefix stable (don't repeatedly edit system prompts) to keep hitting the cache.

---

## 7. Final Recommended Configuration

### 🏆 Primary (daily coding agent)

```
Model:  Qwen3.8-27B-NVFP4-MTP-LOW.gguf (14.47 GiB)
Engine: llama.cpp b10889 (or newer official builds)
Flags:  -ngl 99 -fa on -fit off -c 192000 --cache-type-k q8_0 --cache-type-v q8_0
        --load-mode none --jinja --spec-type draft-mtp --spec-draft-n-max 3
Perf:   79.6 tok/s generation · 9.7 s for 15.6K input · max context 200K (192K recommended)
Quality: indistinguishable from BF16 in community controlled tests (all 4-bit quants tie FP8)
```

### Backup (ultra-long context)

```
Model:  DASLab GSQ-RCO IQ3_S-MTP (11.29 GiB)
Flags:  same as above, -c 212000 (up to 240K)
Perf:   64.4 tok/s generation · 14.9 s for 15.6K input
Why:    Task-lossless academic validation; smallest disk footprint
```

### Universal API requirement (all three)

```json
{
  "messages": [...],
  "chat_template_kwargs": { "reasoning_effort": "medium" }
}
```
Thinking mode sampling: `temp 1.0 / top_p 0.95 / top_k 20`; non-thinking: `temp 0.7 / top_p 0.80 / top_k 20`.

---

## 8. Toolbox

`scripts/` contains three PowerShell launchers used throughout this study (paths parameterized):

| Script | Purpose |
|---|---|
| `start-nvfp4-low.ps1` | 🏆 Primary config (NVFP4-LOW @192K + q8_0 + MTP) |
| `start-iq3s.ps1` | Backup config (IQ3_S @212K) |
| `start-nvfp4-midhigh.ps1` | Early comparison group (NVFP4-MID-HIGH @84K) |

**Before use**: edit the two variables at the top → `$ENGINE_DIR` (llama.cpp directory) and `$MODELS_DIR` (model directory).

> ⚠️ Two known pitfalls (already handled in the scripts):
> 1. **Script files must be saved as UTF-8 with BOM** — otherwise PowerShell 5.1 decodes Chinese comments as ANSI and produces syntax errors ("string terminator missing").
> 2. **b10889+ does not support `--no-mmap`** — use `--load-mode none` instead.

---

## 9. Reproduction Guide

```powershell
# 1. Get the engine (either build)
#    Official prebuilt: https://github.com/ggml-org/llama.cpp/releases
#    Download both the Windows CUDA main package and the cudart package; unzip into one folder

# 2. Get the model
#    NVFP4-LOW: https://huggingface.co/esatapedico/Qwen3.8-27B-NVFP4-MTP-GGUF
#    IQ3_S:     search HuggingFace for "DASLab Qwen3.8-27B GSQ-RCO"
#    (hf-mirror.com works as a mirror in restricted networks)

# 3. Launch (primary config)
.\scripts\start-nvfp4-low.ps1
# → open http://127.0.0.1:8082

# 4. Verify
curl http://127.0.0.1:8082/health
# Expected: {"status":"ok"}
```

**Acceptance baseline** (for comparison): after health check passes, 256-token generation should reach **75–85 tok/s** (variance comes from content-dependent MTP acceptance); a 15.6K-token input prefills in ~10 s.

---

## Data Notes

- All speeds are multi-run sampled; ±10% variance is normal (MTP acceptance depends on generated content)
- Capacity figures are measured extremes with successful inference; "launch OK but inference crash" cases are labeled separately
- Testing conducted September 2026; all model and engine versions are stated inline

## License

- This document: CC BY 4.0
- Tool scripts: MIT
- Model weights follow their respective upstream licenses (Qwen3.8-27B family is Apache-2.0)

## Acknowledgements

- **Alibaba / Qwen team** — the Qwen3.8-27B base model
- **unsloth** — NVFP4 quantization method, dynamic quant family, prebuilt llama.cpp
- **DASLab** — GSQ-RCO academic quantization
- **esatapedico** — NVFP4-MTP GGUF family packaging and transparent model cards
- **llama.cpp community** — the inference engine and MTP support

---

*Tested September 2026 · Platform: RTX 5090 Laptop 24GB · Windows 11*
