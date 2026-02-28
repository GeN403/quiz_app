"""
generate_quiz ノードのユニットテスト (Task 7.3)

Requirements: 2.5, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from unittest.mock import patch, MagicMock

from google.api_core import exceptions as google_exceptions

from app.agent.nodes import make_generate_quiz_node


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
    def setup_method(self):
        self.generate_quiz = make_generate_quiz_node("test-api-key")

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_successful_call_sets_llm_raw_response(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"question": "Q?", "answer": "A"}')
        mock_llm_class.return_value = mock_llm

        result = self.generate_quiz(make_state())

        assert "error_code" not in result
        assert "llm_raw_response" in result
        assert result["llm_raw_response"] == '{"question": "Q?", "answer": "A"}'

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_unauthenticated_returns_api_key_invalid(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = google_exceptions.Unauthenticated("auth error")
        mock_llm_class.return_value = mock_llm

        result = self.generate_quiz(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_INVALID"
        assert result["error_status"] == 401

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_permission_denied_returns_permission_error(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = google_exceptions.PermissionDenied("permission error")
        mock_llm_class.return_value = mock_llm

        result = self.generate_quiz(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_PERMISSION_DENIED"
        assert result["error_status"] == 403

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_resource_exhausted_returns_rate_limit(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = google_exceptions.ResourceExhausted("rate limit")
        mock_llm_class.return_value = mock_llm

        result = self.generate_quiz(make_state())

        assert result["error_code"] == "GEMINI_RATE_LIMIT"
        assert result["error_status"] == 429

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_service_unavailable_returns_service_error(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = google_exceptions.ServiceUnavailable("service error")
        mock_llm_class.return_value = mock_llm

        result = self.generate_quiz(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_internal_server_error_returns_service_error(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = google_exceptions.InternalServerError("internal error")
        mock_llm_class.return_value = mock_llm

        result = self.generate_quiz(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_deadline_exceeded_returns_timeout(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = google_exceptions.DeadlineExceeded("timeout")
        mock_llm_class.return_value = mock_llm

        result = self.generate_quiz(make_state())

        assert result["error_code"] == "GEMINI_TIMEOUT"
        assert result["error_status"] == 504

    @patch("app.agent.nodes.ChatGoogleGenerativeAI")
    def test_gemini_api_key_injected_via_closure(self, mock_llm_class):
        """gemini_api_key がクロージャ経由で ChatGoogleGenerativeAI に注入されること"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="response")
        mock_llm_class.return_value = mock_llm

        custom_node = make_generate_quiz_node("custom-key-123")
        custom_node(make_state())

        call_kwargs = mock_llm_class.call_args[1]
        assert call_kwargs.get("google_api_key") == "custom-key-123"
