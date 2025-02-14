def pytest_configure(config):
    config.addinivalue_line("markers", "unit: mark test as unit test")
