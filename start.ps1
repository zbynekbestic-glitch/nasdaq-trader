# NASDAQ Fundamental Trader - Startup Script
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting server..." -ForegroundColor Green
Write-Host "Open browser: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

Set-Location backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
