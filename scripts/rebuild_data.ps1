param(
    [switch]$IncludeRawZip
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = $null
foreach ($Candidate in @("python", "py")) {
    if (Get-Command $Candidate -ErrorAction SilentlyContinue) {
        $Python = $Candidate
        break
    }
}
if (-not $Python) {
    throw "Python을 찾을 수 없습니다. Python 3을 설치한 뒤 다시 실행하세요."
}

$Args = @(".\scripts\build_ui_data.py")
if ($IncludeRawZip) {
    $Args += "--include-raw-zip"
}

& $Python @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python ".\scripts\validate_ui_data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "UI 데이터 생성 완료" -ForegroundColor Green
Write-Host "다음 명령으로 실행하세요: .\scripts\run_local.ps1"
