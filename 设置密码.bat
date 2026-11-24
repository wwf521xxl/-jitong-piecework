@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo   计件通 · 修改管理员密码 / 员工 PIN
echo ============================================================
echo   管理员：输入 admin
echo   员工：输入工号 1-17
echo.
set /p ACCOUNT=请输入账号：
python tools\set_password.py "%ACCOUNT%"
echo.
pause
