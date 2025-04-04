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
from typing import Any, Dict, List
import json
import app.repository.product_repository as product_repo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample test data that matches what's in the contract
# IMPORTANT: Product IDs must be integers according to the contract
TEST_PRODUCTS = [
    {
        "id": 1,  # Integer ID as required by contract
        "name": "Product 1",
        "description": "Product 1 description",
        "category": "Category A",
        "sku": "SKU123",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-02T00:00:00Z",
    },
    {
        "id": 2,  # Integer ID as required by contract
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

# Dictionary to store original module functions for later restoration
_original_functions: Dict[str, Any] = {}


@provider_state_router.post("/_pact/provider_states/")
async def provider_states(request_body: dict):
    """
    Handle provider state setup for Pact testing.

    This endpoint receives state setup requests from the Pact verifier and
    configures the test environment accordingly.
    """
    state = request_body.get("state")
    params = request_body.get("params", {})
    logger.info("Setting up provider state: %s with params: %s", state, params)

    # Handle different provider states
    if state == "products exist":
        logger.info("Provider state: Setting up test products")
        # In a real implementation, this would:
        # 1. Clear the test database's product table
        # 2. Insert the test products that match what's expected in the contract

        # For this example, we're using a mock/override approach at the repository level
        # This is more reliable than mocking at the module level
        if hasattr(product_repo, "list_products"):
            # Store original function for restoration later
            if "list_products" not in _original_functions:
                _original_functions["list_products"] = product_repo.list_products

            # Override with test data
            def mock_list_products(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
                logger.info(
                    "Mock list_products called, returning test data with integer IDs"
                )
                # Verify that all test products have integer IDs
                for product in TEST_PRODUCTS:
                    assert isinstance(
                        product["id"], int
                    ), f"Product ID must be an integer, got {type(product['id'])}"
                return TEST_PRODUCTS

            # Replace the function
            product_repo.list_products = mock_list_products
            logger.info("Successfully mocked product_repo.list_products")

    # Add more states as needed based on your contracts
    # For example:
    elif state == "no products exist":
        logger.info("Provider state: Setting up empty products list")
        if hasattr(product_repo, "list_products"):
            if "list_products" not in _original_functions:
                _original_functions["list_products"] = product_repo.list_products

            def mock_empty_list_products(
                *args: Any, **kwargs: Any
            ) -> List[Dict[str, Any]]:
                logger.info("Mock empty list_products called, returning empty list")
                return []

            product_repo.list_products = mock_empty_list_products
            logger.info(
                "Successfully mocked product_repo.list_products with empty response"
            )

    # You can add more states based on other contract requirements

    return {"status": "success"}


# Add the provider state router to the test app
app.include_router(provider_state_router)


# Helper function to customize requests for Pact Verifier
def request_customizer(request):
    """
    Customize requests to ensure redirects are followed and headers are properly set.
    This is a clean way to handle redirects without modifying the application routes.
    """
    modified_request = {**request}

    # Set allow_redirects to True to follow redirects
    modified_request["allow_redirects"] = True

    # Ensure proper headers are set
    if "headers" not in modified_request:
        modified_request["headers"] = {}

    # Always set Accept header for JSON
    modified_request["headers"]["Accept"] = "application/json"

    # Log the customized request
    path = request.get("path", "")
    logger.info(f"Customizing request for path: {path}")
    logger.info(f"Modified request: {modified_request}")

    return modified_request


@pytest.mark.contract
class InventoryManagementContractsTest(unittest.TestCase):
    """
    Tests all Pact contracts for the WMS Inventory Management Service.

    This test verifies that the inventory management service fulfills all contracts
    expected by consumer services by checking all pact files in the specified
    directory. This includes contracts from UI, Order Processing, and any other
    service that relies on inventory management.
    """

    @classmethod
    def wait_for_server(cls, host: str, port: int, timeout: int = 10) -> None:
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
        """Pact verification test for all Inventory Management service contracts."""
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
                    logger.info(
                        f"Processing contract for consumer: {pact_content.get('consumer', {}).get('name', 'unknown')}"
                    )

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

            if output[0] != 0:
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

        # Restore any mocked functions
        for module_name, original_func in _original_functions.items():
            if hasattr(product_repo, module_name):
                setattr(product_repo, module_name, original_func)

        # Clear the original functions dictionary
        _original_functions.clear()
