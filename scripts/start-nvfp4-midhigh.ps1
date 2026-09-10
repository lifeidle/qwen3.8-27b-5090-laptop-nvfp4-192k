# ============================================================
# Qwen3.8-27B Comparison Config —— NVFP4-MTP-MID-HIGH
# Purpose: early benchmark comparison group (larger heads, smaller context)
# Measured (RTX 5090 Laptop 24GB, llama.cpp b10840):
#   Generation: 63.8 tok/s  (MTP n-max 3, acceptance 57.3%)
#   15.6K prompt prefill: 10.7 s  (dual-GPU split on older engine)
#   Max context: 88K (F16 KV) / 160K+ expected with q8_0 KV
# ============================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start-nvfp4-midhigh.ps1
#   then open http://127.0.0.1:8081
#
# NOTE: save this file as UTF-8 with BOM (PowerShell 5.1 requirement).
# ============================================================

$ErrorActionPreference = "Stop"

# ---- EDIT THESE TWO PATHS ----
$ENGINE_DIR = "D:\llama.cpp"
$MODELS_DIR = "D:\models"
# ------------------------------

$MODEL = Join-Path $MODELS_DIR "Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf"

# ---- Context tier ----
$CTX      = 84000    # Recommended for this tier
# $CTX = 88000       # Extreme
$KV_TYPES = @("--cache-type-k", "q8_0", "--cache-type-v", "q8_0")

if (-not (Test-Path "$ENGINE_DIR\llama-server.exe")) { throw "llama-server.exe not found in: $ENGINE_DIR" }
if (-not (Test-Path $MODEL)) { throw "Model not found: $MODEL" }

Write-Host "Model : NVFP4-MTP-MID-HIGH (15.75 GiB, comparison group)"
Write-Host "Config: ctx=$CTX  KV=q8_0  |  MTP: on (n-max 3)" -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:8081 after launch" -ForegroundColor Cyan
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
    --host 127.0.0.1 --port 8081
