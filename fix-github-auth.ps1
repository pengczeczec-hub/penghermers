# 移除失效的 GITHUB_TOKEN，改由 gh auth 驅動 Hermes
$ErrorActionPreference = "SilentlyContinue"
Remove-Item Env:GITHUB_TOKEN -Force
Write-Host "已清除目前工作階段的 GITHUB_TOKEN。"
Write-Host "建議：編輯 .env，刪除或註解 GITHUB_TOKEN= 那一行。"
Write-Host ""
gh auth status
