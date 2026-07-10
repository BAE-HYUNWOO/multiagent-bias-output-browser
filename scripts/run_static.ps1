$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".\dist\index.html")) {
    throw "dist\index.html was not found. Apply the no-npm patch first."
}

if (-not (Test-Path ".\public\data\index.json")) {
    throw "UI data was not found. Run scripts\rebuild_data.ps1 first."
}

Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

Remove-Item ".\dist\data" -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item ".\public\data" ".\dist\data" -Recurse -Force

Remove-Item ".\dist\downloads" -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path ".\public\downloads") {
    Copy-Item ".\public\downloads" ".\dist\downloads" -Recurse -Force
}

$Port = 5173
$Url = "http://localhost:$Port"

Write-Host ""
Write-Host "Starting Multi-Agent Bias Browser..." -ForegroundColor Green
Write-Host "URL: $Url" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

Start-Process $Url

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m http.server $Port --directory ".\dist"
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m http.server $Port --directory ".\dist"
}
else {
    throw "Python 3 was not found."
}
