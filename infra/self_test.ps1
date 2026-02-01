\
$ErrorActionPreference="Stop"
Write-Host "== Katopu GenLab self-test =="

docker version | Out-Null

Set-Location (Split-Path $MyInvocation.MyCommand.Path)
docker compose up -d --build | Out-Null

$api = "http://localhost:8000/health"
for ($i=0; $i -lt 30; $i++) {
  try {
    $r = Invoke-RestMethod -Uri $api -Method GET
    if ($r.ok -eq $true) { break }
  } catch {}
  Start-Sleep -Seconds 1
}
$r = Invoke-RestMethod -Uri $api -Method GET
if ($r.ok -ne $true) { throw "Health failed" }
Write-Host "OK /health"

$body = @{ intent="ilk 5 baz sil"; mode="strict" } | ConvertTo-Json
$res = Invoke-RestMethod -Uri "http://localhost:8000/run?sequence=ATGACCTTGGCTAACCTGTTACGATGGCCTTAA" -Method POST -ContentType "application/json" -Body $body
if (-not $res.after) { throw "run response missing after" }
Write-Host ("OK /run after=" + $res.after)

Write-Host "DONE"
