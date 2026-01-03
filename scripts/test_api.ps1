# PowerShell script to test API endpoints
# Usage: .\scripts\test_api.ps1

Write-Host "=== API Endpoint Test ===" -ForegroundColor Cyan
Write-Host ""

# Test Backend (FastAPI)
Write-Host "[1/2] Testing Backend (http://localhost:8000/openapi.json)..." -ForegroundColor Yellow

try {
    $backendResponse = Invoke-RestMethod -Uri "http://localhost:8000/openapi.json" -Method Get -TimeoutSec 5 -ErrorAction Stop
    if ($backendResponse) {
        Write-Host "[OK] Backend is running (HTTP 200)" -ForegroundColor Green
        Write-Host "     OpenAPI version: $($backendResponse.openapi)" -ForegroundColor Gray
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode) {
        Write-Host "[FAIL] Backend returned HTTP $statusCode" -ForegroundColor Red
    } else {
        Write-Host "[FAIL] Backend is not reachable" -ForegroundColor Red
        Write-Host "       Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "       Hint: Is 'docker compose up' running?" -ForegroundColor Yellow
    }
}

Write-Host ""

# Test Frontend (Next.js)
Write-Host "[2/2] Testing Frontend (http://localhost:3000)..." -ForegroundColor Yellow

try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 5 -ErrorAction Stop
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "[OK] Frontend is running (HTTP 200)" -ForegroundColor Green
        Write-Host "     Content-Type: $($frontendResponse.Headers.'Content-Type')" -ForegroundColor Gray
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode) {
        Write-Host "[FAIL] Frontend returned HTTP $statusCode" -ForegroundColor Red
    } else {
        Write-Host "[FAIL] Frontend is not reachable" -ForegroundColor Red
        Write-Host "       Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "       Hint: Is 'docker compose up' running?" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
