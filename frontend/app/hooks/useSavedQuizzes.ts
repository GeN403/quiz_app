'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  deleteSavedQuiz,
  getSavedQuizDetail,
  listSavedQuizzes,
  NotFoundError,
  SavedQuizDetail,
  SavedQuizListItem,
} from '../lib/savedQuizzesApi';

interface UseSavedQuizzesReturn {
  items: SavedQuizListItem[];
  isLoading: boolean;
  error: string | null;
  deletingId: string | null;
  refetch: () => Promise<void>;
  fetchDetail: (id: string) => Promise<SavedQuizDetail | null>;
  deleteItem: (id: string) => Promise<{ success: boolean; error?: string }>;
}

export function useSavedQuizzes(): UseSavedQuizzesReturn {
  const [items, setItems] = useState<SavedQuizListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listSavedQuizzes();
      setItems(data);
    } catch {
      setError('一覧の取得に失敗しました。再度お試しください。');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const fetchDetail = useCallback(
    async (id: string): Promise<SavedQuizDetail | null> => {
      try {
        return await getSavedQuizDetail(id);
      } catch (e) {
        if (e instanceof NotFoundError) return null;
        throw e;
      }
    },
    []
  );

  const deleteItem = useCallback(
    async (id: string): Promise<{ success: boolean; error?: string }> => {
      if (deletingId) return { success: false, error: '削除中です' };

      const previousItems = items;
      setDeletingId(id);
      // 楽観的更新: 即時 UI から除去
      setItems((prev) => prev.filter((item) => item.id !== id));

      try {
        await deleteSavedQuiz(id);
        return { success: true };
      } catch {
        // ロールバック
        setItems(previousItems);
        return { success: false, error: '削除に失敗しました。もう一度お試しください。' };
      } finally {
        setDeletingId(null);
      }
    },
    [deletingId, items]
  );

  return { items, isLoading, error, deletingId, refetch, fetchDetail, deleteItem };
}
