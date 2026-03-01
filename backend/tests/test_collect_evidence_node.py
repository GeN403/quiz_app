"""
collect_evidence ノードのユニットテスト

Task 4.1, 4.2 (Task 8.2 optional)
Requirements: 2.1, 2.4, 3.7
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def make_state(**kwargs):
    base = {
        "claims": [{"claim_id": "C0001", "text": "Python は動的型付け言語である"}],
        "source_text": "Python は動的型付け言語です。型ヒントは実行時に強制されません。",
        "source_url": "https://example.com",
    }
    base.update(kwargs)
    return base


def _make_quote_response(quote: str) -> MagicMock:
    return MagicMock(content=json.dumps({"quote": quote}, ensure_ascii=False))


def _make_url_response(url: str) -> MagicMock:
    return MagicMock(content=json.dumps({"url": url}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Task 4.1: source_text から EvidenceEntry を生成する
# ---------------------------------------------------------------------------

class TestCollectEvidenceNodeSourceText:
    def test_returns_evidence_list(self):
        """evidence_list が返される（常に正常終了）"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_quote_response("Python は動的型付け言語です。")
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        assert "evidence_list" in result
        assert "error_code" not in result

    def test_evidence_id_is_e0001_for_source_entry(self):
        """source_text 由来の最初の EvidenceEntry の evidence_id が E0001 になる"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_quote_response("Python は動的型付け言語です。")
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        assert len(result["evidence_list"]) == 1
        assert result["evidence_list"][0]["evidence_id"] == "E0001"

    def test_evidence_id_is_zero_padded_4_digits(self):
        """evidence_id がゼロ埋め 4 桁形式（E0001〜）になる"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_quote_response("テスト引用")
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        ev_id = result["evidence_list"][0]["evidence_id"]
        assert len(ev_id) == 5       # "E" + 4 digits
        assert ev_id[0] == "E"
        assert ev_id[1:].isdigit()

    def test_source_entry_has_rank_1(self):
        """source_text 由来の EvidenceEntry は rank=1 になる (Requirements: 3.7)"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_quote_response("Python は動的型付け言語です。")
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        assert result["evidence_list"][0]["rank"] == 1

    def test_source_entry_claim_id_matches(self):
        """EvidenceEntry の claim_id が入力の claim_id と一致する"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_quote_response("テスト引用")
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        assert result["evidence_list"][0]["claim_id"] == "C0001"

    def test_source_entry_url_matches_source_url(self):
        """source_text 由来の EvidenceEntry の url が source_url と一致する"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_quote_response("テスト引用")
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        assert result["evidence_list"][0]["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# Task 4.2: 補足 URL のフォールバックと例外処理
# ---------------------------------------------------------------------------

class TestCollectEvidenceNodeSupplementary:
    def test_source_resolver_exception_yields_zero_entries(self):
        """SourceResolver が例外を throw したとき 0 件で続行する (Requirements: 2.4)"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls, \
             patch("app.agent.nodes.SourceResolver") as mock_sr_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = [
                _make_quote_response(""),                            # source から空 quote
                _make_url_response("https://supp.example.com"),     # URL 提案
            ]
            mock_cls.return_value = mock_llm

            mock_sr = MagicMock()
            mock_sr.fetch_and_parse.side_effect = Exception("fetch failed")
            mock_sr_cls.return_value = mock_sr

            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        assert "error_code" not in result
        assert result["evidence_list"] == []

    def test_llm_exception_yields_zero_entries_no_error(self):
        """LLM が例外を throw したとき 0 件で続行する（エラー終了しない）"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("LLM error")
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state())

        assert "error_code" not in result
        assert "evidence_list" in result


# ---------------------------------------------------------------------------
# Task 4.2: 複数主張のフラットな evidence_list
# ---------------------------------------------------------------------------

class TestCollectEvidenceNodeMultipleClaims:
    def test_evidence_list_is_flat_for_multiple_claims(self):
        """複数主張の EvidenceEntry が フラットな evidence_list に格納される (Requirements: 2.5)"""
        from app.agent.nodes import make_collect_evidence_node

        claims = [
            {"claim_id": "C0001", "text": "主張A"},
            {"claim_id": "C0002", "text": "主張B"},
        ]
        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = [
                _make_quote_response("根拠A"),
                _make_quote_response("根拠B"),
            ]
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state(claims=claims))

        ev_list = result["evidence_list"]
        assert isinstance(ev_list, list)
        claim_ids = [e["claim_id"] for e in ev_list]
        assert "C0001" in claim_ids
        assert "C0002" in claim_ids

    def test_evidence_id_resets_per_claim(self):
        """claim_id が変わると evidence_id が E0001 からリセットされる"""
        from app.agent.nodes import make_collect_evidence_node

        claims = [
            {"claim_id": "C0001", "text": "主張A"},
            {"claim_id": "C0002", "text": "主張B"},
        ]
        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = [
                _make_quote_response("根拠A"),
                _make_quote_response("根拠B"),
            ]
            mock_cls.return_value = mock_llm
            node = make_collect_evidence_node("test-key")
            result = node(make_state(claims=claims))

        ev_list = result["evidence_list"]
        for ev in ev_list:
            # 各 claim の最初のエントリは E0001
            if ev["evidence_id"] == "E0001":
                assert True
        # 両 claim が E0001 を持つ
        e_ids = [e["evidence_id"] for e in ev_list]
        assert e_ids.count("E0001") == 2

    def test_empty_claims_returns_empty_evidence_list(self):
        """claims が空の場合 evidence_list は空になる"""
        from app.agent.nodes import make_collect_evidence_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            node = make_collect_evidence_node("test-key")
            result = node(make_state(claims=[]))

        assert result["evidence_list"] == []
