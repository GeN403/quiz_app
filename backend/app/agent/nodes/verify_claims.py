"""Verify claims node factory."""
import logging

from typing import Any, Callable

from pydantic import ValidationError

from app.agent.adapters.gemini_llm import GeminiLLMAdapter
from app.agent.state import (
    AgentState,
    ClaimEntry,
    EvidenceEntry,
    VerificationResult,
    VerificationSnapshot,
    DisambiguationParametersModel,
    JudgementResult,
)
from app.agent.loop_control import LoopControlService
from app.agent.disambiguation_services import (
    MinorDisambiguationService,
    MajorDisambiguationService,
)
from app.clients.gemini_client import parse_json_with_retry
from app.core.prompt_builder import build_prompt_verify_claim
logger = logging.getLogger(__name__)


MAX_VERIFICATION_RETRIES = 3


def make_verify_claims_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。各主張を根拠エントリと照合して pass/fail 判定し、
    結果に応じてスナップショットを蓄積してループ遷移先を決定するノード関数を返す。

    返すノード関数:
      全 pass:    {"verification_results": list[VerificationResult]}
      fail(上限内): {"verification_results": ..., "verification_history": [snapshot]}
      fail(上限超過): {"verification_results": ..., "verification_history": [snapshot],
                       "error_code": "VERIFICATION_MAX_RETRIES_EXCEEDED", "error_status": 500}
      スキーマエラー: {"error_code": "INTERNAL_SCHEMA_ERROR", "error_status": 500}
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.2, 4.4, 4.5
    """

    def _resolve_disambiguation_parameters(
        state: AgentState,
    ) -> tuple[DisambiguationParametersModel | None, dict[str, Any] | None]:
        raw_params = state.get("disambiguation_parameters")
        try:
            if isinstance(raw_params, DisambiguationParametersModel):
                return raw_params, None
            if isinstance(raw_params, dict):
                return DisambiguationParametersModel(**raw_params), None
            return DisambiguationParametersModel(), None
        except ValidationError:
            return None, {
                "error_code": "PARAMETER_CONSTRAINT_VIOLATION",
                "error_status": 400,
                "termination_reason_code": "UNKNOWN",
                "termination_reason_message": "判定パラメータの制約違反",
            }

    def verify_claims(state: AgentState) -> dict[str, Any]:
        logger.info("[verify_claims] Starting")
        params, param_error = _resolve_disambiguation_parameters(state)
        if param_error:
            return param_error

        claims: list[ClaimEntry] = state.get("claims", [])
        evidence_list: list[EvidenceEntry] = state.get("evidence_list", [])
        quiz_text: str = state.get("quiz_text", "")
        verification_attempts: int = state.get("verification_attempts", 0)
        retrieval_retry_count: int = state.get("retrieval_retry_count", 0)
        no_change_count: int = state.get("verification_no_change_count", 0)

        # claim_id → EvidenceEntry リストのインデックスを構築
        evidence_by_claim: dict[str, list[EvidenceEntry]] = {}
        for ev in evidence_list:
            cid = ev["claim_id"]
            if cid not in evidence_by_claim:
                evidence_by_claim[cid] = []
            evidence_by_claim[cid].append(ev)

        # LLM インスタンス（根拠あり主張の判定に使用）
        llm = GeminiLLMAdapter(api_key=gemini_api_key)

        verification_results: list[VerificationResult] = []

        # Task 5.1: 各主張を判定する
        for claim in claims:
            claim_id = claim["claim_id"]
            evidences = evidence_by_claim.get(claim_id, [])

            if not evidences:
                # Task 5.1: 根拠 0 件 → 自動 fail（LLM 呼び出しなし）(Requirements: 3.6)
                auto_fail: VerificationResult = {
                    "claim_id": claim_id,
                    "verdict": "fail",
                    "reason": "根拠が取得できないため検証不能",
                }
                verification_results.append(auto_fail)
                logger.info(f"[verify_claims] Auto-fail for {claim_id} (no evidence)")
                continue

            # Task 5.1: 根拠あり → LLM 判定 (Requirements: 3.1)
            prompt = build_prompt_verify_claim(claim, evidences)
            try:
                response_text = llm.invoke(prompt)
                parsed = parse_json_with_retry(response_text)

                if not isinstance(parsed, dict):
                    verdict = "fail"
                    reason = "LLM 応答のパースに失敗"
                else:
                    verdict = str(parsed.get("verdict", "fail"))
                    # None を "" に変換してから strip
                    reason = str(parsed.get("reason", "") or "").strip()

                # Task 5.1: verdict=="fail" かつ reason が空/None → INTERNAL_SCHEMA_ERROR
                if verdict == "fail" and not reason:
                    logger.info(f"[verify_claims] INTERNAL_SCHEMA_ERROR: fail with empty reason for {claim_id}")
                    return {"error_code": "INTERNAL_SCHEMA_ERROR", "error_status": 500}

                vr: VerificationResult = {
                    "claim_id": claim_id,
                    "verdict": verdict,  # type: ignore[typeddict-item]
                }
                if reason:
                    vr["reason"] = reason
                verification_results.append(vr)
                logger.info(f"[verify_claims] {claim_id}: {verdict}")

            except Exception as e:
                # LLM 呼び出し例外 → fail として処理
                reason = f"LLM 呼び出しに失敗: {str(e)[:100]}"
                vr_err: VerificationResult = {
                    "claim_id": claim_id,
                    "verdict": "fail",
                    "reason": reason,
                }
                verification_results.append(vr_err)
                logger.info(f"[verify_claims] LLM error for {claim_id}: {e}")

        # Task 5.2: 全 pass チェック
        failed_results = [r for r in verification_results if r.get("verdict") == "fail"]

        if not failed_results:
            # 全 pass: verification_results のみ返す（スナップショット追記なし）
            logger.info("[verify_claims] All claims passed")
            verification_outcome: JudgementResult = {
                "verdict": "pass",
                "reason": "全主張が根拠と整合したため通過",
                "evidence_status": "ok",
                "effective_competing_count": 0,
            }
            return {
                "verification_results": verification_results,
                "disambiguation_parameters": params,
                "verification_outcome": verification_outcome,
                "verification_no_change_count": 0,
            }

        # fail あり: スナップショットを先に構築して verification_history に差分追記
        failed_claim_ids = [r["claim_id"] for r in failed_results]
        snapshot: VerificationSnapshot = {
            "attempt": verification_attempts,
            "quiz_text": quiz_text,
            "claims": claims,
            "evidence_list": evidence_list,
            "verification_results": verification_results,
            "failed_claim_ids": failed_claim_ids,
            "retrieval_retry_count": retrieval_retry_count,
            "llm_meta": {
                "model": "gemini-2.0-flash-lite",
                "temperature": 0.0,
            },
        }
        logger.info(
            f"[verify_claims] Fail detected: {failed_claim_ids}, "
            f"attempts={verification_attempts}"
        )

        loop_control = LoopControlService()
        previous_history = state.get("verification_history", [])
        if previous_history and previous_history[-1].get("failed_claim_ids") == failed_claim_ids:
            no_change_count += 1
        else:
            no_change_count = 0

        effective_failed_count = len(failed_claim_ids)
        if effective_failed_count >= params.major_count_threshold:
            loop_verdict = "fail_major"
        else:
            loop_verdict = "fail_minor"

        loop_decision = loop_control.should_continue(
            verdict=loop_verdict,
            attempts=verification_attempts,
            no_change_count=no_change_count,
            retrieval_retry_count=retrieval_retry_count,
            params=params,
        )

        if not loop_decision["continue_loop"]:
            snapshot["termination_reason_code"] = loop_decision["termination_reason_code"]
            snapshot["termination_reason_message"] = loop_decision["termination_reason_message"]
            verification_outcome: JudgementResult = {
                "verdict": "unknown",
                "reason": loop_decision["termination_reason_message"],
                "evidence_status": "partial",
                "effective_competing_count": effective_failed_count,
                "termination_reason": loop_decision["termination_reason_code"],
            }
            return {
                "verification_results": verification_results,
                "verification_history": [snapshot],
                "disambiguation_parameters": params,
                "verification_outcome": verification_outcome,
                "verification_no_change_count": no_change_count,
                "termination_reason_code": loop_decision["termination_reason_code"],
                "termination_reason_message": loop_decision["termination_reason_message"],
            }

        if loop_verdict == "fail_major":
            proposal = MajorDisambiguationService().propose(
                concept_text=quiz_text[:50],
                candidates=[
                    {
                        "competing_id": failed["claim_id"],
                        "source": "verification",
                        "original_label": failed.get("reason", "") or failed["claim_id"],
                        "normalized_label": (failed.get("reason", "") or failed["claim_id"]).lower(),
                        "category": "related",
                        "similarity": 1.0,
                        "score": 1.0,
                        "selected": True,
                    }
                    for failed in failed_results
                ],
            )
        else:
            proposal = MinorDisambiguationService().propose(
                concept_text=quiz_text[:50],
                reason=failed_results[0].get("reason", "") or "限定語を追加",
            )
        snapshot["proposal"] = proposal
        verification_outcome = {
            "verdict": loop_verdict,
            "reason": failed_results[0].get("reason", "") or "検証に失敗",
            "evidence_status": "ok",
            "effective_competing_count": effective_failed_count,
        }

        return {
            "verification_results": verification_results,
            "verification_history": [snapshot],
            "disambiguation_parameters": params,
            "verification_outcome": verification_outcome,
            "verification_no_change_count": no_change_count,
        }

    return verify_claims


# ---------------------------------------------------------------------------
# Task 6 (検証ループ): rewrite_quiz ノードファクトリ
# ---------------------------------------------------------------------------
