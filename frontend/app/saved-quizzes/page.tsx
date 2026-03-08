'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
} from '@mui/material';
import { useSavedQuizzes } from '../hooks/useSavedQuizzes';

export default function SavedQuizzesPage() {
  const { items, isLoading, error, deletingId, refetch, deleteItem } = useSavedQuizzes();
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
      setSnackbarMessage('クイズを削除しました');
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
      <Box sx={{ width: '100%', maxWidth: '700px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          保存済みクイズ
        </Typography>
        <Link href="/" passHref>
          <Button variant="outlined" size="small">
            ← ホームへ戻る
          </Button>
        </Link>
      </Box>

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert
          severity="error"
          sx={{ width: '100%', maxWidth: '700px' }}
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
        <Paper sx={{ p: 4, width: '100%', maxWidth: '700px', textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            保存されたクイズはありません
          </Typography>
        </Paper>
      )}

      {!isLoading && items.map((item) => (
        <Paper
          key={item.id}
          sx={{ p: 3, width: '100%', maxWidth: '700px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <Box>
            <Typography variant="h6" component="h2">
              {item.topic}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              問題数: {item.question_count}件
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              保存日時: {new Date(item.saved_at).toLocaleString('ja-JP')}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Link href={`/saved-quizzes/${item.id}`} passHref>
              <Button variant="outlined" size="small">
                詳細
              </Button>
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

      {/* 削除確認ダイアログ */}
      <Dialog open={Boolean(confirmDeleteId)} onClose={() => setConfirmDeleteId(null)}>
        <DialogTitle>クイズの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            このクイズを削除しますか？この操作は取り消せません。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDeleteId(null)}>キャンセル</Button>
          <Button onClick={handleDeleteConfirm} color="error" autoFocus>
            削除
          </Button>
        </DialogActions>
      </Dialog>

      {/* 削除結果トースト */}
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
