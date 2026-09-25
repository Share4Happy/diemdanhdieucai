@echo off
chcp 65001 > nul
title HE THONG DIEM DANH TU DONG AI - THPT DIEU CAI
cd /d "%~dp0"
echo =========================================================================
echo    HE THONG DIEM DANH HOC SINH TU DONG BANG CAMERA AI - THPT DIEU CAI
echo    MOHINH AI: YOLO26m Native NMS-Free and STAL Small Object Detection
echo =========================================================================
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\activate.bat" (
    call "venv_cuda\Scripts\activate.bat"
    set PYTHON_EXEC=python
    echo [*] Phat hien va kich hoat moi truong GPU [venv_cuda] - NVIDIA CUDA RTX 3050!
) else if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
    echo [*] Phat hien moi truong GPU [venv_cuda] - Kich hoat tang toc NVIDIA CUDA!
)

echo [1/3] Dang kiem tra moi truong Python...
%PYTHON_EXEC% --version
if errorlevel 1 (
    echo [LOI] Chua tim thay Python. Vui long kiem tra lai moi truong Python.
    pause
    exit /b
)

echo.
echo [2/3] Dang khoi tao CSDL va chuan bi du lieu mau...
%PYTHON_EXEC% -c "from database.db_session import init_db; init_db()"
%PYTHON_EXEC% training\sample_extractor.py

echo.
echo [3/3] Dang khoi dong Web Server va Bo Lap Lich 06:45 AM...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
echo Truy cap Dashboard quan tri tai: http://localhost:8000
echo Truy cap Quan ly Camera tai: http://localhost:8000/cameras
echo Truy cap Cau hinh Khong gian ROI tai: http://localhost:8000/roi-config
echo Truy cap Quan ly Bao cao tai: http://localhost:8000/reports
echo.
%PYTHON_EXEC% app.py
pause
