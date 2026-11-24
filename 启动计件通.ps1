# 计件通 · PowerShell 启动脚本
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '  计件通 · 工厂个人计件统计' -ForegroundColor White
Write-Host '============================================================' -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host '[错误] 没有找到 Python，请先安装 Python 3.11+。' -ForegroundColor Red
    Write-Host '下载地址：https://www.python.org/downloads/'
    Read-Host '按回车退出'
    exit 1
}

& $python.Source 'start.py'
if ($LASTEXITCODE -ne 0) {
    Write-Host '启动失败，请检查错误信息。' -ForegroundColor Red
    Read-Host '按回车退出'
}
