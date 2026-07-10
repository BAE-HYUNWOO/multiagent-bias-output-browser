$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

powershell -ExecutionPolicy Bypass -File ".\scripts\rebuild_data.ps1"
powershell -ExecutionPolicy Bypass -File ".\scripts\run_static.ps1"
