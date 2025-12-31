# validate_api.ps1
# Backend API validation script for /generate-quiz endpoint
# Runnable in PowerShell environment

#Requires -Version 5.1

# Stop on error
$ErrorActionPreference = "Stop"

# UTF-8 output encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Colored message output functions
function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Failure {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

# Backend URL
$ApiUrl = "http://localhost:8000/generate-quiz"

# Test URL (real kotobank URL)
$TestUrl = "https://kotobank.jp/word/%E6%A1%9C%E7%94%B0%E9%96%80%E5%A4%96%E3%81%AE%E5%A4%89-68811"

# Test result counters
$PassCount = 0
$FailCount = 0

Write-Info "=== Backend API Validation Script ==="
Write-Info "API URL: $ApiUrl"
Write-Info ""

# Check if backend is running
try {
    Write-Info "Checking if backend is running..."
    # Try localhost first, then 127.0.0.1
    try {
        $healthCheck = Invoke-WebRequest -Uri "http://localhost:8000/docs" -Method GET -TimeoutSec 3 -ErrorAction Stop
    } catch {
        $healthCheck = Invoke-WebRequest -Uri "http://127.0.0.1:8000/docs" -Method GET -TimeoutSec 3 -ErrorAction Stop
    }
    Write-Success "Backend is running"
} catch {
    Write-Failure "Backend is not running"
    Write-Host "Please start the backend before running this script:" -ForegroundColor Yellow
    Write-Host "  cd backend" -ForegroundColor Yellow
    Write-Host "  python -m uvicorn main:app --reload" -ForegroundColor Yellow
    exit 1
}

Write-Info ""

# Test 1-3: Category mode (run 3 times to check AI output variance)
Write-Info "=== Test 1-3: Category Mode (3 executions) ==="
for ($i = 1; $i -le 3; $i++) {
    Write-Info "Category mode test $i/3 running..."

    $body = @{
        category = "history"
        source_type = "category"
        question_count = 1
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri $ApiUrl `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 30

        # Response validation
        if ($null -eq $response) {
            throw "Response is null"
        }

        if (-not $response.question) {
            throw "Missing 'question' field"
        }

        if (-not $response.source) {
            throw "Missing 'source' field"
        }

        if (-not $response.source.url) {
            throw "Missing 'source.url' field"
        }

        # Validate source.url (allowed domains or fallback message)
        $sourceUrl = $response.source.url
        $allowedPattern = "^https://(kotobank\.jp|.*\.go\.jp|.*\.ac\.jp)"
        $fallbackMessage = "Cannot provide reference URL"

        # Check if it's in Japanese
        if ($sourceUrl -match "[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]") {
            # Japanese fallback message
            Write-Success "Test $i passed: source.url = (fallback message in Japanese)"
        } elseif ($sourceUrl -notmatch $allowedPattern) {
            throw "source.url is not in allowed domains: $sourceUrl"
        } else {
            Write-Success "Test $i passed: source.url = $sourceUrl"
        }
        $PassCount++

    } catch {
        Write-Failure "Test $i failed: $($_.Exception.Message)"
        if ($_.ErrorDetails) {
            Write-Host "Response details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
        }
        $FailCount++
    }
}

Write-Info ""

# Test 4: URL mode
Write-Info "=== Test 4: URL Mode ==="
Write-Info "URL mode test running..."
Write-Info "Test URL: $TestUrl"

$body = @{
    category = "history"
    source_type = "url"
    source_value = $TestUrl
    question_count = 1
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $ApiUrl `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 60

    # Response validation
    if ($null -eq $response) {
        throw "Response is null"
    }

    if (-not $response.question) {
        throw "Missing 'question' field"
    }

    if (-not $response.source) {
        throw "Missing 'source' field"
    }

    if (-not $response.source.url) {
        throw "Missing 'source.url' field"
    }

    # Verify source.url matches input URL
    if ($response.source.url -ne $TestUrl) {
        throw "source.url does not match input URL: expected=$TestUrl, actual=$($response.source.url)"
    }

    # Verify source.quote exists and is not empty
    if (-not $response.source.quote) {
        throw "source.quote field is missing or empty"
    }

    $quoteLength = $response.source.quote.Length
    if ($quoteLength -lt 30) {
        throw "source.quote is too short (${quoteLength} chars, minimum 30 required)"
    }

    Write-Success "URL mode passed: source.quote = ${quoteLength} chars"
    Write-Info "Quote preview: $($response.source.quote.Substring(0, [Math]::Min(50, $quoteLength)))..."
    $PassCount++

} catch {
    Write-Failure "URL mode failed: $($_.Exception.Message)"
    if ($_.ErrorDetails) {
        Write-Host "Response details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    $FailCount++
}

# Result summary
Write-Info ""
Write-Info "=== Validation Results Summary ==="
Write-Host "Passed: $PassCount / $(($PassCount + $FailCount)) tests" -ForegroundColor $(if ($FailCount -eq 0) { "Green" } else { "Yellow" })
Write-Host "Failed: $FailCount / $(($PassCount + $FailCount)) tests" -ForegroundColor $(if ($FailCount -eq 0) { "Green" } else { "Red" })

if ($FailCount -gt 0) {
    Write-Failure "Some tests failed"
    exit 1
} else {
    Write-Success "All tests passed"
    exit 0
}
