"""
/resolve-source エンドポイント
"""

from fastapi import APIRouter, HTTPException
from app.schemas.requests import ResolveSourceRequest
from app.schemas.responses import ResolveSourceResponse
from app.core.domain_validator import validate_url_domain
from app.services.source_resolver import SourceResolver


router = APIRouter()


@router.post("/resolve-source", response_model=ResolveSourceResponse)
async def resolve_source(request: ResolveSourceRequest):
    """
    URLから本文を取得し、quote候補を生成する

    フロー:
    1. URLのドメイン検証
    2. HTMLをフェッチして本文抽出
    3. quote候補を生成（100-500文字の段落）
    4. title, url, text_excerpt, quotes を返す

    Args:
        request: { url: string }

    Returns:
        {
            url: string,
            title: string,
            text_excerpt: string,  # 本文先頭3000文字
            quotes: string[]       # quote候補リスト
        }

    Raises:
        400: URLドメインが許可されていない
        502: URLの取得・パース失敗
    """
    print(f"\n{'='*60}")
    print(f"[RESOLVE-SOURCE] Requesting URL: {request.url}")
    print(f"{'='*60}\n")

    # URLドメイン検証
    validate_url_domain(request.url)

    try:
        # SourceResolverでURL解決
        resolver = SourceResolver(request.url, timeout=10)
        resolved = resolver.fetch_and_parse()

        # レスポンス生成
        response = ResolveSourceResponse(
            url=resolved["url"],
            title=resolved["title"],
            text_excerpt=resolved["text"][:3000],  # 先頭3000文字
            quotes=resolved["quotes"]
        )

        print(f"[RESOLVE-SOURCE] Success: {len(response.quotes)} quotes generated")
        print(f"{'='*60}\n")

        return response

    except HTTPException:
        # HTTPExceptionはそのまま再スロー
        raise
    except Exception as e:
        error_str = str(e)
        print(f"[RESOLVE-SOURCE ERROR] {error_str[:200]}")
        raise HTTPException(
            status_code=502,
            detail=f"SOURCE_RESOLVE_ERROR: URL解決中にエラーが発生しました: {error_str}"
        )
