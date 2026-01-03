/**
 * LocalStorage 操作ユーティリティ
 */

import { QuizHistory } from "./types";
import { HISTORY_STORAGE_KEY } from "./constants";

// LocalStorageから履歴を取得
export const getHistory = (): QuizHistory[] => {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error("履歴の読み込みに失敗しました:", error);
    return [];
  }
};

// LocalStorageに履歴を保存
export const saveHistory = (history: QuizHistory[]) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  } catch (error) {
    console.error("履歴の保存に失敗しました:", error);
  }
};

// 履歴に新しいエントリを追加
export const addHistoryEntry = (entry: QuizHistory) => {
  const history = getHistory();
  // 新しいエントリを先頭に追加（最新が最初）
  history.unshift(entry);
  // 最大100件まで保存
  if (history.length > 100) {
    history.pop();
  }
  saveHistory(history);
};

// 履歴をクリア
export const clearHistory = () => {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
  } catch (error) {
    console.error("履歴のクリアに失敗しました:", error);
  }
};
