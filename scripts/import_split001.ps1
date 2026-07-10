param(
    [string]$ExperimentRoot = "C:\Users\samsung-user\Desktop\multiagent_bias_experiment",
    [string]$Split = "001"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SourceOutput = Join-Path $ExperimentRoot "outputs\runs\split$Split"
$SourceSplit = Join-Path $ExperimentRoot "data\splits\bbq_cbbq_kobbq_pair20_split$Split.csv"
$TargetOutput = Join-Path $ProjectRoot "source_data\outputs\split$Split"
$TargetSplits = Join-Path $ProjectRoot "source_data\splits"

if (-not (Test-Path $SourceOutput)) {
    throw "실험 output 폴더를 찾을 수 없습니다: $SourceOutput"
}
if (-not (Test-Path $SourceSplit)) {
    throw "split CSV를 찾을 수 없습니다: $SourceSplit"
}

New-Item -ItemType Directory -Path (Split-Path -Parent $TargetOutput) -Force | Out-Null
New-Item -ItemType Directory -Path $TargetSplits -Force | Out-Null

if (Test-Path $TargetOutput) {
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Backup = "${TargetOutput}_backup_$Timestamp"
    Move-Item $TargetOutput $Backup
    Write-Host "기존 복사본 백업: $Backup" -ForegroundColor Yellow
}

Write-Host "Copying output folder..." -ForegroundColor Cyan
Copy-Item $SourceOutput $TargetOutput -Recurse -Force

Write-Host "Copying split CSV..." -ForegroundColor Cyan
Copy-Item $SourceSplit (Join-Path $TargetSplits (Split-Path $SourceSplit -Leaf)) -Force

Write-Host ""
Write-Host "복사 완료" -ForegroundColor Green
Write-Host "Output: $TargetOutput"
Write-Host "Split:  $TargetSplits"
Write-Host ""
Write-Host "다음 명령:" -ForegroundColor Cyan
Write-Host ".\scripts\rebuild_data.ps1"
