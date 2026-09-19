@echo off
chcp 65001 >nul
title KIỂM THỬ ĐIỂM DANH AI - HÌNH 3 (THPT ĐIỀU CẢI)
color 0B
echo ===================================================================
echo   CHẠY KIỂM THỬ ĐIỂM DANH AI TRÊN HÌNH 3 - THPT ĐIỀU CẢI
echo ===================================================================
echo.
cd /d "%~dp0"
.\venv_cuda\Scripts\python test_hinh_3.py
echo.
pause
