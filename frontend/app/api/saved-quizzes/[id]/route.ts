import { NextRequest, NextResponse } from 'next/server';

const backendUrl = () =>
  process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';

/**
 * GET /api/saved-quizzes/[id]
 * 保存済みクイズの詳細をバックエンドから取得して返す
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const res = await fetch(`${backendUrl()}/saved-quizzes/${id}`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error(`Proxy error (GET /saved-quizzes/${id}):`, error);
    return NextResponse.json(
      { error: 'Failed to proxy request to backend' },
      { status: 502 }
    );
  }
}

/**
 * DELETE /api/saved-quizzes/[id]
 * 保存済みクイズを削除する
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const res = await fetch(`${backendUrl()}/saved-quizzes/${id}`, {
      method: 'DELETE',
    });
    if (res.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error(`Proxy error (DELETE /saved-quizzes/${id}):`, error);
    return NextResponse.json(
      { error: 'Failed to proxy request to backend' },
      { status: 502 }
    );
  }
}
