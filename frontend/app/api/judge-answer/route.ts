import { NextRequest, NextResponse } from 'next/server';

const backendUrl = () =>
  process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';

/**
 * POST /api/judge-answer
 * 回答の正誤判定リクエストをバックエンドに転送する
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${backendUrl()}/judge-answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Proxy error (POST /judge-answer):', error);
    return NextResponse.json(
      { error: 'Failed to proxy request to backend' },
      { status: 502 }
    );
  }
}
