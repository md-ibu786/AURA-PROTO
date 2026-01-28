@echo off
echo Starting AURA-PROTO...

echo Stopping any existing Redis instances...
wsl sudo pkill redis-server 2>nul
timeout /t 2 /nobreak >nul

echo Starting Redis (WSL) on port 6379...
start "Redis Server" cmd /k "wsl sudo redis-server --bind 0.0.0.0 --daemonize no"

echo Waiting for Redis to be ready...
timeout /t 3 /nobreak >nul

REM Use localhost for Redis connection
set REDIS_HOST=localhost

echo Starting Backend API on port 8001...
start "AURA Backend" cmd /k "call ..\.venv\Scripts\activate && set REDIS_HOST=localhost && cd api && python -m uvicorn main:app --reload --port 8001"

echo Starting Celery Worker for KG Processing...
start "Celery Worker" cmd /k "call ..\.venv\Scripts\activate && set REDIS_HOST=localhost && cd api && celery -A tasks worker -l info -Q kg_processing -P solo"

echo Starting Frontend on port 5174...
start "AURA Frontend" cmd /k "cd frontend && npm run dev -- --port 5174"

echo.
echo ============================================
echo   All services started!
echo ============================================
echo   Redis:    WSL Redis on port 6379
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5174
echo   Celery:   Worker processing kg_processing queue
echo.
echo   Note: Close all windows to stop all services
echo ============================================
