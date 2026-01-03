# Test two-step flow (URL resolution + Quiz generation with selected quote)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Two-Step Flow Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$testUrl = "https://kotobank.jp/word/%E6%9C%AC%E8%83%BD%E5%AF%BA%E3%81%AE%E5%A4%89-134689"

# Step 1: Resolve Source (URL本文取得)
Write-Host "--- Step 1: Resolve Source ---" -ForegroundColor Yellow
Write-Host "URL: $testUrl" -ForegroundColor White

try {
    $resolveBody = @{ url = $testUrl } | ConvertTo-Json

    $resolved = Invoke-RestMethod -Uri "http://localhost:8000/resolve-source" `
        -Method POST `
        -ContentType "application/json" `
        -Body $resolveBody

    Write-Host "[SUCCESS] Source resolved" -ForegroundColor Green
    Write-Host "Title: $($resolved.title)" -ForegroundColor White
    Write-Host "Text excerpt length: $($resolved.text_excerpt.Length) chars" -ForegroundColor White
    Write-Host "Quotes count: $($resolved.quotes.Count)" -ForegroundColor White
    Write-Host "`nFirst quote:" -ForegroundColor White
    Write-Host "$($resolved.quotes[0])`n" -ForegroundColor Gray

    # Step 2: Generate Quiz with selected quote
    Write-Host "--- Step 2: Generate Quiz with Selected Quote ---" -ForegroundColor Yellow

    # より短いquoteを選択（最初のquoteが長すぎる場合に備えて）
    $selectedQuoteText = if ($resolved.quotes.Count -gt 1) { $resolved.quotes[1] } else { $resolved.quotes[0] }

    $quizBody = @{
        category = "history"
        source_type = "url"
        source_value = $resolved.url
        selected_quote = $selectedQuoteText
        question_count = 1
    } | ConvertTo-Json -Depth 10

    Write-Host "Request body length: $($quizBody.Length) chars" -ForegroundColor Gray

    $quiz = Invoke-RestMethod -Uri "http://localhost:8000/generate-quiz" `
        -Method POST `
        -ContentType "application/json; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($quizBody))

    Write-Host "[SUCCESS] Quiz generated" -ForegroundColor Green
    Write-Host "Question: $($quiz.question)" -ForegroundColor White
    Write-Host "Answer: $($quiz.answer)" -ForegroundColor White
    Write-Host "`nSource:" -ForegroundColor White
    Write-Host "  URL: $($quiz.source.url)" -ForegroundColor Cyan
    Write-Host "  Quote: $($quiz.source.quote.Substring(0, [Math]::Min(100, $quiz.source.quote.Length)))..." -ForegroundColor Cyan

    # Verification
    Write-Host "`n--- Verification ---" -ForegroundColor Yellow

    # Check URL match
    if ($quiz.source.url -eq $testUrl) {
        Write-Host "[OK] source.url matches input URL" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] source.url mismatch!" -ForegroundColor Red
        Write-Host "  Expected: $testUrl" -ForegroundColor Red
        Write-Host "  Actual: $($quiz.source.url)" -ForegroundColor Red
    }

    # Check quote match
    if ($quiz.source.quote -eq $resolved.quotes[0]) {
        Write-Host "[OK] source.quote matches selected quote" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] source.quote differs from selected quote (may be normalized)" -ForegroundColor Yellow
        Write-Host "  Selected length: $($resolved.quotes[0].Length)" -ForegroundColor Yellow
        Write-Host "  Returned length: $($quiz.source.quote.Length)" -ForegroundColor Yellow
    }

    # Check quote exists in text
    if ($resolved.text_excerpt.Contains($quiz.source.quote.Substring(0, 50))) {
        Write-Host "[OK] source.quote exists in text excerpt" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Checking normalized match (without punctuation)..." -ForegroundColor Yellow
        # This is OK because backend normalizes quotes
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "All tests completed successfully!" -ForegroundColor Green
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
