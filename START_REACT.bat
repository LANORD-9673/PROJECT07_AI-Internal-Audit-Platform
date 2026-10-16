@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
 echo Can cai Python 3.12 va them vao PATH.
 pause
 exit /b 1
)
if not exist ".venv-react\Scripts\python.exe" python -m venv .venv-react
call .venv-react\Scripts\activate.bat
python -m pip install -r backend\requirements.txt
if errorlevel 1 goto fail
if not exist frontend\dist\index.html (
 echo Thieu frontend\dist. Chay npm ci va npm run build trong frontend.
 goto fail
)
if not exist .env copy .env.example .env >nul
echo NEXUS React: http://localhost:8000
python -m uvicorn cloud:app --app-dir backend --host 127.0.0.1 --port 8000 --env-file .env
:fail
pause
