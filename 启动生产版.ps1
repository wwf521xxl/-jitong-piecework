# 计件通 · 生产版启动脚本
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '  计件通 · 生产版（多人共享数据）' -ForegroundColor White
Write-Host '============================================================' -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host '[错误] 没有找到 Python，请先安装 Python 3.11+。' -ForegroundColor Red
    Read-Host '按回车退出'
    exit 1
}

& $python.Source -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host '首次运行，正在安装后端依赖...' -ForegroundColor Yellow
    & $python.Source -m pip install -r server\requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[错误] 依赖安装失败，请检查网络。' -ForegroundColor Red
        Read-Host '按回车退出'
        exit 1
    }
}

& $python.Source -m server.main
if ($LASTEXITCODE -ne 0) {
    Write-Host '生产版启动失败，请检查错误信息。' -ForegroundColor Red
    Read-Host '按回车退出'
}
