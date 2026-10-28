@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python manage.py runserver
pause
