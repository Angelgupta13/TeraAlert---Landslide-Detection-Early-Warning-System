@echo off
echo Starting Web Frontend...
cd frontend
python -m http.server 3000
pause
