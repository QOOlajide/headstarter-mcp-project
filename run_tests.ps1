# PowerShell script to run tests with virtual environment activated
# Usage: .\run_tests.ps1

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Run simple tests
Write-Host "Running simple tests..." -ForegroundColor Cyan
python test_simple.py

# Optionally run pytest if available
if (Get-Command pytest -ErrorAction SilentlyContinue) {
    Write-Host "`nRunning pytest suite..." -ForegroundColor Cyan
    pytest test_mcp_server.py -v
} else {
    Write-Host "`npytest not found. Install with: pip install pytest pytest-asyncio" -ForegroundColor Yellow
}

