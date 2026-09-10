# ============================================================
# Qwen3.8-27B Backup Config —— DASLab GSQ-RCO IQ3_S-MTP
# Purpose: ultra-long context (largest capacity, smallest footprint)
# Measured (RTX 5090 Laptop 24GB, llama.cpp b10889):
#   Generation: 64.4 tok/s  (MTP n-max 3)
#   15.6K prompt prefill: 14.9 s
#   Max context: 212K (up to 240K measured; 136K with F16 KV)
#   Quality: task-lossless (AIME/GPQA/LiveCodeBench match BF16)
# ============================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start-iq3s.ps1
#   then open http://127.0.0.1:8080
#
# IMPORTANT — API requirement:
#   Always pass reasoning_effort (medium or low); never disable reasoning.
#
# NOTE: save this file as UTF-8 with BOM (PowerShell 5.1 requirement).
# ============================================================

$ErrorActionPreference = "Stop"

# ---- EDIT THESE TWO PATHS ----
$ENGINE_DIR = "D:\llama.cpp"
$MODELS_DIR = "D:\models"
# ------------------------------

$MODEL = Join-Path $MODELS_DIR "Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp.gguf"

# ---- Context tier ----
$CTX      = 212000   # Recommended (240K measured max, tighter VRAM)
# $CTX = 240000      # Extreme
# $CTX = 136000      # Without KV quantization (F16 KV max)
$KV_TYPES = @("--cache-type-k", "q8_0", "--cache-type-v", "q8_0")

if (-not (Test-Path "$ENGINE_DIR\llama-server.exe")) { throw "llama-server.exe not found in: $ENGINE_DIR" }
if (-not (Test-Path $MODEL)) { throw "Model not found: $MODEL" }

Write-Host "Model : GSQ-RCO IQ3_S-MTP (11.29 GiB, task-lossless)"
Write-Host "Config: ctx=$CTX  KV=q8_0  |  MTP: on (n-max 3)" -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:8080 after launch" -ForegroundColor Cyan
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
    --host 127.0.0.1 --port 8080
