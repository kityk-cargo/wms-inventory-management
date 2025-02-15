# Run unit tests with output visible
Write-Host "Running unit tests..."
pytest tests/unit -s --maxfail=0 --disable-warnings --html=unit_report.html
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Run integration tests with output visible
Write-Host "Running integration tests..."
pytest tests/integration -s --maxfail=0 --disable-warnings --html=integration_report.html
exit $LASTEXITCODE
