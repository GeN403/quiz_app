"""
SavedQuizRepository の単体テスト（Task 2.1 / 2.2 / 9.1 対応）

インメモリ SQLite を使用して各メソッドの動作を検証する。
"""

import json
import pytest
import aiosqlite

from app.db.database import init_db
from app.repository.saved_quiz import DuplicateGenerationResultError, SavedQuizRepository
from app.schemas.saved_quiz import GenerationInputParams, SaveQuizRequest

# ---------------------------------------------------------------------------
# テストデータ
# ---------------------------------------------------------------------------

VALID_INPUT_PARAMS = GenerationInputParams(
    mode="keyword",
    category="科学",
    source_url="",
    selected_quote="",
    question_count=5,
    keyword="宇宙",
)

VALID_ANSWER_PACKAGE = {
    "package_id": "pkg_abc123def456",
    "question": "宇宙に関する問題",
    "answer": "A",
}


def make_request(package_id: str = "pkg_abc123def456", **overrides) -> SaveQuizRequest:
    ap = {**VALID_ANSWER_PACKAGE, "package_id": package_id}
    ap.update(overrides)
    return SaveQuizRequest(
        input_params=VALID_INPUT_PARAMS,
        answer_package=ap,
    )


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
async def repo():
    """インメモリ SQLite を使った SavedQuizRepository インスタンス"""
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        yield SavedQuizRepository(db)


# ---------------------------------------------------------------------------
# Task 2.1 — save()
# ---------------------------------------------------------------------------


class TestSave:
    async def test_save_returns_id_and_saved_at(self, repo):
        req = make_request()
        result = await repo.save(req)
        assert result.id
        assert result.saved_at

    async def test_save_generates_uuid_id(self, repo):
        req = make_request()
        result = await repo.save(req)
        # UUID v4 形式 (32 hex chars + 4 dashes = 36 chars)
        assert len(result.id) == 36
        assert result.id.count("-") == 4

    async def test_save_saved_at_is_utc_iso8601(self, repo):
        req = make_request()
        result = await repo.save(req)
        # UTC ISO 8601: "2024-01-01T00:00:00+00:00" または "...Z"
        assert "T" in result.saved_at

    async def test_save_duplicate_generation_result_id_raises(self, repo):
        req1 = make_request("pkg_dup")
        req2 = make_request("pkg_dup")
        await repo.save(req1)
        with pytest.raises(DuplicateGenerationResultError):
            await repo.save(req2)

    async def test_save_topic_derived_from_keyword(self, repo):
        """keyword が存在する場合は keyword を topic に使用する"""
        params = GenerationInputParams(
            mode="keyword",
            category="科学",
            source_url="http://example.com",
            selected_quote="",
            question_count=3,
            keyword="宇宙",
        )
        req = SaveQuizRequest(input_params=params, answer_package=VALID_ANSWER_PACKAGE)
        await repo.save(req)
        rows = await repo.list_all()
        assert rows[0].topic == "宇宙"

    async def test_save_topic_falls_back_to_category(self, repo):
        """keyword がない場合は category を topic に使用する"""
        params = GenerationInputParams(
            mode="category",
            category="歴史",
            source_url="",
            selected_quote="",
            question_count=3,
        )
        req = SaveQuizRequest(
            input_params=params,
            answer_package={**VALID_ANSWER_PACKAGE, "package_id": "pkg_cat"},
        )
        await repo.save(req)
        rows = await repo.list_all()
        assert rows[0].topic == "歴史"

    async def test_save_topic_falls_back_to_source_url(self, repo):
        """keyword も category もない場合は source_url を topic に使用する"""
        params = GenerationInputParams(
            mode="url",
            category="",
            source_url="http://example.com/article",
            selected_quote="",
            question_count=3,
        )
        req = SaveQuizRequest(
            input_params=params,
            answer_package={**VALID_ANSWER_PACKAGE, "package_id": "pkg_url"},
        )
        await repo.save(req)
        rows = await repo.list_all()
        assert rows[0].topic == "http://example.com/article"

    async def test_save_topic_falls_back_to_untitled(self, repo):
        """keyword も category も source_url もない場合は '無題' を使用する"""
        params = GenerationInputParams(
            mode="category",
            category="",
            source_url="",
            selected_quote="",
            question_count=3,
        )
        req = SaveQuizRequest(
            input_params=params,
            answer_package={**VALID_ANSWER_PACKAGE, "package_id": "pkg_none"},
        )
        await repo.save(req)
        rows = await repo.list_all()
        assert rows[0].topic == "無題"


# ---------------------------------------------------------------------------
# Task 2.1 — get_by_id()
# ---------------------------------------------------------------------------


class TestGetById:
    async def test_get_by_id_returns_detail(self, repo):
        req = make_request()
        saved = await repo.save(req)
        detail = await repo.get_by_id(saved.id)
        assert detail is not None
        assert detail.id == saved.id
        assert detail.generation_result_id == "pkg_abc123def456"

    async def test_get_by_id_returns_none_for_missing(self, repo):
        result = await repo.get_by_id("nonexistent-id")
        assert result is None

    async def test_get_by_id_includes_input_params(self, repo):
        req = make_request()
        saved = await repo.save(req)
        detail = await repo.get_by_id(saved.id)
        assert detail.input_params.mode == "keyword"
        assert detail.input_params.keyword == "宇宙"

    async def test_get_by_id_includes_answer_package(self, repo):
        req = make_request()
        saved = await repo.save(req)
        detail = await repo.get_by_id(saved.id)
        assert detail.answer_package["package_id"] == "pkg_abc123def456"


# ---------------------------------------------------------------------------
# Task 2.1 — delete_by_id()
# ---------------------------------------------------------------------------


class TestDeleteById:
    async def test_delete_by_id_returns_true_on_success(self, repo):
        saved = await repo.save(make_request())
        result = await repo.delete_by_id(saved.id)
        assert result is True

    async def test_delete_by_id_returns_false_for_missing(self, repo):
        result = await repo.delete_by_id("nonexistent-id")
        assert result is False

    async def test_delete_by_id_removes_record(self, repo):
        saved = await repo.save(make_request())
        await repo.delete_by_id(saved.id)
        assert await repo.get_by_id(saved.id) is None


# ---------------------------------------------------------------------------
# Task 2.2 — list_all()
# ---------------------------------------------------------------------------


class TestListAll:
    async def test_list_all_returns_empty_when_no_records(self, repo):
        result = await repo.list_all()
        assert result == []

    async def test_list_all_returns_records_in_saved_at_desc_order(self, repo):
        await repo.save(make_request("pkg_first"))
        await repo.save(make_request("pkg_second"))
        rows = await repo.list_all()
        assert len(rows) == 2
        # saved_at 降順: 後に保存した方が先頭
        assert rows[0].generation_result_id == "pkg_second"
        assert rows[1].generation_result_id == "pkg_first"

    async def test_list_all_skips_corrupt_records_and_logs(self, repo, caplog):
        """スキーマ不正レコードをスキップし、他のレコードは返す"""
        import logging

        # 正常レコードを 1 件保存
        good = await repo.save(make_request("pkg_good"))

        # 不正レコードを直接 DB に挿入（input_params が invalid JSON）
        await repo._db.execute(
            """
            INSERT INTO saved_quizzes
            (id, generation_result_id, saved_at, topic, question_count, input_params, answer_package)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("bad-id", "pkg_bad", "2024-01-01T00:00:00+00:00", "不正", 1, "NOT_JSON", "{}"),
        )
        await repo._db.commit()

        with caplog.at_level(logging.WARNING):
            rows = await repo.list_all()

        # 正常レコードのみ返る
        assert len(rows) == 1
        assert rows[0].id == good.id

        # 警告ログが出ている
        assert any("bad-id" in r.message for r in caplog.records)
