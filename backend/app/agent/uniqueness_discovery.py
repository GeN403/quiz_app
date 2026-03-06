"""
競合概念探索の集約サービス。

Task 2.1:
- 探索ソース結果を統合
- evidence_status を ok / partial / failed で判定
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Callable

from app.agent.state import CompetingConcept, DiscoveryResult, SearchParams


SourceFetcher = Callable[[str, str, int, SearchParams], list[dict[str, Any]]]


class CompetingConceptDiscoveryService:
    def __init__(self, source_fetcher: SourceFetcher) -> None:
        self._source_fetcher = source_fetcher

    def discover(
        self,
        concept_text: str,
        sources: list[str],
        max_candidates: int,
        search_params: SearchParams,
    ) -> DiscoveryResult:
        sources_attempted: list[str] = []
        sources_succeeded: list[str] = []
        sources_failed: list[str] = []
        candidates: list[CompetingConcept] = []
        snapshot_id = self._build_snapshot_id(concept_text, sources, search_params)
        seen_normalized_labels: set[str] = set()

        for source in sources:
            sources_attempted.append(source)
            try:
                fetched = self._source_fetcher(
                    source,
                    concept_text,
                    max_candidates,
                    search_params,
                )
                sources_succeeded.append(source)
                for index, raw in enumerate(fetched):
                    label = str(raw.get("label", "")).strip()
                    if not label:
                        continue
                    normalized_label = label.lower()
                    if normalized_label in seen_normalized_labels:
                        continue
                    seen_normalized_labels.add(normalized_label)
                    candidates.append(
                        {
                            "competing_id": self._build_competing_id(
                                snapshot_id=snapshot_id,
                                source=source,
                                normalized_label=normalized_label,
                            ),
                            "source": source,
                            "original_label": label,
                            "normalized_label": normalized_label,
                            "category": "related",
                            "similarity": float(raw.get("similarity", 0.0)),
                            "score": float(raw.get("score", 0.0)),
                            "selected": False,
                        }
                    )
            except Exception:
                sources_failed.append(source)

        if not sources_attempted or len(sources_succeeded) == 0:
            evidence_status = "failed"
        elif len(sources_failed) > 0:
            evidence_status = "partial"
        else:
            evidence_status = "ok"

        return {
            "snapshot_id": snapshot_id,
            "evidence_status": evidence_status,
            "sources_attempted": sources_attempted,
            "sources_succeeded": sources_succeeded,
            "sources_failed": sources_failed,
            "search_params": search_params,
            "candidates": candidates,
        }

    @staticmethod
    def _build_snapshot_id(
        concept_text: str,
        sources: list[str],
        search_params: SearchParams,
    ) -> str:
        fingerprint = "|".join(
            [
                concept_text,
                ",".join(sources),
                search_params["source_policy"],
                str(search_params["max_candidates"]),
                search_params["similarity_metric"],
                str(search_params["score_threshold"]),
                search_params["normalization_rule"],
                search_params["selection_rule"],
            ]
        )
        digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]
        return f"snap-{digest}"

    @staticmethod
    def _build_competing_id(snapshot_id: str, source: str, normalized_label: str) -> str:
        name = f"{source}|{normalized_label}"
        return f"{snapshot_id}-{uuid.uuid5(uuid.NAMESPACE_URL, name)}"
