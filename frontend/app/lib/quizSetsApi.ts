/**
 * クイズセット API クライアント
 */

export interface CreateQuizSetRequest {
  name: string;
  savedQuizIds: string[];
}

export interface QuizSetResponse {
  id: string;
  createdAt: string;
}

export interface QuizSetListItem {
  id: string;
  name: string;
  createdAt: string;
  quizCount: number;
}

export interface QuizSetDetailItem {
  savedQuizId: string;
  topic: string | null;
  savedAt: string | null;
  questionCount: number | null;
  isDeleted: boolean;
}

export interface QuizSetDetail {
  id: string;
  name: string;
  createdAt: string;
  items: QuizSetDetailItem[];
}

export class NotFoundError extends Error {
  constructor(id: string) {
    super(`クイズセットが見つかりません: ${id}`);
    this.name = 'NotFoundError';
  }
}

function mapQuizSetResponse(data: { id: string; created_at: string }): QuizSetResponse {
  return {
    id: data.id,
    createdAt: data.created_at,
  };
}

function mapListItem(data: {
  id: string;
  name: string;
  created_at: string;
  quiz_count: number;
}): QuizSetListItem {
  return {
    id: data.id,
    name: data.name,
    createdAt: data.created_at,
    quizCount: data.quiz_count,
  };
}

function mapDetailItem(data: {
  saved_quiz_id: string;
  topic: string | null;
  saved_at: string | null;
  question_count: number | null;
  is_deleted: boolean;
}): QuizSetDetailItem {
  return {
    savedQuizId: data.saved_quiz_id,
    topic: data.topic,
    savedAt: data.saved_at,
    questionCount: data.question_count,
    isDeleted: data.is_deleted,
  };
}

function mapDetail(data: {
  id: string;
  name: string;
  created_at: string;
  items: Array<{
    saved_quiz_id: string;
    topic: string | null;
    saved_at: string | null;
    question_count: number | null;
    is_deleted: boolean;
  }>;
}): QuizSetDetail {
  return {
    id: data.id,
    name: data.name,
    createdAt: data.created_at,
    items: data.items.map(mapDetailItem),
  };
}

export async function createQuizSet(request: CreateQuizSetRequest): Promise<QuizSetResponse> {
  const res = await fetch('/api/quiz-sets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: request.name,
      saved_quiz_ids: request.savedQuizIds,
    }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }

  const data = await res.json();
  return mapQuizSetResponse(data);
}

export async function listQuizSets(): Promise<QuizSetListItem[]> {
  const res = await fetch('/api/quiz-sets');

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data: {
    items: Array<{
      id: string;
      name: string;
      created_at: string;
      quiz_count: number;
    }>;
  } = await res.json();
  return data.items.map(mapListItem);
}

export async function getQuizSetDetail(id: string): Promise<QuizSetDetail> {
  const res = await fetch(`/api/quiz-sets/${id}`);

  if (res.status === 404) {
    throw new NotFoundError(id);
  }

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data = await res.json();
  return mapDetail(data);
}

export async function deleteQuizSet(id: string): Promise<void> {
  const res = await fetch(`/api/quiz-sets/${id}`, { method: 'DELETE' });

  if (!res.ok && res.status !== 204) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}
