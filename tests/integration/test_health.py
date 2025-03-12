import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError
from app.routers.health import check_database_connectivity

# Mark all tests in this file to require the database
pytestmark = pytest.mark.db


def test_liveness_endpoint(client_with_db):
    """Test the liveness endpoint returns a 200 status code and UP status."""
    response = client_with_db.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "timestamp" in data
    # Liveness either shouldn't have components or should have it set to None
    assert "components" not in data or data["components"] is None


def test_readiness_endpoint_with_db(client_with_db):
    """
    Test the readiness endpoint with a live database connection.
    Should return a 200 status code and UP status for both application and database.
    """
    response = client_with_db.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "timestamp" in data
    assert "components" in data
    assert data["components"]["application"]["status"] == "UP"
    assert data["components"]["database"]["status"] == "UP"
    assert "details" in data["components"]["database"]
    assert "responseTime" in data["components"]["database"]["details"]

    # Verify response time is a reasonable value (should be in milliseconds)
    response_time = float(
        data["components"]["database"]["details"]["responseTime"].replace("ms", "")
    )
    assert 0 <= response_time < 5000  # Reasonable upper bound for database query time


def test_startup_endpoint_with_db(client_with_db):
    """
    Test the startup endpoint with a live database connection.
    Should return a 200 status code and UP status for both application and database.
    """
    response = client_with_db.get("/health/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "timestamp" in data
    assert "components" in data
    assert data["components"]["application"]["status"] == "UP"
    assert data["components"]["database"]["status"] == "UP"
    assert "responseTime" in data["components"]["database"]["details"]


def test_health_endpoint_with_db(client_with_db):
    """
    Test the main health endpoint with a live database connection.
    Should return a 200 status code and UP status for all components.
    """
    response = client_with_db.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "timestamp" in data
    assert "components" in data
    assert data["components"]["application"]["status"] == "UP"
    assert data["components"]["database"]["status"] == "UP"
    assert "responseTime" in data["components"]["database"]["details"]


@pytest.mark.parametrize(
    "exception_class, error_msg, error_type",
    [
        (SQLAlchemyError, "Database connection error", "SQLAlchemyError"),
        (OperationalError, "Connection refused", "OperationalError"),
        (TimeoutError, "Database query timed out", "TimeoutError"),
        (Exception, "Unexpected runtime error", "Exception"),
    ],
    ids=["SQLAlchemyError", "OperationalError", "TimeoutError", "GenericException"],
)
def test_health_endpoint_when_db_down(
    client_with_db, exception_class, error_msg, error_type
):
    """
    Test health endpoint behavior with different types of database errors.
    Should return a 503 Service Unavailable with appropriate error details.
    """
    # Patch the check_database_connectivity function to simulate a database error
    with patch("app.routers.health.check_database_connectivity") as mock_db_check:
        mock_db_check.return_value = {
            "status": "DOWN",
            "details": {"error": error_msg, "errorType": error_type},
        }

        # Test all health endpoints that depend on DB
        endpoints = ["/health", "/health/readiness", "/health/startup"]

        for endpoint in endpoints:
            response = client_with_db.get(endpoint)
            assert (
                response.status_code == 503
            ), f"Expected 503 for {endpoint} with {error_type}"

            data = response.json()
            assert "detail" in data
            assert data["detail"]["status"] == "DOWN"
            assert data["detail"]["components"]["database"]["status"] == "DOWN"
            assert (
                data["detail"]["components"]["database"]["details"]["error"]
                == error_msg  # noqa: W503
            )
            assert (
                data["detail"]["components"]["database"]["details"]["errorType"]
                == error_type  # noqa: W503
            )


def test_database_component_detail(client_with_db):
    """Test that database component includes detailed information."""
    response = client_with_db.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "details" in data["components"]["database"]
    assert "responseTime" in data["components"]["database"]["details"]
    # Verify timestamp format (ISO 8601)
    import re

    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", data["timestamp"])


def test_slow_database_still_reports_up(client_with_db):
    """
    Test that a slow database still reports as UP with high response time.
    """
    with patch("app.routers.health.check_database_connectivity") as mock_db_check:
        # Simulate a very slow but successful DB query
        mock_db_check.return_value = {
            "status": "UP",
            "details": {"responseTime": "4999.99ms"},  # Very slow but still successful
        }

        response = client_with_db.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert data["components"]["database"]["status"] == "UP"
        assert data["components"]["database"]["details"]["responseTime"] == "4999.99ms"


def test_partial_component_failure(client_with_db):
    """
    Test scenario where one component is down but another is up.
    Overall status should be DOWN if any component is DOWN.
    """
    with patch("app.routers.health.check_database_connectivity") as mock_db_check:
        # Simulate database down but application up
        mock_db_check.return_value = {
            "status": "DOWN",
            "details": {"error": "Connection error", "errorType": "ConnectionError"},
        }

        response = client_with_db.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert data["detail"]["status"] == "DOWN"
        assert data["detail"]["components"]["application"]["status"] == "UP"
        assert data["detail"]["components"]["database"]["status"] == "DOWN"


def test_database_connectivity_check_real(db_session):
    """
    Integration test for the database connectivity check function using a real database connection.
    """
    # Use the real database connection to check connectivity
    result = check_database_connectivity(db_session)

    # Verify the result structure and values
    assert result["status"] == "UP"
    assert "details" in result
    assert "responseTime" in result["details"]

    # Verify response time is a reasonable value
    response_time = float(result["details"]["responseTime"].replace("ms", ""))
    assert 0 <= response_time < 5000  # Reasonable upper bound


@pytest.mark.parametrize(
    "exception_to_raise, expected_status, expected_error_type",
    [
        (SQLAlchemyError("Test SQLAlchemy error"), "DOWN", "SQLAlchemyError"),
        (
            # Fix: Pass a real exception for the orig parameter instead of None
            OperationalError(
                "Test operational error",
                params=None,
                orig=Exception("DB connection error"),
            ),
            "DOWN",
            "OperationalError",
        ),
        (Exception("General exception"), "DOWN", "Exception"),
    ],
    ids=["SQLAlchemyError", "OperationalError", "GeneralException"],
)
def test_database_connectivity_check_exceptions(
    db_session, exception_to_raise, expected_status, expected_error_type
):
    """
    Test the behavior of check_database_connectivity with various exceptions.
    """
    with patch.object(db_session, "execute") as mock_execute:
        mock_execute.side_effect = exception_to_raise

        result = check_database_connectivity(db_session)

        assert result["status"] == expected_status
        assert result["details"]["errorType"] == expected_error_type
        assert "error" in result["details"]
