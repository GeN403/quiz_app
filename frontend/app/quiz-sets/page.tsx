'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Snackbar,
  Typography,
} from '@mui/material';
import { useQuizSets } from '../hooks/useQuizSets';

export default function QuizSetsPage() {
  const { items, isLoading, error, deletingId, refetch, deleteItem } = useQuizSets();
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error'>('success');

  const handleDeleteConfirm = async () => {
    if (!confirmDeleteId) return;
    const id = confirmDeleteId;
    setConfirmDeleteId(null);

    const result = await deleteItem(id);
    if (result.success) {
      setSnackbarMessage('クイズセットを削除しました');
      setSnackbarSeverity('success');
    } else {
      setSnackbarMessage(result.error ?? '削除に失敗しました');
      setSnackbarSeverity('error');
    }
    setSnackbarOpen(true);
  };

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
        <Typography variant="h4" component="h1">
          クイズセット
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Link href="/quiz-sets/new" passHref>
            <Button variant="contained" size="small">新規作成</Button>
          </Link>
          <Link href="/" passHref>
            <Button variant="outlined" size="small">← ホームへ戻る</Button>
          </Link>
        </Box>
      </Box>

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert
          severity="error"
          sx={{ width: '100%', maxWidth: '760px' }}
          action={
            <Button color="inherit" size="small" onClick={refetch}>
              再試行
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {!isLoading && !error && items.length === 0 && (
        <Paper sx={{ p: 4, width: '100%', maxWidth: '760px', textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            作成されたクイズセットはありません
          </Typography>
        </Paper>
      )}

      {!isLoading && items.map((item) => (
        <Paper
          key={item.id}
          sx={{ p: 3, width: '100%', maxWidth: '760px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <Box>
            <Typography variant="h6" component="h2">
              {item.name}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              クイズ数: {item.quizCount}件
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              作成日時: {new Date(item.createdAt).toLocaleString('ja-JP')}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Link href={`/quiz-sets/${item.id}`} passHref>
              <Button variant="outlined" size="small">詳細</Button>
            </Link>
            <Button
              variant="outlined"
              color="error"
              size="small"
              onClick={() => setConfirmDeleteId(item.id)}
              disabled={deletingId === item.id}
            >
              {deletingId === item.id ? '削除中...' : '削除'}
            </Button>
          </Box>
        </Paper>
      ))}

      <Dialog open={Boolean(confirmDeleteId)} onClose={() => setConfirmDeleteId(null)}>
        <DialogTitle>クイズセットの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            このクイズセットを削除しますか？この操作は取り消せません。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDeleteId(null)}>キャンセル</Button>
          <Button onClick={handleDeleteConfirm} color="error" autoFocus>削除</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnackbarOpen(false)} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
