@echo off
title BidGuard AI - Dev Launcher
echo ===================================================
echo Starting BidGuard AI Platform (SIH26100)
echo ===================================================

echo [1/2] Launching FastAPI Backend on Port 8001...
start "BidGuard Backend" cmd /k "cd backend && py -m uvicorn main:app --reload --port 8001"

echo [2/2] Launching TanStack Start Frontend...
start "BidGuard Frontend" cmd /k "npm run dev"

echo Waiting for services to initialize...
timeout /t 3 /nobreak >nul

echo Opening BidGuard AI Dashboard in Browser...
start http://localhost:3000

echo ===================================================
echo Both services are running in background windows.
echo Press any key to stop all services...
echo ===================================================
pause >nul

echo Stopping processes...
taskkill /fi "WINDOWTITLE eq BidGuard Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq BidGuard Frontend*" /f >nul 2>&1
echo Done.