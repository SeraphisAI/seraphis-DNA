# CLEAN_REBUILD.ps1
# Hard reset: stop stack, remove containers/volumes, rebuild images, start again.

$ErrorActionPreference = "Stop"

$INFRA = Resolve-Path (Join-Path $PSScriptRoot "..\infra")
Set-Location $INFRA

Write-Host "[1/3] Stopping + removing containers/volumes..."
docker compose down --remove-orphans --volumes

Write-Host "[2/3] Rebuilding + starting..."
docker compose up -d --build

Write-Host "[3/3] Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""
Write-Host "UI  : http://localhost:8501"
Write-Host "API : http://localhost:8000"
Write-Host "DOCS: http://localhost:8000/docs"
