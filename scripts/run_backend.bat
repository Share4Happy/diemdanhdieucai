@echo off
chcp 65001 > nul
title BACKEND API SERVER - THPT DIEU CAI [PORT 8000]
cd /d "%~dp0\.."
color 0B
echo =========================================================================
echo    PHAN HE BACKEND REST API - HE THONG DIEM DANH AI THPT DIEU CAI
echo    MOHINH AI: YOLO26m
echo =========================================================================
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\activate.bat" (
    call "venv_cuda\Scripts\activate.bat"
    set PYTHON_EXEC=python
    echo [*] Phat hien va kich hoat moi truong GPU [venv_cuda] - NVIDIA CUDA RTX 3050!
) else if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
    echo [*] Kich hoat moi truong GPU [venv_cuda]
)

echo [*] Kiem tra ket noi CSDL va khoi tao schema...
%PYTHON_EXEC% -c "from database.db_session import init_db; init_db()"

echo.
echo [*] Dang khoi dong Backend FastAPI Server tai cong 8000 [Auto-Reload ON]...
echo  - API Swagger UI:       http://localhost:8000/docs
echo  - API ReDoc:            http://localhost:8000/redoc
echo  - He thong HealthCheck: http://localhost:8000/api/health
echo.
echo Nhan Ctrl + C de dung may chu.
echo =========================================================================
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
%PYTHON_EXEC% -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
