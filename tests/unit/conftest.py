import sys
import importlib

# Remove the unit inventory mock module globally to avoid interference in DB tests:
sys.modules.pop("tests.test_unit_inventory", None)

from pathlib import Path
import subprocess  # if needed for other commands
import pytest
from pact import Consumer, Provider  # type: ignore
from sqlalchemy import create_engine, text  # updated import
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from fastapi.testclient import TestClient
from app.main import app
import os

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# New: use Testcontainers to run a PostgreSQL instance for testing
from testcontainers.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer

# Add a global to hold our sessionmaker
test_session_local = None


@pytest.fixture(scope="session", autouse=True)
def set_test_session(TestingSessionLocal):
    global test_session_local
    test_session_local = TestingSessionLocal


@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer("postgres:15")
    container.start()

    # Manually create schema "wms_schema"
    temp_engine = create_engine(container.get_connection_url())
    with temp_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS wms_schema;"))
    temp_engine.dispose()

    # Run Liquibase update using a Liquibase Docker container
    jdbc_url = container.get_connection_url().replace(
        "postgresql://", "jdbc:postgresql://"
    )
    username = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    changelog_file = "001_initial_schema.sql"
    # Retrieve changelog directory from env variable with a fallback
    changelog_host = os.getenv(
        "LIQUIBASE_CHANGELOG_HOST",
        "c:/Users/Alexey/git/WMS/wms-main/liquibase/db/changelogs",
    )
    changelog_container = "/liquibase/changelog"

    liquibase_container = (
        DockerContainer("liquibase/liquibase")
        .with_volume_mapping(changelog_host, changelog_container)
        .with_command(
            f"--url={jdbc_url} --username={username} --password={password} --changeLogFile={changelog_container}/{changelog_file} update"
        )
    )

    liquibase_container.start()
    # Ensure liquibase container finishes; then stop it.
    liquibase_container.stop()

    yield container
    container.stop()


@pytest.fixture(scope="session")
def engine(postgres_container):
    # Create SQLAlchemy engine with the container's connection URL
    engine = create_engine(postgres_container.get_connection_url())
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


# Override the get_db dependency to use our PostgreSQL test database
def override_get_db():
    db = test_session_local()  # use the stored sessionmaker instance
    try:
        yield db
    finally:
        db.close()


def pytest_configure(config):
    config.addinivalue_line("markers", "db: mark test as database integration test")


def pytest_collection_modifyitems(items):
    # Handle DB tests first
    for item in items:
        if "test_stock" in item.nodeid:
            item.add_marker(pytest.mark.db)

    # Then handle docstring-based naming
    for item in items:
        doc = item.function.__doc__
        if doc:
            summary = next(
                (line.strip() for line in doc.strip().splitlines() if line.strip()),
                None,
            )
            if summary:
                if hasattr(item, "callspec"):
                    start = item.nodeid.find("[")
                    param_part = item.nodeid[start:] if start != -1 else ""
                    item._nodeid = summary + param_part
                else:
                    item._nodeid = summary


PACT_MOCK_HOST = "localhost"
PACT_MOCK_PORT = 1234


# Use session scope to initialize pact_setup once for all tests
@pytest.fixture(scope="session")
def pact_setup():
    pact = Consumer("WMSInventory").has_pact_with(
        Provider("WMSNotification"),
        host_name=PACT_MOCK_HOST,
        port=PACT_MOCK_PORT,
        log_dir="./logs",
        pact_dir="./pacts",
    )
    pact.start_service()
    yield pact
    pact.stop_service()


# Set up the PostgreSQL database
@pytest.fixture(scope="session", autouse=True)
def setup_database(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(TestingSessionLocal):
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c


# Add new fixture for tests that require DB access:
@pytest.fixture(scope="function")
def client_with_db():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)
