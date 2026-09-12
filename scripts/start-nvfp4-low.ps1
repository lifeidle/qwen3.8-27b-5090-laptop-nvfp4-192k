# ============================================================
# 千问3.8-27B 主力启动脚本 —— NVFP4-MTP LOW（速度冠军档）
# 实测（新引擎 b10889 + 192K + q8_0 KV + MTP n-max 3）：
#   生成 79.6 tok/s | 15.6K 长输入 9.7 秒 | 质量与 BF16 统计打平
#   开视觉（mmproj）后：推荐 150K——细扫实测 86.2 tok/s（152K 起滑坡，详见 README）
# ============================================================
# 用法：双击同目录的  启动-主力.bat
#       或 powershell -ExecutionPolicy Bypass -File 本脚本
# 启动后（网页版）http://127.0.0.1:8082 ｜ API 端点 /v1/chat/completions
#
# ★★ API 调用必读 ★★
#   1) reasoning_effort 必须显式传参，可选：xhigh / medium / low
#      默认 xhigh 实测 84 秒仍未答完（6000 token 全烧在思考）→ 强烈建议 medium 或 low
#   2) 如果用 API 且不需要思考 → "enable_thinking": false
#      {"messages":[...], "chat_template_kwargs":{"reasoning_effort":"medium"}}
#   3) 图像输入：content 数组里放 {"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}
# ============================================================

$ErrorActionPreference = "Stop"

# ---- 引擎与模型（★ 改成你自己的路径）----
$LLAMA = "D:\llama.cpp"                  # llama.cpp Windows CUDA 包解压目录（建议 b10889 或更新）
$MODELS_DIR = "D:\models\Qwen3.8-27B"    # GGUF 模型所在目录
$MODEL = Join-Path $MODELS_DIR "Qwen3.8-27B-NVFP4-MTP-LOW.gguf"

# ---- 视觉（多模态）开关：占用额外显存 ----
$ENABLE_VISION = $true
# 用 Q8_0 量化版视觉组件（600 MB，比 BF16 版省 288 MB；实测识别质量相同）
# 如需最高画质可换回 mmproj-BF16.gguf，但上下文要相应降到 ~144K
$MMPROJ = Join-Path $MODELS_DIR "mmproj-Q8_0.gguf"

# ---- 上下文档位（按是否开视觉自动选择）----
if ($ENABLE_VISION) {
    $CTX = 150000     # ⭐ 开视觉的最优档（细扫实测）：86.2 tok/s + prefill 1899
                      #    150K 是甜蜜点峰值；152K 掉到 63.6，160K 掉到 37.2 —— 非线性滑坡
} else {
    $CTX = 192000     # 不开视觉：192K 实测 79.6 tok/s（极限 200K）
}
# 其他参考档：不开视觉且用 F16 KV → 96K；极限 200K（余量很小，桌面别开太多程序）

$KV_TYPES = @("--cache-type-k", "q8_0", "--cache-type-v", "q8_0")
$visionArgs = @()
if ($ENABLE_VISION) {
    if (-not (Test-Path $MMPROJ)) { throw "找不到视觉组件: $MMPROJ（可从 HF 的 esatapedico/Qwen3.8-27B-NVFP4-MTP-GGUF 下载 mmproj-BF16.gguf）" }
    $visionArgs = @("--mmproj", $MMPROJ)
}

if (-not (Test-Path "$LLAMA\llama-server.exe")) { throw "找不到 llama-server.exe: $LLAMA" }
if (-not (Test-Path $MODEL)) { throw "找不到模型: $MODEL" }

Write-Host ""
Write-Host "  模型 : NVFP4-MTP LOW（14.47 GiB，速度冠军档）"
Write-Host "  视觉 : $(if ($ENABLE_VISION) { '开启（mmproj-BF16）' } else { '关闭' })"
Write-Host "  配置 : ctx=$CTX  KV=q8_0  MTP=n-max 3" -ForegroundColor Cyan
Write-Host "  访问 : http://127.0.0.1:8082   （API: /v1/chat/completions）" -ForegroundColor Cyan
Write-Host ""

Set-Location $LLAMA
& "$LLAMA\llama-server.exe" `
    -m $MODEL `
    @visionArgs `
    -ngl 99 `
    -fa on `
    -fit off `
    -c $CTX `
    -np 1 `
    --ctx-checkpoints 4 `
    --load-mode none `
    --jinja `
    @KV_TYPES `
    --spec-type draft-mtp `
    --spec-draft-n-max 3 `
    --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.0 `
    --host 127.0.0.1 --port 8082
