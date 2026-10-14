$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'frontend')
if (-not (Test-Path 'node_modules')) {
    Write-Host 'Cai dependencies frontend lan dau...' -ForegroundColor Cyan
    npm.cmd install
    if ($LASTEXITCODE -ne 0) { throw 'npm install that bai. Cai Node.js LTS truoc.' }
}
Write-Host 'Frontend: http://localhost:5173' -ForegroundColor Green
npm.cmd run dev
