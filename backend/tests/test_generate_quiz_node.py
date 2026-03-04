"""
generate_quiz ??????????? (Task 7.3)

Requirements: 2.5, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from unittest.mock import MagicMock, patch

from app.agent.nodes import make_generate_quiz_node
from app.agent.ports.llm import LLMPortError


def make_state(**kwargs):
    base = {
        "category": "science",
        "source_url": "https://example.com",
        "source_title": "Example Title",
        "source_text": "Sample text content",
        "selected_quote_final": "Sample quote",
        "llm_raw_response": "",
        "result": None,
        "error_code": None,
        "error_status": None,
    }
    base.update(kwargs)
    return base


class TestGenerateQuizNode:
    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_successful_call_sets_llm_raw_response(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = '{"question": "Q?", "answer": "A"}'
        mock_adapter_cls.return_value = mock_adapter

        node = make_generate_quiz_node("test-api-key")
        result = node(make_state())

        assert "error_code" not in result
        assert "llm_raw_response" in result
        assert result["llm_raw_response"] == '{"question": "Q?", "answer": "A"}'

    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_unauthenticated_returns_api_key_invalid(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = LLMPortError("GEMINI_API_KEY_INVALID", 401, "auth error")
        mock_adapter_cls.return_value = mock_adapter

        node = make_generate_quiz_node("test-api-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_INVALID"
        assert result["error_status"] == 401

    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_permission_denied_returns_permission_error(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = LLMPortError("GEMINI_API_KEY_PERMISSION_DENIED", 403, "permission error")
        mock_adapter_cls.return_value = mock_adapter

        node = make_generate_quiz_node("test-api-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_PERMISSION_DENIED"
        assert result["error_status"] == 403

    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_resource_exhausted_returns_rate_limit(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = LLMPortError("GEMINI_RATE_LIMIT", 429, "rate limit")
        mock_adapter_cls.return_value = mock_adapter

        node = make_generate_quiz_node("test-api-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_RATE_LIMIT"
        assert result["error_status"] == 429

    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_service_unavailable_returns_service_error(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = LLMPortError("GEMINI_SERVICE_UNAVAILABLE", 503, "service error")
        mock_adapter_cls.return_value = mock_adapter

        node = make_generate_quiz_node("test-api-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503

    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_deadline_exceeded_returns_timeout(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = LLMPortError("GEMINI_TIMEOUT", 504, "timeout")
        mock_adapter_cls.return_value = mock_adapter

        node = make_generate_quiz_node("test-api-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_TIMEOUT"
        assert result["error_status"] == 504

    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_unexpected_error_returns_service_error(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = RuntimeError("boom")
        mock_adapter_cls.return_value = mock_adapter

        node = make_generate_quiz_node("test-api-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503

    @patch("app.agent.nodes.generate_quiz.GeminiLLMAdapter")
    def test_gemini_api_key_injected_via_closure(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = "response"
        mock_adapter_cls.return_value = mock_adapter

        custom_node = make_generate_quiz_node("custom-key-123")
        custom_node(make_state())

        call_kwargs = mock_adapter_cls.call_args.kwargs
        assert call_kwargs.get("api_key") == "custom-key-123"
