"""
反復制御サービスのユニットテスト

Tasks: 5.1, 5.2
"""

from app.agent.state import DisambiguationParametersModel


def _params(**kwargs):
    base = DisambiguationParametersModel(
        major_count_threshold=16,
        minor_count_threshold=5,
        score_threshold=0.7,
        max_attempts=3,
        no_change_stop_threshold=2,
        max_retrieval_retries=1,
    )
    if not kwargs:
        return base
    return base.model_copy(update=kwargs)


class TestLoopControlService:
    def test_unknown_stops_immediately(self):
        from app.agent.services.loop_control import LoopControlService

        service = LoopControlService()
        decision = service.should_continue(
            verdict="unknown",
            attempts=1,
            no_change_count=0,
            retrieval_retry_count=0,
            params=_params(),
        )
        assert decision["continue_loop"] is False
        assert decision["termination_reason_code"] == "UNKNOWN"

    def test_max_attempts_stops(self):
        from app.agent.services.loop_control import LoopControlService

        service = LoopControlService()
        decision = service.should_continue(
            verdict="fail_minor",
            attempts=3,
            no_change_count=0,
            retrieval_retry_count=0,
            params=_params(max_attempts=3),
        )
        assert decision["continue_loop"] is False
        assert decision["termination_reason_code"] == "MAX_VERIFICATION_ATTEMPTS_REACHED"

    def test_no_change_limit_stops(self):
        from app.agent.services.loop_control import LoopControlService

        service = LoopControlService()
        decision = service.should_continue(
            verdict="fail_minor",
            attempts=1,
            no_change_count=2,
            retrieval_retry_count=0,
            params=_params(no_change_stop_threshold=2),
        )
        assert decision["continue_loop"] is False
        assert decision["termination_reason_code"] == "NO_CHANGE_LIMIT_REACHED"

    def test_retrieval_retry_exceeded_stops_with_unknown(self):
        from app.agent.services.loop_control import LoopControlService

        service = LoopControlService()
        decision = service.should_continue(
            verdict="fail_minor",
            attempts=1,
            no_change_count=0,
            retrieval_retry_count=2,
            params=_params(max_retrieval_retries=1),
        )
        assert decision["continue_loop"] is False
        assert decision["termination_reason_code"] == "RETRIEVAL_RETRY_EXCEEDED"

    def test_fail_minor_continues_when_within_limits(self):
        from app.agent.services.loop_control import LoopControlService

        service = LoopControlService()
        decision = service.should_continue(
            verdict="fail_minor",
            attempts=1,
            no_change_count=0,
            retrieval_retry_count=0,
            params=_params(),
        )
        assert decision["continue_loop"] is True
