"""Fetch source node."""

from typing import Any

from app.services.source_resolver import SourceResolver
from app.agent.state import AgentState


def fetch_source(state: AgentState) -> dict[str, Any]:
    """Fetch and normalize source content from URL."""
    source_value = state.get("source_value", "")
    selected_quote = state.get("selected_quote", "")
    print(f"[fetch_source] Fetching URL: {source_value}")

    try:
        resolver = SourceResolver(source_value, timeout=10)
        resolved = resolver.fetch_and_parse()
    except Exception as e:
        print(f"[fetch_source] Error fetching source: {e}")
        return {"error_code": "SOURCE_FETCH_FAILED", "error_status": 502}

    text = resolved.get("text", "")
    if len(text) > 8000:
        print(f"[fetch_source] Text truncated from {len(text)} to 8000 chars")
        text = text[:8000]

    title = resolved.get("title") or source_value

    quotes = resolved.get("quotes", [])
    if selected_quote:
        is_found = resolver.verify_quote(selected_quote)
        if is_found:
            selected_quote_final = selected_quote
        else:
            print("[fetch_source] Selected quote not found, using first candidate")
            selected_quote_final = quotes[0] if quotes else ""
    else:
        selected_quote_final = quotes[0] if quotes else ""

    print(f"[fetch_source] Success: title={title!r}, text_len={len(text)}")
    return {
        "source_text": text,
        "source_title": title,
        "source_url": resolved.get("url", source_value),
        "selected_quote_final": selected_quote_final,
    }
