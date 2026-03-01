"""
/suggest-source endpoint.

ジャンルに紐づく URL 候補を返す。
topic が与えられた場合は URL 語彙との一致度で並べ替える。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class SuggestSourceResponse(BaseModel):
    genre: str
    urls: List[str]


def load_genre_sources() -> dict[str, list[str]]:
    json_path = Path(__file__).parent.parent.parent / "data" / "genre_sources.json"
    try:
        if not json_path.exists():
            raise HTTPException(status_code=500, detail="GENRE_SOURCES_NOT_FOUND")
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="GENRE_SOURCES_PARSE_ERROR") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="GENRE_SOURCES_LOAD_ERROR") from exc


def _extract_url_term(url: str) -> str:
    """
    URL 末尾から比較用語彙を抽出する。
    例: https://kotobank.jp/word/%E6%98%8E%E6%B2%BB%E7%B6%AD%E6%96%B0-142305 -> 明治維新
    """
    try:
        parsed = urlparse(url)
        segment = parsed.path.rstrip("/").split("/")[-1]
        decoded = unquote(segment)
        if "-" in decoded:
            return decoded.rsplit("-", 1)[0]
        return decoded
    except Exception:
        return url


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _topic_match_score(topic: str, term: str) -> int:
    norm_topic = _normalize_text(topic)
    norm_term = _normalize_text(term)
    if not norm_topic or not norm_term:
        return 0
    if norm_topic == norm_term:
        return 100
    if norm_topic in norm_term or norm_term in norm_topic:
        return 50
    score = 0
    tokens = [t for t in re.split(r"[、。,，．・\s]+", topic) if len(t.strip()) >= 2]
    for token in tokens:
        if _normalize_text(token) in norm_term:
            score += 10
    return score


def _rank_urls_by_topic(urls: list[str], topic: str | None) -> list[str]:
    if not topic or not topic.strip():
        return urls

    scored: list[tuple[int, int, str]] = []
    for idx, url in enumerate(urls):
        term = _extract_url_term(url)
        score = _topic_match_score(topic, term)
        scored.append((score, idx, url))

    # 一致候補が無い場合は既存順を維持
    if all(score == 0 for score, _, _ in scored):
        return urls

    ranked = sorted(scored, key=lambda row: (-row[0], row[1]))
    return [url for _, _, url in ranked]


@router.get("/suggest-source", response_model=SuggestSourceResponse)
async def suggest_source(
    genre: str = Query(..., min_length=1, description="ジャンル名"),
    k: int = Query(3, ge=1, le=10, description="返却件数"),
    topic: str | None = Query(None, min_length=1, description="トピック（任意）"),
):
    genre_sources = load_genre_sources()

    if genre not in genre_sources:
        raise HTTPException(status_code=404, detail="GENRE_NOT_FOUND")

    urls = genre_sources[genre]
    if not urls:
        raise HTTPException(status_code=404, detail="GENRE_EMPTY")

    ranked_urls = _rank_urls_by_topic(urls, topic)
    selected_urls = ranked_urls[:k]
    return SuggestSourceResponse(genre=genre, urls=selected_urls)

