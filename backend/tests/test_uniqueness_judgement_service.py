"""
UniquenessJudgementService / ReasonTemplateFormatter 縺ｮ繝ｦ繝九ャ繝医ユ繧ｹ繝・

Tasks: 3.1, 3.2, 3.3
"""

from app.agent.state import DisambiguationParametersModel


def _params(**kwargs):
    base = DisambiguationParametersModel(
        major_count_threshold=3,
        minor_count_threshold=1,
        score_threshold=0.70,
        max_attempts=3,
        no_change_stop_threshold=2,
        max_retrieval_retries=0,
    )
    if not kwargs:
        return base
    return base.model_copy(update=kwargs)


def _candidate(label: str, category: str, similarity: float):
    return {
        "competing_id": f"id-{label}",
        "source": "wikipedia",
        "original_label": label,
        "normalized_label": label.lower(),
        "category": category,
        "similarity": similarity,
        "score": 0.0,
        "selected": False,
    }


class TestUniquenessJudgementService:
    def test_score_and_selected_are_assigned(self):
        from app.agent.uniqueness_judgement import UniquenessJudgementService

        service = UniquenessJudgementService()
        candidates = [
            _candidate("A", "exact", 0.90),
            _candidate("B", "related", 0.40),
        ]

        result = service.judge(candidates=candidates, evidence_status="ok", params=_params())

        assert result["effective_competing_count"] == 1
        assert candidates[0]["score"] >= 0.70
        assert candidates[0]["selected"] is True
        assert candidates[1]["selected"] is False

    def test_major_threshold_returns_fail_major(self):
        from app.agent.uniqueness_judgement import UniquenessJudgementService

        service = UniquenessJudgementService()
        candidates = [
            _candidate("A", "exact", 0.90),
            _candidate("B", "synonym", 0.90),
            _candidate("C", "hyper_hypo", 1.00),
        ]
        result = service.judge(candidates, "ok", _params())
        assert result["verdict"] == "fail_major"

    def test_minor_threshold_returns_fail_minor(self):
        from app.agent.uniqueness_judgement import UniquenessJudgementService

        service = UniquenessJudgementService()
        candidates = [_candidate("A", "synonym", 0.90)]
        result = service.judge(candidates, "ok", _params(major_count_threshold=5))
        assert result["verdict"] == "fail_minor"

    def test_ok_and_under_threshold_returns_pass(self):
        from app.agent.uniqueness_judgement import UniquenessJudgementService

        service = UniquenessJudgementService()
        candidates = [_candidate("A", "related", 0.20)]
        result = service.judge(candidates, "ok", _params(minor_count_threshold=1))
        assert result["verdict"] == "pass"

    def test_partial_or_failed_returns_unknown(self):
        from app.agent.uniqueness_judgement import UniquenessJudgementService

        service = UniquenessJudgementService()
        candidates = [_candidate("A", "exact", 0.99)]
        partial = service.judge(candidates, "partial", _params())
        failed = service.judge(candidates, "failed", _params())
        assert partial["verdict"] == "unknown"
        assert failed["verdict"] == "unknown"


class TestReasonTemplateFormatter:
    def test_reason_contains_category_and_count_and_threshold(self):
        from app.agent.uniqueness_judgement import ReasonTemplateFormatter

        formatter = ReasonTemplateFormatter()
        reason = formatter.format(
            verdict="fail_minor",
            top_competitor=_candidate("Python", "exact", 0.90),
            effective_competing_count=2,
            params=_params(),
        )
        assert "同名競合" in reason
        assert "2件" in reason
        assert "minor_count_threshold=1" in reason

