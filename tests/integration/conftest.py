import os
import platform
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer  # type: ignore
from testcontainers.core.container import DockerContainer  # type: ignore

from app.database import get_db
from app.main import app

# Load environment variables from .env.test located two directories up
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env.test")
)


def convert_path_for_docker(file_path: str) -> str:
    """
    Convert a Windows path to a Docker-compatible POSIX path.
    """
    absolute_path = Path(file_path).resolve()
    drive_letter = absolute_path.drive.lower().rstrip(":")
    relative_path = absolute_path.relative_to(absolute_path.anchor).as_posix()
    docker_path = f"/{drive_letter}/{relative_path}"
    if not docker_path.endswith("/"):
        docker_path += "/"
    return docker_path


def reset_database_schema(connection_url: str) -> None:
    """
    Drops the existing schema (if any) and creates a fresh schema for testing.
    """
    engine = create_engine(connection_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS wms_schema;"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS wms_schema;"))
    engine.dispose()


def get_jdbc_url_from_container(postgres_container: PostgresContainer) -> str:
    """
    Constructs a JDBC URL using the container's connection info.
    """
    connection_url = postgres_container.get_connection_url()
    parsed_url = urlparse(connection_url)
    host_ip = (
        "host.docker.internal"
        if platform.system().lower() == "windows"
        else "172.17.0.1"
    )
    exposed_port = postgres_container.get_exposed_port(5432)
    database_name = parsed_url.path.lstrip("/")
    return f"jdbc:postgresql://{host_ip}:{exposed_port}/{database_name}"


def poll_liquibase_logs(
    liquibase_container: DockerContainer, timeout: int = 30, interval: int = 1
) -> str:
    """
    Polls the Liquibase container logs until the migration completes successfully or times out.
    """
    start_time = time.time()
    while True:
        logs = liquibase_container.get_logs()
        logs_text = logs.decode("utf-8") if isinstance(logs, bytes) else logs
        if isinstance(logs_text, tuple):
            logs_text = "".join(
                part.decode("utf-8") if isinstance(part, bytes) else part
                for part in logs_text
            )
        if "Liquibase command 'update' was executed successfully" in logs_text:
            return logs_text
        if time.time() - start_time > timeout:
            print(f"Liquibase logs:\n{logs_text}")
            raise Exception("Liquibase migration timed out")
        time.sleep(interval)


def run_liquibase_migration(jdbc_url: str) -> None:
    """
    Runs the Liquibase migration in a Docker container and polls for its successful execution.
    """
    username = "test"
    password = "test"
    change_log_filename = "changelog.xml"

    liquibase_change_log_host = os.getenv("LIQUIBASE_CHANGELOG_HOST")
    liquibase_change_log_host_abs = (
        convert_path_for_docker(liquibase_change_log_host)
        if liquibase_change_log_host
        else liquibase_change_log_host
    )
    print(f"Using changelog file at: {liquibase_change_log_host_abs}")

    container_change_log_dir = "/lb"
    liquibase_version = os.getenv("LIQUIBASE_VERSION", "4.31.0")
    liquibase_command = (
        f"--log-level=info --url={jdbc_url} --username={username} --password={password} "
        f"--changeLogFile={change_log_filename} --searchPath={container_change_log_dir}/db update"
    )

    liquibase_container = (
        DockerContainer(f"liquibase/liquibase:{liquibase_version}")
        .with_volume_mapping(liquibase_change_log_host_abs, container_change_log_dir)
        .with_command(liquibase_command)
    )
    liquibase_container.start()

    logs_text = poll_liquibase_logs(liquibase_container)
    print("Liquibase container logs:")
    print(logs_text)
    liquibase_container.stop()


@pytest.fixture(scope="session")
def postgres_container():
    postgres_container_instance = PostgresContainer("postgres:15")
    postgres_container_instance.start()

    # Reset the schema for tests
    connection_url = postgres_container_instance.get_connection_url()
    reset_database_schema(connection_url)

    # Run Liquibase migration to set up the database schema
    jdbc_url = get_jdbc_url_from_container(postgres_container_instance)
    run_liquibase_migration(jdbc_url)

    yield postgres_container_instance
    postgres_container_instance.stop()


@pytest.fixture(scope="session")
def db_engine(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def TestingSessionLocal(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture(scope="function")
def db_session(TestingSessionLocal):
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clear_test_data(db_session):
    """
    Clears data from test tables between test runs.
    """
    truncate_statement = text(
        "TRUNCATE TABLE wms_schema.stock, wms_schema.locations, wms_schema.products RESTART IDENTITY CASCADE;"
    )
    db_session.execute(truncate_statement)
    db_session.commit()


@pytest.fixture(scope="function")
def client_with_db(TestingSessionLocal):
    """
    Provides a TestClient instance with a database dependency override.
    """

    def override_get_db():
        test_database = TestingSessionLocal()
        try:
            yield test_database
        finally:
            test_database.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
