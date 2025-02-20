import sys
from pathlib import Path
import pytest
from pact import Consumer, Provider  # type: ignore
import os  # add this import if not already present

# Set project root so that app modules are found
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Shared: Improve test names from docstrings.
def pytest_collection_modifyitems(items):
    for item in items:
        doc = item.function.__doc__
        if doc:
            summary = next(
                (line.strip() for line in doc.splitlines() if line.strip()), None
            )
            if summary:
                if hasattr(item, "callspec"):
                    start = item.nodeid.find("[")
                    param_part = item.nodeid[start:] if start != -1 else ""
                    item._nodeid = summary + param_part
                else:
                    item._nodeid = summary


# Shared: Pact fixture used for consumer tests.
PACT_MOCK_HOST = "localhost"
PACT_MOCK_PORT = 1234


@pytest.fixture(scope="session")
def pact_setup():
    # Set structured pacts directory: consumer/provider
    consumer_name = "wms_inventory_management"
    provider_name = "wms_notification"
    pacts_directory = f"./pacts/{provider_name}"
    pact = Consumer(consumer_name).has_pact_with(
        Provider(provider_name),
        host_name=PACT_MOCK_HOST,
        port=PACT_MOCK_PORT,
        log_dir="./logs",
        pact_dir=pacts_directory,
    )
    pact.start_service()
    yield pact
    pact.stop_service()
    # Rename pact file: from consumer-provider.json to consumer.json
    old_file = f"{pacts_directory}/{consumer_name}-{provider_name}.json"
    new_file = f"{pacts_directory}/{consumer_name}.json"
    if os.path.exists(old_file):
        os.replace(old_file, new_file)
