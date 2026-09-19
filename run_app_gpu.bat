@echo off
chcp 65001 >nul
echo ===================================================================
echo   HE THONG DIEM DANH AI THPT DIEU CAI (GPU NVIDIA RTX 3050 ACCELERATED)
echo ===================================================================
echo.
cd /d "%~dp0"
echo [*] Khoi dong Web Server FastAPI voi ho tro GPU CUDA...
.\venv_cuda\Scripts\python app.py
pause
