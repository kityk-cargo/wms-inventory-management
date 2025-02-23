import logging
import requests
from types import SimpleNamespace

from app.services import notification


def dummy_stock():
    return SimpleNamespace(product_id=1, location_id=1, quantity=5)


def test_send_low_stock_alert_without_url(monkeypatch, caplog):
    """Should log a critical error when NOTIFICATION_SERVICE_URL is undefined."""
    # Arrange
    monkeypatch.delenv("NOTIFICATION_SERVICE_URL", raising=False)
    caplog.set_level(logging.CRITICAL)
    # Act
    result = notification.send_low_stock_alert(dummy_stock())
    # Assert
    assert any(
        "notification-url-undefined" in record.message for record in caplog.records
    )
    assert result is None


def fake_post(*args, **kwargs):
    raise requests.exceptions.ConnectionError("API unreachable")


def test_send_low_stock_alert_api_unreachable(monkeypatch, caplog):
    """Should log an error and return an error dict when notification API is unreachable."""
    # Arrange
    monkeypatch.setenv("NOTIFICATION_SERVICE_URL", "http://dummy-url")
    monkeypatch.setattr(notification.requests, "post", fake_post)
    caplog.set_level(logging.ERROR)
    # Act
    result = notification.send_low_stock_alert(dummy_stock())
    # Assert
    assert any("alert-failed" in record.message for record in caplog.records)
    expected = {
        "status": "error",
        "message": "Failed to deliver notification",
        "details": "API unreachable",
    }
    assert result == expected
