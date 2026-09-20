@echo off
chcp 65001 > nul
title FRONTEND UI SERVER - THPT DIEU CAI (PORT 3000)
cd /d "%~dp0"
color 0E
echo =========================================================================
echo    PHÂN HỆ FRONTEND GIAO DIỆN - HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI
echo =========================================================================
echo.
echo [*] Khoi dong may chu phuc vu file tinh Frontend tai cong 3000...
echo [*] Giao dien tu dong ket noi toi Backend API tai http://localhost:8000
echo.
echo Truy cap cac trang giao dien:
echo  - Dashboard Diem Danh:  http://localhost:3000/index.html
echo  - Quan Ly Camera:       http://localhost:3000/cameras.html
echo  - Cau Hinh Vung ROI:    http://localhost:3000/roi-config.html
echo  - Bao Cao & Thong Ke:   http://localhost:3000/reports.html
echo.
echo Tu dong mo trinh duyet...
start http://localhost:3000/index.html

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
)
%PYTHON_EXEC% -m http.server 3000 -d frontend
pause
