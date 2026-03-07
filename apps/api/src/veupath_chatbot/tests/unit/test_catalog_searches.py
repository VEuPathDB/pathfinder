"""Unit tests for services/catalog/searches.py.

Covers list_searches(), search_for_searches(), _search_for_searches_via_site_search(),
_resolve_record_type_for_search(), and the term_variants helper.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from veupath_chatbot.services.catalog.searches import (
    _resolve_record_type_for_search,
    _search_for_searches_via_site_search,
    list_searches,
    search_for_searches,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_discovery(
    record_types: list[Any] | None = None,
    searches_by_rt: dict[str, list[Any]] | None = None,
) -> MagicMock:
    """Build a mock discovery service."""
    discovery = MagicMock()
    discovery.get_record_types = AsyncMock(return_value=record_types or [])
    if searches_by_rt is not None:
        discovery.get_searches = AsyncMock(
            side_effect=lambda _site_id, rt: searches_by_rt.get(rt, [])
        )
    else:
        discovery.get_searches = AsyncMock(return_value=[])
    return discovery


def _mock_client(
    record_types: list[Any] | None = None,
    searches_by_rt: dict[str, list[Any]] | None = None,
) -> MagicMock:
    """Build a mock VEuPathDBClient."""
    client = MagicMock()
    client.get_record_types = AsyncMock(return_value=record_types or [])
    if searches_by_rt is not None:
        client.get_searches = AsyncMock(
            side_effect=lambda rt: searches_by_rt.get(rt, [])
        )
    else:
        client.get_searches = AsyncMock(return_value=[])
    return client


# ---------------------------------------------------------------------------
# list_searches
# ---------------------------------------------------------------------------


class TestListSearches:
    """Test the list_searches() function."""

    async def test_basic_list(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "name": "GenesByTaxonQuestion",
                        "displayName": "Genes by Taxon",
                        "description": "Find genes by organism",
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await list_searches("plasmodb", "gene")

        assert len(result) == 1
        assert result[0]["name"] == "GenesByTaxon"
        assert result[0]["displayName"] == "Genes by Taxon"
        assert result[0]["description"] == "Find genes by organism"

    async def test_prefers_url_segment_over_name(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {"urlSegment": "GenesByTaxon", "name": "GenesByTaxonQ"},
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await list_searches("plasmodb", "gene")

        assert result[0]["name"] == "GenesByTaxon"

    async def test_falls_back_to_name_when_no_url_segment(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [{"name": "GenesByTaxonQ"}],
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await list_searches("plasmodb", "gene")

        assert result[0]["name"] == "GenesByTaxonQ"

    async def test_filters_internal_searches(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "isInternal": False,
                    },
                    {
                        "urlSegment": "InternalSearch",
                        "displayName": "Internal",
                        "isInternal": True,
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await list_searches("plasmodb", "gene")

        assert len(result) == 1
        assert result[0]["name"] == "GenesByTaxon"

    async def test_skips_non_dict_entries(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    "not_a_dict",
                    None,
                    {"urlSegment": "GenesByTaxon"},
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await list_searches("plasmodb", "gene")

        assert len(result) == 1

    async def test_empty_list(self) -> None:
        discovery = _mock_discovery(searches_by_rt={"gene": []})
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await list_searches("plasmodb", "gene")

        assert result == []

    async def test_missing_optional_fields_default_to_empty(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [{"urlSegment": "GenesByTaxon"}],
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await list_searches("plasmodb", "gene")

        assert result[0]["displayName"] == ""
        assert result[0]["description"] == ""


# ---------------------------------------------------------------------------
# _search_for_searches_via_site_search
# ---------------------------------------------------------------------------


class TestSearchForSearchesViaSiteSearch:
    """Test the _search_for_searches_via_site_search() function."""

    async def test_basic_site_search_result(self) -> None:
        site_search_response = {
            "searchResults": {
                "documents": [
                    {
                        "primaryKey": ["GenesByTaxon", "gene"],
                        "hyperlinkName": "Genes by Taxon",
                        "foundInFields": {
                            "TEXT__search_description": ["Find genes by taxonomy"],
                        },
                    },
                ]
            }
        }
        with patch(
            "veupath_chatbot.services.catalog.searches.query_site_search",
            new_callable=AsyncMock,
            return_value=site_search_response,
        ):
            result = await _search_for_searches_via_site_search("plasmodb", "taxon")

        assert len(result) == 1
        assert result[0]["name"] == "GenesByTaxon"
        assert result[0]["displayName"] == "Genes by Taxon"
        assert result[0]["recordType"] == "gene"
        assert result[0]["description"] == "Find genes by taxonomy"

    async def test_returns_empty_on_exception(self) -> None:
        with patch(
            "veupath_chatbot.services.catalog.searches.query_site_search",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Network error"),
        ):
            result = await _search_for_searches_via_site_search("plasmodb", "taxon")

        assert result == []

    async def test_skips_bad_primary_keys(self) -> None:
        site_search_response = {
            "searchResults": {
                "documents": [
                    {"primaryKey": ["onlyone"]},  # too short
                    {"primaryKey": None},  # not a list
                    {"primaryKey": ["", "gene"]},  # empty search name
                    {"primaryKey": ["GenesByTaxon", ""]},  # empty record type
                    {
                        "primaryKey": ["ValidSearch", "gene"],
                        "hyperlinkName": "Valid",
                    },
                ]
            }
        }
        with patch(
            "veupath_chatbot.services.catalog.searches.query_site_search",
            new_callable=AsyncMock,
            return_value=site_search_response,
        ):
            result = await _search_for_searches_via_site_search("plasmodb", "test")

        assert len(result) == 1
        assert result[0]["name"] == "ValidSearch"

    async def test_respects_limit(self) -> None:
        docs = [
            {
                "primaryKey": [f"Search{i}", "gene"],
                "hyperlinkName": f"Search {i}",
            }
            for i in range(10)
        ]
        site_search_response = {"searchResults": {"documents": docs}}
        with patch(
            "veupath_chatbot.services.catalog.searches.query_site_search",
            new_callable=AsyncMock,
            return_value=site_search_response,
        ):
            result = await _search_for_searches_via_site_search(
                "plasmodb", "search", limit=3
            )

        assert len(result) == 3

    async def test_display_name_falls_back_to_found_in_fields(self) -> None:
        site_search_response = {
            "searchResults": {
                "documents": [
                    {
                        "primaryKey": ["GenesByTaxon", "gene"],
                        "hyperlinkName": "",
                        "foundInFields": {
                            "TEXT__search_displayName": ["<em>Genes</em> by Taxon"],
                        },
                    },
                ]
            }
        }
        with patch(
            "veupath_chatbot.services.catalog.searches.query_site_search",
            new_callable=AsyncMock,
            return_value=site_search_response,
        ):
            result = await _search_for_searches_via_site_search("plasmodb", "taxon")

        # HTML tags should be stripped
        assert result[0]["displayName"] == "Genes by Taxon"

    async def test_display_name_falls_back_to_search_name(self) -> None:
        site_search_response = {
            "searchResults": {
                "documents": [
                    {
                        "primaryKey": ["GenesByTaxon", "gene"],
                        "hyperlinkName": "",
                        "foundInFields": {},
                    },
                ]
            }
        }
        with patch(
            "veupath_chatbot.services.catalog.searches.query_site_search",
            new_callable=AsyncMock,
            return_value=site_search_response,
        ):
            result = await _search_for_searches_via_site_search("plasmodb", "taxon")

        assert result[0]["displayName"] == "GenesByTaxon"

    async def test_non_dict_docs_skipped(self) -> None:
        site_search_response = {
            "searchResults": {
                "documents": [
                    "not_a_dict",
                    {
                        "primaryKey": ["GenesByTaxon", "gene"],
                        "hyperlinkName": "Valid",
                    },
                ]
            }
        }
        with patch(
            "veupath_chatbot.services.catalog.searches.query_site_search",
            new_callable=AsyncMock,
            return_value=site_search_response,
        ):
            result = await _search_for_searches_via_site_search("plasmodb", "test")

        assert len(result) == 1


# ---------------------------------------------------------------------------
# search_for_searches
# ---------------------------------------------------------------------------


class TestSearchForSearches:
    """Test the search_for_searches() function."""

    async def test_uses_site_search_when_no_record_type(self) -> None:
        """When record_type is None, should try site-search first."""
        with (
            patch(
                "veupath_chatbot.services.catalog.searches._search_for_searches_via_site_search",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "name": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "",
                        "recordType": "gene",
                    }
                ],
            ),
            patch(
                "veupath_chatbot.services.catalog.searches.get_discovery_service",
                return_value=_mock_discovery(),
            ),
        ):
            result = await search_for_searches("plasmodb", None, "taxon")

        assert len(result) == 1
        assert result[0]["name"] == "GenesByTaxon"

    async def test_falls_back_to_discovery_when_site_search_empty(self) -> None:
        discovery = _mock_discovery(
            record_types=[{"urlSegment": "gene", "name": "Genes"}],
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "Find genes",
                        "name": "GenesByTaxonQ",
                    },
                ]
            },
        )
        with (
            patch(
                "veupath_chatbot.services.catalog.searches._search_for_searches_via_site_search",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "veupath_chatbot.services.catalog.searches.get_discovery_service",
                return_value=discovery,
            ),
        ):
            result = await search_for_searches("plasmodb", None, "taxon")

        assert len(result) == 1
        assert result[0]["name"] == "GenesByTaxon"

    async def test_filters_by_single_record_type(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "desc",
                        "name": "Q",
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", "gene", "taxon")

        assert len(result) == 1

    async def test_filters_by_record_type_list(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "desc",
                        "name": "Q",
                    },
                ],
                "transcript": [
                    {
                        "urlSegment": "TranscriptsByTaxon",
                        "displayName": "Transcripts by Taxon",
                        "description": "desc",
                        "name": "Q2",
                    },
                ],
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches(
                "plasmodb", ["gene", "transcript"], "taxon"
            )

        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"GenesByTaxon", "TranscriptsByTaxon"}

    async def test_deduplicates_record_type_list(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "desc",
                        "name": "Q",
                    },
                ],
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", ["gene", "gene"], "taxon")

        # Should not produce duplicate results
        assert len(result) == 1

    async def test_skips_internal_searches(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "desc",
                        "isInternal": False,
                    },
                    {
                        "urlSegment": "InternalSearch",
                        "displayName": "Internal",
                        "description": "internal",
                        "isInternal": True,
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", "gene", "taxon")

        names = [r["name"] for r in result]
        assert "InternalSearch" not in names

    async def test_scores_and_sorts_by_relevance(self) -> None:
        """Searches with more matching terms should rank higher."""
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByLocation",
                        "displayName": "Location Search",
                        "description": "Location only",
                        "name": "Q1",
                    },
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "Find genes by taxon classification",
                        "name": "GenesByTaxonQ",
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", "gene", "genes taxon")

        # GenesByTaxon should rank first (matches both terms)
        assert result[0]["name"] == "GenesByTaxon"

    async def test_term_variant_suffix_stripping(self) -> None:
        """Term variants should match singular/stemmed forms."""
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GeneByOrganism",
                        "displayName": "Gene by Organism",
                        "description": "",
                        "name": "Q",
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            # "genes" should match "gene" via stripping trailing "s"
            result = await search_for_searches("plasmodb", "gene", "genes")

        assert len(result) == 1

    async def test_limits_results_to_20(self) -> None:
        searches = [
            {
                "urlSegment": f"Search{i}",
                "displayName": f"Search {i} keyword",
                "description": "",
                "name": f"Q{i}",
            }
            for i in range(30)
        ]
        discovery = _mock_discovery(searches_by_rt={"gene": searches})
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", "gene", "keyword")

        assert len(result) <= 20

    async def test_no_matches_returns_empty(self) -> None:
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "",
                        "name": "Q",
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", "gene", "zzzznonexistent")

        assert result == []

    async def test_empty_query_matches_on_full_string(self) -> None:
        """Empty query should not match anything (no terms, no query_lower)."""
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes",
                        "description": "",
                        "name": "Q",
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", "gene", "")

        # Empty query has no terms, so nothing matches
        assert result == []

    async def test_result_does_not_contain_score(self) -> None:
        """Score is used internally but should not appear in output."""
        discovery = _mock_discovery(
            searches_by_rt={
                "gene": [
                    {
                        "urlSegment": "GenesByTaxon",
                        "displayName": "Genes by Taxon",
                        "description": "desc",
                        "name": "Q",
                    },
                ]
            }
        )
        with patch(
            "veupath_chatbot.services.catalog.searches.get_discovery_service",
            return_value=discovery,
        ):
            result = await search_for_searches("plasmodb", "gene", "taxon")

        for r in result:
            assert "score" not in r


# ---------------------------------------------------------------------------
# _resolve_record_type_for_search
# ---------------------------------------------------------------------------


class TestResolveRecordTypeForSearch:
    """Test the _resolve_record_type_for_search() function."""

    async def test_finds_search_in_given_record_type(self) -> None:
        client = _mock_client(
            record_types=[
                {"urlSegment": "gene", "name": "Genes"},
                {"urlSegment": "transcript", "name": "Transcripts"},
            ],
            searches_by_rt={
                "gene": [{"urlSegment": "GenesByTaxon"}],
                "transcript": [],
            },
        )
        result = await _resolve_record_type_for_search(client, "gene", "GenesByTaxon")
        assert result == "gene"

    async def test_finds_search_in_different_record_type(self) -> None:
        """Should search other record types if not found in the given one."""
        client = _mock_client(
            record_types=[
                {"urlSegment": "gene", "name": "Genes"},
                {"urlSegment": "transcript", "name": "Transcripts"},
            ],
            searches_by_rt={
                "gene": [],
                "transcript": [{"urlSegment": "TranscriptsByTaxon"}],
            },
        )
        result = await _resolve_record_type_for_search(
            client, "gene", "TranscriptsByTaxon"
        )
        assert result == "transcript"

    async def test_returns_original_when_not_found_anywhere(self) -> None:
        client = _mock_client(
            record_types=[{"urlSegment": "gene"}],
            searches_by_rt={"gene": []},
        )
        result = await _resolve_record_type_for_search(
            client, "gene", "NonexistentSearch"
        )
        assert result == "gene"

    async def test_returns_original_on_get_record_types_error(self) -> None:
        client = MagicMock()
        client.get_record_types = AsyncMock(side_effect=RuntimeError("fail"))
        result = await _resolve_record_type_for_search(client, "gene", "GenesByTaxon")
        assert result == "gene"

    async def test_continues_when_get_searches_fails_for_one_rt(self) -> None:
        async def _get_searches(rt: str) -> list[Any]:
            if rt == "gene":
                raise RuntimeError("fail")
            return [{"urlSegment": "TranscriptsByTaxon"}]

        client = MagicMock()
        client.get_record_types = AsyncMock(
            return_value=[
                {"urlSegment": "gene"},
                {"urlSegment": "transcript"},
            ]
        )
        client.get_searches = AsyncMock(side_effect=_get_searches)

        result = await _resolve_record_type_for_search(
            client, "gene", "TranscriptsByTaxon"
        )
        assert result == "transcript"

    async def test_handles_string_record_types(self) -> None:
        client = _mock_client(
            record_types=["gene", "transcript"],
            searches_by_rt={
                "gene": [{"urlSegment": "GenesByTaxon"}],
                "transcript": [],
            },
        )
        result = await _resolve_record_type_for_search(client, "gene", "GenesByTaxon")
        assert result == "gene"

    async def test_prioritizes_given_record_type(self) -> None:
        """The given record type should be checked first (ordered.insert(0, ...))."""
        client = _mock_client(
            record_types=[
                {"urlSegment": "transcript"},
                {"urlSegment": "gene"},
            ],
            searches_by_rt={
                "gene": [{"urlSegment": "SharedSearch"}],
                "transcript": [{"urlSegment": "SharedSearch"}],
            },
        )
        result = await _resolve_record_type_for_search(client, "gene", "SharedSearch")
        # gene should be checked first since it was the given record_type
        assert result == "gene"

    async def test_matches_by_name_fallback(self) -> None:
        """Should match search by 'name' field when urlSegment is not present."""
        client = _mock_client(
            record_types=[{"urlSegment": "gene"}],
            searches_by_rt={
                "gene": [{"name": "GenesByTaxon"}],
            },
        )
        result = await _resolve_record_type_for_search(client, "gene", "GenesByTaxon")
        assert result == "gene"

    async def test_skips_non_dict_non_str_record_types(self) -> None:
        client = _mock_client(
            record_types=[42, None, {"urlSegment": "gene"}],
            searches_by_rt={"gene": [{"urlSegment": "GenesByTaxon"}]},
        )
        result = await _resolve_record_type_for_search(client, "gene", "GenesByTaxon")
        assert result == "gene"

    async def test_skips_non_dict_search_entries(self) -> None:
        client = _mock_client(
            record_types=[{"urlSegment": "gene"}],
            searches_by_rt={
                "gene": [
                    "not_a_dict",
                    {"urlSegment": "GenesByTaxon"},
                ],
            },
        )
        result = await _resolve_record_type_for_search(client, "gene", "GenesByTaxon")
        assert result == "gene"
