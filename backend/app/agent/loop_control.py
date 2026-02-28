"""
反復制御サービス。
"""

from __future__ import annotations

from app.agent.state import DisambiguationParametersModel, LoopDecision


class LoopControlService:
    def should_continue(
        self,
        verdict: str,
        attempts: int,
        no_change_count: int,
        retrieval_retry_count: int,
        params: DisambiguationParametersModel,
    ) -> LoopDecision:
        if verdict == "unknown":
            return {
                "continue_loop": False,
                "termination_reason_code": "UNKNOWN",
                "termination_reason_message": "探索不完全/失敗により確定判定不能",
                "next_attempt": attempts,
                "retrieval_retry_count": retrieval_retry_count,
            }
        if attempts >= params.max_attempts:
            return {
                "continue_loop": False,
                "termination_reason_code": "MAX_VERIFICATION_ATTEMPTS_REACHED",
                "termination_reason_message": "最大反復回数に到達",
                "next_attempt": attempts,
                "retrieval_retry_count": retrieval_retry_count,
            }
        if no_change_count >= params.no_change_stop_threshold:
            return {
                "continue_loop": False,
                "termination_reason_code": "NO_CHANGE_LIMIT_REACHED",
                "termination_reason_message": "不変状態が連続したため停止",
                "next_attempt": attempts,
                "retrieval_retry_count": retrieval_retry_count,
            }
        if retrieval_retry_count > params.max_retrieval_retries:
            return {
                "continue_loop": False,
                "termination_reason_code": "RETRIEVAL_RETRY_EXCEEDED",
                "termination_reason_message": "探索再試行上限に到達",
                "next_attempt": attempts,
                "retrieval_retry_count": retrieval_retry_count,
            }
        return {
            "continue_loop": True,
            "termination_reason_code": "ALL_CLAIMS_PASSED",
            "termination_reason_message": "継続可能",
            "next_attempt": attempts + 1,
            "retrieval_retry_count": retrieval_retry_count,
        }
