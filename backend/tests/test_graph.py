"""Unit tests for QuizAgentGraph wiring and routing."""

import json
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from google.api_core import exceptions as google_exceptions


VALID_QUIZ_JSON = json.dumps(
    {
        "question": "What is 2+2?",
        "answer": "4",
        "Alternative Solutions/Correctness Judgment Criteria": "None",
        "explanation": "Basic arithmetic.",
        "source": {"title": "Old", "url": "https://old.com", "quote": "old"},
    }
)


def make_initial_state(**kwargs):
    base = {
        "category": "science",
        "question_count": 1,
        "source_type": "url",
        "source_value": "https://example.com",
        "selected_quote": "",
        "source_text": "",
        "source_title": "",
        "source_url": "",
        "selected_quote_final": "",
        "llm_raw_response": "",
        "result": None,
        "error_code": None,
        "error_status": None,
        "topic": None,
        "resolved_topic": None,
    }
    base.update(kwargs)
    return base


def make_happy_mocks(mock_sr_class, mock_llm_class):
    mock_resolver = MagicMock()
    mock_resolver.fetch_and_parse.return_value = {
        "url": "https://example.com",
        "title": "Server Title",
        "text": "Sample text content for quiz generation",
        "quotes": ["Server quote"],
    }
    mock_resolver.verify_quote.return_value = True
    mock_sr_class.return_value = mock_resolver

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        MagicMock(text="arithmetic"),
        MagicMock(content=VALID_QUIZ_JSON),
        MagicMock(content=json.dumps([{"text": "2 + 2 = 4"}])),
        MagicMock(content=json.dumps({"quote": "Basic arithmetic."})),
        MagicMock(content=json.dumps({"verdict": "pass", "reason": "Correct"})),
    ]
    mock_llm_class.return_value = mock_llm


class TestQuizAgentGraph:
    @patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI")
    @patch("app.agent.nodes.fetch_source.SourceResolver")
    def test_happy_path_returns_result(self, mock_sr_class, mock_llm_class):
        from app.agent.graph import create_quiz_agent_graph

        make_happy_mocks(mock_sr_class, mock_llm_class)
        graph = create_quiz_agent_graph("test-key")
        final_state = graph.invoke(make_initial_state())

        assert final_state.get("error_code") is None
        assert final_state.get("result") is not None
        assert "question" in final_state["result"]

    @patch("app.agent.nodes.fetch_source.SourceResolver")
    def test_validate_input_error_short_circuits_to_end(self, mock_sr_class):
        from app.agent.graph import create_quiz_agent_graph

        graph = create_quiz_agent_graph("test-key")
        final_state = graph.invoke(make_initial_state(question_count=2))

        assert final_state.get("error_code") == "INVALID_QUESTION_COUNT"
        assert final_state.get("error_status") == 400
        mock_sr_class.assert_not_called()

    @patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI")
    @patch("app.agent.nodes.fetch_source.SourceResolver")
    def test_fetch_source_error_short_circuits(self, mock_sr_class, mock_llm_class):
        from app.agent.graph import create_quiz_agent_graph

        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.side_effect = HTTPException(502, "error")
        mock_sr_class.return_value = mock_resolver

        graph = create_quiz_agent_graph("test-key")
        final_state = graph.invoke(make_initial_state())

        assert final_state.get("error_code") == "SOURCE_FETCH_FAILED"
        mock_llm_class.return_value.invoke.assert_not_called()

    @patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI")
    @patch("app.agent.nodes.fetch_source.SourceResolver")
    def test_generate_quiz_error_short_circuits(self, mock_sr_class, mock_llm_class):
        from app.agent.graph import create_quiz_agent_graph

        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = {
            "url": "https://example.com",
            "title": "T",
            "text": "text content",
            "quotes": [],
        }
        mock_sr_class.return_value = mock_resolver

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(text="arithmetic"),
            google_exceptions.Unauthenticated("auth error"),
        ]
        mock_llm_class.return_value = mock_llm

        graph = create_quiz_agent_graph("test-key")
        final_state = graph.invoke(make_initial_state())

        assert final_state.get("error_code") == "GEMINI_API_KEY_INVALID"
        assert final_state.get("result") is None

    @patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI")
    @patch("app.agent.nodes.fetch_source.SourceResolver")
    def test_parse_output_error_returns_ai_invalid_json(self, mock_sr_class, mock_llm_class):
        from app.agent.graph import create_quiz_agent_graph

        make_happy_mocks(mock_sr_class, mock_llm_class)
        mock_llm_class.return_value.invoke.side_effect = [
            MagicMock(text="arithmetic"),
            MagicMock(content="INVALID JSON {{{"),
        ]

        graph = create_quiz_agent_graph("test-key")
        final_state = graph.invoke(make_initial_state())

        assert final_state.get("error_code") == "AI_INVALID_JSON"
        assert final_state.get("error_status") == 500
