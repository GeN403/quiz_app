"""
CompetingConceptDiscoveryService のユニットテスト

Task 2.1
Requirements: 1.1, 1.3, 1.4, 1.6, 2.8, 2.9
"""

import pytest


def _search_params():
    return {
        "source_policy": "test-policy",
        "max_candidates": 10,
        "similarity_metric": "cosine",
        "score_threshold": 0.7,
        "normalization_rule": "none",
        "selection_rule": "top-k",
    }


class TestCompetingConceptDiscoveryService:
    def test_all_sources_succeeded_sets_evidence_status_ok(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            assert concept_text == "Python"
            return [{"label": f"{source}-candidate"}]

        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="Python",
            sources=["wikipedia", "search"],
            max_candidates=10,
            search_params=_search_params(),
        )

        assert result["evidence_status"] == "ok"
        assert result["sources_succeeded"] == ["wikipedia", "search"]
        assert result["sources_failed"] == []
        assert len(result["candidates"]) == 2

    def test_zero_candidates_with_success_is_ok_not_failed(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            return []

        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="NoHit",
            sources=["wikipedia"],
            max_candidates=10,
            search_params=_search_params(),
        )

        assert result["evidence_status"] == "ok"
        assert result["sources_succeeded"] == ["wikipedia"]
        assert result["candidates"] == []

    def test_partial_when_some_sources_failed(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            if source == "search":
                raise RuntimeError("timeout")
            return [{"label": "candidate-from-wiki"}]

        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="Python",
            sources=["wikipedia", "search"],
            max_candidates=10,
            search_params=_search_params(),
        )

        assert result["evidence_status"] == "partial"
        assert result["sources_succeeded"] == ["wikipedia"]
        assert result["sources_failed"] == ["search"]
        assert len(result["candidates"]) == 1

    def test_failed_when_all_sources_failed(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            raise RuntimeError("down")

        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="Python",
            sources=["wikipedia", "search"],
            max_candidates=10,
            search_params=_search_params(),
        )

        assert result["evidence_status"] == "failed"
        assert result["sources_succeeded"] == []
        assert result["sources_failed"] == ["wikipedia", "search"]
        assert result["candidates"] == []

    def test_empty_sources_is_failed(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            return [{"label": "x"}]

        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="Python",
            sources=[],
            max_candidates=10,
            search_params=_search_params(),
        )

        assert result["evidence_status"] == "failed"
        assert result["sources_attempted"] == []
        assert result["candidates"] == []

    def test_search_params_are_recorded_as_is(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            return []

        params = _search_params()
        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="Python",
            sources=["wikipedia"],
            max_candidates=10,
            search_params=params,
        )

        assert result["search_params"] == params

    def test_snapshot_id_is_stable_for_same_input(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            return []

        service = CompetingConceptDiscoveryService(fetcher)
        kwargs = {
            "concept_text": "Python",
            "sources": ["wikipedia"],
            "max_candidates": 10,
            "search_params": _search_params(),
        }
        result1 = service.discover(**kwargs)
        result2 = service.discover(**kwargs)

        assert result1["snapshot_id"] == result2["snapshot_id"]

    def test_competing_id_uses_snapshot_and_normalized_label(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            return [{"label": "  PYTHON  "}]

        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="Python",
            sources=["wikipedia"],
            max_candidates=10,
            search_params=_search_params(),
        )

        candidate = result["candidates"][0]
        assert candidate["normalized_label"] == "python"
        assert result["snapshot_id"] in candidate["competing_id"]

    def test_normalized_label_deduplication(self):
        from app.agent.services.uniqueness_discovery import CompetingConceptDiscoveryService

        def fetcher(source, concept_text, max_candidates, search_params):
            return [{"label": "Python"}, {"label": " python "}, {"label": "PYTHON"}]

        service = CompetingConceptDiscoveryService(fetcher)
        result = service.discover(
            concept_text="Python",
            sources=["wikipedia"],
            max_candidates=10,
            search_params=_search_params(),
        )

        assert len(result["candidates"]) == 1
