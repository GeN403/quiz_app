"""Rewrite quiz node factory."""
import logging

from typing import Any, Callable

from google.api_core import exceptions as google_exceptions

from app.agent.state import AgentState
from app.core.prompt_builder import build_prompt_rewrite_quiz
logger = logging.getLogger(__name__)


def make_rewrite_quiz_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。fail した主張情報をもとに LLM に問題を書き換えさせ、
    llm_raw_response を更新して verification_attempts をインクリメントするノード関数を返す。

    返すノード関数:
      正常時: {"llm_raw_response": str, "verification_attempts": int}
      エラー時: {"error_code": str, "error_status": int}
    Requirements: 4.1, 4.3
    """

    def rewrite_quiz(state: AgentState) -> dict[str, Any]:
        logger.info("[rewrite_quiz] Starting")

        quiz_text: str = state.get("quiz_text", "")
        verification_results = state.get("verification_results", [])
        current_attempts: int = state.get("verification_attempts", 0)

        # fail した主張の claim_id と reason を抽出
        failed_claims = [
            {
                "claim_id": r["claim_id"],
                "text": "",  # verification_results には text は含まれないため空文字
                "reason": str(r.get("reason", "") or ""),
            }
            for r in verification_results
            if r.get("verdict") == "fail"
        ]

        # claims から text を補完（state["claims"] がある場合）
        claims_map = {c["claim_id"]: c["text"] for c in state.get("claims", [])}
        for fc in failed_claims:
            fc["text"] = claims_map.get(fc["claim_id"], "")

        prompt = build_prompt_rewrite_quiz(quiz_text, failed_claims)
        logger.info(f"[rewrite_quiz] Rewriting quiz with {len(failed_claims)} failed claims")

        try:
            from app.agent import nodes as nodes_pkg
            llm = nodes_pkg.ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-lite",
                google_api_key=gemini_api_key,
            )
            response = llm.invoke(prompt)
            raw_text = response.content
            logger.info(f"[rewrite_quiz] LLM response received ({len(raw_text)} chars)")

        except google_exceptions.Unauthenticated:
            logger.info("[rewrite_quiz] Unauthenticated error")
            return {"error_code": "GEMINI_API_KEY_INVALID", "error_status": 401}
        except google_exceptions.PermissionDenied:
            logger.info("[rewrite_quiz] PermissionDenied error")
            return {"error_code": "GEMINI_API_KEY_PERMISSION_DENIED", "error_status": 403}
        except google_exceptions.ResourceExhausted:
            logger.info("[rewrite_quiz] ResourceExhausted error")
            return {"error_code": "GEMINI_RATE_LIMIT", "error_status": 429}
        except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError):
            logger.info("[rewrite_quiz] Service unavailable error")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}
        except google_exceptions.DeadlineExceeded:
            logger.info("[rewrite_quiz] DeadlineExceeded error")
            return {"error_code": "GEMINI_TIMEOUT", "error_status": 504}
        except Exception as e:
            logger.info(f"[rewrite_quiz] Unexpected error: {e}")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}

        # verification_attempts を +1 インクリメント
        new_attempts = current_attempts + 1
        logger.info(f"[rewrite_quiz] Incremented verification_attempts: {current_attempts} → {new_attempts}")

        return {
            "llm_raw_response": raw_text,
            "verification_attempts": new_attempts,
        }

    return rewrite_quiz
