/**
 * アプリケーション定数
 */

// カテゴリの定義（13ジャンル）
export const CATEGORIES = [
  { value: "natural_science", label: "自然科学" },
  { value: "literature", label: "文学" },
  { value: "philosophy", label: "思想" },
  { value: "language", label: "言葉" },
  { value: "history", label: "歴史" },
  { value: "geography", label: "地理" },
  { value: "civics", label: "公民" },
  { value: "arts", label: "芸術" },
  { value: "blue", label: "青" },
  { value: "lifestyle", label: "生活" },
  { value: "sports", label: "スポーツ" },
  { value: "entertainment", label: "芸能" },
  { value: "non_section", label: "ノンセクション" },
] as const;

// LocalStorageのキー名
export const HISTORY_STORAGE_KEY = "quiz_app_history";

// 回答の最大文字数
export const MAX_ANSWER_LENGTH = 200;
