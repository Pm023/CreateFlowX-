@echo off
echo ===================================================
echo   Starting CreateFlowX (CFX) Frontend Server...
echo ===================================================
echo [INFO] Static files served on http://localhost:8080
python -m http.server 8080 --directory frontend
pause
