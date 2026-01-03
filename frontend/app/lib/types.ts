/**
 * 型定義
 */

// AIから返ってくるJSONの型を定義
export interface QuizData {
  question: string;
  answer: string;
  "Alternative Solutions/Correctness Judgment Criteria": string;
  explanation: string;
  source: {
    title: string;
    url: string;
    quote: string;
  };
}

// 履歴データの型を定義
export interface QuizHistory {
  id: string; // 一意のID
  category: string; // カテゴリ
  categoryLabel: string; // カテゴリの日本語名
  question: string; // 問題文
  correctAnswer: string; // 想定解答
  userAnswer: string; // ユーザーの回答
  isCorrect: boolean; // 正誤
  timestamp: number; // タイムスタンプ（UNIXタイム）
}

// URL本文取得結果の型
export interface ResolvedSource {
  url: string;
  title: string;
  text_excerpt: string;
  quotes: string[];
}
