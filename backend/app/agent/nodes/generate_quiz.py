"""Generate quiz node factory."""
import logging

from typing import Any, Callable

from google.api_core import exceptions as google_exceptions
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.state import AgentState
from app.core.prompt_builder import build_prompt_url_mode
logger = logging.getLogger(__name__)


def make_generate_quiz_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """Create generate_quiz node."""

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
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-lite",
                google_api_key=gemini_api_key,
            )
            response = llm.invoke(prompt)
            raw_text = response.content
            logger.info(f"[generate_quiz] LLM response received ({len(raw_text)} chars)")
            return {"llm_raw_response": raw_text}

        except google_exceptions.Unauthenticated:
            logger.info("[generate_quiz] Unauthenticated error")
            return {"error_code": "GEMINI_API_KEY_INVALID", "error_status": 401}
        except google_exceptions.PermissionDenied:
            logger.info("[generate_quiz] PermissionDenied error")
            return {"error_code": "GEMINI_API_KEY_PERMISSION_DENIED", "error_status": 403}
        except google_exceptions.ResourceExhausted:
            logger.info("[generate_quiz] ResourceExhausted error")
            return {"error_code": "GEMINI_RATE_LIMIT", "error_status": 429}
        except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError):
            logger.info("[generate_quiz] Service unavailable error")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}
        except google_exceptions.DeadlineExceeded:
            logger.info("[generate_quiz] DeadlineExceeded error")
            return {"error_code": "GEMINI_TIMEOUT", "error_status": 504}
        except Exception as e:
            logger.info(f"[generate_quiz] Unexpected error: {e}")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}

    return generate_quiz
