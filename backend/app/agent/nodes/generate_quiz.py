"""Generate quiz node factory."""
import logging

from typing import Any, Callable

from app.agent.adapters.gemini_llm import GeminiLLMAdapter
from app.agent.ports.llm import LLMPortError
from app.agent.state import AgentState
from app.core.prompt_builder import build_prompt_url_mode
logger = logging.getLogger(__name__)


def make_generate_quiz_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """Create generate_quiz node."""
    llm = GeminiLLMAdapter(api_key=gemini_api_key)

    def generate_quiz(state: AgentState) -> dict[str, Any]:
        logger.info("[generate_quiz] Building prompt and calling Gemini API")

        quote_final = state.get("selected_quote_final", "")
        prompt = build_prompt_url_mode(
            category_name=state.get("category", ""),
            url=state.get("source_url", ""),
            title=state.get("source_title", ""),
            text_excerpt=state.get("source_text", ""),
            quotes=[quote_final] if quote_final else [],
            question_count=1,
            topic=state.get("resolved_topic"),
        )

        try:
            raw_text = llm.invoke(prompt)
            logger.info(f"[generate_quiz] LLM response received ({len(raw_text)} chars)")
            return {"llm_raw_response": raw_text}
        except LLMPortError as e:
            logger.info(f"[generate_quiz] LLMPortError: {e.error_code}")
            return {"error_code": e.error_code, "error_status": e.status_code}
        except Exception as e:
            logger.info(f"[generate_quiz] Unexpected error: {e}")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}

    return generate_quiz
