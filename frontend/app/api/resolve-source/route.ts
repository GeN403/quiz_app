import { NextRequest, NextResponse } from 'next/server';

/**
 * URL本文取得プロキシAPI
 * ブラウザ -> Next.js (/api/resolve-source)
 *          -> FastAPI (http://backend:8000/resolve-source)
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // バックエンドのURL
    const backendUrl = process.env.BACKEND_INTERNAL_URL || 'http://backend:8000';
    const targetUrl = `${backendUrl}/resolve-source`;

    console.log('[PROXY] /api/resolve-source called');
    console.log('[PROXY] Backend URL:', targetUrl);
    console.log('[PROXY] Request body:', body);

    // バックエンドに転送
    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      // タイムアウト15秒（HTMLフェッチに時間がかかる場合がある）
      signal: AbortSignal.timeout(15000),
    });

    console.log('[PROXY] Backend response status:', backendResponse.status);

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      console.error('[PROXY] Backend error:', data);
    } else {
      console.log('[PROXY] Backend success:', {
        url: data.url,
        title: data.title,
        quotesCount: data.quotes?.length || 0
      });
    }

    return NextResponse.json(data, { status: backendResponse.status });

  } catch (error) {
    console.error('[PROXY] Error:', error);

    if (error instanceof Error && error.name === 'TimeoutError') {
      return NextResponse.json(
        {
          error: 'Request timeout',
          message: 'URLの取得がタイムアウトしました。サイトの応答が遅い可能性があります。'
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
