"""Parse LLM output node."""
import logging

from typing import Any

from pydantic import ValidationError

from app.agent.state import AgentState
from app.clients.gemini_client import parse_json_with_retry
from app.models.quiz import QuizData
logger = logging.getLogger(__name__)


def parse_output(state: AgentState) -> dict[str, Any]:
    """Parse quiz JSON output and enforce server source fields."""
    logger.info("[parse_output] Parsing LLM response")
    raw_response = state.get("llm_raw_response", "")

    try:
        parsed = parse_json_with_retry(raw_response)
    except Exception as e:
        logger.info(f"[parse_output] JSON parse error: {e}")
        return {"error_code": "AI_INVALID_JSON", "error_status": 500}

    if not isinstance(parsed, dict):
        logger.info(f"[parse_output] Parsed result is not a dict: {type(parsed)}")
        return {"error_code": "AI_INVALID_JSON", "error_status": 500}

    parsed["source"] = {
        "url": state.get("source_url", ""),
        "title": state.get("source_title", ""),
        "quote": state.get("selected_quote_final", ""),
    }
    logger.info("[parse_output] Source overwritten with server-confirmed values")

    try:
        quiz_data = QuizData(**parsed)
        result = quiz_data.model_dump(by_alias=True)
    except ValidationError as e:
        logger.info(f"[parse_output] Pydantic validation error: {e}")
        return {"error_code": "AI_INVALID_JSON", "error_status": 500}

    logger.info("[parse_output] Success")
    return {"result": result}
