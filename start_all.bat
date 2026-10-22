@echo off
title AICTE Platform Launcher
echo ========================================================
echo   Starting AICTE Application Platform on Localhost
echo ========================================================
echo.

echo [1/3] Starting Mock Issuing Authority APIs (Port 8001)...
start "AICTE Mock APIs (Port 8001)" cmd /k "cd mock-apis && py -m uvicorn main:app --port 8001 --host 0.0.0.0 --reload"

echo [2/3] Starting Backend FastAPI Server (Port 8000)...
start "AICTE Backend (Port 8000)" cmd /k "cd backend && py -m uvicorn app.main:app --port 8000 --host 0.0.0.0 --reload"

echo [3/3] Starting Frontend React/Vite Server (Port 3000)...
start "AICTE Frontend (Port 3000)" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo   All 3 services are launching in separate windows!
echo   - Frontend:  http://localhost:3000
echo   - Backend:   http://localhost:8000/docs
echo   - Mock APIs: http://localhost:8001/docs
echo ========================================================
echo.
pause
