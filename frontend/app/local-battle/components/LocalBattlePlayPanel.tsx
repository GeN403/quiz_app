'use client';

import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import { BattleQuestion } from '../../lib/localBattleApi';

interface LocalBattlePlayPanelProps {
  question: BattleQuestion;
  questionNumber: number;
  totalQuestions: number;
  answererName: string;
  waitingForBuzz: boolean;
  buzzHint: string;
  isSubmitting: boolean;
  isAnswered: boolean;
  isCorrect: boolean | null;
  onSubmitAnswer: (answerText: string) => void;
  onProceedNext: () => void;
}

export default function LocalBattlePlayPanel({
  question,
  questionNumber,
  totalQuestions,
  answererName,
  waitingForBuzz,
  buzzHint,
  isSubmitting,
  isAnswered,
  isCorrect,
  onSubmitAnswer,
  onProceedNext,
}: LocalBattlePlayPanelProps) {
  const [inputValue, setInputValue] = useState('');

  useEffect(() => {
    setInputValue('');
  }, [question.questionId]);

  const handleSubmit = () => {
    if (inputValue.trim() === '') return;
    onSubmitAnswer(inputValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <Paper sx={{ p: 3, width: '100%', maxWidth: '760px', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="subtitle2" color="text.secondary">
        問題 {questionNumber} / {totalQuestions}
      </Typography>

      <Typography variant="h6">回答者: {answererName || '未確定'}</Typography>
      <Typography variant="body2" color="text.secondary">
        {buzzHint}
      </Typography>

      {waitingForBuzz && (
        <Alert severity="info">F/J のどちらかを押して回答権を取ってください。</Alert>
      )}

      <Typography variant="h5" sx={{ whiteSpace: 'pre-wrap' }}>
        {question.prompt}
      </Typography>

      <Stack spacing={1.5}>
        <TextField
          label="回答を入力"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={waitingForBuzz || isSubmitting || isAnswered}
          autoComplete="off"
          fullWidth
        />
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={waitingForBuzz || isSubmitting || isAnswered || inputValue.trim() === ''}
        >
          回答する
        </Button>
      </Stack>

      {isAnswered && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Alert severity={isCorrect ? 'success' : 'error'}>
            {isCorrect ? '正解です。' : '不正解です。'}
          </Alert>
          <Typography variant="body2" color="text.secondary">
            正解: {question.correctAnswerText}
          </Typography>
          <Button variant="contained" onClick={onProceedNext}>
            {questionNumber >= totalQuestions ? '結果へ進む' : '次の問題へ進む'}
          </Button>
        </Box>
      )}
    </Paper>
  );
}
