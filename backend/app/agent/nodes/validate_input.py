"""Validate input node."""
import logging

from typing import Any

from app.agent.state import AgentState
logger = logging.getLogger(__name__)


def validate_input(state: AgentState) -> dict[str, Any]:
    """Validate incoming agent input."""
    logger.info("[validate_input] Starting validation")

    if state.get("question_count") != 1:
        logger.info(f"[validate_input] Invalid question_count: {state.get('question_count')}")
        return {"error_code": "INVALID_QUESTION_COUNT", "error_status": 400}

    if state.get("source_type") != "url":
        logger.info(f"[validate_input] Invalid source_type: {state.get('source_type')!r}")
        return {"error_code": "INVALID_INPUT", "error_status": 400}

    source_value = state.get("source_value", "")
    if not source_value or not source_value.startswith(("http://", "https://")):
        logger.info(f"[validate_input] Invalid source_value: {source_value!r}")
        return {"error_code": "INVALID_INPUT", "error_status": 400}

    logger.info("[validate_input] Validation passed")
    return {}
