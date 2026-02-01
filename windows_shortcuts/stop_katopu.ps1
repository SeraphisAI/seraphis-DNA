# STOP_KATOPU.ps1
# Stops Katopu GenLab (API + UI) via docker compose.

$ErrorActionPreference = "Stop"

$INFRA = Resolve-Path (Join-Path $PSScriptRoot "..\infra")
Set-Location $INFRA

docker compose down --remove-orphans
Write-Host "Stopped." 
