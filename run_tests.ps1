# Run unit tests with output visible
Write-Host "Running unit tests..."
pytest tests/unit -s --maxfail=0 --disable-warnings --html=unit_report.html
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Run integration tests with output visible
Write-Host "Running integration tests..."
pytest tests/integration -s --maxfail=0 --disable-warnings --html=integration_report.html
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Run contract tests with output visible
Write-Host "Running contract tests..."
pytest tests/contract -s --maxfail=0 --disable-warnings -m contract --html=contract_report.html
exit $LASTEXITCODE
