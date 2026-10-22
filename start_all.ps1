Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Starting AICTE Application Platform on Localhost" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Write-Host "`n[1/3] Starting Mock APIs on port 8001..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\mock-apis'; py -m uvicorn main:app --port 8001 --host 0.0.0.0 --reload"

Write-Host "[2/3] Starting Backend API on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; py -m uvicorn app.main:app --port 8000 --host 0.0.0.0 --reload"

Write-Host "[3/3] Starting Frontend React/Vite on port 3000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host "`nAll 3 services launched successfully in dedicated windows!" -ForegroundColor Green
Write-Host "  - Frontend : http://localhost:3000" -ForegroundColor White
Write-Host "  - Backend  : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Mock APIs: http://localhost:8001/docs" -ForegroundColor White
