# Test /resolve-source endpoint

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Resolve Source API Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$testUrl = "https://kotobank.jp/word/%E6%9C%AC%E8%83%BD%E5%AF%BA%E3%81%AE%E5%A4%89-134689"

Write-Host "URL: $testUrl" -ForegroundColor White

try {
    $body = @{ url = $testUrl } | ConvertTo-Json

    Write-Host "`nCalling /resolve-source..." -ForegroundColor Yellow

    $result = Invoke-RestMethod -Uri "http://localhost:8000/resolve-source" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body

    Write-Host "[SUCCESS] Source resolved" -ForegroundColor Green
    Write-Host "`nTitle: $($result.title)" -ForegroundColor White
    Write-Host "URL: $($result.url)" -ForegroundColor Cyan
    Write-Host "Text excerpt length: $($result.text_excerpt.Length) chars" -ForegroundColor White
    Write-Host "Quotes count: $($result.quotes.Count)" -ForegroundColor White

    Write-Host "`n--- Quote Candidates ---" -ForegroundColor Yellow
    for ($i = 0; $i -lt [Math]::Min(3, $result.quotes.Count); $i++) {
        $quote = $result.quotes[$i]
        $preview = if ($quote.Length -gt 80) { $quote.Substring(0, 80) + "..." } else { $quote }
        Write-Host "[$($i+1)] ($($quote.Length) chars) $preview" -ForegroundColor Gray
    }

    # Verification
    Write-Host "`n--- Verification ---" -ForegroundColor Yellow

    if ($result.url -eq $testUrl) {
        Write-Host "[OK] URL matches input" -ForegroundColor Green
    } else {
        Write-Host "[INFO] URL differs (may be redirected)" -ForegroundColor Yellow
        Write-Host "  Input: $testUrl" -ForegroundColor Gray
        Write-Host "  Result: $($result.url)" -ForegroundColor Gray
    }

    if ($result.title.Length -gt 0) {
        Write-Host "[OK] Title extracted" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Title is empty" -ForegroundColor Yellow
    }

    if ($result.text_excerpt.Length -ge 1000) {
        Write-Host "[OK] Text excerpt extracted (>= 1000 chars)" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Text excerpt is short ($($result.text_excerpt.Length) chars)" -ForegroundColor Yellow
    }

    if ($result.quotes.Count -ge 5) {
        Write-Host "[OK] Quote candidates generated ($($result.quotes.Count) items)" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Few quote candidates ($($result.quotes.Count) items)" -ForegroundColor Yellow
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "All checks passed!" -ForegroundColor Green
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
