import { NextRequest, NextResponse } from 'next/server';

const backendUrl = () =>
  process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';

/**
 * POST /api/saved-quizzes
 * クイズ保存リクエストをバックエンドに転送する
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${backendUrl()}/saved-quizzes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Proxy error (POST /saved-quizzes):', error);
    return NextResponse.json(
      { error: 'Failed to proxy request to backend' },
      { status: 502 }
    );
  }
}

/**
 * GET /api/saved-quizzes
 * 保存済みクイズ一覧をバックエンドから取得して返す
 */
export async function GET() {
  try {
    const res = await fetch(`${backendUrl()}/saved-quizzes`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Proxy error (GET /saved-quizzes):', error);
    return NextResponse.json(
      { error: 'Failed to proxy request to backend' },
      { status: 502 }
    );
  }
}
