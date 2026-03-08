import { NextRequest, NextResponse } from 'next/server';

const backendUrl = () =>
  process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const res = await fetch(`${backendUrl()}/quiz-sets/${id}/battle-ready`, {
      cache: 'no-store',
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error(`Proxy error (GET /quiz-sets/${id}/battle-ready):`, error);
    return NextResponse.json(
      { error: 'Failed to proxy request to backend' },
      { status: 502 }
    );
  }
}
