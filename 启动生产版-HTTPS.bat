@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo   计件通 · 生产版（本地 HTTPS，手机可扫码）
echo ============================================================
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没有找到 Python，请先安装 Python 3.11+。
  pause
  exit /b 1
)
python -c "import fastapi, uvicorn, cryptography" >nul 2>nul
if errorlevel 1 (
  echo 首次运行，正在安装后端依赖...
  python -m pip install -r server\requirements.txt
  if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
  )
)
if not exist "certs\server.crt" (
  echo 首次运行，正在生成本地 HTTPS 证书...
  python tools\make_local_cert.py
  if errorlevel 1 (
    echo [错误] 证书生成失败。
    pause
    exit /b 1
  )
)
if not exist "certs\jitong-local-ca.cer" (
  echo [错误] 缺少手机根证书 certs\jitong-local-ca.cer。
  pause
  exit /b 1
)
certutil -user -addstore -f Root "certs\jitong-local-ca.crt" >nul 2>&1
echo.
for /f %%i in ('python "%~dp0tools\show_lan_ip.py"') do set "LAN_IP=%%i"
if "%LAN_IP%"=="" set "LAN_IP=服务器IP"
echo 手机证书下载：http://%LAN_IP%:8788/
echo 手机扫码地址：https://%LAN_IP%:8443
echo 如果服务器 IP 变了，请重新运行：python tools\make_local_cert.py --force
echo.
start "计件通证书下载" /min python -m http.server 8788 --directory "%~dp0certs\public"
set "JITONG_PORT=8443"
set "JITONG_SSL_CERT=%CD%\certs\server.crt"
set "JITONG_SSL_KEY=%CD%\certs\server.key"
set "JITONG_COOKIE_SECURE=1"
set "JITONG_OPEN_BROWSER=1"
python -m server.main
if errorlevel 1 (
  echo.
  echo HTTPS 生产版启动失败，请检查上面的错误信息。
  pause
)
