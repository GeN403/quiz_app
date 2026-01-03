# Simple test: URL mode without selected_quote (use server default)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Simple URL Mode Test (No Selected Quote)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$testUrl = "https://kotobank.jp/word/%E6%9C%AC%E8%83%BD%E5%AF%BA%E3%81%AE%E5%A4%89-134689"

Write-Host "URL: $testUrl" -ForegroundColor White

try {
    # Generate quiz without selected_quote (server will use default)
    $body = @{
        category = "history"
        source_type = "url"
        source_value = $testUrl
        question_count = 1
    } | ConvertTo-Json

    Write-Host "`nCalling /generate-quiz..." -ForegroundColor Yellow

    $quiz = Invoke-RestMethod -Uri "http://localhost:8000/generate-quiz" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body

    Write-Host "[SUCCESS] Quiz generated" -ForegroundColor Green
    Write-Host "`nQuestion: $($quiz.question)" -ForegroundColor White
    Write-Host "Answer: $($quiz.answer)" -ForegroundColor White
    Write-Host "`nSource:" -ForegroundColor Cyan
    Write-Host "  Title: $($quiz.source.title)" -ForegroundColor White
    Write-Host "  URL: $($quiz.source.url)" -ForegroundColor White
    Write-Host "  Quote length: $($quiz.source.quote.Length) chars" -ForegroundColor White
    if ($quiz.source.quote.Length -gt 0) {
        Write-Host "  Quote preview: $($quiz.source.quote.Substring(0, [Math]::Min(100, $quiz.source.quote.Length)))..." -ForegroundColor Gray
    }

    # Verification
    Write-Host "`n--- Verification ---" -ForegroundColor Yellow

    if ($quiz.source.url -eq $testUrl) {
        Write-Host "[OK] source.url matches input URL" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] source.url mismatch!" -ForegroundColor Red
        Write-Host "  Expected: $testUrl" -ForegroundColor Red
        Write-Host "  Actual: $($quiz.source.url)" -ForegroundColor Red
    }

    if ($quiz.source.quote.Length -ge 30) {
        Write-Host "[OK] source.quote exists (>= 30 chars)" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] source.quote is too short or empty" -ForegroundColor Yellow
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Test completed successfully!" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan

} catch {
    Write-Host "`n[ERROR] Test failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red

    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Test failed!" -ForegroundColor Red
    Write-Host "========================================`n" -ForegroundColor Cyan
}
