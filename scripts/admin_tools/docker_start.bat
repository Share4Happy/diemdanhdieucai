@echo off
chcp 65001 > nul
title KHOI DONG DOCKER - THPT DIEU CAI
cd /d "%~dp0\.."
color 0A
echo =========================================================================
echo    HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI - KHỞI ĐỘNG CỤM DOCKER
echo    FRONTEND (NGINX: PORT 3000) ^| BACKEND (FASTAPI: PORT 8000)
echo =========================================================================
echo.

docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [CANH BAO] Docker Desktop chua duoc bat hoac daemon chua san sang!
    echo Vui long mo ung dung Docker Desktop tren Windows va thu lai.
    echo.
    pause
    exit /b 1
)

echo [*] Dang build va khoi dong cac container (Backend + Frontend)...
docker compose up -d --build

if %errorlevel% equ 0 (
    echo.
    echo =========================================================================
    echo [THANH CONG] Cac container da san sang hoat dong:
    echo  - Giao dien Frontend:     http://localhost:3000
    echo  - Backend API:            http://localhost:8000
    echo  - API Swagger Docs:       http://localhost:8000/docs
    echo =========================================================================
    echo.
    echo Dang mo trinh duyet...
    start http://localhost:3000
) else (
    echo [THAT BAI] Khong the khoi dong container. Vui long kiem tra log Docker.
)

pause
