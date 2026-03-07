"""Unit tests for services.chat.utils — parse_selected_nodes."""

from veupath_chatbot.services.chat.utils import parse_selected_nodes


class TestParseSelectedNodes:
    def test_no_prefix_returns_original(self):
        selected, text = parse_selected_nodes("Hello world")
        assert selected is None
        assert text == "Hello world"

    def test_empty_message_returns_original(self):
        selected, text = parse_selected_nodes("")
        assert selected is None
        assert text == ""

    def test_valid_node_prefix_with_newline(self):
        msg = '__NODE__{"stepId":"s1","kind":"search"}\nFind kinases'
        selected, text = parse_selected_nodes(msg)
        assert selected == {"stepId": "s1", "kind": "search"}
        assert text == "Find kinases"

    def test_valid_node_prefix_no_newline(self):
        msg = '__NODE__{"stepId":"s1"}'
        selected, text = parse_selected_nodes(msg)
        assert selected == {"stepId": "s1"}
        assert text == ""

    def test_text_after_newline_is_stripped(self):
        msg = '__NODE__{"id":"1"}\n  trimmed message  '
        selected, text = parse_selected_nodes(msg)
        assert selected == {"id": "1"}
        assert text == "trimmed message"

    def test_json_part_with_whitespace(self):
        msg = '__NODE__  {"key": "value"}  \nafter'
        selected, text = parse_selected_nodes(msg)
        assert selected == {"key": "value"}
        assert text == "after"

    def test_invalid_json_returns_original(self):
        msg = "__NODE__{not valid json}\ntext"
        selected, text = parse_selected_nodes(msg)
        assert selected is None
        assert text == msg

    def test_nested_json_object(self):
        msg = '__NODE__{"node":{"id":"s2","params":{"q":"test"}}}\nQuery'
        selected, text = parse_selected_nodes(msg)
        assert selected == {"node": {"id": "s2", "params": {"q": "test"}}}
        assert text == "Query"

    def test_json_array_parsed(self):
        msg = '__NODE__[{"id":"s1"},{"id":"s2"}]\nDo something'
        selected, text = parse_selected_nodes(msg)
        assert selected == [{"id": "s1"}, {"id": "s2"}]
        assert text == "Do something"

    def test_multiline_text_after_prefix(self):
        msg = '__NODE__{"id":"1"}\nLine one\nLine two\nLine three'
        selected, text = parse_selected_nodes(msg)
        assert selected == {"id": "1"}
        assert text == "Line one\nLine two\nLine three"

    def test_prefix_case_sensitive(self):
        msg = '__node__{"id":"1"}\ntext'
        selected, text = parse_selected_nodes(msg)
        assert selected is None
        assert text == msg

    def test_prefix_with_extra_chars_before(self):
        msg = 'X__NODE__{"id":"1"}\ntext'
        selected, text = parse_selected_nodes(msg)
        assert selected is None
        assert text == msg
