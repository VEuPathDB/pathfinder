"""Tests for ai.tools.wdk_error_handler -- pure error-mapping logic."""

from veupath_chatbot.ai.tools.wdk_error_handler import handle_wdk_step_error
from veupath_chatbot.platform.errors import WDKError


def test_404_maps_to_stale_step_message():
    err = WDKError("GET /users/current/steps/99 -> HTTP 404", 404)
    result = handle_wdk_step_error(
        err, wdk_step_id=99, action="read", fallback_message="reading records"
    )
    assert result["ok"] is False
    assert result["code"] == "WDK_ERROR"
    assert "Step not found" in str(result["message"])
    assert "stale" in str(result["message"])
    assert result["wdk_step_id"] == 99
    assert result["http_status"] == 404


def test_400_with_reportname_maps_to_integration_error():
    err = WDKError(
        'POST /temporary-results -> HTTP 400: JSONObject["reportName"] not found.',
        400,
    )
    result = handle_wdk_step_error(
        err, wdk_step_id=42, action="download", fallback_message="downloading"
    )
    assert result["ok"] is False
    assert result["code"] == "WDK_ERROR"
    assert "reportName" in str(result["message"])
    assert result["http_status"] == 400


def test_401_maps_to_auth_error():
    err = WDKError("Unauthorized", 401)
    result = handle_wdk_step_error(
        err, wdk_step_id=10, action="read", fallback_message="reading"
    )
    assert result["ok"] is False
    assert "Not authorized to read" in str(result["message"])
    assert result["http_status"] == 401


def test_403_maps_to_auth_error():
    err = WDKError("Forbidden", 403)
    result = handle_wdk_step_error(
        err, wdk_step_id=10, action="download", fallback_message="downloading"
    )
    assert "Not authorized to download" in str(result["message"])
    assert result["http_status"] == 403


def test_500_maps_to_temporary_unavailable():
    err = WDKError("Internal Server Error", 500)
    result = handle_wdk_step_error(
        err, wdk_step_id=5, action="read", fallback_message="reading step records"
    )
    assert "temporarily unavailable" in str(result["message"])
    assert "reading step records" in str(result["message"])
    assert result["http_status"] == 500


def test_502_maps_to_temporary_unavailable():
    err = WDKError("Bad Gateway", 502)
    result = handle_wdk_step_error(
        err, wdk_step_id=5, action="read", fallback_message="fetching results"
    )
    assert "temporarily unavailable" in str(result["message"])
    assert result["http_status"] == 502


def test_generic_400_without_reportname_falls_through():
    err = WDKError("Bad request: invalid param", 400)
    result = handle_wdk_step_error(
        err, wdk_step_id=7, action="read", fallback_message="reading"
    )
    assert result["ok"] is False
    assert "rejected request for step 7" in str(result["message"])
    assert result["http_status"] == 400


def test_422_falls_through_to_generic():
    err = WDKError("Unprocessable entity", 422)
    result = handle_wdk_step_error(
        err, wdk_step_id=8, action="read", fallback_message="reading"
    )
    assert result["ok"] is False
    assert "rejected request for step 8" in str(result["message"])
    assert result["http_status"] == 422
