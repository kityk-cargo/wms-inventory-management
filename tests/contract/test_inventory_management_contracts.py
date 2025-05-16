import unittest
import os
import logging
import threading
import time
import requests
import uvicorn
from pact import Verifier  # type: ignore # missing stubs for pact
from app.main import app
import io
import contextlib
import glob
from fastapi import APIRouter
import pytest
import json
import app.repository.product_repository as product_repo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data that matches the contract requirements
# Product IDs must be integers according to the contract
TEST_PRODUCTS = [
    {
        "id": 1,
        "name": "Product 1",
        "description": "Product 1 description",
        "category": "Category A",
        "sku": "SKU123",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-02T00:00:00Z",
    },
    {
        "id": 2,
        "name": "Product 2",
        "description": "Product 2 description",
        "category": "Category B",
        "sku": "SKU456",
        "created_at": "2023-01-03T00:00:00Z",
        "updated_at": "2023-01-04T00:00:00Z",
    },
]

# Create a test-only router for provider states
provider_state_router = APIRouter()


class StateManager:
    """Manages provider state for testing different contract scenarios."""

    def __init__(self):
        self.current_state = None
        self.params = {}
        self.simulate_server_error = False

    def set_state(self, state, params=None):
        self.current_state = state
        self.params = params or {}
        self.simulate_server_error = state == "product service is experiencing issues"

    def get_state(self):
        return self.current_state, self.params


# Global instance of StateManager
state_manager = StateManager()


# Mock product repository implementations
def mock_list_products(*args, **kwargs):
    """Returns products based on current provider state"""
    state, _ = state_manager.get_state()
    logger.info(f"Mock list_products called with state: {state}")

    if state == "no products exist":
        return []

    # Default behavior for "products exist" or any other state
    for product in TEST_PRODUCTS:
        assert isinstance(
            product["id"], int
        ), f"Product ID must be an integer, got {type(product['id'])}"
    return TEST_PRODUCTS


def mock_get_by_id(db, product_id):
    """Returns a product by ID based on current provider state"""
    state, _ = state_manager.get_state()
    logger.info(f"Mock get_by_id called with ID: {product_id} and state: {state}")

    if state_manager.simulate_server_error:
        raise Exception("Simulated server error")

    if state == "product with ID 9999 does not exist":
        return None

    return next((p for p in TEST_PRODUCTS if p["id"] == product_id), None)


@provider_state_router.post("/_pact/provider_states/")
async def provider_states(request_body: dict):
    """Handles provider state setup for Pact testing"""
    state = request_body.get("state")
    params = request_body.get("params", {})
    logger.info("Setting up provider state: %s with params: %s", state, params)

    # Update the state manager
    state_manager.set_state(state, params)

    # Update the app's flag for server error simulation
    setattr(app, "simulate_server_error", state_manager.simulate_server_error)

    return {"status": "success"}


# Add the provider state router to the test app
app.include_router(provider_state_router)


def request_customizer(request):
    """Customizes requests for Pact Verifier to handle redirects and headers"""
    modified_request = {**request}
    modified_request["allow_redirects"] = True

    # Ensure proper headers
    if "headers" not in modified_request:
        modified_request["headers"] = {}
    modified_request["headers"]["Accept"] = "application/json"

    path = request.get("path", "")
    logger.info(f"Customizing request for path: {path}")
    logger.info(f"Modified request: {modified_request}")

    return modified_request


@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    """Sets up all mocks needed for the tests"""
    monkeypatch.setattr(product_repo, "list_products", mock_list_products)
    monkeypatch.setattr(product_repo, "get_by_id", mock_get_by_id)
    yield
    # No need to manually restore - monkeypatch handles this automatically


@pytest.mark.contract
class InventoryManagementContractsTest(unittest.TestCase):
    """Tests Pact contracts for the WMS Inventory Management Service"""

    @classmethod
    def wait_for_server(cls, host: str, port: int, timeout: int = 10) -> None:
        """Waits for the test server to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"http://{host}:{port}/")
                if resp.status_code < 500:
                    return
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError("Uvicorn server did not start in time")

    @classmethod
    def setUpClass(cls):
        logger.info("Starting uvicorn server in background...")
        cls.host = "127.0.0.1"
        cls.port = 8000
        config = uvicorn.Config(app, host=cls.host, port=cls.port, log_level="info")
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()
        cls.wait_for_server(cls.host, cls.port)
        logger.info("Uvicorn server is up and running")

        # Initialize the server error simulation flag
        setattr(app, "simulate_server_error", False)

        # Verify the endpoint works directly
        try:
            resp = requests.get(
                f"http://{cls.host}:{cls.port}/api/v1/products",
                headers={"Accept": "application/json"},
                allow_redirects=True,
            )
            logger.info(f"Test request to products endpoint: {resp.status_code}")
            logger.info(f"Response: {resp.text}")
        except Exception as e:
            logger.error(f"Error testing products endpoint: {e}")

    def test_provider(self):
        """Verifies all Inventory Management service contracts"""
        logger.info("Starting Pact verification test...")

        # Set up the default directory path
        default_pact_dir = "../wms-contracts/pact/rest/wms_inventory_management"
        pact_dir = os.getenv("PACT_DIR_PATH", default_pact_dir)

        # Check if the directory exists
        if not os.path.exists(pact_dir):
            logger.error("Pact directory not found at path: %s", pact_dir)
            raise FileNotFoundError(f"Pact directory not found: {pact_dir}")

        # Find all pact files in the directory
        pact_files = glob.glob(os.path.join(pact_dir, "*.json"))

        if not pact_files:
            logger.error("No Pact files found in directory: %s", pact_dir)
            raise FileNotFoundError(f"No Pact files found in: {pact_dir}")

        logger.info("Found %d Pact files to verify: %s", len(pact_files), pact_files)

        # Initialize success flag
        verification_successful = True
        all_outputs = []

        # Verify each pact file
        for pact_file in pact_files:
            logger.info("Verifying Pact file: %s", pact_file)

            # Examine the pact file to understand what needs to be verified
            try:
                with open(pact_file, "r") as f:
                    pact_content = json.load(f)
                    consumer_name = pact_content.get("consumer", {}).get(
                        "name", "unknown"
                    )
                    logger.info(f"Processing contract for consumer: {consumer_name}")

                    # Extract interactions to help debug issues
                    for idx, interaction in enumerate(
                        pact_content.get("interactions", [])
                    ):
                        logger.info(
                            f"Interaction {idx}: {interaction.get('description')}"
                        )
                        logger.info(
                            f"  Method: {interaction.get('request', {}).get('method')}"
                        )
                        logger.info(
                            f"  Path: {interaction.get('request', {}).get('path')}"
                        )
            except Exception as e:
                logger.error(f"Error reading Pact file: {e}")

            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                verifier = Verifier(
                    provider="wms_inventory_management",
                    provider_base_url=f"http://{self.__class__.host}:{self.__class__.port}",
                    enable_pending=True,
                    publish_verification_results=False,
                    provider_verify_options={
                        "follow_redirects": True,
                        "request_customizer": request_customizer,
                    },
                )

                output = verifier.verify_pacts(
                    pact_file,
                    provider_states_setup_url=f"http://{self.__class__.host}:{self.__class__.port}/_pact/provider_states/",
                )
                verifier_output = buf.getvalue()
                all_outputs.append(
                    f"File: {os.path.basename(pact_file)}\n{verifier_output}"
                )

            logger.info(
                "Pact verification for %s: %s",
                pact_file,
                "SUCCESS" if output[0] == 0 else "FAILED",
            )

            pact_verification_failed: bool = output[0] != 0

            if pact_verification_failed:
                verification_successful = False
                logger.error("Pact verification failed for: %s", pact_file)
                logger.error(f"Verification output: {verifier_output}")

        # Log all outputs at the end
        logger.info("All Pact verification outputs:\n%s", "\n".join(all_outputs))

        # Fail the test if any verification failed
        if not verification_successful:
            self.fail("One or more Pact verifications failed. See logs for details.")
        else:
            logger.info("All Pact verifications passed successfully")

    @classmethod
    def tearDownClass(cls):
        logger.info("Signaling uvicorn server to shutdown...")
        cls.server.should_exit = True
        cls.server_thread.join()
        logger.info("Uvicorn server shutdown complete")
