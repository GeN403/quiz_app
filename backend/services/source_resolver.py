"""Backward-compatible SourceResolver export."""

import warnings

from app.services.source_resolver import SourceResolver

warnings.warn(
    "backend.services.source_resolver is deprecated; import from app.services.source_resolver instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SourceResolver"]
