"""Unit tests for veupath_chatbot.integrations.veupathdb.temporary_results.

Tests TemporaryResultsAPI: create_temporary_result, get_download_url,
get_step_preview, and the _extract_download_url static method.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veupath_chatbot.integrations.veupathdb.temporary_results import TemporaryResultsAPI


def _make_api(user_id: str = "current") -> tuple[TemporaryResultsAPI, MagicMock]:
    """Create TemporaryResultsAPI with a mocked client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    api = TemporaryResultsAPI(client)
    api.user_id = user_id
    return api, client


# ---------------------------------------------------------------------------
# _extract_download_url (static method, no mocking needed)
# ---------------------------------------------------------------------------


class TestExtractDownloadUrl:
    """Tests for the static _extract_download_url method."""

    def test_direct_url_field(self) -> None:
        assert (
            TemporaryResultsAPI._extract_download_url({"url": "https://x/dl"})
            == "https://x/dl"
        )

    def test_download_url_field(self) -> None:
        assert (
            TemporaryResultsAPI._extract_download_url({"downloadUrl": "https://x/dl"})
            == "https://x/dl"
        )

    def test_download_url_snake_case(self) -> None:
        assert (
            TemporaryResultsAPI._extract_download_url({"download_url": "https://x/dl"})
            == "https://x/dl"
        )

    def test_links_download_field(self) -> None:
        payload = {"links": {"download": "https://x/dl"}}
        assert TemporaryResultsAPI._extract_download_url(payload) == "https://x/dl"

    def test_links_url_field(self) -> None:
        payload = {"links": {"url": "https://x/dl"}}
        assert TemporaryResultsAPI._extract_download_url(payload) == "https://x/dl"

    def test_empty_payload_returns_empty(self) -> None:
        assert TemporaryResultsAPI._extract_download_url({}) == ""

    def test_blank_url_returns_empty(self) -> None:
        assert TemporaryResultsAPI._extract_download_url({"url": "  "}) == ""

    def test_non_string_url_returns_empty(self) -> None:
        assert TemporaryResultsAPI._extract_download_url({"url": 123}) == ""

    def test_links_not_dict_returns_empty(self) -> None:
        assert TemporaryResultsAPI._extract_download_url({"links": "not_dict"}) == ""


# ---------------------------------------------------------------------------
# _ensure_session
# ---------------------------------------------------------------------------


class TestEnsureSession:
    """Session resolution resolves the WDK user ID once."""

    async def test_resolves_user_id(self) -> None:
        api, client = _make_api()
        with patch(
            "veupath_chatbot.integrations.veupathdb.strategy_api.base.resolve_wdk_user_id",
            new_callable=AsyncMock,
            return_value="12345",
        ):
            await api._ensure_session()
        assert api.user_id == "12345"
        assert api._session_initialized is True

    async def test_does_not_resolve_twice(self) -> None:
        api, client = _make_api()
        with patch(
            "veupath_chatbot.integrations.veupathdb.strategy_api.base.resolve_wdk_user_id",
            new_callable=AsyncMock,
            return_value="12345",
        ) as mock_resolve:
            await api._ensure_session()
            await api._ensure_session()
        mock_resolve.assert_awaited_once()

    async def test_keeps_current_if_resolve_returns_none(self) -> None:
        api, client = _make_api()
        with patch(
            "veupath_chatbot.integrations.veupathdb.strategy_api.base.resolve_wdk_user_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await api._ensure_session()
        assert api.user_id == "current"


# ---------------------------------------------------------------------------
# create_temporary_result
# ---------------------------------------------------------------------------


class TestCreateTemporaryResult:
    """Tests for creating temporary results."""

    async def test_basic_creation(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {"id": "abc123", "url": "https://x/dl"}

        result = await api.create_temporary_result(step_id=42)

        client.post.assert_awaited_once_with(
            "/temporary-results",
            json={
                "stepId": 42,
                "reportName": "standard",
            },
        )
        assert result["id"] == "abc123"

    async def test_custom_reporter_and_format_config(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {"id": "abc"}

        config = {"type": "json"}
        await api.create_temporary_result(
            step_id=42, reporter="fullRecord", format_config=config
        )

        call_args = client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["reportName"] == "fullRecord"
        assert payload["reportConfig"] == {"type": "json"}

    async def test_uses_report_name_not_reporter_name(self) -> None:
        """WDK requires 'reportName', not 'reporterName' (see source comment)."""
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {"id": "x"}

        await api.create_temporary_result(step_id=1)

        payload = client.post.call_args.kwargs["json"]
        assert "reportName" in payload
        assert "reporterName" not in payload


# ---------------------------------------------------------------------------
# get_download_url
# ---------------------------------------------------------------------------


class TestGetDownloadUrl:
    """Tests for get_download_url which creates a temporary result and extracts URL."""

    async def test_returns_url_from_direct_response(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {
            "id": "result1",
            "url": "https://plasmodb.org/download/result1.csv",
        }

        url = await api.get_download_url(step_id=42, format="csv")
        assert url == "https://plasmodb.org/download/result1.csv"

    async def test_csv_format_uses_standard_reporter(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {"url": "https://x/dl"}

        await api.get_download_url(step_id=42, format="csv")

        payload = client.post.call_args.kwargs["json"]
        assert payload["reportName"] == "standard"

    async def test_json_format_uses_full_record_reporter(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {"url": "https://x/dl"}

        await api.get_download_url(step_id=42, format="json")

        payload = client.post.call_args.kwargs["json"]
        assert payload["reportName"] == "fullRecord"

    async def test_with_attributes(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {"url": "https://x/dl"}

        await api.get_download_url(
            step_id=42, format="csv", attributes=["gene_name", "product"]
        )

        payload = client.post.call_args.kwargs["json"]
        assert payload.get("reportConfig", {}).get("attributes") == [
            "gene_name",
            "product",
        ]

    async def test_polls_when_no_direct_url(self) -> None:
        """When initial response has no URL but has an ID, poll for it."""
        api, client = _make_api("12345")
        api._session_initialized = True
        # Initial create returns ID but no URL
        client.post.return_value = {"id": "result1"}
        # First poll: no URL yet. Second poll: URL ready.
        client.get.side_effect = [
            {"id": "result1", "status": "PENDING"},
            {"id": "result1", "url": "https://x/dl/result1.csv"},
        ]

        url = await api.get_download_url(step_id=42, format="csv")
        assert url == "https://x/dl/result1.csv"
        assert client.get.call_count == 2

    async def test_raises_when_no_url_and_no_id(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {}

        with pytest.raises(RuntimeError, match="download URL or a temporary result id"):
            await api.get_download_url(step_id=42, format="csv")


# ---------------------------------------------------------------------------
# get_step_preview
# ---------------------------------------------------------------------------


class TestGetStepPreview:
    """Tests for get_step_preview which uses the standard report endpoint."""

    async def test_basic_preview(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {
            "records": [{"id": [{"name": "source_id", "value": "PF3D7_0100100"}]}],
            "meta": {"totalCount": 1},
        }

        await api.get_step_preview(step_id=42, limit=10)

        client.post.assert_awaited_once()
        call_args = client.post.call_args
        assert "/steps/42/reports/standard" in call_args.args[0]
        payload = call_args.kwargs["json"]
        assert payload["reportConfig"]["pagination"]["numRecords"] == 10

    async def test_preview_with_attributes(self) -> None:
        api, client = _make_api("12345")
        api._session_initialized = True
        client.post.return_value = {"records": [], "meta": {"totalCount": 0}}

        await api.get_step_preview(step_id=42, attributes=["gene_name", "product"])

        payload = client.post.call_args.kwargs["json"]
        assert payload["reportConfig"]["attributes"] == ["gene_name", "product"]
