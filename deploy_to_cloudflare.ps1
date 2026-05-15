# Hermes → Cloudflare Pages 部署輔助
# 由 Cursor 在終端機執行；使用本機 git + 可選 wrangler
# 密鑰僅從環境變數讀取，不寫入此檔

param(
    [switch]$DryRun,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

Write-Host "[Hermes] Cloudflare 部署流程" -ForegroundColor Cyan
Write-Host "  輸出目錄: dist/"
Write-Host ""

if (-not $SkipPush) {
    if (-not $env:GITHUB_TOKEN) {
        Write-Host "警告: GITHUB_TOKEN 未設定。若 Pages 綁 GitHub，請先 push。" -ForegroundColor Yellow
    }
    if ($DryRun) {
        Write-Host "[dry-run] python tools/test_github_push.py --dry-run"
    } else {
        python tools/test_github_push.py --push
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

$wrangler = Get-Command wrangler -ErrorAction SilentlyContinue
if ($wrangler) {
    Write-Host ""
    if ($DryRun) {
        Write-Host "[dry-run] wrangler pages deploy dist"
    } else {
        wrangler pages deploy dist
    }
} else {
    Write-Host ""
    Write-Host "未安裝 wrangler CLI。" -ForegroundColor Yellow
    Write-Host "若 Cloudflare Pages 已連 GitHub 倉庫，push 後會在儀表板自動建置。"
    Write-Host "請確認 Pages 專案「輸出目錄」設為 dist。"
}

Write-Host ""
Write-Host "[Hermes] 部署腳本結束。" -ForegroundColor Green
