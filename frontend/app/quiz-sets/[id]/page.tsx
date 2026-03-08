'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Typography,
} from '@mui/material';
import { QuizSetDetail } from '../../lib/quizSetsApi';
import { useQuizSets } from '../../hooks/useQuizSets';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function QuizSetDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const { fetchDetail } = useQuizSets();
  const [detail, setDetail] = useState<QuizSetDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchDetail(id)
      .then((value) => {
        if (value === null) {
          setNotFound(true);
          return;
        }
        setDetail(value);
      })
      .catch(() => {
        setError('詳細の取得に失敗しました。');
      })
      .finally(() => setIsLoading(false));
  }, [fetchDetail, id]);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (notFound || !detail) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 8, gap: 2 }}>
        <Typography variant="h5">クイズセットが見つかりません</Typography>
        <Link href="/quiz-sets" passHref>
          <Button variant="contained">一覧へ戻る</Button>
        </Link>
      </Box>
    );
  }

  return (
    <Box
      component="main"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        minHeight: '100vh',
        padding: 4,
        gap: 2,
        backgroundColor: '#f5f5f5',
      }}
    >
      <Box sx={{ width: '100%', maxWidth: '760px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">Quiz Set Detail</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Link href={`/local-battle?setId=${detail.id}&setName=${encodeURIComponent(detail.name)}`} passHref>
            <Button variant="contained" size="small">Battle with this Set</Button>
          </Link>
          <Link href="/quiz-sets" passHref>
            <Button variant="outlined" size="small">Back to List</Button>
          </Link>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ width: '100%', maxWidth: '760px' }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3, width: '100%', maxWidth: '760px' }}>
        <Typography variant="h6" gutterBottom>{detail.name}</Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          作成日時: {new Date(detail.createdAt).toLocaleString('ja-JP')}
        </Typography>
      </Paper>

      {detail.items.map((item) => (
        <Paper key={item.savedQuizId} sx={{ p: 3, width: '100%', maxWidth: '760px' }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {item.isDeleted ? '削除済み' : item.topic}
          </Typography>
          {item.isDeleted ? (
            <Typography variant="body2" color="text.secondary">
              このクイズは削除済みです。
            </Typography>
          ) : (
            <>
              <Typography variant="body2" color="text.secondary">
                問題数: {item.questionCount}件
              </Typography>
              <Typography variant="body2" color="text.secondary">
                保存日時: {item.savedAt ? new Date(item.savedAt).toLocaleString('ja-JP') : '-'}
              </Typography>
            </>
          )}
        </Paper>
      ))}
    </Box>
  );
}
