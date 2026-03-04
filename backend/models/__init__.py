"""Backward-compatible model exports."""

import warnings

from app.models import QuizData, QuizListResponse, QuizSource, ResolvedConfigData

warnings.warn(
    "backend.models is deprecated; import from app.models instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "QuizSource",
    "QuizData",
    "ResolvedConfigData",
    "QuizListResponse",
]
