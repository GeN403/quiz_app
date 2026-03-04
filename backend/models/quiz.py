"""Backward-compatible quiz model exports."""

import warnings

from app.models.quiz import QuizData, QuizListResponse, QuizSource, ResolvedConfigData

warnings.warn(
    "backend.models.quiz is deprecated; import from app.models.quiz instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "QuizSource",
    "QuizData",
    "ResolvedConfigData",
    "QuizListResponse",
]
