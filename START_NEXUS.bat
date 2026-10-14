@echo off
cd /d "%~dp0"
echo ==================================================
echo    NEXUS AI Internal Audit Platform - LOCAL DEMO
echo ==================================================
echo Opening backend and frontend terminals...
start "NEXUS Backend" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0start_backend.ps1"
start "NEXUS Frontend" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0start_frontend.ps1"
echo.
echo WAIT until both windows report ready.
echo Then open: http://localhost:5173
start "" "http://localhost:5173"
pause
