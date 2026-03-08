"""
クイズセット関連 Pydantic スキーマ
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator, model_validator


class CreateQuizSetRequest(BaseModel):
    name: str
    saved_quiz_ids: list[str]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name は必須です")
        if len(stripped) > 100:
            raise ValueError("name は100文字以内である必要があります")
        return stripped

    @field_validator("saved_quiz_ids")
    @classmethod
    def validate_saved_quiz_ids_not_empty(cls, value: list[str]) -> list[str]:
        if len(value) == 0:
            raise ValueError("saved_quiz_ids は1件以上必要です")
        return value

    @model_validator(mode="after")
    def validate_saved_quiz_ids_unique(self) -> "CreateQuizSetRequest":
        if len(self.saved_quiz_ids) != len(set(self.saved_quiz_ids)):
            raise ValueError("saved_quiz_ids に重複があります")
        return self


class QuizSetResponse(BaseModel):
    id: str
    created_at: str


class QuizSetListItem(BaseModel):
    id: str
    name: str
    created_at: str
    quiz_count: int


class QuizSetDetailItem(BaseModel):
    saved_quiz_id: str
    topic: str | None
    saved_at: str | None
    question_count: int | None
    is_deleted: bool


class QuizSetDetail(BaseModel):
    id: str
    name: str
    created_at: str
    items: list[QuizSetDetailItem]
