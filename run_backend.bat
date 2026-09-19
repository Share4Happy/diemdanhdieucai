@echo off
chcp 65001 > nul
title BACKEND REST API - THPT DIEU CAI (FastAPI)
cd /d "%~dp0"
echo =========================================================================
echo    BACKEND REST API - HE THONG DIEM DANH AI THPT DIEU CAI
echo =========================================================================
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
    echo [*] Sử dụng môi trường GPU CUDA: venv_cuda
)

echo [*] Khởi tạo Database nếu chưa tồn tại...
%PYTHON_EXEC% -c "from database.db_session import init_db; init_db()"

echo.
echo [*] Đang khởi động Backend REST API Server tại http://localhost:8000 ...
echo [*] Swagger API Docs: http://localhost:8000/docs
echo [*] ReDoc API Docs:   http://localhost:8000/redoc
echo.

%PYTHON_EXEC% -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
