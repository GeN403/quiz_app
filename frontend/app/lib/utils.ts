/**
 * ユーティリティ関数
 */

// 回答を正規化する関数（スペース削除、小文字変換、全角→半角）
export const normalizeAnswer = (text: string): string => {
  return text
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "") // スペース削除
    .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (s) => String.fromCharCode(s.charCodeAt(0) - 0xfee0)); // 全角→半角
};
