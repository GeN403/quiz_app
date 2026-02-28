"""
リクエストモデル
"""

from pydantic import BaseModel, StrictInt, field_validator
from typing import Optional, Literal


class ResolveSourceRequest(BaseModel):
    """URL本文取得リクエスト"""
    url: str


class QuizRequest(BaseModel):
    category: str
    source_type: Optional[Literal["category", "url"]] = "category"
    source_value: Optional[str] = None  # URL指定時に使用
    selected_quote: Optional[str] = None  # UIで選択されたquote（推奨）
    question_count: Optional[int] = 1  # 生成する問題数（デフォルト1）

    # 新フィールド（すべて任意）
    difficulty: Optional[str] = None  # easy / normal / hard
    length: Optional[str] = None      # short / medium / long
    genre: Optional[str] = None       # 自由記述ジャンル（50文字以内）
    topic: Optional[str] = None       # 自由記述トピック（100文字以内）
    resolve_seed: Optional[StrictInt] = None  # seed 指定時にランダム解決を有効化

    @field_validator("resolve_seed", mode="after")
    @classmethod
    def validate_resolve_seed(cls, v: Optional[int]) -> Optional[int]:
        """resolve_seed の 32-bit 符号付き整数範囲チェック（Req 5.5）"""
        INT32_MIN = -2_147_483_648
        INT32_MAX = 2_147_483_647
        if v is not None and not (INT32_MIN <= v <= INT32_MAX):
            raise ValueError("INVALID_SEED")
        return v

    @field_validator("difficulty", "length", "genre", "topic", mode="before")
    @classmethod
    def normalize_empty_to_none(cls, v):
        """空文字・空白のみの入力を None に正規化する（Req 2.6）"""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v):
        """difficulty の有効値チェック（Req 1.5）"""
        if v is not None and v not in ("easy", "normal", "hard"):
            raise ValueError("INVALID_DIFFICULTY")
        return v

    @field_validator("length")
    @classmethod
    def validate_length(cls, v):
        """length の有効値チェック（Req 1.6）"""
        if v is not None and v not in ("short", "medium", "long"):
            raise ValueError("INVALID_LENGTH")
        return v

    @field_validator("genre")
    @classmethod
    def validate_genre(cls, v):
        """genre の文字数チェック（Req 1.7）"""
        if v is not None and len(v) > 50:
            raise ValueError("GENRE_TOO_LONG")
        return v

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v):
        """topic の文字数チェック（Req 1.8）"""
        if v is not None and len(v) > 100:
            raise ValueError("TOPIC_TOO_LONG")
        return v
