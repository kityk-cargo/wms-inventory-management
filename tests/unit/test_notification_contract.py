"""
This consumer test uses Pact to generate the expected contract for the notification service.
"""

import os
from types import SimpleNamespace
import pytest
from app.services.notification import send_low_stock_alert
from typing import Final

# Remove local pact initialization; use the shared pact_setup fixture instead.
pytestmark = pytest.mark.usefixtures("pact_setup")
# Optionally, retain constants if required.
PACT_MOCK_HOST = "localhost"
PACT_MOCK_PORT = 1234

NOTIFICATION_PATH: Final[str] = "/api/v1/notifications"


@pytest.mark.parametrize(
    "scenario, test_description, expected_status, expected_response",
    [
        (
            "success",
            "Low stock alert notification sends successfully",
            200,
            {"status": "success", "message": "Alert sent successfully"},
        ),
        (
            "failure",
            "Low stock alert notification was not delivered",
            500,
            {
                "status": "error",
                "message": "Failed to deliver notification",
                "details": "Simulated failure for testing",
            },
        ),
    ],
    ids=["Low stock alert success", "Low stock alert failure"],
)
def test_send_low_stock_alert_contract(
    pact_setup, scenario, test_description, expected_status, expected_response
):
    """
    [Contract] Test sending low stock alert notification contract.
    """
    # Arrange
    expected_payload = {
        "level": "Warning",
        "category": "stock alerts",
        "title": "Low stock alert for product 1 at location 101",
        "message": "Stock level is 15. Consider restocking.",
    }
    interaction_description = (
        "a low stock alert notification"
        if scenario == "success"
        else "a low stock alert notification that fails"
    )
    provider_state = (
        "Notification service is configured for success"
        if scenario == "success"
        else "Notification service is experiencing a failure"
    )
    pact_setup.given(provider_state).upon_receiving(
        interaction_description
    ).with_request(
        "post",
        NOTIFICATION_PATH,
        body=expected_payload,
        headers={"Content-Type": "application/json"},
    ).will_respond_with(
        status=expected_status, body=expected_response
    )

    # Act
    with pact_setup:
        os.environ[
            "NOTIFICATION_SERVICE_URL"
        ] = f"http://{PACT_MOCK_HOST}:{PACT_MOCK_PORT}{NOTIFICATION_PATH}"
        dummy_stock_data = SimpleNamespace(product_id=1, location_id=101, quantity=15)
        result = send_low_stock_alert(dummy_stock_data)
        # Assert
        assert result == expected_response

    pact_setup.verify()
