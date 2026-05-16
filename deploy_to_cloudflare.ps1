# Hermers - Cloudflare Python Worker 部署（uvx + pywrangler）
# 需安裝：https://docs.astral.sh/uv/（內含 uvx）與 Node.js
# 使用 uvx 從 workers-py 拉取 pywrangler，無須事先安裝於 venv。
# 密鑰僅透過環境變數 / wrangler secret，勿寫入腳本。
#
# 部署模式（依目前 git 分支）：
#   - 與「生產預設分支」相同（預設讀 config/hermes.yaml → github.branch，多為 main）：
#       uvx --from workers-py pywrangler deploy
#   - 其餘分支（非生產）：
#       uvx --from workers-py pywrangler deploy --env preview

param(
    [switch]$DryRun,
    [switch]$SkipPush,
    # 若未指定，會從 config/hermes.yaml 的 github.branch 讀取；讀不到則為 main
    [string]$ProductionBranch = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-HermesProductionBranch {
    $path = Join-Path $PSScriptRoot "config\hermes.yaml"
    if (-not (Test-Path $path)) { return "main" }
    $raw = Get-Content $path -Raw -Encoding utf8
    if ($raw -match '(?ms)^github:\s*\r?\n(?:.*\r?\n)*?\s+branch:\s*(\S+)') {
        return $Matches[1].Trim().TrimEnd("'", '"')
    }
    return "main"
}

function Get-GitCurrentBranch {
    try {
        $out = git rev-parse --abbrev-ref HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return $out.Trim() }
    }
    catch { }
    return ""
}

function Build-PywranglerArgs {
    param(
        [bool]$IsProduction
    )
    $deployArgs = @("deploy")
    if (-not $IsProduction) {
        $deployArgs += @("--env", "preview")
    }
    return , $deployArgs
}

function Invoke-Pywrangler {
    param([string[]]$PyArgs)
    if (Get-Command uvx -ErrorAction SilentlyContinue) {
        & uvx --from workers-py pywrangler @PyArgs
    }
    else {
        & uv tool run --from workers-py pywrangler @PyArgs
    }
}

$prodBranch = if ($ProductionBranch) { $ProductionBranch.Trim() } else { Get-HermesProductionBranch }
$gitBranch = Get-GitCurrentBranch
$isProduction = ($gitBranch -ne "" -and $gitBranch -eq $prodBranch)

Write-Host "[Hermes] Cloudflare Python Worker deploy" -ForegroundColor Cyan
Write-Host "  生產分支（設定）: $prodBranch"
Write-Host "  目前 git 分支:    $(if ($gitBranch) { $gitBranch } else { '(無法偵測，將以 preview 部署)' })"
if ($isProduction) {
    Write-Host "  模式:            生產（無 --env preview）" -ForegroundColor Green
    Write-Host "  命令:            uvx --from workers-py pywrangler deploy" -ForegroundColor Green
}
else {
    Write-Host "  模式:            非生產（--env preview）" -ForegroundColor Yellow
    Write-Host "  命令:            uvx --from workers-py pywrangler deploy --env preview" -ForegroundColor Yellow
}
Write-Host "  入口:            main.py (WorkerEntrypoint)"
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
    Write-Host "找不到 uv（需含 uvx）。請安裝：https://docs.astral.sh/uv/" -ForegroundColor Yellow
    Write-Host "Windows 可選：winget install astral-sh.uv"
    exit 1
}

# pywrangler：若根目錄存在 requirements.txt 會直接失敗（與 pyproject.toml 互斥）
$reqPath = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqPath) {
    Remove-Item -Force $reqPath
    Write-Host "[Hermes] 已刪除本機 requirements.txt（避免與 pywrangler 衝突）" -ForegroundColor DarkYellow
}

$pyArgs = Build-PywranglerArgs -IsProduction $isProduction
$cmdLine = "uvx --from workers-py pywrangler $($pyArgs -join ' ')"
if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) {
    $cmdLine = "uv tool run --from workers-py pywrangler $($pyArgs -join ' ')"
}

Write-Host ""
if ($DryRun) {
    Write-Host "(dry-run) $cmdLine"
}
else {
    Invoke-Pywrangler -PyArgs $pyArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "[Hermes] Done." -ForegroundColor Green
