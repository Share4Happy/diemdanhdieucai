@echo off
chcp 65001 > nul
title HE THONG DIEM DANH TU DONG AI - THPT DIEU CAI
echo =========================================================================
echo    HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG CAMERA AI - THPT ĐIỀU CẢI
echo =========================================================================
echo.
echo [1/3] Đang kiểm tra môi trường Python...
python --version
if %errorlevel% neq 0 (
    echo [LỖI] Chưa tìm thấy Python. Vui lòng cài đặt Python 3.10+ và thử lại.
    pause
    exit /b
)

echo.
echo [2/3] Đang khởi tạo CSDL và chuẩn bị dữ liệu mẫu...
python -c "from database.db_session import init_db; init_db()"
python sample_extractor.py

echo.
echo [3/3] Đang khởi động Web Server và Bộ Lập Lịch 06:45 AM...
echo Truy cập Dashboard quản trị tại: http://localhost:8000
echo Truy cập Quản lý Camera tại: http://localhost:8000/cameras
echo Truy cập Cấu hình Không gian ROI tại: http://localhost:8000/roi-config
echo Truy cập Quản lý Báo cáo tại: http://localhost:8000/reports
echo.
python app.py
pause
