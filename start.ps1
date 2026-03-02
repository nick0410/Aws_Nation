Write-Host "Starting AWS AutoNation..."

# Start backend (FastAPI on port 8000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python main.py" -WindowStyle Normal

# Start frontend (Vite on port 5173)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "Both servers are starting:"
Write-Host "  Backend  >  http://localhost:8000"
Write-Host "  Frontend >  http://localhost:5173"
