@echo off
chcp 65001 > nul
title KIEM TRA TIEN DO VA TRANG THAI HE THONG - THPT DIEU CAI
cd /d "%~dp0\.."

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
)

%PYTHON_EXEC% backend\system_check.py
echo.
pause
