import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)


def pytest_collection_modifyitems(items):
    for item in items:
        doc = item.function.__doc__
        if doc:
            summary = next(
                (line.strip() for line in doc.strip().splitlines() if line.strip()),
                None,
            )
            if summary:
                if hasattr(item, "callspec"):
                    # For parameterized tests, preserve parameter id from the original nodeid.
                    start = item.nodeid.find("[")
                    param_part = item.nodeid[start:] if start != -1 else ""
                    item._nodeid = summary + param_part
                else:
                    item._nodeid = summary
