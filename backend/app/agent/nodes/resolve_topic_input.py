"""Resolve topic input node factory."""

import logging
from typing import Any, Callable

from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def make_resolve_topic_input_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """Create resolve_topic_input node."""
    from app.agent import nodes as nodes_pkg
    explore_llm = nodes_pkg.ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=gemini_api_key,
        temperature=0.2,
        max_tokens=32,
    )

    def resolve_topic_input(state: AgentState) -> dict[str, Any]:
        topic = state.get("topic")

        if topic is not None:
            logger.info(
                "[resolve_topic_input] topic provided, skipping exploration: %s", topic
            )
            return {"resolved_topic": topic}

        source_text = state.get("source_text", "")
        source_title = state.get("source_title", "")
        prompt = (
            f"????: {source_title}\n\n"
            f"??:\n{source_text[:2000]}\n\n"
            "?????????????????????????????"
            "1?????????"
            "????????1??20???????????????????"
        )

        try:
            ai_msg = explore_llm.invoke(prompt)
            raw = ai_msg.text

            resolved_topic = raw.split("\n")[0].strip()
            if not resolved_topic:
                return {"error_code": "TOPIC_RESOLVE_FAILED", "error_status": 500}
            if len(resolved_topic) > 20:
                resolved_topic = resolved_topic[:20]

            logger.info(
                "[resolve_topic_input] topic not provided, exploring... resolved: %s",
                resolved_topic,
            )
            return {"resolved_topic": resolved_topic}

        except Exception:
            return {"error_code": "TOPIC_RESOLVE_FAILED", "error_status": 500}

    return resolve_topic_input
