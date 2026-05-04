Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "     Starting tests and code coverage" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Running tests... Please wait." -ForegroundColor Yellow
pytest tests/ -q --tb=no --cov=ai --cov=simulation --cov=ui --cov=core --cov-report=html --cov-report=term --html=htmlcov/test_report.html --self-contained-html > test_console.log
Write-Host "Testing completed!" -ForegroundColor Green
Write-Host "-> Test report: htmlcov/test_report.html" -ForegroundColor Green
Write-Host "-> Coverage report: htmlcov/index.html" -ForegroundColor Green

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "             Complexity analysis            " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
radon cc ai/ simulation/ core/ ui/ -s -a

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "           Maintainability Index            " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
radon mi ai/ simulation/ core/ ui/

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "          Style code checking             " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Running code style auto-fix..." -ForegroundColor Yellow
ruff check . --fix > ruff_log.txt
Write-Host "Linting completed! Details in ruff_log.txt" -ForegroundColor Green
Write-Host "`nTest coverage report saved in htmlcov/index.html" -ForegroundColor Green
