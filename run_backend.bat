@echo off
echo ===================================================
echo   Starting CreateFlowX (CFX) Backend API Server...
echo ===================================================
cd backend

:: Verify virtual environment exists, if not create and install
if not exist .venv (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
    echo [INFO] Installing packages...
    .venv\Scripts\pip install -r requirements.txt
)

:: Start Uvicorn
echo [INFO] Running FastAPI with Uvicorn...
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
