"""
AgentState 拡張: 検証ループ用 TypedDict 型定義とフィールドのテスト

Task 1.1, 1.2
Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 4.7, 4.8
"""

import operator
import pytest
from typing import Annotated, get_type_hints
from pydantic import ValidationError

from app.agent.state import (
    AgentState,
    ClaimEntry,
    EvidenceEntry,
    VerificationResult,
    VerificationSnapshot,
    calculate_verification_attempts,
    DisambiguationParametersModel,
    SearchParams,
    CompetingConcept,
    DiscoveryResult,
    JudgementResult,
    MinorProposal,
    MajorProposal,
    LoopDecision,
    DisambiguationSnapshot,
)


class TestClaimEntry:
    def test_required_keys(self):
        assert ClaimEntry.__required_keys__ == frozenset({"claim_id", "text"})

    def test_no_optional_keys(self):
        assert ClaimEntry.__optional_keys__ == frozenset()

    def test_instantiation(self):
        entry: ClaimEntry = {"claim_id": "C0001", "text": "Python は動的型付け言語である"}
        assert entry["claim_id"] == "C0001"
        assert entry["text"] == "Python は動的型付け言語である"


class TestEvidenceEntry:
    def test_required_keys(self):
        assert EvidenceEntry.__required_keys__ == frozenset(
            {"claim_id", "evidence_id", "url", "quote", "rank"}
        )

    def test_optional_keys(self):
        assert EvidenceEntry.__optional_keys__ == frozenset({"title", "retrieved_at"})

    def test_instantiation_required_only(self):
        entry: EvidenceEntry = {
            "claim_id": "C0001",
            "evidence_id": "E0001",
            "url": "https://example.com",
            "quote": "Python は...",
            "rank": 1,
        }
        assert entry["rank"] == 1
        assert "title" not in entry

    def test_instantiation_with_optional_fields(self):
        entry: EvidenceEntry = {
            "claim_id": "C0001",
            "evidence_id": "E0001",
            "url": "https://example.com",
            "quote": "Python は...",
            "rank": 1,
            "title": "Python 公式",
            "retrieved_at": "2026-02-28T00:00:00+09:00",
        }
        assert entry["title"] == "Python 公式"
        assert entry["retrieved_at"] == "2026-02-28T00:00:00+09:00"

    def test_rank_is_int(self):
        entry: EvidenceEntry = {
            "claim_id": "C0002",
            "evidence_id": "E0002",
            "url": "https://example.com",
            "quote": "...",
            "rank": 2,
        }
        assert isinstance(entry["rank"], int)


class TestVerificationResult:
    def test_required_keys(self):
        assert VerificationResult.__required_keys__ == frozenset(
            {"claim_id", "verdict"}
        )

    def test_optional_keys(self):
        assert VerificationResult.__optional_keys__ == frozenset(
            {"reason", "used_evidence_ids", "confidence"}
        )

    def test_instantiation_pass_without_reason(self):
        result: VerificationResult = {"claim_id": "C0001", "verdict": "pass"}
        assert result["verdict"] == "pass"
        assert "reason" not in result

    def test_instantiation_fail_with_reason(self):
        result: VerificationResult = {
            "claim_id": "C0001",
            "verdict": "fail",
            "reason": "根拠テキストに該当する記述がない",
        }
        assert result["verdict"] == "fail"
        assert result["reason"] == "根拠テキストに該当する記述がない"

    def test_instantiation_with_all_optional_fields(self):
        result: VerificationResult = {
            "claim_id": "C0001",
            "verdict": "pass",
            "used_evidence_ids": ["E0001", "E0002"],
            "confidence": 0.95,
        }
        assert result["used_evidence_ids"] == ["E0001", "E0002"]
        assert result["confidence"] == 0.95


class TestVerificationSnapshot:
    def test_required_keys(self):
        assert VerificationSnapshot.__required_keys__ == frozenset(
            {
                "attempt",
                "quiz_text",
                "claims",
                "evidence_list",
                "verification_results",
                "failed_claim_ids",
            }
        )

    def test_optional_keys(self):
        assert VerificationSnapshot.__optional_keys__ == frozenset(
            {
                "retrieval_retry_count",
                "termination_reason_code",
                "termination_reason_message",
                "proposal",
                "llm_meta",
            }
        )

    def test_instantiation(self):
        snapshot: VerificationSnapshot = {
            "attempt": 0,
            "quiz_text": (
                "QUESTION:\nQ\n\n---\n\nEXPLANATION:\nE\n\n---\n\nALTERNATIVE:\nA"
            ),
            "claims": [{"claim_id": "C0001", "text": "Python は動的型付け言語である"}],
            "evidence_list": [],
            "verification_results": [
                {"claim_id": "C0001", "verdict": "fail", "reason": "根拠なし"}
            ],
            "failed_claim_ids": ["C0001"],
        }
        assert snapshot["attempt"] == 0
        assert snapshot["failed_claim_ids"] == ["C0001"]
        assert len(snapshot["claims"]) == 1

    def test_attempt_zero_origin(self):
        """attempt は 0-origin（初回 fail が attempt=0）"""
        snapshot: VerificationSnapshot = {
            "attempt": 0,
            "quiz_text": "QUESTION:\nQ\n\n---\n\nEXPLANATION:\nE\n\n---\n\nALTERNATIVE:\nA",
            "claims": [],
            "evidence_list": [],
            "verification_results": [],
            "failed_claim_ids": [],
        }
        assert snapshot["attempt"] == 0


class TestAgentStateExtension:
    """Task 1.2: AgentState への検証ループ用フィールド追加を検証する"""

    VERIFICATION_FIELDS = {
        "claims",
        "quiz_text",
        "evidence_list",
        "verification_results",
        "verification_attempts",
        "verification_history",
        "retrieval_retry_count",
    }

    def test_new_fields_in_annotations(self):
        """6 つの新フィールドが AgentState.__annotations__ に存在する"""
        annotations = AgentState.__annotations__
        for field in self.VERIFICATION_FIELDS:
            assert field in annotations, f"{field} が AgentState に見つかりません"

    def test_verification_history_uses_annotated_reducer(self):
        """verification_history が Annotated[list[VerificationSnapshot], operator.add] を使用する"""
        annotations = AgentState.__annotations__
        vh_type = annotations["verification_history"]
        # Annotated であることを確認
        assert hasattr(vh_type, "__metadata__"), (
            "verification_history は Annotated 型である必要があります"
        )
        # reducer が operator.add であることを確認
        assert operator.add in vh_type.__metadata__, (
            "verification_history の reducer は operator.add である必要があります"
        )

    def test_verification_history_is_only_reducer(self):
        """他の検証フィールドは Annotated を使用しない（非 reducer 方式との混在禁止）"""
        annotations = AgentState.__annotations__
        non_history_fields = self.VERIFICATION_FIELDS - {"verification_history"}
        for field in non_history_fields:
            ann = annotations[field]
            assert not hasattr(ann, "__metadata__"), (
                f"{field} が意図せず Annotated を使用しています（reducer 混在禁止）"
            )


class TestVerificationAttemptsCalculation:
    def test_empty_history_returns_zero(self):
        assert calculate_verification_attempts([]) == 0

    def test_attempts_calculated_from_max_attempt_plus_one(self):
        history: list[VerificationSnapshot] = [
            {
                "attempt": 0,
                "quiz_text": "Q",
                "claims": [],
                "evidence_list": [],
                "verification_results": [],
                "failed_claim_ids": [],
            },
            {
                "attempt": 2,
                "quiz_text": "Q2",
                "claims": [],
                "evidence_list": [],
                "verification_results": [],
                "failed_claim_ids": [],
            },
        ]
        assert calculate_verification_attempts(history) == 3


class TestDisambiguationParametersModel:
    def test_defaults_are_fixed(self):
        params = DisambiguationParametersModel()
        assert params.major_count_threshold == 16
        assert params.minor_count_threshold == 5
        assert params.score_threshold == 0.70
        assert params.max_attempts == 3
        assert params.no_change_stop_threshold == 2
        assert params.max_retrieval_retries == 0

    def test_constraint_minor_must_be_less_than_major(self):
        with pytest.raises(ValidationError):
            DisambiguationParametersModel(
                major_count_threshold=5,
                minor_count_threshold=5,
            )

    def test_constraint_score_range(self):
        with pytest.raises(ValidationError):
            DisambiguationParametersModel(score_threshold=1.01)

    def test_constraint_max_attempts_minimum(self):
        with pytest.raises(ValidationError):
            DisambiguationParametersModel(max_attempts=0)

    def test_constraint_no_change_minimum(self):
        with pytest.raises(ValidationError):
            DisambiguationParametersModel(no_change_stop_threshold=0)


class TestDisambiguationContracts:
    def test_search_params_required_keys(self):
        assert SearchParams.__required_keys__ == frozenset(
            {
                "source_policy",
                "max_candidates",
                "similarity_metric",
                "score_threshold",
                "normalization_rule",
                "selection_rule",
            }
        )

    def test_discovery_result_required_keys(self):
        assert DiscoveryResult.__required_keys__ == frozenset(
            {
                "snapshot_id",
                "evidence_status",
                "sources_attempted",
                "sources_succeeded",
                "sources_failed",
                "search_params",
                "candidates",
            }
        )

    def test_judgement_result_optional_termination_reason(self):
        assert "termination_reason" in JudgementResult.__optional_keys__

    def test_minor_proposal_uses_preface_not_suffix(self):
        sample: MinorProposal = {
            "mode": "preface",
            "before_concept": "A",
            "after_concept": "B",
            "added_preface": "入門",
            "edit_ops": [{"op": "insert", "path": "text", "before": "", "after": "入門"}],
        }
        assert sample["mode"] == "preface"

    def test_loop_decision_has_termination_reason_code(self):
        decision: LoopDecision = {
            "continue_loop": False,
            "termination_reason_code": "MAX_VERIFICATION_ATTEMPTS_REACHED",
            "termination_reason_message": "上限到達",
            "next_attempt": 3,
            "retrieval_retry_count": 0,
        }
        assert decision["termination_reason_code"] == "MAX_VERIFICATION_ATTEMPTS_REACHED"

    def test_disambiguation_snapshot_has_reproducibility_field(self):
        snapshot: DisambiguationSnapshot = {
            "attempt": 1,
            "input_concept": "A",
            "normalized_concept": "a",
            "verdict": "unknown",
            "reason": "探索不完全",
            "evidence_status": "partial",
            "snapshot_id": "snap-1",
            "effective_competing_count": 0,
            "llm_meta": {"model": "x", "temperature": 0.0},
        }
        assert "llm_meta" in snapshot
