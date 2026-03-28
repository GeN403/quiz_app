"""
/judge-answer エンドポイント
"""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.gemini_client import call_llm_with_retry

logger = logging.getLogger(__name__)


class JudgeAnswerRequest(BaseModel):
    question: str
    correct_answer: str
    user_answer: str


class JudgeAnswerResponse(BaseModel):
    is_correct: bool


def create_judge_answer_router(model) -> APIRouter:
    router = APIRouter()

    @router.post("/judge-answer", response_model=JudgeAnswerResponse, tags=["quiz"])
    async def judge_answer(request: JudgeAnswerRequest):
        prompt = f"""あなたはクイズの採点者です。以下のクイズについて、ユーザーの回答が正解かどうかを判定してください。

問題: {request.question}
正解: {request.correct_answer}
ユーザーの回答: {request.user_answer}

判定基準:
- 表記の揺れ（ひらがな・カタカナ・漢字の違い）は正解とする
- 同義語・略称・別名も正解とする
- 意味・内容が正解と同じであれば正解とする
- 明らかに異なる内容は不正解とする

以下のJSON形式のみで回答してください（説明不要）:
{{"is_correct": true}}
または
{{"is_correct": false}}"""

        raw = call_llm_with_retry(model, prompt, max_retries=1)

        cleaned = raw.strip()
        if "```json" in cleaned:
            match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
        elif cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3].strip()

        try:
            parsed = json.loads(cleaned)
            is_correct = bool(parsed.get("is_correct", False))
            return JudgeAnswerResponse(is_correct=is_correct)
        except Exception as e:
            logger.warning("[JUDGE] Failed to parse response: %s, raw: %.100s", e, raw)
            raise HTTPException(status_code=502, detail="JUDGE_PARSE_ERROR")

    return router
