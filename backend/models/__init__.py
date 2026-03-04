"""Backward-compatible model exports."""

from app.models import QuizData, QuizListResponse, QuizSource, ResolvedConfigData

__all__ = [
    "QuizSource",
    "QuizData",
    "ResolvedConfigData",
    "QuizListResponse",
]
