@echo off
chcp 65001 >nul
cd /d "%~dp0backend"

echo ┌──────────────────────────────────┐
echo │  📚 建筑书店管理系统              │
echo │  厦门建筑书店独立站后端           │
echo └──────────────────────────────────┘
echo.
echo 🚀 正在启动后端服务...
echo.

echo 如果启动失败，请先关闭占用8899端口的程序。
echo.

:: 先杀掉已占用的端口进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8899 .* LISTENING"') do (
    echo 🔪 关闭旧进程 PID: %%a
    taskkill /f /pid %%a >nul 2>&1
    timeout /t 1 >nul
)
echo.

start "" "http://localhost:8899/admin/admin.html"

"C:\Users\53296\AppData\Local\Programs\Hermes One-Click\runtime\python\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8899 --log-level info

echo.
echo ⚠️ 服务已停止。按任意键关闭窗口...
pause >nul
