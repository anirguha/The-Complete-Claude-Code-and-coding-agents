# Stops and removes the Prelegal container. Accounts and saved-document records stay in the
# prelegal-data volume; to wipe them, run: docker volume rm prelegal-data
if (docker ps -aq --filter "name=^prelegal$") {
    docker rm -f prelegal | Out-Null
    Write-Host "Prelegal stopped"
} else {
    Write-Host "Prelegal was not running"
}
