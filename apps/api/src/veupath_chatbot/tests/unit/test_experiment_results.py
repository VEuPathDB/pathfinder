"""Tests for experiment result helpers."""

from veupath_chatbot.services.wdk.helpers import (
    extract_displayable_attr_names,
    extract_pk,
    order_primary_key,
)


class TestExtractPk:
    def test_extracts_first_value(self):
        record = {"id": [{"name": "source_id", "value": "PF3D7_0100100"}]}
        assert extract_pk(record) == "PF3D7_0100100"

    def test_strips_whitespace(self):
        record = {"id": [{"name": "source_id", "value": "  PF3D7_0100100  "}]}
        assert extract_pk(record) == "PF3D7_0100100"

    def test_returns_none_for_empty_list(self):
        assert extract_pk({"id": []}) is None

    def test_returns_none_for_missing_id(self):
        assert extract_pk({}) is None


class TestOrderPrimaryKey:
    """WDK requires PK columns in the exact order of primaryKeyColumnRefs.

    Per VEuPathDB/WDK RecordRequest.java, the primary key array order
    must match the record class definition.
    """

    def test_reorders_to_match_refs(self):
        """PK parts sent in wrong order are reordered to match record class."""
        pk_parts = [
            {"name": "project_id", "value": "PlasmoDB"},
            {"name": "source_id", "value": "PF3D7_0100100"},
        ]
        pk_refs = ["source_id", "project_id"]
        result = order_primary_key(pk_parts, pk_refs, pk_defaults={})
        assert result == [
            {"name": "source_id", "value": "PF3D7_0100100"},
            {"name": "project_id", "value": "PlasmoDB"},
        ]

    def test_fills_missing_project_id(self):
        """Missing project_id is filled from pk_defaults."""
        pk_parts = [{"name": "source_id", "value": "PF3D7_0100100"}]
        pk_refs = ["source_id", "project_id"]
        result = order_primary_key(
            pk_parts, pk_refs, pk_defaults={"project_id": "PlasmoDB"}
        )
        assert result == [
            {"name": "source_id", "value": "PF3D7_0100100"},
            {"name": "project_id", "value": "PlasmoDB"},
        ]

    def test_already_ordered(self):
        """PK parts already in correct order are unchanged."""
        pk_parts = [
            {"name": "source_id", "value": "PF3D7_0100100"},
            {"name": "project_id", "value": "PlasmoDB"},
        ]
        pk_refs = ["source_id", "project_id"]
        result = order_primary_key(pk_parts, pk_refs, pk_defaults={})
        assert result == pk_parts

    def test_empty_refs_returns_empty(self):
        """Empty primaryKeyColumnRefs returns empty list."""
        pk_parts = [{"name": "source_id", "value": "PF3D7_0100100"}]
        result = order_primary_key(pk_parts, [], pk_defaults={})
        assert result == []

    def test_extra_pk_parts_ignored(self):
        """PK parts not in refs are discarded."""
        pk_parts = [
            {"name": "source_id", "value": "PF3D7_0100100"},
            {"name": "project_id", "value": "PlasmoDB"},
            {"name": "extra_col", "value": "junk"},
        ]
        pk_refs = ["source_id", "project_id"]
        result = order_primary_key(pk_parts, pk_refs, pk_defaults={})
        assert len(result) == 2
        assert result[0]["name"] == "source_id"
        assert result[1]["name"] == "project_id"

    def test_missing_part_with_no_default_gets_empty_string(self):
        """Missing PK column with no default gets empty string value."""
        pk_parts = [{"name": "source_id", "value": "PF3D7_0100100"}]
        pk_refs = ["source_id", "project_id"]
        result = order_primary_key(pk_parts, pk_refs, pk_defaults={})
        assert result[1] == {"name": "project_id", "value": ""}


class TestExtractDisplayableAttrNames:
    """WDK record type info returns attributes in expanded or map format.

    Per VEuPathDB/WDK AttributeFieldFormatter.java, each attribute has
    ``name``, ``isDisplayable``, etc.  Empty or missing names must be
    filtered out because WDK's ``RecordRequest.parseAttributeNames``
    rejects names not found in the record class attribute field map.
    """

    def test_extracts_from_dict_format(self):
        """attributesMap (dict keyed by name) returns displayable names."""
        attrs = {
            "source_id": {"displayName": "Gene ID", "isDisplayable": True},
            "product": {"displayName": "Product", "isDisplayable": True},
            "internal_col": {"displayName": "Internal", "isDisplayable": False},
        }
        result = extract_displayable_attr_names(attrs)
        assert "source_id" in result
        assert "product" in result
        assert "internal_col" not in result

    def test_extracts_from_list_format(self):
        """Expanded format (list of objects) returns displayable names."""
        attrs = [
            {"name": "source_id", "displayName": "Gene ID", "isDisplayable": True},
            {"name": "product", "displayName": "Product", "isDisplayable": True},
            {"name": "internal_col", "displayName": "Internal", "isDisplayable": False},
        ]
        result = extract_displayable_attr_names(attrs)
        assert "source_id" in result
        assert "product" in result
        assert "internal_col" not in result

    def test_filters_empty_names_from_list(self):
        """Attribute objects with empty or missing name are excluded.

        WDK rejects empty attribute names with:
        ``Attribute name '' is not in record class ...``
        """
        attrs = [
            {"name": "source_id", "isDisplayable": True},
            {"name": "", "isDisplayable": True},
            {"isDisplayable": True},
            {"name": None, "isDisplayable": True},
        ]
        result = extract_displayable_attr_names(attrs)
        assert result == ["source_id"]

    def test_filters_empty_names_from_dict(self):
        """Dict keys that are empty strings are excluded."""
        attrs = {
            "source_id": {"isDisplayable": True},
            "": {"isDisplayable": True},
        }
        result = extract_displayable_attr_names(attrs)
        assert result == ["source_id"]

    def test_returns_empty_for_unexpected_type(self):
        """Non-dict, non-list input returns empty list."""
        assert extract_displayable_attr_names("unexpected") == []
        assert extract_displayable_attr_names(None) == []
        assert extract_displayable_attr_names(42) == []

    def test_defaults_is_displayable_to_true(self):
        """Attributes missing ``isDisplayable`` are treated as displayable.

        Per WDK: ``FieldScope.NON_INTERNAL.isFieldInScope(attribute)`` is True
        for most attributes; only internal ones are False.
        """
        attrs = [
            {"name": "gene_type", "displayName": "Gene Type"},
        ]
        result = extract_displayable_attr_names(attrs)
        assert "gene_type" in result
