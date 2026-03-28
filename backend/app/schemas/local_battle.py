"""
ローカル対戦用 Pydantic スキーマ
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BattleQuestion(BaseModel):
    question_id: str
    source_saved_quiz_id: str
    prompt: str
    correct_answer_text: str


class BattleReadyResponse(BaseModel):
    set_id: str
    set_name: str
    total_item_count: int
    deleted_excluded_count: int
    active_item_count: int
    non_multiple_choice_excluded_count: int
    eligible_question_count: int
    startable: bool
    reason_code: Literal["NO_ELIGIBLE_QUESTIONS"] | None
    questions: list[BattleQuestion]
