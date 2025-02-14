import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer  # type: ignore
from testcontainers.core.container import DockerContainer  # type: ignore
from app.database import get_db
from app.models import Base
from app.main import app


# --- Database Container Fixture ---
@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer(
        "postgres:15"
    )  # todo: the version in constants global to WMS?
    container.start()
    # Create schema if not exists
    engine = create_engine(container.get_connection_url())
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS wms_schema;"))
    engine.dispose()

    # Run liquibase migration via Docker container
    jdbc_url = container.get_connection_url().replace(
        "postgresql://", "jdbc:postgresql://"
    )
    username = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    changelog_file = "001_initial_schema.sql"
    changelog_host = os.getenv("LIQUIBASE_CHANGELOG_HOST")
    changelog_container = "/liquibase/changelog"
    liquibase_container = (
        DockerContainer("liquibase/liquibase")
        .with_volume_mapping(changelog_host, changelog_container)
        .with_command(
            f"--url={jdbc_url} --username={username} --password={password} "
            f"--changeLogFile={changelog_container}/{changelog_file} update"
        )
    )
    liquibase_container.start()
    liquibase_container.stop()

    yield container
    container.stop()


# --- Database Engine and Session --------------------------------------
@pytest.fixture(scope="session")
def db_engine(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def TestingSessionLocal(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database(db_engine):
    Base.metadata.create_all(bind=db_engine)
    yield
    Base.metadata.drop_all(bind=db_engine)


@pytest.fixture(scope="function")
def db_session(TestingSessionLocal):
    session = TestingSessionLocal()
    yield session
    session.close()


# New: Autouse fixture to clear data (shard data) before each test.
@pytest.fixture(autouse=True)
def clear_data(db_session):
    from sqlalchemy import text  # ensure text is imported

    db_session.execute(
        text(
            "TRUNCATE TABLE wms_schema.stock, wms_schema.locations, wms_schema.products RESTART IDENTITY CASCADE;"
        )
    )
    db_session.commit()


# Fixture: Test client that uses the test database.
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
