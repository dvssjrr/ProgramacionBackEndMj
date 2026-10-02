@echo off
cd /d "%~dp0"

if not exist ".\env\Scripts\python.exe" (
    echo No se encontro el entorno virtual en .\env
    echo Crea el entorno virtual o revisa la ruta.
    pause
    exit /b 1
)

netstat -ano | findstr :8000 >nul
if not errorlevel 1 (
    echo La pagina ya esta ejecutandose en http://localhost:8000
    echo Si quieres reiniciarla, cierra el proceso actual o usa otro puerto.
    pause
    exit /b 0
)

call .\env\Scripts\activate.bat
python manage.py migrate
python manage.py seed_demo_users
python manage.py runserver 0.0.0.0:8000
