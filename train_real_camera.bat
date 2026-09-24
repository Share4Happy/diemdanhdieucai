@echo off
chcp 65001 > nul
title HUAN LUYEN AI CAMERA THUC TE - NVIDIA GEFORCE RTX 3050 [THPT DIEU CAI]
color 0B
echo ===================================================================
echo   HUAN LUYEN YOLO VOI DU LIEU CAMERA THUC TE - THPT DIEU CAI
echo   Dataset: studenthead1.v1-1.yolo26 (Camera 1 ^& Camera 2)
echo   Hardware: NVIDIA GeForce RTX 3050 Laptop GPU (CUDA 12.1)
echo ===================================================================
echo.
cd /d "%~dp0"
echo [*] Thu muc lam viec: %CD%
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=.\venv_cuda\Scripts\python.exe
)

echo [*] Dang bat dau qua trinh Fine-tuning [30 epochs, batch 4, imgsz 640]...
echo.
%PYTHON_EXEC% training\train_real_camera.py --epochs 30 --batch 4 --imgsz 640 --device 0

echo.
echo ===================================================================
echo [HOAN TAT] File trong so toi uu nhat da duoc luu tai:
echo  - models\classroom_real_camera_best.pt
echo  - models\classroom_best.pt
echo ===================================================================
pause
