# Windows 自编译完整配方（CUDA 13.3 + MSVC + Blackwell/sm_120）

> 2026-09 全程实战验证。目标：从源码构建 llama.cpp，性能 **≥ 官方构建**。
> 实测结果：自编译版在 RTX 5090 Laptop 24GB 上跑 Qwen3.8-27B NVFP4，**decode 75.3 tok/s / prefill 23K=1405 tok/s / 视觉 4.5s**——综合优于官方 b10889。
> 相关上游 issue（发现了 nvcc 12.8 的性能 bug）：[ggml-org/llama.cpp#28790](https://github.com/ggml-org/llama.cpp/issues/28790)

## 一、工具链（★ 硬红线）

| 组件 | 版本 | 说明 |
|---|---|---|
| MSVC | **19.44**（VS 2022 17.14 BuildTools）| 官方 Windows 构建同款 |
| **CUDA Toolkit** | **13.3.33** | ★★ 必须与 MSVC 19.44 配对（官方构建同款组合）|
| CMake | 4.4+ |  |
| Ninja | 1.13+ | 不要用 VS generator（CUDA 集成常缺失）|

### ⚠️ 最重要的坑：nvcc 12.8 + MSVC 19.44 = 性能灾难

实测（同一模型、同一参数）：

| 编译工具链 | prefill（MTP 开启）| 结论 |
|---|---|---|
| nvcc 12.8 + MSVC 19.44（强行 `-allow-unsupported-compiler`）| **32.7 tok/s** | ❌ 慢 57 倍 |
| nvcc 13.3 + MSVC 19.44（官方配对）| **1675.7 tok/s** | ✅ 正常 |

- CUDA 12.8 **官方不支持** MSVC 19.44 → 强编出来的 CUDA kernel 在 **MTP prefill 路径**生成问题代码
- **只影响 prefill**（decode 一直正常）→ 极难察觉
- 完整定位过程（DLL 互换法）见 issue #28790

### ⚠️ CUDA 13 的新目录布局

**CUDA 13.x 把运行时 DLL 移到了 `bin\x64\`**（以前在 `bin\`，`bin\` 现在只放工具）：

```
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin\x64\
    ├── cudart64_13.dll      (0.5 MB)
    ├── cublas64_13.dll      (49.5 MB)
    └── cublasLt64_13.dll    (439 MB)
```

**如果编译时用了 `-DGGML_BACKEND_DL=ON`（后端动态加载，官方配置）**：运行时找不到这 3 个 DLL → `ggml-cuda.dll` **静默加载失败** → **回退 CPU 推理**（表现为 ~3 tok/s、CPU 满载、GPU 空闲 7%）。

**解法**：把上面 3 个 DLL 复制到 `llama-server.exe` 旁边。

## 二、编译命令（完整）

```powershell
# 1. 克隆（或指定你的分支/补丁）
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp

# 2. 配置（Ninja + MSVC + CUDA 13.3 + sm_120）
cmake -G Ninja -B build `
  -DCMAKE_BUILD_TYPE=Release `
  -DGGML_CUDA=ON `
  -DCMAKE_CUDA_ARCHITECTURES=120 `
  -DGGML_CUDA_FA_QUANTS=all `
  -DGGML_BACKEND_DL=ON `
  -DGGML_CPU_ALL_VARIANTS=ON `
  -DGGML_NATIVE=OFF `
  -DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON `
  -DCMAKE_CUDA_COMPILER="C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin\nvcc.exe"

# 3. 编译
cmake --build build -j 8

# 4. 补 CUDA 运行时 DLL（★ 关键一步）
$bin = "build\bin"
$cu  = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin\x64"
Copy-Item "$cu\cudart64_13.dll","$cu\cublas64_13.dll","$cu\cublasLt64_13.dll" $bin
```

**验证**（应显示两位数以上 tok/s）：

```powershell
.\build\bin\llama-server.exe -m 你的模型.gguf -ngl 99 -fa on -c 4096 --port 8080
curl.exe -X POST http://127.0.0.1:8080/completion -H "Content-Type: application/json" -d "{\"prompt\":\"hi\",\"n_predict\":64}"
# → timings.predicted_per_second 应该是 70-90（不是 3）
```

## 三、四个坑及解法（按踩坑顺序）

| # | 坑 | 症状 | 解法 |
|---|---|---|---|
| 1 | `Path`/`PATH` 环境变量重复键 | MSBuild 崩：`ArgumentException: 已添加项 "Path"` | 在干净的 Python subprocess 环境里调 CMake（合并重复键）|
| 2 | 不要用 VS generator | `No CUDA toolset found` | 用 Ninja |
| 3 | **PCH 导致 DLL 链接失败** | `exports.def : error LNK2001: 无法解析的外部符号 __` | `-DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON` |
| 4 | **CUDA 13 新布局 + DL 模式静默回退 CPU** | 3 tok/s、CPU 满载、GPU 7% | 复制 3 个 DLL 到程序目录（见上）|

## 四、性能基线（RTX 5090 Laptop 24GB + Qwen3.8-27B NVFP4-LOW）

| 配置 | decode | prefill（4K）| 视觉识别 |
|---|---|---|---|
| 官方 b10889 | 51.7 | 1482 | 6.1 s |
| 官方 b10917 | 50.3 | 1344.9 | — |
| **自编译（nvcc 13.3 + 官方配置）** | **75.3–88.7** | **1675.7** | **4.5 s** |

运行参数：`-ngl 99 -fa on -c 150000 --cache-type-k q8_0 --cache-type-v q8_0 --ctx-checkpoints 4 --spec-type draft-mtp --spec-draft-n-max 3 --load-mode none --jinja`
