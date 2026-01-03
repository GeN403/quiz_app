/**
 * アプリケーション定数
 */

// カテゴリの定義
export const CATEGORIES = [
  { value: "history", label: "歴史" },
  { value: "science", label: "科学" },
  { value: "literature", label: "文学" },
  { value: "geography", label: "地理" },
  { value: "sports", label: "スポーツ" },
  { value: "arts", label: "芸術" },
  { value: "general", label: "一般知識" },
] as const;

// LocalStorageのキー名
export const HISTORY_STORAGE_KEY = "quiz_app_history";

// 回答の最大文字数
export const MAX_ANSWER_LENGTH = 200;
