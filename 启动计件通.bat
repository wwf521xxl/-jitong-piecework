@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo   计件通 · 工厂个人计件统计
echo ============================================================
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没有找到 Python，请先安装 Python 3.11+。
  echo 下载地址：https://www.python.org/downloads/
  pause
  exit /b 1
)
python start.py
if errorlevel 1 (
  echo.
  echo 启动失败。请检查上面的错误信息，或确认 8787 端口是否被占用。
  pause
)
