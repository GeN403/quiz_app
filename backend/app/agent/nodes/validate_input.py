"""Validate input node."""

from typing import Any

from app.agent.state import AgentState


def validate_input(state: AgentState) -> dict[str, Any]:
    """Validate incoming agent input."""
    print("[validate_input] Starting validation")

    if state.get("question_count") != 1:
        print(f"[validate_input] Invalid question_count: {state.get('question_count')}")
        return {"error_code": "INVALID_QUESTION_COUNT", "error_status": 400}

    if state.get("source_type") != "url":
        print(f"[validate_input] Invalid source_type: {state.get('source_type')!r}")
        return {"error_code": "INVALID_INPUT", "error_status": 400}

    source_value = state.get("source_value", "")
    if not source_value or not source_value.startswith(("http://", "https://")):
        print(f"[validate_input] Invalid source_value: {source_value!r}")
        return {"error_code": "INVALID_INPUT", "error_status": 400}

    print("[validate_input] Validation passed")
    return {}
