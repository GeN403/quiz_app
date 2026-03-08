'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  FormGroup,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { createQuizSet } from '../../lib/quizSetsApi';
import { listSavedQuizzes, SavedQuizListItem } from '../../lib/savedQuizzesApi';

export default function QuizSetNewPage() {
  const router = useRouter();
  const [savedQuizzes, setSavedQuizzes] = useState<SavedQuizListItem[]>([]);
  const [name, setName] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);

  const fetchSavedQuizzes = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await listSavedQuizzes();
      setSavedQuizzes(data);
    } catch {
      setLoadError('クイズ一覧を取得できませんでした。');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSavedQuizzes();
  }, []);

  const toggleSelection = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const validate = (): boolean => {
    const trimmed = name.trim();
    let hasError = false;

    if (!trimmed) {
      setNameError('セット名を入力してください。');
      hasError = true;
    } else if (trimmed.length > 100) {
      setNameError('セット名は100文字以内で入力してください。');
      hasError = true;
    } else {
      setNameError(null);
    }

    if (selectedIds.size === 0) {
      setSelectionError('クイズを1つ以上選択してください。');
      hasError = true;
    } else {
      setSelectionError(null);
    }

    return !hasError;
  };

  const handleSubmit = async () => {
    setSubmitError(null);
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const created = await createQuizSet({
        name: name.trim(),
        savedQuizIds: Array.from(selectedIds),
      });
      router.push(`/quiz-sets/${created.id}`);
    } catch (e) {
      const message = e instanceof Error ? e.message : '作成に失敗しました。';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
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
          クイズセット作成
        </Typography>
        <Link href="/quiz-sets" passHref>
          <Button variant="outlined" size="small">← 一覧へ戻る</Button>
        </Link>
      </Box>

      <Paper sx={{ p: 3, width: '100%', maxWidth: '760px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField
          label="セット名"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={Boolean(nameError)}
          helperText={nameError ?? '最大100文字'}
          fullWidth
          inputProps={{ maxLength: 100 }}
          disabled={isSubmitting}
        />

        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress />
          </Box>
        )}

        {loadError && (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={fetchSavedQuizzes}>
                再試行
              </Button>
            }
          >
            {loadError}
          </Alert>
        )}

        {!isLoading && !loadError && savedQuizzes.length === 0 && (
          <Alert severity="info">保存済みクイズがないため、セットを作成できません。</Alert>
        )}

        {!isLoading && !loadError && savedQuizzes.length > 0 && (
          <>
            <Typography variant="subtitle1">含めるクイズを選択</Typography>
            <FormGroup>
              {savedQuizzes.map((quiz) => (
                <FormControlLabel
                  key={quiz.id}
                  control={
                    <Checkbox
                      checked={selectedIds.has(quiz.id)}
                      onChange={() => toggleSelection(quiz.id)}
                      disabled={isSubmitting}
                    />
                  }
                  label={`${quiz.topic}（${quiz.question_count}問）`}
                />
              ))}
            </FormGroup>
            {selectionError && (
              <Typography variant="caption" color="error">{selectionError}</Typography>
            )}
          </>
        )}

        {submitError && <Alert severity="error">{submitError}</Alert>}

        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isSubmitting || isLoading || Boolean(loadError) || savedQuizzes.length === 0}
        >
          {isSubmitting ? '作成中...' : '作成する'}
        </Button>
      </Paper>
    </Box>
  );
}
