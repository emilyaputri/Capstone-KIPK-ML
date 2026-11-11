# ============================================================
# KIPK-ML System - Local Runner
# Menjalankan Backend (FastAPI :8000) + Frontend (Vite :5173)
# Usage:  .\RUN.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " KIPK-ML System - Local Development" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Cek venv backend ---
$venvPython = Join-Path $backend "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[!] venv backend tidak ditemukan. Membuat..." -ForegroundColor Yellow
    Push-Location $backend
    python -m venv venv
    Pop-Location
}

# --- Cek dependencies backend ---
$hasFastapi = & $venvPython -c "import fastapi, uvicorn, pandas, openpyxl, xgboost, sklearn, imblearn, shap, joblib, multipart, sqlalchemy; print('ok')" 2>$null
if ($hasFastapi -ne "ok") {
    Write-Host "[*] Install dependencies backend..." -ForegroundColor Yellow
    Push-Location $backend
    & $venvPython -m pip install -r requirements.txt
    Pop-Location
}

# --- Cek dependencies frontend ---
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "[*] Install dependencies frontend..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install --no-audit --no-fund
    Pop-Location
}

Write-Host "[*] Starting Backend  -> http://localhost:8000  (docs: /docs)" -ForegroundColor Green
Write-Host "[*] Starting Frontend -> http://localhost:5173" -ForegroundColor Green
Write-Host "[*] Login: admin / admin123" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# --- Jalankan keduanya ---
$backendJob = Start-Job -ScriptBlock {
    param($py, $dir)
    Set-Location $dir
    & $py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
} -ArgumentList $venvPython, $backend

$frontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    npm run dev
} -ArgumentList $frontend

Write-Host "[*] Menunggu server siap..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 10
    Write-Host "[OK] Backend aktif (HTTP $($r.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "[!] Backend belum merespon: $_" -ForegroundColor Red
}

try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:5173/" -UseBasicParsing -TimeoutSec 15
    Write-Host "[OK] Frontend aktif (HTTP $($r2.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "[!] Frontend belum merespon: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Tekan Ctrl+C untuk menghentikan semua proses." -ForegroundColor Cyan

try {
    # Tampilkan log realtime dari kedua job
    while ($true) {
        Receive-Job -Job $frontendJob -ErrorAction SilentlyContinue
        Receive-Job -Job $backendJob -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "`n[*] Menghentikan server..." -ForegroundColor Yellow
    Stop-Job -Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob, $frontendJob -Force -ErrorAction SilentlyContinue
}
