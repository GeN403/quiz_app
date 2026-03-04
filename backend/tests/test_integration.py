"""
Integration tests for /generate-quiz-agent and router regressions.

Tasks covered:
- Task 8: integration happy/error/regression behaviors
- Task 9: claim-verification loop behavior
"""

import inspect
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_QUIZ_JSON = json.dumps(
    {
        "question": "What is the capital of France?",
        "answer": "Paris",
        "Alternative Solutions/Correctness Judgment Criteria": "None",
        "explanation": "Paris is the capital city of France.",
        "source": {
            "title": "LLM Generated Title (overwritten by server)",
            "url": "https://llm-generated-url.com",
            "quote": "LLM generated quote",
        },
    }
)


def create_test_app(api_key="test-api-key"):
    from app.api.routes.generate_quiz_agent import create_generate_quiz_agent_router

    app = FastAPI()
    router = create_generate_quiz_agent_router(api_key)
    app.include_router(router)
    return app


@pytest.fixture
def mocked_client():
    with (
        patch("app.agent.nodes.fetch_source.SourceResolver") as mock_sr_class,
        patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI") as mock_llm_class,
    ):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = {
            "url": "https://example.com",
            "title": "Server Title",
            "text": "Sample text content for quiz generation",
            "quotes": ["Server quote"],
        }
        mock_resolver.verify_quote.return_value = True
        mock_sr_class.return_value = mock_resolver

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            # resolve_topic_input
            MagicMock(text="capital cities"),
            # generate_quiz
            MagicMock(content=VALID_QUIZ_JSON),
            # decompose_claims
            MagicMock(content=json.dumps([{"text": "Paris is the capital city of France."}])),
            # collect_evidence
            MagicMock(content=json.dumps({"quote": "Paris is the capital city of France."})),
            # verify_claims
            MagicMock(content=json.dumps({"verdict": "pass", "reason": "Grounded in evidence."})),
        ]
        mock_llm_class.return_value = mock_llm

        app = create_test_app()
        yield TestClient(app)


class TestHappyPath:
    def test_returns_http_200(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        assert response.status_code == 200

    def test_response_has_five_required_keys(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        data = response.json()
        assert "question" in data
        assert "answer" in data
        assert "Alternative Solutions/Correctness Judgment Criteria" in data
        assert "explanation" in data
        assert "source" in data

    def test_source_has_three_required_subkeys(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        source = response.json()["source"]
        assert "url" in source
        assert "title" in source
        assert "quote" in source

    def test_source_url_matches_server_confirmed_value(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        source = response.json()["source"]
        assert source["url"] == "https://example.com"

    def test_source_title_matches_server_confirmed_value(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        source = response.json()["source"]
        assert source["title"] == "Server Title"

    def test_response_is_single_object_not_array(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        assert isinstance(response.json(), dict)
        assert not isinstance(response.json(), list)

    def test_content_type_is_json(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        assert "application/json" in response.headers.get("content-type", "")

    def test_response_contains_verification_block(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        body = response.json()
        assert "verification" in body
        assert "attempts" in body["verification"]
        assert body["verification"]["verdict"] == "pass"


class TestErrorCases:
    def test_question_count_2_returns_400_invalid_question_count(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 2,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        assert response.status_code == 400
        assert response.json() == {"detail": "INVALID_QUESTION_COUNT"}

    def test_empty_source_value_returns_400_invalid_input(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "",
            },
        )
        assert response.status_code == 400
        assert response.json() == {"detail": "INVALID_INPUT"}

    def test_question_count_as_string_returns_400_not_422(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": "not-a-number",
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        assert response.status_code == 400
        assert response.status_code != 422
        assert response.json() == {"detail": "INVALID_INPUT"}

    def test_missing_required_field_returns_400(self, mocked_client):
        response = mocked_client.post(
            "/generate-quiz-agent",
            json={
                "question_count": 1,
            },
        )
        assert response.status_code == 400
        assert response.json() == {"detail": "INVALID_INPUT"}

    def test_business_uncertainty_returns_200_with_partial_status(self):
        with (
            patch("app.agent.nodes.fetch_source.SourceResolver") as mock_sr_class,
            patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI") as mock_llm_class,
        ):
            mock_resolver = MagicMock()
            mock_resolver.fetch_and_parse.return_value = {
                "url": "https://example.com",
                "title": "Server Title",
                "text": "Sample text content for quiz generation",
                "quotes": ["Server quote"],
            }
            mock_resolver.verify_quote.return_value = True
            mock_sr_class.return_value = mock_resolver

            quiz_without_policy = json.dumps(
                {
                    "question": "What is the capital of France?",
                    "answer": "Paris",
                    "Alternative Solutions/Correctness Judgment Criteria": "",
                    "explanation": "Paris is the capital city of France.",
                    "source": {
                        "title": "LLM Generated Title (overwritten by server)",
                        "url": "https://llm-generated-url.com",
                        "quote": "LLM generated quote",
                    },
                }
            )
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = [
                MagicMock(text="capital cities"),
                MagicMock(content=quiz_without_policy),
                MagicMock(content=json.dumps([{"text": "Paris is the capital city of France."}])),
                MagicMock(content=json.dumps({"quote": "Paris is the capital city of France."})),
                MagicMock(content=json.dumps({"verdict": "pass", "reason": "Grounded in evidence."})),
            ]
            mock_llm_class.return_value = mock_llm

            app = create_test_app()
            client = TestClient(app)

            response = client.post(
                "/generate-quiz-agent",
                json={
                    "category": "science",
                    "question_count": 1,
                    "source_type": "url",
                    "source_value": "https://example.com",
                },
            )
            assert response.status_code == 200
            assert response.json()["status"] == "partial"

    def test_missing_api_key_returns_500(self):
        app = create_test_app(api_key=None)
        no_key_client = TestClient(app)

        response = no_key_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "GEMINI_API_KEY_NOT_SET"}

    def test_empty_api_key_returns_500(self):
        app = create_test_app(api_key="")
        no_key_client = TestClient(app)

        response = no_key_client.post(
            "/generate-quiz-agent",
            json={
                "category": "science",
                "question_count": 1,
                "source_type": "url",
                "source_value": "https://example.com",
            },
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "GEMINI_API_KEY_NOT_SET"}


class TestHealthEndpoint:
    def test_health_returns_ok(self, mocked_client):
        response = mocked_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_without_api_key_still_returns_ok(self):
        app = create_test_app(api_key=None)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRegression:
    def test_create_api_router_signature_unchanged(self):
        from app.api.router import create_api_router

        sig = inspect.signature(create_api_router)
        params = list(sig.parameters.keys())
        assert "gemini_model" in params

    def test_both_routers_register_independent_routes(self):
        from app.api.router import create_agent_router, create_api_router

        mock_model = MagicMock()
        api_router = create_api_router(mock_model)

        with patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI"):
            agent_router = create_agent_router("test-key")

        app = FastAPI()
        app.include_router(api_router)
        app.include_router(agent_router)

        route_paths = [r.path for r in app.routes]
        assert "/generate-quiz" in route_paths
        assert "/generate-quiz-agent" in route_paths
        assert "/health" in route_paths

    def test_generate_quiz_endpoint_returns_non_404(self):
        from app.api.router import create_api_router

        mock_model = MagicMock()
        api_router = create_api_router(mock_model)

        app = FastAPI()
        app.include_router(api_router)
        client = TestClient(app)

        response = client.post("/generate-quiz", json={})
        assert response.status_code != 404

    def test_resolve_source_endpoint_still_accessible(self):
        from app.api.router import create_api_router

        mock_model = MagicMock()
        api_router = create_api_router(mock_model)

        app = FastAPI()
        app.include_router(api_router)

        route_paths = [r.path for r in app.routes]
        assert "/resolve-source" in route_paths

    def test_suggest_source_endpoint_still_accessible(self):
        from app.api.router import create_api_router

        mock_model = MagicMock()
        api_router = create_api_router(mock_model)

        app = FastAPI()
        app.include_router(api_router)

        route_paths = [r.path for r in app.routes]
        assert "/suggest-source" in route_paths


class TestVerificationLoop:
    def test_failed_verification_triggers_rewrite_and_recovers(self):
        with (
            patch("app.agent.nodes.fetch_source.SourceResolver") as mock_sr_class,
            patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI") as mock_llm_class,
        ):
            mock_resolver = MagicMock()
            mock_resolver.fetch_and_parse.return_value = {
                "url": "https://example.com",
                "title": "Server Title",
                "text": "Paris is the capital city of France.",
                "quotes": ["Paris is the capital city of France."],
            }
            mock_resolver.verify_quote.return_value = True
            mock_sr_class.return_value = mock_resolver

            llm = MagicMock()
            llm.invoke.side_effect = [
                # resolve_topic_input, generate_quiz
                MagicMock(text="capital cities"),
                MagicMock(content=VALID_QUIZ_JSON),
                # first pass: decompose, collect, verify(fail)
                MagicMock(content=json.dumps([{"text": "Paris is in Germany."}])),
                MagicMock(content=json.dumps({"quote": "Paris is the capital city of France."})),
                MagicMock(content=json.dumps({"verdict": "fail", "reason": "Contradicted"})),
                # rewrite
                MagicMock(content=VALID_QUIZ_JSON),
                # second pass: decompose, collect, verify(pass)
                MagicMock(content=json.dumps([{"text": "Paris is the capital city of France."}])),
                MagicMock(content=json.dumps({"quote": "Paris is the capital city of France."})),
                MagicMock(content=json.dumps({"verdict": "pass", "reason": "Correct"})),
            ]
            mock_llm_class.return_value = llm

            app = create_test_app()
            client = TestClient(app)

            response = client.post(
                "/generate-quiz-agent",
                json={
                    "category": "science",
                    "question_count": 1,
                    "source_type": "url",
                    "source_value": "https://example.com",
                },
            )

            assert response.status_code == 200
            body = response.json()
            assert "question" in body

    def test_exceeding_max_retries_returns_unknown_200(self):
        with (
            patch("app.agent.nodes.fetch_source.SourceResolver") as mock_sr_class,
            patch("app.agent.adapters.gemini_llm.ChatGoogleGenerativeAI") as mock_llm_class,
        ):
            mock_resolver = MagicMock()
            mock_resolver.fetch_and_parse.return_value = {
                "url": "https://example.com",
                "title": "Server Title",
                "text": "Paris is the capital city of France.",
                "quotes": ["Paris is the capital city of France."],
            }
            mock_resolver.verify_quote.return_value = True
            mock_sr_class.return_value = mock_resolver

            llm = MagicMock()
            side_effect = [
                MagicMock(text="capital cities"),
                MagicMock(content=VALID_QUIZ_JSON),
            ]
            # first 3 failures with rewrite
            for _ in range(3):
                side_effect.extend(
                    [
                        MagicMock(content=json.dumps([{"text": "Paris is in Germany."}])),
                        MagicMock(content=json.dumps({"quote": "Paris is the capital city of France."})),
                        MagicMock(content=json.dumps({"verdict": "fail", "reason": "Contradicted"})),
                        MagicMock(content=VALID_QUIZ_JSON),
                    ]
                )
            # 4th failure should stop without rewrite
            side_effect.extend(
                [
                    MagicMock(content=json.dumps([{"text": "Paris is in Germany."}])),
                    MagicMock(content=json.dumps({"quote": "Paris is the capital city of France."})),
                    MagicMock(content=json.dumps({"verdict": "fail", "reason": "Contradicted"})),
                ]
            )
            llm.invoke.side_effect = side_effect
            mock_llm_class.return_value = llm

            app = create_test_app()
            client = TestClient(app)

            response = client.post(
                "/generate-quiz-agent",
                json={
                    "category": "science",
                    "question_count": 1,
                    "source_type": "url",
                    "source_value": "https://example.com",
                },
            )

            assert response.status_code == 200
            body = response.json()
            assert body["verification"]["verdict"] == "unknown"
            assert body["verification"]["termination_reason"]["code"] in {
                "MAX_VERIFICATION_ATTEMPTS_REACHED",
                "NO_CHANGE_LIMIT_REACHED",
            }
