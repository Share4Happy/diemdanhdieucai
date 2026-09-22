@echo off
echo ======================================
echo CAI DAT PYTHON-DOTENV
echo ======================================
echo.

echo Dang cai dat python-dotenv...
pip install python-dotenv

echo.
echo ======================================
echo Kiem tra cai dat...
python -c "from dotenv import load_dotenv; print('OK: python-dotenv da cai thanh cong!')"

echo.
echo ======================================
echo Test load .env file...
python test_env_loading.py

echo.
pause
