@echo off
echo Starting AWS AutoNation...

:: Start backend (FastAPI on port 8000)
start "AWS AutoNation - Backend" cmd /k "cd /d %~dp0backend && python main.py"

:: Start frontend (Vite on port 5173)
start "AWS AutoNation - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both servers are starting:
echo   Backend  ^>  http://localhost:8000
echo   Frontend ^>  http://localhost:5173
echo.
