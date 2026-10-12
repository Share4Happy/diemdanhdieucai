@echo off
chcp 65001 > nul
echo ======================================
echo XU LY LOI DANG NHAP
echo ======================================
echo.

cd /d "%~dp0\..\.."

echo Buoc 1: Kiem tra admin...
python tests\check_admin.py
echo.

pause

echo.
echo Buoc 2: Reset password admin...
python tests\reset_admin_password.py
echo.

pause

echo.
echo Buoc 3: Test API...
python tests\test_login_api.py
echo.

pause

echo.
echo ======================================
echo HOAN TAT!
echo ======================================
echo Bay gio thu dang nhap tai: http://localhost:8000
echo Email: admin@truongdieucai.edu.vn
echo Password: Admin@2025
echo.
pause
