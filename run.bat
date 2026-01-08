@echo off
echo Starting AURA-PROTO...

echo Starting Backend on port 8001...
start "AURA Backend" cmd /k "call .venv\Scripts\activate && cd api && python -m uvicorn main:app --reload --port 8001"

echo Starting Frontend on port 5174...
start "AURA Frontend" cmd /k "cd frontend && npm run dev -- --port 5174"

echo Done.
