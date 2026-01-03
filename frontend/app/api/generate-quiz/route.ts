import { NextRequest, NextResponse } from 'next/server';

/**
 * BFF (Backend For Frontend) プロキシAPI
 * ブラウザからの /api/generate-quiz リクエストを backend コンテナに転送
 *
 * ブラウザ -> Next.js (localhost:3000/api/generate-quiz)
 *          -> FastAPI (http://backend:8000/generate-quiz) ← コンテナ間通信
 */
export async function POST(request: NextRequest) {
  try {
    // リクエストボディを取得
    const body = await request.json();

    // バックエンドのURL (コンテナ内部用、NEXT_PUBLIC_ をつけない)
    const backendUrl = process.env.BACKEND_INTERNAL_URL || 'http://backend:8000';
    const targetUrl = `${backendUrl}/generate-quiz`;

    // バックエンドに転送（タイムアウト60秒：LLM呼び出しに時間がかかる場合がある）
    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60000),
    });

    // バックエンドからのレスポンスを取得
    const data = await backendResponse.json();

    // ステータスコードとレスポンスボディをそのまま返す
    return NextResponse.json(data, { status: backendResponse.status });

  } catch (error) {
    console.error('Proxy error:', error);

    // エラーの詳細を返す
    return NextResponse.json(
      {
        error: 'Failed to proxy request to backend',
        message: error instanceof Error ? error.message : 'Unknown error',
        hint: 'Check if backend container is running and accessible at http://backend:8000'
      },
      { status: 502 }
    );
  }
}
