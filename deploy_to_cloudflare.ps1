# Hermes - Cloudflare Pages deploy helper
# Run from Cursor terminal. Secrets from env only.

param(
    [switch]$DryRun,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[Hermes] Cloudflare deploy" -ForegroundColor Cyan
Write-Host "  output: dist/"
Write-Host ""

if (-not $SkipPush) {
    if (-not $env:GITHUB_TOKEN) {
        Write-Host "WARN: GITHUB_TOKEN not set. Push may fail." -ForegroundColor Yellow
    }
    if ($DryRun) {
        Write-Host '(dry-run) python tools/test_github_push.py --dry-run'
    }
    else {
        python tools/test_github_push.py --push
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

$wrangler = Get-Command wrangler -ErrorAction SilentlyContinue
if ($wrangler) {
    Write-Host ""
    if ($DryRun) {
        Write-Host '(dry-run) wrangler pages deploy dist'
    }
    else {
        wrangler pages deploy dist
    }
}
else {
    Write-Host ""
    Write-Host "wrangler CLI not found." -ForegroundColor Yellow
    Write-Host "If Pages is linked to GitHub, push triggers build in dashboard."
    Write-Host "Set build output directory to dist."
}

Write-Host ""
Write-Host "[Hermes] Done." -ForegroundColor Green
