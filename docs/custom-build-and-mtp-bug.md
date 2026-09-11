# 自编译实录：从编译成功到发现 MTP prefill bug

> 2026-09-12 完整记录：为什么要自己编译、踩了哪些坑、发现了什么、结论是什么。
> **上游 issue 已提交：ggml-org/llama.cpp#28790**

## 一、动机

目标：在官方构建之上叠加社区优化补丁（NVFP4 prefill 融合 / GDN 分块内核 / server 修复），把 24GB 的潜力再往上压 10~25%。

参考配方：`cdiamond/Qwen3.8-27B-iMatrix-NVFP4-MTP-GGUF` 附带 `recipe/llama.cpp-patches.md`（6 个 PR 的精确 commit hash）。

## 二、编译环境（Windows + Ninja + CUDA）

```
CMake 4.4.3 + Ninja 1.13.2 + MSVC 19.44 (VS 2022 BuildTools) + CUDA Toolkit 12.8
```

```powershell
cmake -G Ninja -B build `
  -DCMAKE_BUILD_TYPE=Release `
  -DGGML_CUDA=ON `
  -DCMAKE_CUDA_ARCHITECTURES=120 `
  -DGGML_CUDA_FA_QUANTS=all `
  -DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON
cmake --build build -j 12 --target llama-server llama-cli llama-quantize llama-bench
```

### 四个必踩的坑（及解法）

| # | 坑 | 现象 | 解法 |
|---|---|---|---|
| 1 | 环境变量 `Path`/`PATH` 重复键 | MSBuild 崩：`ArgumentException: 已添加项 "Path"/"PATH"` | 用 Python subprocess 构造干净环境（合并重复键）|
| 2 | 不要用 VS generator | CUDA 的 VS 集成常缺失（`No CUDA toolset found`）| 改用 **Ninja** generator |
| 3 | **PCH 导致 DLL 链接失败** | `exports.def : error LNK2001: 无法解析的外部符号 __`（master 新 PCH 特性 #28091）| 加 `-DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON` |
| 4 | Ninja 需要 rc.exe/mt.exe | `RC Pass 1 failed: no such file` | PATH 加 `Windows Kits\10\bin\<ver>\x64` |

另：MSVC 19.44 超出 CUDA 12.8 官方支持范围，需要 `-DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler`。

**编译成功**（185/185 目标，产物 ~67MB ggml-cuda.dll）。

## 三、★ 实测发现：MTP 让 prefill 慢 57 倍

编译成功后的 A/B（同模型、同参数、同机器）：

| 构建 | prefill（4800 token）| decode |
|---|---|---|
| **自编译 + MTP** | **32.7 tok/s** | 77.1 tok/s |
| **自编译，关 MTP** | **1867.5 tok/s** | 39.3 tok/s |
| 官方 b10917（Clang + CUDA 13.3）+ MTP | 1344.9 tok/s | 50.3 tok/s |
| 官方 b10889（Clang + CUDA 13.x）+ MTP | 1482 tok/s | 51.7 tok/s |

服务日志显示 prefill 期间是 **~30.6 ms/token**（等于 decode 速度）——text tokens 被逐个处理，批量并行失效。

### 排查过程（4 个假设逐一排除）

1. ❌ 参数语法（`-fa on` 正常、batch 默认值正常）
2. ❌ 补丁 #26001（回退后依旧慢）
3. ❌ KV 类型（f16 KV 同样慢）
4. ✅ **去掉 `--spec-type draft-mtp` → prefill 立刻恢复正常（1867 tok/s）**

### 官方对照实验

下载官方同日构建（b10917，Clang + CUDA 13.3）→ **完全正常**（1344.9 tok/s）。

**结论**：该 bug 是 **MSVC + CUDA 12.8 自编译组合特有**（官方构建的 Clang + CUDA 13.x 不受影响）。机制疑似与上游 #27306 同类（`common_speculative_process` 在每个 prefill ubatch 后跑 `llama_decode(ctx_dft)`），但我们的现象是静默降速而非崩溃。

## 四、最终结论

| 方案 | 判定 |
|---|---|
| 官方 b10917（最新）| ✅ 可用，但相比 b10889 无明显提升（prefill -9%、decode -3%，噪声范围内）|
| 官方 b10889（现役）| ✅ 推荐保持 |
| 自编译版 | ❌ 不推荐日常使用（MTP bug + 视觉路径慢：14.8s vs 6.1s）|

**给 Windows 自编译者的警告**：如果你用 MSVC + CUDA 12.8 自编译并开启 `--spec-type draft-mtp`，务必先测 prefill——你可能踩中同一个坑。官方 issue：**ggml-org/llama.cpp#28790**。

## 五、这次自编译的净值

- ➖ 预期收益（+10~25%）没有兑现（被 MTP bug 掩盖）
- ➕ 定位并复现了一个真实的上游 bug（含完整对照数据，已提交 issue）
- ➕ 证明了官方构建的工程质量（同样的代码，官方构建无此问题）
- ➕ 验证了「最新 ≠ 最好」：b10917 与 b10889 性能基本持平，升级无收益
