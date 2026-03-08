'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
} from '@mui/material';
import { getSavedQuizDetail, NotFoundError, SavedQuizDetail } from '../../lib/savedQuizzesApi';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function SavedQuizDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const [detail, setDetail] = useState<SavedQuizDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getSavedQuizDetail(id)
      .then(setDetail)
      .catch((e) => {
        if (e instanceof NotFoundError) setNotFound(true);
      })
      .finally(() => setIsLoading(false));
  }, [id]);

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
        <Typography variant="h5">クイズが見つかりません</Typography>
        <Link href="/saved-quizzes" passHref>
          <Button variant="contained">一覧へ戻る</Button>
        </Link>
      </Box>
    );
  }

  const ap = detail.answer_package as Record<string, unknown>;
  const ip = detail.input_params;

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
      <Box sx={{ width: '100%', maxWidth: '700px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          クイズ詳細
        </Typography>
        <Link href="/saved-quizzes" passHref>
          <Button variant="outlined" size="small">
            ← 一覧へ戻る
          </Button>
        </Link>
      </Box>

      {/* 入力パラメータ */}
      <Paper sx={{ p: 3, width: '100%', maxWidth: '700px' }}>
        <Typography variant="h6" gutterBottom>
          生成設定
        </Typography>
        <Typography variant="body2">モード: {ip.mode}</Typography>
        {ip.keyword && <Typography variant="body2">キーワード: {ip.keyword}</Typography>}
        {ip.category && <Typography variant="body2">カテゴリ: {ip.category}</Typography>}
        {ip.source_url && <Typography variant="body2">URL: {ip.source_url}</Typography>}
        <Typography variant="body2">問題数: {ip.question_count}</Typography>
        {ip.difficulty && <Typography variant="body2">難易度: {ip.difficulty}</Typography>}
        {ip.length && <Typography variant="body2">解答文字数: {ip.length}</Typography>}
        {ip.genre && <Typography variant="body2">ジャンル: {ip.genre}</Typography>}
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          保存日時: {new Date(detail.saved_at).toLocaleString('ja-JP')}
        </Typography>
      </Paper>

      {/* 問題文 */}
      <Paper sx={{ p: 3, width: '100%', maxWidth: '700px' }}>
        <Typography variant="h6" gutterBottom>
          問題文
        </Typography>
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {String(ap.question ?? '')}
        </Typography>
      </Paper>

      {/* 正解 */}
      <Paper sx={{ p: 3, width: '100%', maxWidth: '700px', backgroundColor: '#e8f5e9' }}>
        <Typography variant="h6" gutterBottom color="success.dark">
          正解
        </Typography>
        <Typography variant="body1" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
          {String(ap.answer ?? '')}
        </Typography>
      </Paper>

      {/* 別解・判定基準 */}
      {ap['Alternative Solutions/Correctness Judgment Criteria'] && (
        <Paper sx={{ p: 3, width: '100%', maxWidth: '700px' }}>
          <Typography variant="h6" gutterBottom>
            別解/正誤判定基準
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {String(ap['Alternative Solutions/Correctness Judgment Criteria'])}
          </Typography>
        </Paper>
      )}

      {/* 解説 */}
      {ap.explanation && (
        <Paper sx={{ p: 3, width: '100%', maxWidth: '700px' }}>
          <Typography variant="h6" gutterBottom>
            解説
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {String(ap.explanation)}
          </Typography>
        </Paper>
      )}

      {/* 出典 */}
      {ap.source && typeof ap.source === 'object' && (
        <Paper sx={{ p: 3, width: '100%', maxWidth: '700px' }}>
          <Typography variant="h6" gutterBottom>
            出典
          </Typography>
          <Typography variant="body2">
            <a
              href={String((ap.source as Record<string, unknown>).url ?? '')}
              target="_blank"
              rel="noopener noreferrer"
            >
              {String((ap.source as Record<string, unknown>).title ?? '')}
            </a>
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
