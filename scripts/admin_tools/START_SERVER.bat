@echo off
chcp 65001 > nul
cls
echo.
echo ========================================================================
echo         KHOI DONG HE THONG DIEM DANH AI - THPT DIEU CAI
echo ========================================================================
echo.
echo Dashboard:        http://localhost:8000/
echo Camera Manager:   http://localhost:8000/cameras
echo ROI Config:       http://localhost:8000/roi-config
echo Reports:          http://localhost:8000/reports
echo Modal Demo (NEW): http://localhost:8000/modal-demo
echo.
echo Dang khoi dong server...
echo.

cd /d "%~dp0"
python app.py

pause
