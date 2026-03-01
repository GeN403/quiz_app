"""
fetch_source ノードのユニットテスト (Task 7.2)

Requirements: 2.3, 2.4
"""

from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from app.agent.nodes import fetch_source


def make_state(**kwargs):
    base = {
        "source_value": "https://example.com",
        "source_type": "url",
        "selected_quote": "",
        "source_text": "",
        "source_title": "",
        "source_url": "",
        "selected_quote_final": "",
        "llm_raw_response": "",
        "result": None,
        "error_code": None,
        "error_status": None,
    }
    base.update(kwargs)
    return base


def make_mock_resolved(
    text="Sample text content " * 50,
    title="Example Title",
    url="https://example.com",
    quotes=["Quote 1", "Quote 2"],
):
    return {"url": url, "title": title, "text": text, "quotes": quotes}


class TestFetchSource:
    @patch("app.agent.nodes.SourceResolver")
    def test_successful_fetch_sets_state_fields(self, mock_sr_class):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = make_mock_resolved()
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state())

        assert "error_code" not in result
        assert result["source_title"] == "Example Title"
        assert result["source_url"] == "https://example.com"
        assert "source_text" in result
        assert "selected_quote_final" in result

    @patch("app.agent.nodes.SourceResolver")
    def test_text_truncated_to_8000_chars(self, mock_sr_class):
        long_text = "x" * 10000
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = make_mock_resolved(text=long_text)
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state())

        assert len(result["source_text"]) == 8000

    @patch("app.agent.nodes.SourceResolver")
    def test_text_within_8000_chars_not_truncated(self, mock_sr_class):
        text = "x" * 5000
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = make_mock_resolved(text=text)
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state())

        assert len(result["source_text"]) == 5000

    @patch("app.agent.nodes.SourceResolver")
    def test_source_resolver_http_exception_returns_source_fetch_failed(self, mock_sr_class):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.side_effect = HTTPException(
            status_code=502, detail="URL_FETCH_FAILED"
        )
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state())

        assert result["error_code"] == "SOURCE_FETCH_FAILED"
        assert result["error_status"] == 502

    @patch("app.agent.nodes.SourceResolver")
    def test_source_resolver_general_exception_returns_source_fetch_failed(self, mock_sr_class):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.side_effect = Exception("network error")
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state())

        assert result["error_code"] == "SOURCE_FETCH_FAILED"
        assert result["error_status"] == 502

    @patch("app.agent.nodes.SourceResolver")
    def test_no_selected_quote_uses_first_candidate(self, mock_sr_class):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = make_mock_resolved(
            quotes=["First quote", "Second quote"]
        )
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state(selected_quote=""))

        assert result["selected_quote_final"] == "First quote"

    @patch("app.agent.nodes.SourceResolver")
    def test_no_quotes_uses_empty_string(self, mock_sr_class):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = make_mock_resolved(quotes=[])
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state(selected_quote=""))

        assert result["selected_quote_final"] == ""

    @patch("app.agent.nodes.SourceResolver")
    def test_valid_selected_quote_is_used(self, mock_sr_class):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = make_mock_resolved(
            quotes=["Other quote"]
        )
        mock_resolver.verify_quote.return_value = True
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state(selected_quote="My selected quote"))

        assert result["selected_quote_final"] == "My selected quote"

    @patch("app.agent.nodes.SourceResolver")
    def test_invalid_selected_quote_falls_back_to_first_candidate(self, mock_sr_class):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = make_mock_resolved(
            quotes=["Fallback quote"]
        )
        mock_resolver.verify_quote.return_value = False
        mock_sr_class.return_value = mock_resolver

        result = fetch_source(make_state(selected_quote="Not in text"))

        assert result["selected_quote_final"] == "Fallback quote"
