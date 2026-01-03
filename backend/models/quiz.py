"""
クイズデータのPydanticモデル

サーバ側でsourceの真実性を保証するため、厳密にバリデーションする。
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class QuizSource(BaseModel):
    """
    クイズの参照元（source）モデル

    重要: このschemaは固定。余計なキーや重複キーは禁止。
    """
    title: str = Field(..., description="参照元のタイトル")
    url: str = Field(..., description="参照元のURL（サーバが選定したもの）")
    quote: str = Field(default="", description="参照元からの引用（サーバが取得した本文に含まれること）")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """URLが空または「参照URLを提示できません」の場合を許可"""
        if not v:
            raise ValueError("source.url must not be empty")
        return v

    @field_validator('quote')
    @classmethod
    def validate_quote(cls, v: str) -> str:
        """quoteは空文字列を許可（カテゴリモード時）"""
        return v

    class Config:
        # 余計なフィールドを禁止
        extra = "forbid"


class QuizData(BaseModel):
    """
    単一のクイズデータモデル

    フロントエンドとの互換性のため、既存のキー名を維持：
    - "Alternative Solutions/Correctness Judgment Criteria" （スラッシュ含む）
    """
    question: str = Field(..., description="問題文")
    answer: str = Field(..., description="正解")

    # 既存フロントとの互換性のため、スラッシュ含みのキー名を維持
    # （本来は alternative_solutions などsnake_caseが望ましい）
    alternative_solutions_or_criteria: str = Field(
        ...,
        alias="Alternative Solutions/Correctness Judgment Criteria",
        description="別解/正誤判定基準"
    )

    explanation: str = Field(..., description="解説")
    source: QuizSource = Field(..., description="参照元")

    class Config:
        # aliasを使うための設定
        populate_by_name = True
        # 余計なフィールドを禁止
        extra = "forbid"


class QuizListResponse(BaseModel):
    """複数問のクイズを返すレスポンス"""
    questions: List[QuizData] = Field(..., description="クイズのリスト")

    class Config:
        extra = "forbid"
