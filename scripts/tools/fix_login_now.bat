@echo off
echo ======================================
echo XU LY LOI DANG NHAP
echo ======================================
echo.

echo Buoc 1: Kiem tra admin...
python check_admin.py
echo.

pause

echo.
echo Buoc 2: Reset password admin...
python reset_admin_password.py
echo.

pause

echo.
echo Buoc 3: Test API...
python test_login_api.py
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
