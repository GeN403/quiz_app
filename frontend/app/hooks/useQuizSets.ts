'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  deleteQuizSet,
  getQuizSetDetail,
  listQuizSets,
  NotFoundError,
  QuizSetDetail,
  QuizSetListItem,
} from '../lib/quizSetsApi';

interface UseQuizSetsReturn {
  items: QuizSetListItem[];
  isLoading: boolean;
  error: string | null;
  deletingId: string | null;
  refetch: () => Promise<void>;
  fetchDetail: (id: string) => Promise<QuizSetDetail | null>;
  deleteItem: (id: string) => Promise<{ success: boolean; error?: string }>;
}

export function useQuizSets(): UseQuizSetsReturn {
  const [items, setItems] = useState<QuizSetListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listQuizSets();
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

  const fetchDetail = useCallback(async (id: string): Promise<QuizSetDetail | null> => {
    try {
      return await getQuizSetDetail(id);
    } catch (e) {
      if (e instanceof NotFoundError) return null;
      throw e;
    }
  }, []);

  const deleteItem = useCallback(
    async (id: string): Promise<{ success: boolean; error?: string }> => {
      if (deletingId !== null) {
        return { success: false, error: '削除中です' };
      }

      const previousItems = items;
      setDeletingId(id);
      setItems((prev) => prev.filter((item) => item.id !== id));

      try {
        await deleteQuizSet(id);
        return { success: true };
      } catch {
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
