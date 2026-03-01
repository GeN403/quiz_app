/**
 * API呼び出しユーティリティ
 */

import { QuizData, ResolvedSource } from "./types";
import { DIFFICULTY_OPTIONS, LENGTH_OPTIONS } from "./constants";

export type DifficultyOption = typeof DIFFICULTY_OPTIONS[number];
export type LengthOption = typeof LENGTH_OPTIONS[number];

export interface GenerateQuizOptionalFields {
  difficulty?: string;
  length?: string;
  genre?: string;
  topic?: string;
}

export interface GenerateQuizFieldErrors {
  difficulty?: string;
  length?: string;
  genre?: string;
  topic?: string;
}

/**
 * URL本文取得API呼び出し
 */
export async function fetchResolveSource(url: string): Promise<ResolvedSource> {
  console.log("[DEBUG] Calling /api/resolve-source...");
  const res = await fetch('/api/resolve-source', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: url.trim() }),
  });

  console.log("[DEBUG] Response status:", res.status);

  if (!res.ok) {
    const errorData = await res.json();
    console.error("[DEBUG] Error response:", errorData);
    throw new Error(errorData.detail || `HTTP ${res.status}`);
  }

  const data = await res.json();
  console.log("[DEBUG] Success! Received data:", {
    url: data.url,
    title: data.title,
    quotesCount: data.quotes?.length || 0
  });

  return data;
}

/**
 * クイズ生成API呼び出し
 */
export async function fetchGenerateQuiz(params: {
  category: string;
  questionCount: number;
  sourceUrl: string;
  selectedQuote: string;
  difficulty?: DifficultyOption;
  length?: LengthOption;
  genre?: string;
  topic?: string;
}): Promise<QuizData | { questions: QuizData[] }> {
  const requestBody: Record<string, unknown> = {
    category: params.category,
    question_count: params.questionCount,
    source_type: "url",
    source_value: params.sourceUrl,
    selected_quote: params.selectedQuote,
  };

  Object.assign(requestBody, buildOptionalGeneratePayload(params));

  // タイムアウト設定（30秒）
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    // Next.js プロキシAPI経由でバックエンドに接続（同一オリジン、CORS回避）
    const res = await fetch('/api/generate-quiz', {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal, // タイムアウト用
    });

    clearTimeout(timeoutId); // タイムアウトをクリア

    if (!res.ok) {
      // レスポンスボディからエラーメッセージを取得
      let errorDetail = "";
      try {
        const errorData = await res.json();
        errorDetail = errorData.detail || "";
      } catch {
        // JSON解析に失敗した場合は空文字列のまま
      }

      // HTTPステータスコードとエラーメッセージに応じた処理
      if (res.status === 401 || errorDetail.includes("GEMINI_API_KEY_INVALID")) {
        throw new Error(
          "Gemini APIキーが無効です。\n" +
          "管理者にお問い合わせください。\n\n" +
          "開発者向け: backend/.envファイルのGEMINI_API_KEYを確認してください。"
        );
      } else if (res.status === 403 || errorDetail.includes("GEMINI_API_KEY_PERMISSION_DENIED")) {
        throw new Error(
          "Gemini APIキーの権限が不足しています。\n" +
          "管理者にお問い合わせください。"
        );
      } else if (res.status === 429 || errorDetail.includes("GEMINI_RATE_LIMIT")) {
        throw new Error(
          "Gemini APIのリクエスト制限に達しました。\n" +
          "しばらく待ってから再度お試しください。"
        );
      } else if (res.status === 503 || errorDetail.includes("GEMINI_SERVICE_UNAVAILABLE")) {
        throw new Error(
          "Gemini AIサービスが一時的に利用できません。\n" +
          "しばらく待ってから再度お試しください。"
        );
      } else if (res.status === 504 || errorDetail.includes("GEMINI_TIMEOUT")) {
        throw new Error(
          "Gemini APIへのリクエストがタイムアウトしました。\n" +
          "もう一度お試しください。"
        );
      } else if (errorDetail.includes("GEMINI_API_KEY_NOT_SET")) {
        throw new Error(
          "Gemini APIキーが設定されていません。\n" +
          "管理者にお問い合わせください。\n\n" +
          "開発者向け: backend/.envファイルにGEMINI_API_KEYを設定してください。"
        );
      } else if (errorDetail.includes("AI_INVALID_JSON")) {
        throw new Error(
          "AIの応答形式が不正です。\n" +
          "もう一度お試しください。"
        );
      } else if (errorDetail.includes("SOURCE_RESTRICTION_VIOLATION")) {
        throw new Error(
          "参照元が制限（コトバンク/公式サイト）に一致しないため、生成結果を表示できません。\n" +
          "別のカテゴリで再試行してください。"
        );
      } else if (res.status >= 500) {
        throw new Error(
          "バックエンドサーバーでエラーが発生しました。\n" +
          "時間をおいて再度お試しください。"
        );
      } else if (res.status === 400) {
        if (errorDetail.includes("CATEGORY_MODE_DEPRECATED")) {
          throw new Error(
            "カテゴリモードは廃止されました。\n" +
            "URLを入力して「本文を取得」ボタンを押してからクイズを生成してください。"
          );
        } else {
          throw new Error(
            errorDetail || "リクエストが無効です。もう一度お試しください。"
          );
        }
      } else {
        throw new Error(`APIエラー: ${res.status} ${res.statusText}`);
      }
    }

    const data = await res.json();
    return data;
  } catch (error: any) {
    // エラーの種類に応じたメッセージ
    if (error.name === "AbortError") {
      throw new Error(
        "リクエストがタイムアウトしました。ネットワーク接続を確認するか、時間をおいて再度お試しください。"
      );
    } else if (error.message.includes("Failed to fetch") || error.message.includes("fetch")) {
      throw new Error(
        "バックエンドサーバーに接続できません。サーバーが起動しているか確認してください。\n" +
        "起動方法: backend/ で「uvicorn main:app --reload」を実行"
      );
    } else {
      throw error;
    }
  }
}

export function buildOptionalGeneratePayload(
  fields: GenerateQuizOptionalFields
): GenerateQuizOptionalFields {
  const payload: GenerateQuizOptionalFields = {};
  const difficulty = fields.difficulty?.trim();
  const length = fields.length?.trim();
  const genre = fields.genre?.trim();
  const topic = fields.topic?.trim();

  if (difficulty) payload.difficulty = difficulty;
  if (length) payload.length = length;
  if (genre) payload.genre = genre;
  if (topic) payload.topic = topic;

  return payload;
}

export const buildGeneratePayload = buildOptionalGeneratePayload;
