# START_KATOPU.ps1
# Starts Katopu GenLab (API + UI) via docker compose.

$ErrorActionPreference = "Stop"

# Locate infra/ relative to this script (repo_root\windows_shortcuts\start_katopu.ps1)
$INFRA = Resolve-Path (Join-Path $PSScriptRoot "..\infra")
Set-Location $INFRA

# Quick sanity: is Docker Desktop/daemon reachable?
try {
  docker version | Out-Null
} catch {
  Write-Host "Docker daemon not reachable. Start Docker Desktop and ensure you are using Linux containers." -ForegroundColor Red
  throw
}

docker compose up -d --build

Write-Host ""
Write-Host "Containers:" 
 docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""
Write-Host "UI  : http://localhost:8501"
Write-Host "API : http://localhost:8000"
Write-Host "DOCS: http://localhost:8000/docs"
