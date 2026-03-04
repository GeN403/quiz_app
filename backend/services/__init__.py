"""Backward-compatible service exports."""

import warnings

from app.services import SourceResolver

warnings.warn(
    "backend.services is deprecated; import from app.services instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SourceResolver"]
