"""Decompose claims node factory."""
import logging

from typing import Any, Callable

from app.agent.adapters.gemini_llm import GeminiLLMAdapter
from app.agent.ports.llm import LLMPortError
from app.agent.state import AgentState, ClaimEntry
from app.clients.gemini_client import parse_json_with_retry
from app.core.prompt_builder import build_prompt_decompose_claims
logger = logging.getLogger(__name__)


def make_decompose_claims_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    llm = GeminiLLMAdapter(api_key=gemini_api_key)
    """
    ファクトリ関数。llm_raw_response を解析して quiz_text を構築し、
    LLM に原子的主張リストの分解を要求するノード関数を返す。

    返すノード関数:
      正常時: {
          "claims": list[ClaimEntry],  # claim_id C0001〜・最大 5 件
          "quiz_text": str,
          "evidence_list": [],         # リセット
          "verification_results": [],  # リセット
      }
      エラー時: {"error_code": str, "error_status": int}
    Requirements: 1.1, 1.2, 1.3, 1.4, 4.6
    """

    def decompose_claims(state: AgentState) -> dict[str, Any]:
        logger.info("[decompose_claims] Starting")

        # 1. llm_raw_response をパースして QuizData を取り出す (Task 3.1)
        raw_response = state.get("llm_raw_response", "")
        try:
            parsed = parse_json_with_retry(raw_response)
        except Exception as e:
            logger.info(f"[decompose_claims] Failed to parse llm_raw_response: {e}")
            return {"error_code": "AI_INVALID_JSON", "error_status": 500}

        if not isinstance(parsed, dict):
            logger.info("[decompose_claims] llm_raw_response is not a dict")
            return {"error_code": "AI_INVALID_JSON", "error_status": 500}

        # 2. quiz_text を構築する (Task 3.1)
        question = parsed.get("question", "")
        explanation = parsed.get("explanation", "")
        alternative = parsed.get(
            "Alternative Solutions/Correctness Judgment Criteria", ""
        )
        quiz_text = (
            f"QUESTION:\n{question}\n\n"
            f"---\n\nEXPLANATION:\n{explanation}\n\n"
            f"---\n\nALTERNATIVE:\n{alternative}"
        )
        logger.info(f"[decompose_claims] Built quiz_text ({len(quiz_text)} chars)")

        # 3. build_prompt_decompose_claims を呼び出して LLM に主張リストを要求する (Task 3.1)
        prompt = build_prompt_decompose_claims(quiz_text)
        try:
            claims_raw = llm.invoke(prompt)
            logger.info(f"[decompose_claims] LLM response received ({len(claims_raw)} chars)")
        except LLMPortError as e:
            logger.info(f"[decompose_claims] LLMPortError: {e.error_code}")
            return {"error_code": e.error_code, "error_status": e.status_code}
        except Exception as e:
            logger.info(f"[decompose_claims] Unexpected error: {e}")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}

        # 4. LLM レスポンスをパースして主張リストを取り出す (Task 3.2)
        try:
            claims_parsed = parse_json_with_retry(claims_raw)
        except Exception as e:
            logger.info(f"[decompose_claims] Failed to parse claims response: {e}")
            return {"error_code": "CLAIM_DECOMPOSE_FAILED", "error_status": 500}

        if not isinstance(claims_parsed, list):
            logger.info("[decompose_claims] Claims response is not a list")
            return {"error_code": "CLAIM_DECOMPOSE_FAILED", "error_status": 500}

        # 5. claim_id を付与して最大 5 件に切り詰める (Task 3.2)
        claims: list[ClaimEntry] = []
        for i, item in enumerate(claims_parsed[:5], 1):
            if isinstance(item, dict) and "text" in item:
                claims.append({
                    "claim_id": f"C{i:04d}",
                    "text": str(item["text"]),
                })

        # 6. 主張が 0 件の場合はエラー (Task 3.2, Requirements: 1.4)
        if not claims:
            logger.info("[decompose_claims] No valid claims extracted")
            return {"error_code": "CLAIM_DECOMPOSE_FAILED", "error_status": 500}

        logger.info(f"[decompose_claims] Extracted {len(claims)} claims")
        # 7. claims / quiz_text を返し、evidence_list / verification_results をリセット
        return {
            "claims": claims,
            "quiz_text": quiz_text,
            "evidence_list": [],
            "verification_results": [],
        }

    return decompose_claims
