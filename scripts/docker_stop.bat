@echo off
chcp 65001 > nul
title DUNG DOCKER - THPT DIEU CAI
cd /d "%~dp0\.."
color 0C
echo =========================================================================
echo    HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI - DỪNG CỤM DOCKER
echo =========================================================================
echo.
echo [*] Dang dung va go bo cac container...
docker compose down

echo.
echo [*] Cac container da duoc dung an toan.
pause
