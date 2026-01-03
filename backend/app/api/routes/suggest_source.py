"""
/suggest-source エンドポイント - ジャンルからURL候補を提案
"""

import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter()


class SuggestSourceResponse(BaseModel):
    """URL候補提案レスポンス"""
    genre: str
    urls: List[str]


def load_genre_sources() -> dict:
    """
    genre_sources.json を読み込む

    Returns:
        dict: ジャンル -> URLリストのマッピング

    Raises:
        HTTPException: ファイルが見つからない、または読み込みエラー
    """
    json_path = Path(__file__).parent.parent.parent / "data" / "genre_sources.json"

    try:
        if not json_path.exists():
            print(f"[ERROR] genre_sources.json not found at {json_path}")
            raise HTTPException(
                status_code=500,
                detail=f"GENRE_SOURCES_NOT_FOUND: URLカタログファイルが見つかりません"
            )

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"[OK] Loaded genre_sources.json with {len(data)} genres")
            return data

    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse genre_sources.json: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"GENRE_SOURCES_PARSE_ERROR: URLカタログファイルの解析に失敗しました"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to load genre_sources.json: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"GENRE_SOURCES_LOAD_ERROR: URLカタログファイルの読み込みに失敗しました: {str(e)}"
        )


@router.get("/suggest-source", response_model=SuggestSourceResponse)
async def suggest_source(
    genre: str = Query(..., min_length=1, description="ジャンル名"),
    k: int = Query(3, ge=1, le=10, description="取得するURL数（最大10件）")
):
    """
    指定されたジャンルからURL候補を提案する

    Args:
        genre: ジャンル名（例: "歴史", "文学"）
        k: 取得するURL数（デフォルト3、最大10）

    Returns:
        SuggestSourceResponse: ジャンルとURL候補リスト

    Raises:
        404: ジャンルが未登録、またはURLが空
        500: カタログファイルの読み込みエラー
    """
    print(f"\n[SUGGEST-SOURCE] genre={genre}, k={k}")

    # URLカタログを読み込む
    genre_sources = load_genre_sources()

    # ジャンルの存在チェック
    if genre not in genre_sources:
        available_genres = list(genre_sources.keys())
        print(f"[ERROR] Genre '{genre}' not found. Available: {available_genres}")
        raise HTTPException(
            status_code=404,
            detail=f"GENRE_NOT_FOUND: ジャンル '{genre}' は登録されていません。利用可能なジャンル: {', '.join(available_genres)}"
        )

    urls = genre_sources[genre]

    # URLリストが空の場合
    if not urls or len(urls) == 0:
        print(f"[ERROR] Genre '{genre}' has no URLs")
        raise HTTPException(
            status_code=404,
            detail=f"GENRE_EMPTY: ジャンル '{genre}' にはURLが登録されていません"
        )

    # 先頭k件を返す（シンプルな実装）
    selected_urls = urls[:k]

    print(f"[OK] Returning {len(selected_urls)} URLs for genre '{genre}'")

    return SuggestSourceResponse(
        genre=genre,
        urls=selected_urls
    )
