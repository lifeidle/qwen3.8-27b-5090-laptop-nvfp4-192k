# ============================================================
# Qwen3.8-27B Primary Config —— NVFP4-MTP-LOW (speed champion)
# Measured (RTX 5090 Laptop 24GB, llama.cpp b10889):
#   Generation: 79.6 tok/s  (MTP n-max 3)
#   15.6K prompt prefill: 9.7 s
#   Max context: 200K (192K recommended for safety margin)
#   Quality: ties FP8 in community controlled tests (4,800 tasks)
# ============================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start-nvfp4-low.ps1
#   then open http://127.0.0.1:8082
#
# IMPORTANT — API requirement:
#   Always pass reasoning_effort (medium or low); never disable reasoning.
#   {"messages":[...], "chat_template_kwargs":{"reasoning_effort":"medium"}}
#   Thinking mode sampling: temp 1.0 / top_p 0.95 / top_k 20
#
# NOTE: save this file as UTF-8 with BOM (PowerShell 5.1 requirement).
# ============================================================

$ErrorActionPreference = "Stop"

# ---- EDIT THESE TWO PATHS ----
$ENGINE_DIR = "D:\llama.cpp"                     # llama.cpp directory (contains llama-server.exe)
$MODELS_DIR = "D:\models" # directory containing the .gguf files
# ------------------------------

$MODEL = Join-Path $MODELS_DIR "Qwen3.8-27B-NVFP4-MTP-LOW.gguf"

# ---- Context tier ----
$CTX      = 192000   # Recommended (200K measured max; 192K leaves ~500 MiB headroom)
# $CTX = 200000      # Extreme (measured OK, very tight VRAM)
# $CTX = 96000       # Without KV quantization (F16 KV max)
$KV_TYPES = @("--cache-type-k", "q8_0", "--cache-type-v", "q8_0")

if (-not (Test-Path "$ENGINE_DIR\llama-server.exe")) { throw "llama-server.exe not found in: $ENGINE_DIR" }
if (-not (Test-Path $MODEL)) { throw "Model not found: $MODEL" }

Write-Host "Model : NVFP4-MTP-LOW (14.47 GiB, speed champion)"
Write-Host "Config: ctx=$CTX  KV=q8_0  |  MTP: on (n-max 3)" -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:8082 after launch" -ForegroundColor Cyan
Write-Host ""

Set-Location $ENGINE_DIR
& "$ENGINE_DIR\llama-server.exe" `
    -m $MODEL `
    -ngl 99 `
    -fa on `
    -fit off `
    -c $CTX `
    -np 1 `
    --load-mode none `
    --jinja `
    @KV_TYPES `
    --spec-type draft-mtp `
    --spec-draft-n-max 3 `
    --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.0 `
    --host 127.0.0.1 --port 8082
