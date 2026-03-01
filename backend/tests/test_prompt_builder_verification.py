"""
検証ループ用プロンプトビルダーのユニットテスト

Task 2.1, 2.2, 2.3
Requirements: 1.1, 1.2, 3.1, 4.1
"""

import pytest

from app.core.prompt_builder import (
    build_prompt_decompose_claims,
    build_prompt_verify_claim,
    build_prompt_rewrite_quiz,
)
from app.agent.state import ClaimEntry, EvidenceEntry


# ---- Task 2.1: build_prompt_decompose_claims ----

class TestBuildPromptDecomposeClaims:
    QUIZ_TEXT = (
        "QUESTION:\nPython は静的型付け言語でしょうか？\n\n"
        "---\n\nEXPLANATION:\nPython は動的型付け言語です。\n\n"
        "---\n\nALTERNATIVE:\n型ヒントは実行時には強制されません。"
    )

    def test_returns_string(self):
        result = build_prompt_decompose_claims(self.QUIZ_TEXT)
        assert isinstance(result, str)

    def test_contains_quiz_text(self):
        result = build_prompt_decompose_claims(self.QUIZ_TEXT)
        assert "Python は静的型付け言語でしょうか" in result

    def test_mentions_max_claims(self):
        """最大 5 件の制約がプロンプトに含まれる"""
        result = build_prompt_decompose_claims(self.QUIZ_TEXT)
        assert "5" in result

    def test_mentions_json_array_format(self):
        """LLM に JSON 配列形式で返却させる指示がある"""
        result = build_prompt_decompose_claims(self.QUIZ_TEXT)
        assert "text" in result  # {"text": "..."} を含む配列形式

    def test_mentions_claim_as_statement(self):
        """主語＋述語の短文（主張）として返させる指示がある"""
        result = build_prompt_decompose_claims(self.QUIZ_TEXT)
        # 主張・claim などのキーワードが含まれること
        assert any(kw in result for kw in ["主張", "claim", "命題"])


# ---- Task 2.2: build_prompt_verify_claim ----

class TestBuildPromptVerifyClaim:
    CLAIM: ClaimEntry = {"claim_id": "C0001", "text": "Python は動的型付け言語である"}

    def _make_evidence(self, claim_id: str, evidence_id: str, quote: str, rank: int) -> EvidenceEntry:
        return {
            "claim_id": claim_id,
            "evidence_id": evidence_id,
            "url": "https://example.com",
            "quote": quote,
            "rank": rank,
        }

    def test_returns_string(self):
        evidences = [self._make_evidence("C0001", "E0001", "Python は動的型付け言語です。", 1)]
        result = build_prompt_verify_claim(self.CLAIM, evidences)
        assert isinstance(result, str)

    def test_contains_claim_text(self):
        evidences = [self._make_evidence("C0001", "E0001", "Python は動的型付け言語です。", 1)]
        result = build_prompt_verify_claim(self.CLAIM, evidences)
        assert "Python は動的型付け言語である" in result

    def test_contains_evidence_quote(self):
        evidences = [self._make_evidence("C0001", "E0001", "Python は動的型付け言語です。", 1)]
        result = build_prompt_verify_claim(self.CLAIM, evidences)
        assert "Python は動的型付け言語です。" in result

    def test_quote_truncated_to_500_chars(self):
        """quote が 500 文字を超える場合、先頭 500 文字のみが含まれる"""
        long_quote = "A" * 600
        evidences = [self._make_evidence("C0001", "E0001", long_quote, 1)]
        result = build_prompt_verify_claim(self.CLAIM, evidences)
        assert "A" * 500 in result
        assert "A" * 501 not in result

    def test_uses_max_3_evidences(self):
        """rank 昇順で最大 3 件のみ使用する（4 件目以降は無視）"""
        evidences = [
            self._make_evidence("C0001", f"E{i:04d}", f"quote_{i}", i)
            for i in range(1, 5)  # rank 1〜4 の 4 件
        ]
        result = build_prompt_verify_claim(self.CLAIM, evidences)
        assert "quote_1" in result
        assert "quote_2" in result
        assert "quote_3" in result
        assert "quote_4" not in result

    def test_mentions_verdict_format(self):
        """pass/fail 形式で返却させる指示がある"""
        evidences = [self._make_evidence("C0001", "E0001", "Python は動的型付け言語です。", 1)]
        result = build_prompt_verify_claim(self.CLAIM, evidences)
        assert "pass" in result.lower() or "fail" in result.lower()

    def test_empty_evidence_list(self):
        """根拠が 0 件でもクラッシュしない"""
        result = build_prompt_verify_claim(self.CLAIM, [])
        assert isinstance(result, str)


# ---- Task 2.3: build_prompt_rewrite_quiz ----

class TestBuildPromptRewriteQuiz:
    QUIZ_TEXT = (
        "QUESTION:\nPython は静的型付け言語でしょうか？\n\n"
        "---\n\nEXPLANATION:\nPython は動的型付け言語です。\n\n"
        "---\n\nALTERNATIVE:\n型ヒントは実行時には強制されません。"
    )
    FAILED_CLAIMS = [
        {"claim_id": "C0001", "text": "Python は静的型付け言語である", "reason": "Python は動的型付けである"},
    ]

    def test_returns_string(self):
        result = build_prompt_rewrite_quiz(self.QUIZ_TEXT, self.FAILED_CLAIMS)
        assert isinstance(result, str)

    def test_contains_quiz_text(self):
        result = build_prompt_rewrite_quiz(self.QUIZ_TEXT, self.FAILED_CLAIMS)
        assert "Python は静的型付け言語でしょうか" in result

    def test_contains_failed_claim_reason(self):
        result = build_prompt_rewrite_quiz(self.QUIZ_TEXT, self.FAILED_CLAIMS)
        assert "Python は動的型付けである" in result

    def test_contains_failed_claim_text(self):
        result = build_prompt_rewrite_quiz(self.QUIZ_TEXT, self.FAILED_CLAIMS)
        assert "Python は静的型付け言語である" in result

    def test_mentions_json_output_format(self):
        """QuizData 互換 JSON を返させる指示がある"""
        result = build_prompt_rewrite_quiz(self.QUIZ_TEXT, self.FAILED_CLAIMS)
        assert "question" in result

    def test_multiple_failed_claims(self):
        failed = [
            {"claim_id": "C0001", "text": "主張A", "reason": "理由A"},
            {"claim_id": "C0002", "text": "主張B", "reason": "理由B"},
        ]
        result = build_prompt_rewrite_quiz(self.QUIZ_TEXT, failed)
        assert "主張A" in result
        assert "主張B" in result
        assert "理由A" in result
        assert "理由B" in result
