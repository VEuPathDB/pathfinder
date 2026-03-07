"""Unit tests for services.strategies.engine.step_builder.StepBuilderMixin."""

from veupath_chatbot.domain.strategy.session import StrategySession
from veupath_chatbot.services.strategies.engine.step_builder import StepBuilderMixin


def _make_mixin() -> StepBuilderMixin:
    session = StrategySession("plasmodb")
    return StepBuilderMixin(session)


# ── _filter_search_options ────────────────────────────────────────────


class TestFilterSearchOptions:
    def test_matches_by_name(self) -> None:
        mixin = _make_mixin()
        searches = [
            {"name": "GenesByTextSearch", "displayName": "Text Search"},
            {"name": "GenesByGoTerm", "displayName": "GO Term Search"},
            {"name": "GenesByOrthologs", "displayName": "Ortholog Search"},
        ]
        results = mixin._filter_search_options(searches, "Text")
        assert results == ["GenesByTextSearch"]

    def test_matches_by_display_name(self) -> None:
        mixin = _make_mixin()
        searches = [
            {"name": "GenesByTextSearch", "displayName": "Text Search"},
            {"name": "GenesByGoTerm", "displayName": "GO Term Search"},
        ]
        results = mixin._filter_search_options(searches, "GO Term")
        assert results == ["GenesByGoTerm"]

    def test_case_insensitive_match(self) -> None:
        mixin = _make_mixin()
        searches = [{"name": "GenesByTextSearch", "displayName": "Text Search"}]
        results = mixin._filter_search_options(searches, "text")
        assert results == ["GenesByTextSearch"]

    def test_respects_limit(self) -> None:
        mixin = _make_mixin()
        searches = [{"name": f"Gene{i}", "displayName": f"Gene {i}"} for i in range(50)]
        results = mixin._filter_search_options(searches, "Gene", limit=5)
        assert len(results) == 5

    def test_empty_searches(self) -> None:
        mixin = _make_mixin()
        results = mixin._filter_search_options([], "anything")
        assert results == []

    def test_skips_non_dict_entries(self) -> None:
        mixin = _make_mixin()
        searches = ["not-a-dict", {"name": "GenesByTextSearch"}]
        results = mixin._filter_search_options(searches, "Text")
        assert results == ["GenesByTextSearch"]

    def test_uses_url_segment_as_fallback(self) -> None:
        mixin = _make_mixin()
        searches = [{"urlSegment": "GenesByTextSearch"}]
        results = mixin._filter_search_options(searches, "Text")
        assert results == ["GenesByTextSearch"]

    def test_no_match_returns_empty(self) -> None:
        mixin = _make_mixin()
        searches = [{"name": "GenesByTextSearch"}]
        results = mixin._filter_search_options(searches, "zzz_nonexistent")
        assert results == []


# ── _extract_vocab_options ────────────────────────────────────────────


def _make_vocab_tree() -> dict:
    return {
        "data": {"display": "@@fake@@", "value": "root"},
        "children": [
            {
                "data": {"display": "Plasmodium", "value": "plasmodium"},
                "children": [
                    {
                        "data": {"display": "P. falciparum 3D7", "value": "pf3d7"},
                        "children": [],
                    },
                    {
                        "data": {"display": "P. vivax", "value": "pvivax"},
                        "children": [],
                    },
                ],
            },
            {
                "data": {"display": "Toxoplasma", "value": "toxoplasma"},
                "children": [],
            },
        ],
    }


class TestExtractVocabOptions:
    def test_extracts_display_values(self) -> None:
        mixin = _make_mixin()
        options = mixin._extract_vocab_options(_make_vocab_tree())
        # Should skip @@fake@@ root
        assert "@@fake@@" not in options
        assert "Plasmodium" in options
        assert "P. falciparum 3D7" in options
        assert "Toxoplasma" in options

    def test_respects_limit(self) -> None:
        mixin = _make_mixin()
        options = mixin._extract_vocab_options(_make_vocab_tree(), limit=2)
        assert len(options) == 2

    def test_empty_vocab(self) -> None:
        mixin = _make_mixin()
        options = mixin._extract_vocab_options({})
        assert options == []


# ── _vocab_contains_value ─────────────────────────────────────────────


class TestVocabContainsValue:
    def test_finds_display_value(self) -> None:
        mixin = _make_mixin()
        assert mixin._vocab_contains_value(_make_vocab_tree(), "Plasmodium") is True

    def test_finds_raw_value(self) -> None:
        mixin = _make_mixin()
        assert mixin._vocab_contains_value(_make_vocab_tree(), "pf3d7") is True

    def test_missing_value(self) -> None:
        mixin = _make_mixin()
        assert mixin._vocab_contains_value(_make_vocab_tree(), "nonexistent") is False

    def test_empty_value(self) -> None:
        mixin = _make_mixin()
        assert mixin._vocab_contains_value(_make_vocab_tree(), "") is False

    def test_whitespace_stripped(self) -> None:
        mixin = _make_mixin()
        assert mixin._vocab_contains_value(_make_vocab_tree(), "  Plasmodium  ") is True

    def test_empty_vocab(self) -> None:
        mixin = _make_mixin()
        assert mixin._vocab_contains_value({}, "anything") is False


# ── _match_vocab_value ────────────────────────────────────────────────


class TestMatchVocabValue:
    def test_exact_display_match_returns_value(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._match_vocab_value(vocab, "Plasmodium")
        assert result == "plasmodium"

    def test_exact_value_match_returns_value(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._match_vocab_value(vocab, "pf3d7")
        assert result == "pf3d7"

    def test_normalized_match(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._match_vocab_value(vocab, "plasmodium")
        assert result == "plasmodium"

    def test_no_match_returns_target(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._match_vocab_value(vocab, "unknown_organism")
        assert result == "unknown_organism"

    def test_none_value_returns_empty_string(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._match_vocab_value(vocab, None)
        assert result == ""

    def test_empty_vocab_returns_target(self) -> None:
        mixin = _make_mixin()
        result = mixin._match_vocab_value({}, "some_value")
        assert result == "some_value"

    def test_list_vocab_format(self) -> None:
        mixin = _make_mixin()
        vocab = [["val1", "Display 1"], ["val2", "Display 2"]]
        result = mixin._match_vocab_value(vocab, "Display 1")
        assert result == "val1"


# ── _get_vocab_node_value ─────────────────────────────────────────────


class TestGetVocabNodeValue:
    def test_prefers_value_field(self) -> None:
        mixin = _make_mixin()
        node = {"data": {"value": "the_value", "display": "Display"}}
        assert mixin._get_vocab_node_value(node) == "the_value"

    def test_falls_back_to_id(self) -> None:
        mixin = _make_mixin()
        node = {"data": {"id": "the_id", "display": "Display"}}
        assert mixin._get_vocab_node_value(node) == "the_id"

    def test_falls_back_to_term(self) -> None:
        mixin = _make_mixin()
        node = {"data": {"term": "the_term"}}
        assert mixin._get_vocab_node_value(node) == "the_term"

    def test_falls_back_to_name(self) -> None:
        mixin = _make_mixin()
        node = {"data": {"name": "the_name"}}
        assert mixin._get_vocab_node_value(node) == "the_name"

    def test_falls_back_to_display(self) -> None:
        mixin = _make_mixin()
        node = {"data": {"display": "the_display"}}
        assert mixin._get_vocab_node_value(node) == "the_display"

    def test_empty_data_returns_empty(self) -> None:
        mixin = _make_mixin()
        node = {"data": {}}
        assert mixin._get_vocab_node_value(node) == ""

    def test_no_data_key_returns_empty(self) -> None:
        mixin = _make_mixin()
        node = {}
        assert mixin._get_vocab_node_value(node) == ""


# ── _find_vocab_node_for_match ────────────────────────────────────────


class TestFindVocabNodeForMatch:
    def test_exact_match_by_value(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        node = mixin._find_vocab_node_for_match(vocab, "plasmodium")
        assert node is not None
        assert node["data"]["value"] == "plasmodium"

    def test_exact_match_by_display(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        node = mixin._find_vocab_node_for_match(vocab, "Plasmodium")
        assert node is not None

    def test_normalized_match(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        node = mixin._find_vocab_node_for_match(vocab, "PLASMODIUM")
        assert node is not None

    def test_no_match_returns_none(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        node = mixin._find_vocab_node_for_match(vocab, "nonexistent")
        assert node is None

    def test_finds_in_children(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        node = mixin._find_vocab_node_for_match(vocab, "pf3d7")
        assert node is not None
        assert node["data"]["value"] == "pf3d7"


# ── _collect_leaf_terms ───────────────────────────────────────────────


class TestCollectLeafTerms:
    def test_leaf_node_returns_value(self) -> None:
        mixin = _make_mixin()
        node = {"data": {"value": "leaf_val"}, "children": []}
        assert mixin._collect_leaf_terms(node) == ["leaf_val"]

    def test_parent_node_returns_children_values(self) -> None:
        mixin = _make_mixin()
        node = {
            "data": {"value": "parent"},
            "children": [
                {"data": {"value": "child1"}, "children": []},
                {"data": {"value": "child2"}, "children": []},
            ],
        }
        leaves = mixin._collect_leaf_terms(node)
        assert leaves == ["child1", "child2"]

    def test_deep_nesting(self) -> None:
        mixin = _make_mixin()
        node = {
            "data": {"value": "root"},
            "children": [
                {
                    "data": {"value": "mid"},
                    "children": [
                        {"data": {"value": "deep_leaf"}, "children": []},
                    ],
                },
            ],
        }
        leaves = mixin._collect_leaf_terms(node)
        assert leaves == ["deep_leaf"]

    def test_empty_value_skipped(self) -> None:
        mixin = _make_mixin()
        node = {"data": {}, "children": []}
        assert mixin._collect_leaf_terms(node) == []


# ── _expand_leaf_values ───────────────────────────────────────────────


class TestExpandLeafValues:
    def test_expands_parent_to_leaves(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._expand_leaf_values(vocab, ["Plasmodium"])
        assert "pf3d7" in result
        assert "pvivax" in result

    def test_include_parent_adds_parent_value(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._expand_leaf_values(vocab, ["Plasmodium"], include_parent=True)
        assert "plasmodium" in result
        assert "pf3d7" in result

    def test_unmatched_value_passes_through(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._expand_leaf_values(vocab, ["unknown_value"])
        assert result == ["unknown_value"]

    def test_deduplicates_values(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._expand_leaf_values(vocab, ["pf3d7", "pf3d7"])
        assert result.count("pf3d7") == 1

    def test_empty_values(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._expand_leaf_values(vocab, [])
        assert result == []

    def test_empty_string_skipped(self) -> None:
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._expand_leaf_values(vocab, [""])
        assert result == []

    def test_leaf_value_returns_itself(self) -> None:
        """A leaf node has no children, so it returns just its own value."""
        mixin = _make_mixin()
        vocab = _make_vocab_tree()
        result = mixin._expand_leaf_values(vocab, ["pf3d7"])
        assert result == ["pf3d7"]
