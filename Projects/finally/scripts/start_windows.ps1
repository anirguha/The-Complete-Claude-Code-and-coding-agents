# Start FinAlly in Docker (Windows PowerShell). Safe to run repeatedly.
#
#   scripts\start_windows.ps1 [-Build] [-NoOpen]
#
#   -Build    Rebuild the image, even if it exists.
#   -NoOpen   Do not open the browser.
#
# $env:FINALLY_PORT sets the host port (default 8000).
param(
    [switch]$Build,
    [switch]$NoOpen
)

# Native command failures are checked through $LASTEXITCODE. Under "Stop", Windows
# PowerShell 5.1 would turn any redirected docker stderr into a terminating error.
$ErrorActionPreference = 'Continue'

$Image = 'finally'
$Container = 'finally'
$Volume = 'finally-data'
$ContainerPort = 8000
$HealthTimeoutSeconds = 90
# Must exceed uvicorn's 3s graceful shutdown, or docker kills the app before it finishes.
$StopTimeoutSeconds = 10

$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root '.env'
$EnvExample = Join-Path $Root '.env.example'

function Stop-WithError([string]$Message) {
    [Console]::Error.WriteLine("Error: $Message")
    exit 1
}

function Test-PortTaken([int]$PortNumber) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $PortNumber)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

$PortText = if ($env:FINALLY_PORT) { $env:FINALLY_PORT } else { '8000' }
$Port = 0
if (-not [int]::TryParse($PortText, [ref]$Port) -or $Port -lt 1 -or $Port -gt 65535) {
    Stop-WithError "FINALLY_PORT must be a port number from 1 to 65535, got '$PortText'."
}
$PortTakenMessage = "port $Port is already in use by another program. Choose a free one, for example: `$env:FINALLY_PORT=8030; scripts\start_windows.ps1"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-WithError 'docker is not installed.'
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-WithError 'cannot reach Docker. Is it running?'
}

# Our own running container is about to be replaced, so its port does not count as taken.
# Checking before anything changes means a failed start leaves a running app alone.
$OwnPort = ''
if (docker ps -q --filter "name=^/$Container$") {
    $Mapping = docker port $Container "$ContainerPort/tcp" 2>$null | Select-Object -First 1
    if ($Mapping) {
        $OwnPort = ($Mapping -split ':')[-1]
    }
}
if ("$Port" -ne $OwnPort -and (Test-PortTaken $Port)) {
    Stop-WithError $PortTakenMessage
}

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    Copy-Item -LiteralPath $EnvExample -Destination $EnvFile
    Write-Host 'Created .env from .env.example. Add OPENROUTER_API_KEY to it to enable AI chat.'
}

if ($Build -or -not (docker images -q $Image)) {
    Write-Host "Building the $Image image. The first build takes a few minutes."
    docker build -t $Image $Root
    if ($LASTEXITCODE -ne 0) {
        Stop-WithError 'the image build failed. See the output above.'
    }
}

if (docker ps -aq --filter "name=^/$Container$") {
    Write-Host "Replacing the existing $Container container. Your data is kept."
    docker stop -t $StopTimeoutSeconds $Container *> $null
    docker rm $Container *> $null
}

# Published on loopback only: the app has no login, and its chat can place trades.
$RunOutput = docker run -d `
    --name $Container `
    --stop-timeout $StopTimeoutSeconds `
    -v "${Volume}:/app/db" `
    -p "127.0.0.1:${Port}:$ContainerPort" `
    --env-file $EnvFile `
    $Image 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    docker rm $Container *> $null
    if ($RunOutput -match 'port is already allocated|address already in use') {
        Stop-WithError $PortTakenMessage
    }
    Stop-WithError "could not start the container: $RunOutput"
}

Write-Host -NoNewline 'Waiting for the app to become healthy'
$Status = ''
for ($i = 0; $i -lt $HealthTimeoutSeconds; $i++) {
    $Status = docker inspect --format '{{.State.Status}}/{{.State.Health.Status}}' $Container
    if ($Status -match '^(running/(un)?healthy|exited/.*|dead/.*)$') {
        break
    }
    Write-Host -NoNewline '.'
    Start-Sleep -Seconds 1
}
Write-Host ''

if ($Status -ne 'running/healthy') {
    docker logs --tail 30 $Container
    Stop-WithError "the app did not become healthy (status: $Status). See the logs above."
}

$Url = "http://localhost:$Port"
Write-Host "FinAlly is running at $Url"
Write-Host "Stop it with scripts\stop_windows.ps1. Your data is kept in the $Volume volume."

if (-not $NoOpen) {
    Start-Process $Url
}
