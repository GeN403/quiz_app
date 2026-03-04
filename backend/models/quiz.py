"""Backward-compatible quiz model exports."""

from app.models.quiz import QuizData, QuizListResponse, QuizSource, ResolvedConfigData

__all__ = [
    "QuizSource",
    "QuizData",
    "ResolvedConfigData",
    "QuizListResponse",
]
