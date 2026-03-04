"""Unit tests for collect_evidence node."""

import json
from unittest.mock import MagicMock, patch


def make_state(**kwargs):
    base = {
        "claims": [{"claim_id": "C0001", "text": "Python is dynamically typed"}],
        "source_text": "Python is dynamically typed and supports type hints.",
        "source_url": "https://example.com",
    }
    base.update(kwargs)
    return base


def _quote_response(quote: str) -> str:
    return json.dumps({"quote": quote}, ensure_ascii=False)


def _url_response(url: str) -> str:
    return json.dumps({"url": url}, ensure_ascii=False)


class TestCollectEvidenceNode:
    @patch("app.agent.nodes.collect_evidence.GeminiLLMAdapter")
    def test_returns_source_evidence(self, mock_adapter_cls):
        from app.agent.nodes import make_collect_evidence_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _quote_response("Python is dynamically typed")
        mock_adapter_cls.return_value = mock_adapter

        node = make_collect_evidence_node("test-key")
        result = node(make_state())

        assert "error_code" not in result
        assert len(result["evidence_list"]) == 1
        entry = result["evidence_list"][0]
        assert entry["claim_id"] == "C0001"
        assert entry["evidence_id"] == "E0001"
        assert entry["rank"] == 1
        assert entry["url"] == "https://example.com"

    @patch("app.agent.nodes.collect_evidence.SourceResolver")
    @patch("app.agent.nodes.collect_evidence.GeminiLLMAdapter")
    def test_fallback_to_supplementary_source(self, mock_adapter_cls, mock_sr_cls):
        from app.agent.nodes import make_collect_evidence_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = [
            _quote_response(""),
            _url_response("https://supp.example.com"),
            _quote_response("supp quote"),
        ]
        mock_adapter_cls.return_value = mock_adapter

        mock_sr = MagicMock()
        mock_sr.fetch_and_parse.return_value = {"text": "supp text"}
        mock_sr_cls.return_value = mock_sr

        node = make_collect_evidence_node("test-key")
        result = node(make_state())

        assert len(result["evidence_list"]) == 1
        entry = result["evidence_list"][0]
        assert entry["url"] == "https://supp.example.com"
        assert entry["rank"] == 2

    @patch("app.agent.nodes.collect_evidence.GeminiLLMAdapter")
    def test_llm_exception_returns_empty_list_without_error(self, mock_adapter_cls):
        from app.agent.nodes import make_collect_evidence_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = RuntimeError("boom")
        mock_adapter_cls.return_value = mock_adapter

        node = make_collect_evidence_node("test-key")
        result = node(make_state())

        assert "error_code" not in result
        assert result["evidence_list"] == []

    @patch("app.agent.nodes.collect_evidence.GeminiLLMAdapter")
    def test_multiple_claims_flattened(self, mock_adapter_cls):
        from app.agent.nodes import make_collect_evidence_node

        claims = [
            {"claim_id": "C0001", "text": "A"},
            {"claim_id": "C0002", "text": "B"},
        ]
        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = [
            _quote_response("evidence A"),
            _quote_response("evidence B"),
        ]
        mock_adapter_cls.return_value = mock_adapter

        node = make_collect_evidence_node("test-key")
        result = node(make_state(claims=claims))

        assert len(result["evidence_list"]) == 2
        assert {e["claim_id"] for e in result["evidence_list"]} == {"C0001", "C0002"}
        assert all(e["evidence_id"] == "E0001" for e in result["evidence_list"])
