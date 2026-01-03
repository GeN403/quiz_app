# Test API for source resolution improvements

Write-Host "`n=== Test 1: Category Mode ===" -ForegroundColor Cyan

$body1 = @{
    category = "science"
    source_type = "category"
    question_count = 1
} | ConvertTo-Json

try {
    $result1 = Invoke-RestMethod -Uri "http://localhost:8000/generate-quiz" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body1

    Write-Host "[SUCCESS] Quiz generated" -ForegroundColor Green
    Write-Host "Question: $($result1.question)" -ForegroundColor White
    Write-Host "Answer: $($result1.answer)" -ForegroundColor White
    Write-Host "Source URL: $($result1.source.url)" -ForegroundColor Yellow
    Write-Host "Source Quote: $($result1.source.quote)" -ForegroundColor Yellow
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Test 2: URL Mode (Kotobank) ===" -ForegroundColor Cyan

$body2 = @{
    category = "history"
    source_type = "url"
    source_value = "https://kotobank.jp/word/%E6%9C%AC%E8%83%BD%E5%AF%BA%E3%81%AE%E5%A4%89-134689"
    question_count = 1
} | ConvertTo-Json

try {
    $result2 = Invoke-RestMethod -Uri "http://localhost:8000/generate-quiz" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body2

    Write-Host "[SUCCESS] Quiz generated from URL" -ForegroundColor Green
    Write-Host "Question: $($result2.question)" -ForegroundColor White
    Write-Host "Source URL: $($result2.source.url)" -ForegroundColor Yellow
    Write-Host "Source Quote length: $($result2.source.quote.Length) chars" -ForegroundColor Yellow

    # Verify URL match
    if ($result2.source.url -eq "https://kotobank.jp/word/%E6%9C%AC%E8%83%BD%E5%AF%BA%E3%81%AE%E5%A4%89-134689") {
        Write-Host "[VERIFY] URL matched!" -ForegroundColor Green
    } else {
        Write-Host "[VERIFY] URL mismatch!" -ForegroundColor Red
    }

    # Verify quote exists
    if ($result2.source.quote.Length -ge 30) {
        Write-Host "[VERIFY] Quote exists (>= 30 chars)" -ForegroundColor Green
    } else {
        Write-Host "[VERIFY] Quote too short!" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Test 3: Invalid Domain (should fail) ===" -ForegroundColor Cyan

$body3 = @{
    category = "history"
    source_type = "url"
    source_value = "https://ja.wikipedia.org/wiki/Test"
    question_count = 1
} | ConvertTo-Json

try {
    $result3 = Invoke-RestMethod -Uri "http://localhost:8000/generate-quiz" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body3

    Write-Host "[UNEXPECTED] Should have failed but succeeded!" -ForegroundColor Red
} catch {
    Write-Host "[EXPECTED] Request rejected as expected" -ForegroundColor Green
    Write-Host "Error: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
}

Write-Host "`n=== All Tests Complete ===" -ForegroundColor Cyan
