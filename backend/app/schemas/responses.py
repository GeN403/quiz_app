"""
レスポンスモデル
"""

from pydantic import BaseModel
from typing import List


class ResolveSourceResponse(BaseModel):
    """URL本文取得レスポンス"""
    url: str
    title: str
    text_excerpt: str  # 本文抜粋（先頭3000文字程度）
    quotes: List[str]  # quote候補リスト
