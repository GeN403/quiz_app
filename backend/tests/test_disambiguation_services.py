"""
fail_minor / fail_major 解消サービスのユニットテスト

Tasks: 4.1, 4.2
"""


def _candidate(label: str, score: float):
    return {
        "competing_id": f"id-{label}",
        "source": "wikipedia",
        "original_label": label,
        "normalized_label": label.lower(),
        "category": "related",
        "similarity": score,
        "score": score,
        "selected": True,
    }


class TestMinorDisambiguationService:
    def test_returns_preface_mode_with_edit_ops(self):
        from app.agent.services.disambiguation import MinorDisambiguationService

        service = MinorDisambiguationService()
        proposal = service.propose("Python", "同名競合があるため前置き推奨")

        assert proposal["mode"] in {"qualifier", "preface"}
        assert proposal["before_concept"] == "Python"
        assert proposal["after_concept"] != "Python"
        assert len(proposal["edit_ops"]) >= 1

    def test_qualifier_mode_appends_suffix(self):
        from app.agent.services.disambiguation import MinorDisambiguationService

        service = MinorDisambiguationService()
        proposal = service.propose("Python", "限定語を追加")

        if proposal["mode"] == "qualifier":
            assert proposal["after_concept"].startswith("Python")


class TestMajorDisambiguationService:
    def test_major_proposal_returns_ranked_alternatives(self):
        from app.agent.services.disambiguation import MajorDisambiguationService

        service = MajorDisambiguationService()
        proposal = service.propose("Python", [_candidate("Ruby", 0.8), _candidate("Go", 0.9)])

        assert len(proposal["alternatives"]) >= 1
        assert proposal["alternatives"][0]["rank"] == 1
        assert proposal["selected_alternative"]["rank"] == 1
        assert proposal["replaced_concept"] == "Python"
