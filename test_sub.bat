@echo off
chcp 65001 > nul
title HE THONG DIEM DANH TU DONG AI - THPT DIEU CAI
cd /d "%~dp0"
echo =========================================================================
echo    HE THONG DIEM DANH HOC SINH TU DONG BANG CAMERA AI - THPT DIEU CAI
echo    (MOHINH AI: YOLO26m Native NMS-Free ^& STAL Small Object Detection)
echo =========================================================================
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=venv_cuda\Scripts\python.exe
    echo [*] Phat hien moi truong GPU (venv_cuda) - Kich hoat tang toc NVIDIA CUDA!
