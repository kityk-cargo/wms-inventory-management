import os
import logging
import requests


def send_low_stock_alert(stock):
    url = os.environ.get("NOTIFICATION_SERVICE_URL")
    if not url:
        logging.critical(
            "notification-url-undefined: No URL defined for notification service, skipping alert"
        )
        return
    payload = {
        "level": "Warning",
        "category": "stock alerts",
        "title": f"Low stock alert for product {stock.product_id} at location {stock.location_id}",
        "message": f"Stock level is {stock.quantity}. Consider restocking.",
    }
    try:
        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.exception(f"alert-failed: Failed to send notification: {e}")
        # Return the expected error response on failure
        return {
            "status": "error",
            "message": "Failed to deliver notification",
            "details": "Connection error",
        }
    except Exception as e:
        logging.exception(f"alert-failed: Unexpected error: {e}")
        return {
            "status": "error",
            "message": "Failed to deliver notification",
            "details": "Connection error",
        }
