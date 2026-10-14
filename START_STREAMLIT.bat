@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m streamlit run streamlit_app.py
if errorlevel 1 goto error
exit /b 0
:error
echo Streamlit startup failed. Read the error above.
pause
exit /b 1
