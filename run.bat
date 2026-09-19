@echo off
chcp 65001 > nul
title HE THONG DIEM DANH TU DONG AI - THPT DIEU CAI
cd /d "%~dp0"
echo =========================================================================
echo    HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG CAMERA AI - THPT ĐIỀU CẢI
echo =========================================================================
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
    echo [*] Phat hien moi truong GPU (venv_cuda) - Kich hoat tang toc NVIDIA CUDA!
)

echo [1/3] Đang kiểm tra môi trường Python...
%PYTHON_EXEC% --version
if %errorlevel% neq 0 (
    echo [LỖI] Chưa tìm thấy Python. Vui lòng cài đặt Python 3.10+ và thử lại.
    pause
    exit /b
)

echo.
echo [2/3] Đang khởi tạo CSDL và chuẩn bị dữ liệu mẫu...
%PYTHON_EXEC% -c "from database.db_session import init_db; init_db()"
%PYTHON_EXEC% training\sample_extractor.py

echo.
echo [3/3] Đang khởi động Web Server và Bộ Lập Lịch 06:45 AM...
echo Truy cập Dashboard quản trị tại: http://localhost:8000
echo Truy cập Quản lý Camera tại: http://localhost:8000/cameras
echo Truy cập Cấu hình Không gian ROI tại: http://localhost:8000/roi-config
echo Truy cập Quản lý Báo cáo tại: http://localhost:8000/reports
echo.
%PYTHON_EXEC% app.py
pause
