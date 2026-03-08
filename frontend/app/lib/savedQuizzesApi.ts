/**
 * 保存済みクイズ API クライアント
 */

// ---------------------------------------------------------------------------
// TypeScript 型定義
// ---------------------------------------------------------------------------

export interface GenerationInputParams {
  mode: 'category' | 'url' | 'keyword';
  category: string;
  source_url: string;
  selected_quote: string;
  question_count: number;
  difficulty?: string;
  length?: string;
  genre?: string;
  keyword?: string;
}

export interface SavedQuizListItem {
  id: string;
  generation_result_id: string;
  saved_at: string;
  topic: string;
  question_count: number;
}

export interface SavedQuizDetail {
  id: string;
  generation_result_id: string;
  saved_at: string;
  input_params: GenerationInputParams;
  answer_package: Record<string, unknown>;
}

/** POST /api/saved-quizzes のリクエストボディ */
export interface SaveQuizRequest {
  input_params: GenerationInputParams;
  answer_package: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// カスタムエラー
// ---------------------------------------------------------------------------

export class DuplicateSaveError extends Error {
  constructor() {
    super('すでに保存済みです');
    this.name = 'DuplicateSaveError';
  }
}

export class NotFoundError extends Error {
  constructor(id: string) {
    super(`保存済みクイズが見つかりません: ${id}`);
    this.name = 'NotFoundError';
  }
}

// ---------------------------------------------------------------------------
// API 関数
// ---------------------------------------------------------------------------

/**
 * クイズを保存する
 * @throws {DuplicateSaveError} 同じ generation_result_id がすでに存在する場合
 */
export async function saveSavedQuiz(
  request: SaveQuizRequest
): Promise<{ id: string; saved_at: string }> {
  const res = await fetch('/api/saved-quizzes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (res.status === 409) {
    throw new DuplicateSaveError();
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * 保存済みクイズ一覧を取得する
 */
export async function listSavedQuizzes(): Promise<SavedQuizListItem[]> {
  const res = await fetch('/api/saved-quizzes');

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data: { items: SavedQuizListItem[] } = await res.json();
  return data.items;
}

/**
 * 保存済みクイズの詳細を取得する
 * @throws {NotFoundError} 指定 ID が存在しない場合
 */
export async function getSavedQuizDetail(id: string): Promise<SavedQuizDetail> {
  const res = await fetch(`/api/saved-quizzes/${id}`);

  if (res.status === 404) {
    throw new NotFoundError(id);
  }

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * 保存済みクイズを削除する
 */
export async function deleteSavedQuiz(id: string): Promise<void> {
  const res = await fetch(`/api/saved-quizzes/${id}`, { method: 'DELETE' });

  if (!res.ok && res.status !== 204) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}
