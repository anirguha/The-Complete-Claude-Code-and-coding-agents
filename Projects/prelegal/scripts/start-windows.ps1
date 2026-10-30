# Builds the Prelegal image and starts it at http://localhost:8000.
# Accounts and saved-document records persist in the prelegal-data Docker volume.
# Set PRELEGAL_PORT to use a different host port.
# Native commands are checked via $LASTEXITCODE: with $ErrorActionPreference = "Stop",
# Windows PowerShell 5.1 aborts on any docker stderr output, even when it is harmless.
Set-Location (Join-Path $PSScriptRoot "..")

$Image = "prelegal"
$Container = "prelegal"
$Port = if ($env:PRELEGAL_PORT) { $env:PRELEGAL_PORT } else { "8000" }

if (docker ps -aq --filter "name=^$Container$") { docker rm -f $Container | Out-Null }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Port $Port is already in use. Stop whatever is using it, or set PRELEGAL_PORT." -ForegroundColor Red
    exit 1
}

docker build -t $Image .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$EnvArgs = @()
if (Test-Path ".env") { $EnvArgs = @("--env-file", ".env") }
docker run -d --name $Container -p "${Port}:8000" -v "prelegal-data:/app/data" @EnvArgs $Image | Out-Null
if ($LASTEXITCODE -ne 0) {
    $Code = $LASTEXITCODE
    if (docker ps -aq --filter "name=^$Container$") { docker rm -f $Container | Out-Null }
    exit $Code
}

for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:$Port/api/health" -TimeoutSec 2 | Out-Null
        Write-Host "Prelegal is running at http://localhost:$Port"
        exit 0
    } catch {
        Start-Sleep -Seconds 1
    }
}
Write-Host "Prelegal did not become healthy; recent logs:" -ForegroundColor Red
docker logs --tail 50 $Container
exit 1
