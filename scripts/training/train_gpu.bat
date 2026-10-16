@echo off
chcp 65001 > nul
title HUAN LUYEN AI DIEM DANH - NVIDIA GEFORCE RTX 3050 [THPT DIEU CAI]
color 0A
echo ===================================================================
echo   HUAN LUYEN YOLO26m BANG GPU NVIDIA GEFORCE RTX 3050 - THPT DIEU CAI
echo   Kien truc YOLO26 Native NMS-Free and STAL Small Object Detection
echo ===================================================================
echo.
cd /d "%~dp0\.."
echo [*] Thu muc lam viec: %CD%
echo [*] Kich hoat moi truong GPU CUDA PyTorch 2.5.1 [RTX 3050]...
echo.

set PYTHON_EXEC=python
if exist "venv_cuda\Scripts\python.exe" (
    set PYTHON_EXEC=.\venv_cuda\Scripts\python.exe
)

if exist "runs\train\dieucai_classroom\weights\last.pt" (
    echo [THONG BAO] Phat hien checkpoint do dang tu luot huan luyen truoc.
    echo Dang tu dong TIEP TUC huan luyen [Resume] de khong bi phi cong suc...
    echo.
    %PYTHON_EXEC% training\train_yolo.py --resume --device 0
) else (
    echo Dang bat dau luot huan luyen moi YOLO26m [25 epochs]...
    echo.
    %PYTHON_EXEC% training\train_yolo.py --model models\yolo26m.pt --epochs 25 --imgsz 640 --batch 4 --device 0
)

echo.
echo ===================================================================
echo [HOAN TAT] Qua trinh huan luyen da ket thuc thanh cong!
echo Trong so toi uu nhat da duoc luu tai models/classroom_yolo26m_best.pt
echo ===================================================================
pause
