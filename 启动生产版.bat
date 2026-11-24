@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo   计件通 · 生产版（多人共享数据）
echo ============================================================
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没有找到 Python，请先安装 Python 3.11 或更高版本。
  echo 下载地址：https://www.python.org/downloads/
  echo 安装时请勾选 Add Python to PATH。
  pause
  exit /b 1
)
python -c "import fastapi, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo 首次运行，正在安装后端依赖...
  python -m pip install -r server\requirements.txt
  if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
  )
)
python -m server.main
if errorlevel 1 (
  echo.
  echo 生产版启动失败，请检查上面的错误信息。
  pause
)
