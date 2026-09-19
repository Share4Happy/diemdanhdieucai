@echo off
chcp 65001 > nul
title FRONTEND UI - THPT DIEU CAI (Port 3000)
cd /d "%~dp0"
echo =========================================================================
echo    FRONTEND CLIENT - HE THONG DIEM DANH AI THPT DIEU CAI
echo =========================================================================
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
)

echo [*] Đang khởi động Frontend Web Server tại http://localhost:3000 ...
echo [*] Kết nối tới Backend REST API tại http://localhost:8000
echo.
start http://localhost:3000
%PYTHON_EXEC% -m http.server 3000 -d frontend

pause
