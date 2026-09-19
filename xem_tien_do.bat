@echo off
chcp 65001 >nul
title TIẾN ĐỘ TRAINING YOLOv8 - NVIDIA RTX 3050 (THPT ĐIỀU CẢI)
color 0B
cd /d "%~dp0"
.\venv_cuda\Scripts\python monitor_training.py
pause
