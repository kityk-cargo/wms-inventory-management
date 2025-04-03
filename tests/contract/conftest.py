"""
Pytest configuration for contract tests.

This module provides fixtures and configurations specific to contract testing.
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment for contract tests.

    This fixture:
    1. Sets up environment variables needed for testing
    2. Could set up test databases or other resources
    3. Tears down resources after tests
    """
    # Setup environment variables for testing
    os.environ["ENVIRONMENT"] = "test"

    # Here you would typically set up test data in a database
    # For example:
    # - Connect to test database
    # - Clear existing data
    # - Insert test data that matches what's expected in the contracts

    logger.info("Contract test environment set up")

    yield

    # Cleanup after tests
    logger.info("Contract test environment tear down complete")
