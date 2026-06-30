@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
echo 📚 建筑书店 - 启动后端服务...
echo.
"C:\Users\53296\AppData\Local\Programs\Hermes One-Click\runtime\python\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8899 --log-level info
pause
