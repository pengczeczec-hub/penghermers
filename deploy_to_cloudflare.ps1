# Hermes - Cloudflare deploy (uvx + pywrangler)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[Hermes] 正在檢查環境與依賴項..." -ForegroundColor Cyan

if (-not (Test-Path "pyproject.toml")) {
    Write-Error "找不到 pyproject.toml，請確認執行路徑是否正確。"
}

if (Test-Path "requirements.txt") {
    Remove-Item -Force "requirements.txt"
    Write-Host "[Hermes] 已刪除 requirements.txt（避免與 pywrangler 衝突）" -ForegroundColor DarkYellow
}

if (-not (Get-Command uvx -ErrorAction SilentlyContinue) -and -not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "找不到 uv/uvx。請安裝：https://docs.astral.sh/uv/  或 winget install astral-sh.uv" -ForegroundColor Red
    exit 1
}

Write-Host "[Hermes] 正在將代碼推送到 GitHub..." -ForegroundColor Cyan
git add .
git commit -m "chore: sync and deploy via local script" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Hermes] 無新變更可提交，略過 commit。" -ForegroundColor DarkGray
}
git push origin main
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[Hermes] 正在同步 Python 依賴 (uv sync)..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[Hermes] 正在執行 Cloudflare 部署指令..." -ForegroundColor Cyan
if (Get-Command uvx -ErrorAction SilentlyContinue) {
    uvx --from workers-py pywrangler deploy
} else {
    uv tool run --from workers-py pywrangler deploy
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[Hermes] Done. 部署完成！" -ForegroundColor Green