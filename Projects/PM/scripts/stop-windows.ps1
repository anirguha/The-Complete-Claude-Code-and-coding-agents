$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
docker compose down
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
