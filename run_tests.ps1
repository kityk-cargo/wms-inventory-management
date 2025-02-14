# Run unit tests
Write-Host "Running unit tests..."
pytest tests/unit --maxfail=0 --disable-warnings --html=unit_report.html
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Run integration tests
Write-Host "Running integration tests..."
pytest tests/integration --maxfail=0 --disable-warnings --html=integration_report.html
exit $LASTEXITCODE
