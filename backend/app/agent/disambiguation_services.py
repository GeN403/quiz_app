"""Backward-compatible re-export for disambiguation services."""

from app.agent.services.disambiguation import (
    MajorDisambiguationService,
    MinorDisambiguationService,
)

__all__ = ["MajorDisambiguationService", "MinorDisambiguationService"]
