'use client';

import { useEffect, useState } from 'react';
import { Button, Snackbar, Alert, CircularProgress } from '@mui/material';
import {
  saveSavedQuiz,
  DuplicateSaveError,
  GenerationInputParams,
} from '../lib/savedQuizzesApi';

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

interface SaveButtonProps {
  answerPackage: Record<string, unknown> | null;
  inputParams: GenerationInputParams | null;
}

export function SaveButton({ answerPackage, inputParams }: SaveButtonProps) {
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error' | 'info'>('success');
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const packageId = typeof answerPackage?.package_id === 'string' ? answerPackage.package_id : null;
  const hasPackageId = Boolean(packageId);
  const isDisabled = !hasPackageId || !inputParams || saveState === 'saving' || saveState === 'saved';

  useEffect(() => {
    setSaveState('idle');
  }, [packageId]);

  const handleSave = async () => {
    if (!answerPackage || !inputParams || !hasPackageId) return;

    setSaveState('saving');
    try {
      await saveSavedQuiz({ input_params: inputParams, answer_package: answerPackage });
      setSaveState('saved');
      setSnackbarMessage('クイズを保存しました');
      setSnackbarSeverity('success');
      setSnackbarOpen(true);
    } catch (e) {
      if (e instanceof DuplicateSaveError) {
        setSaveState('saved');
        setSnackbarMessage('すでに保存済みです');
        setSnackbarSeverity('info');
        setSnackbarOpen(true);
      } else {
        setSaveState('idle');
        setSnackbarMessage('保存に失敗しました。もう一度お試しください。');
        setSnackbarSeverity('error');
        setSnackbarOpen(true);
      }
    }
  };

  return (
    <>
      <Button
        variant="outlined"
        size="small"
        onClick={handleSave}
        disabled={isDisabled}
        startIcon={saveState === 'saving' ? <CircularProgress size={16} /> : undefined}
        color={saveState === 'saved' ? 'success' : 'primary'}
      >
        {saveState === 'saving'
          ? '保存中...'
          : saveState === 'saved'
          ? '保存済み'
          : 'クイズを保存'}
      </Button>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbarOpen(false)}
          severity={snackbarSeverity}
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </>
  );
}
