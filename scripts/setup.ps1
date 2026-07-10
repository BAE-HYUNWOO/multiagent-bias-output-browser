$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm을 찾을 수 없습니다. Node.js LTS를 설치한 뒤 다시 실행하세요."
}

npm install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Frontend package 설치 완료" -ForegroundColor Green
