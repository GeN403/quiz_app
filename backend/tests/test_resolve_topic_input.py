"""Unit tests for resolve_topic_input node."""

from unittest.mock import MagicMock, patch


def make_state(**kwargs):
    base = {
        "source_text": "This is sample source text. " * 50,
        "source_title": "Sample Source Title",
        "topic": None,
        "resolved_topic": None,
    }
    base.update(kwargs)
    return base


class TestResolveTopicInputNode:
    @patch("app.agent.nodes.resolve_topic_input.GeminiLLMAdapter")
    def test_topic_provided_skips_llm(self, mock_adapter_cls):
        from app.agent.nodes import make_resolve_topic_input_node

        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        node = make_resolve_topic_input_node("test-api-key")
        result = node(make_state(topic="programming language"))

        mock_adapter.invoke.assert_not_called()
        assert result["resolved_topic"] == "programming language"
        assert "error_code" not in result

    @patch("app.agent.nodes.resolve_topic_input.GeminiLLMAdapter")
    def test_topic_not_provided_calls_llm(self, mock_adapter_cls):
        from app.agent.nodes import make_resolve_topic_input_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = "topic picked"
        mock_adapter_cls.return_value = mock_adapter

        node = make_resolve_topic_input_node("test-api-key")
        result = node(make_state(topic=None))

        mock_adapter.invoke.assert_called_once()
        assert result.get("resolved_topic") == "topic picked"
        assert "error_code" not in result

    @patch("app.agent.nodes.resolve_topic_input.GeminiLLMAdapter")
    def test_llm_exception_returns_error(self, mock_adapter_cls):
        from app.agent.nodes import make_resolve_topic_input_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = Exception("LLM error")
        mock_adapter_cls.return_value = mock_adapter

        node = make_resolve_topic_input_node("test-api-key")
        result = node(make_state(topic=None))

        assert result["error_code"] == "TOPIC_RESOLVE_FAILED"
        assert result["error_status"] == 500


class TestResolveTopicInputNodeBoundary:
    @patch("app.agent.nodes.resolve_topic_input.GeminiLLMAdapter")
    def test_llm_returns_long_text_truncated_to_20_chars(self, mock_adapter_cls):
        from app.agent.nodes import make_resolve_topic_input_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = "A" * 25
        mock_adapter_cls.return_value = mock_adapter

        node = make_resolve_topic_input_node("test-api-key")
        result = node(make_state(topic=None))

        assert result.get("resolved_topic") == "A" * 20

    @patch("app.agent.nodes.resolve_topic_input.GeminiLLMAdapter")
    def test_llm_returns_empty_string_returns_error(self, mock_adapter_cls):
        from app.agent.nodes import make_resolve_topic_input_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = ""
        mock_adapter_cls.return_value = mock_adapter

        node = make_resolve_topic_input_node("test-api-key")
        result = node(make_state(topic=None))

        assert result["error_code"] == "TOPIC_RESOLVE_FAILED"
        assert result["error_status"] == 500

    @patch("app.agent.nodes.resolve_topic_input.GeminiLLMAdapter")
    def test_llm_returns_whitespace_only_returns_error(self, mock_adapter_cls):
        from app.agent.nodes import make_resolve_topic_input_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = "   "
        mock_adapter_cls.return_value = mock_adapter

        node = make_resolve_topic_input_node("test-api-key")
        result = node(make_state(topic=None))

        assert result["error_code"] == "TOPIC_RESOLVE_FAILED"
        assert result["error_status"] == 500
