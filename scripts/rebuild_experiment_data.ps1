param(
    [string]$OutputsZip = (Join-Path ([Environment]::GetFolderPath("Desktop")) "outputs.zip")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
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
    throw "Python 3 was not found."
}
if (-not (Test-Path -LiteralPath $OutputsZip -PathType Leaf)) {
    throw "outputs.zip was not found: $OutputsZip"
}

Write-Host "[1/3] Generating publishable data from outputs.zip" -ForegroundColor Cyan
& $Python ".\scripts\build_experiment_data.py" "--outputs-zip" $OutputsZip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Validating generated data" -ForegroundColor Cyan
& $Python ".\scripts\validate_ui_data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Building the React site for GitHub Pages" -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath ".\node_modules")) {
    & npm.cmd install
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& npm.cmd run build -- --mode github-pages
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Data generation, validation, and production build succeeded." -ForegroundColor Green
