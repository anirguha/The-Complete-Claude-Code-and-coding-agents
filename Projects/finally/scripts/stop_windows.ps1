# Stop and remove the FinAlly container (Windows PowerShell). Safe to run repeatedly.
# The finally-data volume is kept, so your portfolio survives.

# Native command failures are checked through $LASTEXITCODE. Under "Stop", Windows
# PowerShell 5.1 would turn any redirected docker stderr into a terminating error.
$ErrorActionPreference = 'Continue'

$Container = 'finally'
# Must exceed uvicorn's 3s graceful shutdown, or docker kills the app before it finishes.
$StopTimeoutSeconds = 10

$DockerUp = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker info *> $null
    $DockerUp = $LASTEXITCODE -eq 0
}
if (-not $DockerUp) {
    Write-Host 'Docker is not running, so there is nothing to stop.'
    exit 0
}

if (-not (docker ps -aq --filter "name=^/$Container$")) {
    Write-Host 'FinAlly is not running. Nothing to stop.'
    exit 0
}

docker stop -t $StopTimeoutSeconds $Container *> $null
docker rm $Container *> $null
Write-Host 'FinAlly stopped. Your data is kept in the finally-data volume.'
