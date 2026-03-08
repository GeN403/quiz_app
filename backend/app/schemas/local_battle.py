"""
ローカル対戦用 Pydantic スキーマ
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BattleChoice(BaseModel):
    choice_id: str
    text: str


class BattleQuestion(BaseModel):
    question_id: str
    source_saved_quiz_id: str
    prompt: str
    choices: list[BattleChoice]
    correct_choice_id: str


class BattleReadyResponse(BaseModel):
    set_id: str
    set_name: str
    total_item_count: int
    deleted_excluded_count: int
    active_item_count: int
    non_multiple_choice_excluded_count: int
    eligible_question_count: int
    startable: bool
    reason_code: Literal["NO_ELIGIBLE_MULTIPLE_CHOICE"] | None
    questions: list[BattleQuestion]
