from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import suggest_source


def _make_client():
    app = FastAPI()
    app.include_router(suggest_source.router)
    return TestClient(app)


def test_suggest_source_prefers_topic_matching_url(monkeypatch):
    monkeypatch.setattr(
        suggest_source,
        "load_genre_sources",
        lambda: {
            "歴史": [
                "https://kotobank.jp/word/江戸時代-38072",
                "https://kotobank.jp/word/明治維新-142305",
                "https://kotobank.jp/word/戦国時代-87001",
            ]
        },
    )
    client = _make_client()

    response = client.get("/suggest-source", params={"genre": "歴史", "k": 1, "topic": "明治"})

    assert response.status_code == 200
    data = response.json()
    assert data["urls"][0].endswith("明治維新-142305")


def test_suggest_source_keeps_original_order_when_no_topic_match(monkeypatch):
    monkeypatch.setattr(
        suggest_source,
        "load_genre_sources",
        lambda: {
            "歴史": [
                "https://kotobank.jp/word/江戸時代-38072",
                "https://kotobank.jp/word/明治維新-142305",
            ]
        },
    )
    client = _make_client()

    response = client.get("/suggest-source", params={"genre": "歴史", "k": 2, "topic": "恐竜"})

    assert response.status_code == 200
    data = response.json()
    assert data["urls"][0].endswith("江戸時代-38072")
    assert data["urls"][1].endswith("明治維新-142305")

