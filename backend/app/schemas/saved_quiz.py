"""
保存済みクイズ関連 Pydantic スキーマ
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, model_validator


class GenerationInputParams(BaseModel):
    """クイズ生成時の入力パラメータ（現行 generate API の入力項目に対応）"""

    mode: Literal["category", "url", "keyword"]
    category: str
    source_url: str
    selected_quote: str
    question_count: int
    difficulty: Optional[str] = None
    length: Optional[str] = None
    genre: Optional[str] = None
    keyword: Optional[str] = None


class SaveQuizRequest(BaseModel):
    """クイズ保存リクエスト。generation_result_id は answer_package.package_id から導出する。"""

    input_params: GenerationInputParams
    answer_package: dict[str, Any]

    @model_validator(mode="after")
    def validate_answer_package_fields(self) -> SaveQuizRequest:
        ap = self.answer_package
        package_id = ap.get("package_id")
        if not package_id or not isinstance(package_id, str):
            raise ValueError("answer_package.package_id は空でない文字列である必要があります")
        if "question" not in ap:
            raise ValueError("answer_package に question フィールドが必要です")
        if "answer" not in ap:
            raise ValueError("answer_package に answer フィールドが必要です")
        return self

    @property
    def generation_result_id(self) -> str:
        """answer_package.package_id と同一値を返す。"""
        return self.answer_package["package_id"]


class SavedQuizResponse(BaseModel):
    """保存成功レスポンス"""

    id: str
    saved_at: str


class SavedQuizListItem(BaseModel):
    """一覧エントリ"""

    id: str
    generation_result_id: str
    saved_at: str
    topic: str
    question_count: int
    question: str = ""
    answer: str = ""


class SavedQuizDetail(BaseModel):
    """詳細レスポンス"""

    id: str
    generation_result_id: str
    saved_at: str
    input_params: GenerationInputParams
    answer_package: dict[str, Any]
