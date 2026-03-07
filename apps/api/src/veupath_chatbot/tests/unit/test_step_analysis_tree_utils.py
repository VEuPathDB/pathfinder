"""Unit tests for step_analysis._tree_utils -- tree traversal and manipulation."""

from __future__ import annotations

from veupath_chatbot.services.experiment.step_analysis._tree_utils import (
    _build_subtree_with_operator,
    _collect_combine_nodes,
    _collect_leaves,
    _extract_leaf_branch,
    _node_id,
    _remove_leaf_from_tree,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable tree structures
# ---------------------------------------------------------------------------


def _leaf(lid: str, search: str = "") -> dict:
    """Create a leaf node."""
    return {"id": lid, "searchName": search or f"Search_{lid}"}


def _combine(nid: str, primary: dict, secondary: dict, op: str = "INTERSECT") -> dict:
    """Create a combine (binary) node."""
    return {
        "id": nid,
        "operator": op,
        "primaryInput": primary,
        "secondaryInput": secondary,
    }


def _transform(nid: str, child: dict, search: str = "GenesByOrthologs") -> dict:
    """Create a transform (unary) node with only a primaryInput."""
    return {
        "id": nid,
        "searchName": search,
        "primaryInput": child,
    }


# ---------------------------------------------------------------------------
# _node_id
# ---------------------------------------------------------------------------


class TestNodeId:
    def test_returns_id_field(self) -> None:
        assert _node_id({"id": "step_42"}) == "step_42"

    def test_falls_back_to_search_name(self) -> None:
        assert _node_id({"searchName": "GenesByTaxon"}) == "GenesByTaxon"

    def test_falls_back_to_question_mark(self) -> None:
        assert _node_id({}) == "?"

    def test_numeric_id_stringified(self) -> None:
        assert _node_id({"id": 42}) == "42"


# ---------------------------------------------------------------------------
# _collect_leaves
# ---------------------------------------------------------------------------


class TestCollectLeaves:
    def test_single_leaf(self) -> None:
        leaf = _leaf("L1")
        leaves = _collect_leaves(leaf)
        assert len(leaves) == 1
        assert leaves[0]["id"] == "L1"

    def test_two_leaves_from_combine(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        leaves = _collect_leaves(tree)
        ids = {n["id"] for n in leaves}
        assert ids == {"L1", "L2"}

    def test_deep_tree_three_leaves(self) -> None:
        """
        C1
        ├── C2
        │   ├── L1
        │   └── L2
        └── L3
        """
        inner = _combine("C2", _leaf("L1"), _leaf("L2"))
        tree = _combine("C1", inner, _leaf("L3"))
        leaves = _collect_leaves(tree)
        ids = [n["id"] for n in leaves]
        assert set(ids) == {"L1", "L2", "L3"}

    def test_transform_node_with_leaf_child(self) -> None:
        """Transform wrapping a leaf: leaf is collected, transform is not."""
        tree = _transform("T1", _leaf("L1"))
        leaves = _collect_leaves(tree)
        assert len(leaves) == 1
        assert leaves[0]["id"] == "L1"

    def test_combine_under_transform(self) -> None:
        """
        T1
        └── C1
            ├── L1
            └── L2
        """
        inner = _combine("C1", _leaf("L1"), _leaf("L2"))
        tree = _transform("T1", inner)
        leaves = _collect_leaves(tree)
        ids = {n["id"] for n in leaves}
        assert ids == {"L1", "L2"}

    def test_empty_node(self) -> None:
        """A node with no inputs is itself a leaf."""
        leaves = _collect_leaves({"id": "solo"})
        assert len(leaves) == 1


# ---------------------------------------------------------------------------
# _collect_combine_nodes
# ---------------------------------------------------------------------------


class TestCollectCombineNodes:
    def test_single_leaf_returns_empty(self) -> None:
        assert _collect_combine_nodes(_leaf("L1")) == []

    def test_single_combine(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        nodes = _collect_combine_nodes(tree)
        assert len(nodes) == 1
        assert nodes[0]["id"] == "C1"

    def test_nested_combines(self) -> None:
        """
        C1
        ├── C2
        │   ├── L1
        │   └── L2
        └── L3
        """
        inner = _combine("C2", _leaf("L1"), _leaf("L2"))
        tree = _combine("C1", inner, _leaf("L3"))
        nodes = _collect_combine_nodes(tree)
        ids = {n["id"] for n in nodes}
        assert ids == {"C1", "C2"}

    def test_transform_is_not_combine(self) -> None:
        tree = _transform("T1", _leaf("L1"))
        assert _collect_combine_nodes(tree) == []

    def test_three_level_nested_combines(self) -> None:
        """
        C1
        ├── C2
        │   ├── C3
        │   │   ├── L1
        │   │   └── L2
        │   └── L3
        └── L4
        """
        inner = _combine("C3", _leaf("L1"), _leaf("L2"))
        mid = _combine("C2", inner, _leaf("L3"))
        tree = _combine("C1", mid, _leaf("L4"))
        nodes = _collect_combine_nodes(tree)
        ids = {n["id"] for n in nodes}
        assert ids == {"C1", "C2", "C3"}


# ---------------------------------------------------------------------------
# _remove_leaf_from_tree
# ---------------------------------------------------------------------------


class TestRemoveLeafFromTree:
    def test_removing_root_leaf_returns_none(self) -> None:
        assert _remove_leaf_from_tree(_leaf("L1"), "L1") is None

    def test_removing_nonexistent_leaf_returns_full_tree(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        result = _remove_leaf_from_tree(tree, "NOPE")
        assert result is not None
        # Tree should be structurally identical
        assert result["id"] == "C1"

    def test_removing_left_leaf_returns_right(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        result = _remove_leaf_from_tree(tree, "L1")
        assert result is not None
        assert result["id"] == "L2"

    def test_removing_right_leaf_returns_left(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        result = _remove_leaf_from_tree(tree, "L2")
        assert result is not None
        assert result["id"] == "L1"

    def test_deep_tree_prune_preserves_structure(self) -> None:
        """
        C1
        ├── C2
        │   ├── L1   <-- remove this
        │   └── L2
        └── L3

        Expected: C1 with L2 and L3.
        """
        inner = _combine("C2", _leaf("L1"), _leaf("L2"))
        tree = _combine("C1", inner, _leaf("L3"))
        result = _remove_leaf_from_tree(tree, "L1")
        assert result is not None
        leaves = _collect_leaves(result)
        ids = {n["id"] for n in leaves}
        assert ids == {"L2", "L3"}

    def test_does_not_mutate_original(self) -> None:
        inner = _combine("C2", _leaf("L1"), _leaf("L2"))
        tree = _combine("C1", inner, _leaf("L3"))
        _remove_leaf_from_tree(tree, "L1")
        # Original still has all 3 leaves
        original_leaves = _collect_leaves(tree)
        assert len(original_leaves) == 3

    def test_remove_leaf_under_transform(self) -> None:
        """
        T1
        └── L1  <-- remove

        Should return None because the transform collapses.
        """
        tree = _transform("T1", _leaf("L1"))
        result = _remove_leaf_from_tree(tree, "L1")
        assert result is None

    def test_remove_leaf_from_combine_under_transform(self) -> None:
        """
        T1
        └── C1
            ├── L1  <-- remove
            └── L2

        Expected: T1 wrapping L2
        """
        inner = _combine("C1", _leaf("L1"), _leaf("L2"))
        tree = _transform("T1", inner)
        result = _remove_leaf_from_tree(tree, "L1")
        assert result is not None
        leaves = _collect_leaves(result)
        assert len(leaves) == 1
        assert leaves[0]["id"] == "L2"


# ---------------------------------------------------------------------------
# _extract_leaf_branch
# ---------------------------------------------------------------------------


class TestExtractLeafBranch:
    def test_single_leaf_found(self) -> None:
        leaf = _leaf("L1")
        result = _extract_leaf_branch(leaf, "L1")
        assert result is not None
        assert result["id"] == "L1"

    def test_single_leaf_not_found(self) -> None:
        leaf = _leaf("L1")
        assert _extract_leaf_branch(leaf, "L2") is None

    def test_combine_returns_correct_branch(self) -> None:
        """
        C1
        ├── L1
        └── L2

        Extracting L1 should return just L1 (unwrapped from combine).
        """
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        result = _extract_leaf_branch(tree, "L1")
        assert result is not None
        assert result["id"] == "L1"

    def test_combine_returns_secondary_branch(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        result = _extract_leaf_branch(tree, "L2")
        assert result is not None
        assert result["id"] == "L2"

    def test_transform_wraps_leaf(self) -> None:
        """
        T1
        └── L1

        Extracting L1 should return T1 wrapping L1 (preserves transform).
        """
        tree = _transform("T1", _leaf("L1"), search="GenesByOrthologs")
        result = _extract_leaf_branch(tree, "L1")
        assert result is not None
        assert result["id"] == "T1"
        assert result["primaryInput"]["id"] == "L1"

    def test_deep_tree_with_transform(self) -> None:
        """
        C1
        ├── T1
        │   └── L1
        └── L2

        Extracting L1 should return T1 wrapping L1.
        """
        t1 = _transform("T1", _leaf("L1"))
        tree = _combine("C1", t1, _leaf("L2"))
        result = _extract_leaf_branch(tree, "L1")
        assert result is not None
        assert result["id"] == "T1"
        assert result["primaryInput"]["id"] == "L1"

    def test_not_found_returns_none(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        assert _extract_leaf_branch(tree, "NOPE") is None

    def test_does_not_mutate_original(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"))
        result = _extract_leaf_branch(tree, "L1")
        assert result is not None
        result["id"] = "MUTATED"
        assert tree["primaryInput"]["id"] == "L1"


# ---------------------------------------------------------------------------
# _build_subtree_with_operator
# ---------------------------------------------------------------------------


class TestBuildSubtreeWithOperator:
    def test_changes_operator(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"), op="INTERSECT")
        result = _build_subtree_with_operator(tree, "UNION")
        assert result["operator"] == "UNION"

    def test_does_not_mutate_original(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"), op="INTERSECT")
        _build_subtree_with_operator(tree, "UNION")
        assert tree["operator"] == "INTERSECT"

    def test_preserves_children(self) -> None:
        tree = _combine("C1", _leaf("L1"), _leaf("L2"), op="INTERSECT")
        result = _build_subtree_with_operator(tree, "MINUS")
        leaves = _collect_leaves(result)
        ids = {n["id"] for n in leaves}
        assert ids == {"L1", "L2"}
