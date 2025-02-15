import os
import platform
import time
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

# Load environment variables
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env.test")
)


def convert_path_for_docker(path: str) -> str:
    abs_path = os.path.abspath(path)
    drive, rest = os.path.splitdrive(abs_path)
    drive = drive.lower().rstrip(":")
    rest = rest.replace("\\", "/")
    if not rest.endswith("/"):
        rest += "/"
    return f"/{drive}{rest}"


@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer("postgres:15")
    container.start()

    # Create schema if not exists
    engine = create_engine(container.get_connection_url())
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS wms_schema;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS wms_schema;"))
    engine.dispose()

    # Run liquibase migration via Docker container
    container_conn_url = container.get_connection_url()
    parsed_url = urlparse(container_conn_url)
    host_ip = (
        "host.docker.internal"
        if platform.system().lower() == "windows"
        else "172.17.0.1"
    )
    exposed_port = container.get_exposed_port(5432)
    db_name = parsed_url.path.lstrip("/")
    jdbc_url_no_auth = f"jdbc:postgresql://{host_ip}:{exposed_port}/{db_name}"
    username = "test"
    password = "test"
    changelog_file = "changelog.xml"

    changelog_host = os.getenv("LIQUIBASE_CHANGELOG_HOST")
    changelog_host_abs = (
        convert_path_for_docker(changelog_host) if changelog_host else changelog_host
    )
    print(f"Using changelog file at: {changelog_host_abs}")

    changelog_container = "/lb"
    liquibase_version = os.getenv("LIQUIBASE_VERSION", "4.31.0")
    command_str = (
        f"--log-level=info --url={jdbc_url_no_auth} --username={username} --password={password} "
        f"--changeLogFile={changelog_file} --searchPath={changelog_container}/db update"
    )
    liquibase_container = (
        DockerContainer(f"liquibase/liquibase:{liquibase_version}")
        .with_volume_mapping(changelog_host_abs, changelog_container)
        .with_command(command_str)
    )
    liquibase_container.start()

    timeout = 30
    poll_interval = 1
    start_time = time.time()
    while True:
        logs = liquibase_container.get_logs()
        logs_str = logs.decode("utf-8") if isinstance(logs, bytes) else logs
        if isinstance(logs_str, tuple):
            logs_str = "".join(
                s.decode("utf-8") if isinstance(s, bytes) else s for s in logs_str
            )
        if "Liquibase command 'update' was executed successfully" in logs_str:
            break
        if time.time() - start_time > timeout:
            print(f"Logs: {logs_str}")
            raise Exception("Liquibase migration timed out")
        time.sleep(poll_interval)

    print("Liquibase container logs:")
    print(logs_str)
    liquibase_container.stop()

    yield container
    container.stop()


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
def clear_data(db_session):
    db_session.execute(
        text(
            "TRUNCATE TABLE wms_schema.stock, wms_schema.locations, wms_schema.products RESTART IDENTITY CASCADE;"
        )
    )
    db_session.commit()


@pytest.fixture(scope="function")
def client_with_db(TestingSessionLocal):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)
