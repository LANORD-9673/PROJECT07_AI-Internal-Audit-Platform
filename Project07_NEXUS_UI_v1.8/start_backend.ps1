
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
Set-Location ".\backend"

Write-Host "Khoi dong NEXUS Backend..." -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Tao moi truong Python 3.13..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Khong tao duoc moi truong Python."
    }
}

$python = ".\.venv\Scripts\python.exe"

Write-Host "Cai thu vien backend..."
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Cai thu vien backend that bai."
}

if (Test-Path (Join-Path $PSScriptRoot '.env')) {
    Get-Content (Join-Path $PSScriptRoot '.env') | ForEach-Object {
        if ($_ -match '^([A-Z0-9_]+)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process') }
    }
}
Write-Host "Khoi dong FastAPI..."
& $python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
