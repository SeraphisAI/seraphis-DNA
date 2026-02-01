# PowerShell examples (safe JSON)

# 1) intent -> /nl/spec
$payload = @{
  sequence = "ATGC"
  intent   = "ilk 2 baz sil"
  mode     = "strict"
} | ConvertTo-Json -Depth 10

$spec = Invoke-RestMethod -Uri "http://localhost:8000/nl/spec" -Method POST -ContentType "application/json" -Body $payload
$spec

# 2) spec -> /edit/apply
$apply = @{
  sequence = "ATGC"
  mode     = "strict"
  spec     = $spec
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8000/edit/apply" -Method POST -ContentType "application/json" -Body $apply

# 3) one-shot /run
$body3 = @{ intent="ilk 5 baz sil"; mode="strict" } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://localhost:8000/run?sequence=ATGACCTTGGCTAACCTGTTACGATGGCCTTAA" -Method POST -ContentType "application/json" -Body $body3

# curl.exe tip: use --data-binary @file.json to avoid PowerShell quoting issues
@'
{"sequence":"ATGC","intent":"ilk 2 baz sil","mode":"strict"}
'@ | Set-Content -Encoding ascii -NoNewline .\body.json
curl.exe -s -X POST "http://localhost:8000/nl/spec" -H "Content-Type: application/json" --data-binary "@body.json"
