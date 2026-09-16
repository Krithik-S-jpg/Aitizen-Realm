$ErrorActionPreference = "Stop"

$backendUrl = "http://127.0.0.1:8000/api/v1/world"
try {
    $response = Invoke-WebRequest -Uri $backendUrl -Method Get -TimeoutSec 2 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "Aitizen Realm backend is already running on http://127.0.0.1:8000" -ForegroundColor Green
        exit 0
    }
} catch {
    # No healthy server responded, so it is safe to try starting one.
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
Set-Location -LiteralPath $backendRoot
Write-Host "Starting Aitizen Realm backend on http://127.0.0.1:8000" -ForegroundColor Cyan
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
