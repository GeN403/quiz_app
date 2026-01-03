"""
リクエストモデル
"""

from pydantic import BaseModel
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
