import { NextRequest, NextResponse } from 'next/server';

/**
 * URL候補提案プロキシAPI
 * ブラウザ -> Next.js (/api/suggest-source)
 *          -> FastAPI (http://backend:8000/suggest-source)
 */
export async function GET(request: NextRequest) {
  try {
    // クエリパラメータを取得
    const { searchParams } = new URL(request.url);
    const genre = searchParams.get('genre');
    const k = searchParams.get('k') || '3';

    if (!genre) {
      return NextResponse.json(
        { error: 'genre parameter is required' },
        { status: 400 }
      );
    }

    // バックエンドのURL
    const backendUrl = process.env.BACKEND_INTERNAL_URL || 'http://backend:8000';
    const targetUrl = `${backendUrl}/suggest-source?genre=${encodeURIComponent(genre)}&k=${k}`;

    console.log('[PROXY] /api/suggest-source called');
    console.log('[PROXY] Backend URL:', targetUrl);
    console.log('[PROXY] genre:', genre, 'k:', k);

    // バックエンドに転送（タイムアウト10秒）
    const backendResponse = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',  // キャッシュ無効化
      signal: AbortSignal.timeout(10000),
    });

    console.log('[PROXY] Backend response status:', backendResponse.status);

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      console.error('[PROXY] Backend error:', data);
    } else {
      console.log('[PROXY] Backend success:', {
        genre: data.genre,
        urlsCount: data.urls?.length || 0
      });
    }

    return NextResponse.json(data, { status: backendResponse.status });

  } catch (error) {
    console.error('[PROXY] Error:', error);

    if (error instanceof Error && error.name === 'TimeoutError') {
      return NextResponse.json(
        {
          error: 'Request timeout',
          message: 'URL候補の取得がタイムアウトしました'
        },
        { status: 504 }
      );
    }

    return NextResponse.json(
      {
        error: 'Failed to proxy request to backend',
        message: error instanceof Error ? error.message : 'Unknown error',
        hint: 'Check if backend container is running'
      },
      { status: 502 }
    );
  }
}
