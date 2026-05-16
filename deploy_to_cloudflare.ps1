# Hermers - Cloudflare Python Worker 部署（uv + pywrangler）
# 需安裝：https://docs.astral.sh/uv/ 與 Node.js（pywrangler 依賴）
# 密鑰僅透過環境變數 / wrangler secret，勿寫入腳本。

param(
    [switch]$DryRun,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[Hermes] Cloudflare Python Worker deploy" -ForegroundColor Cyan
Write-Host "  command: uv run pywrangler deploy"
Write-Host "  entry:   main.py (WorkerEntrypoint)"
Write-Host ""

if (-not $SkipPush) {
    if ($env:GITHUB_TOKEN) {
        Write-Host "Note: GITHUB_TOKEN in env; Hermes falls back to gh if invalid." -ForegroundColor DarkGray
    }
    if ($DryRun) {
        Write-Host '(dry-run) python tools/test_github_push.py --dry-run'
    }
    else {
        python tools/test_github_push.py --push
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host ""
    Write-Host "找不到 uv。請安裝：https://docs.astral.sh/uv/" -ForegroundColor Yellow
    Write-Host "Windows 可選：winget install astral-sh.uv"
    exit 1
}

Write-Host ""
if ($DryRun) {
    Write-Host '(dry-run) uv sync --extra cloudflare'
    Write-Host '(dry-run) uv run pywrangler deploy'
}
else {
    uv sync --extra cloudflare
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    uv run pywrangler deploy
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "[Hermes] Done." -ForegroundColor Green
