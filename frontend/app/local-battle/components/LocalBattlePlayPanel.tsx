'use client';

import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
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
  selectedChoiceId: string | null;
  isCorrect: boolean | null;
  onSubmitAnswer: (choiceId: string) => void;
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
  selectedChoiceId,
  isCorrect,
  onSubmitAnswer,
  onProceedNext,
}: LocalBattlePlayPanelProps) {
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
        {question.choices.map((choice) => {
          const isSelected = selectedChoiceId === choice.choiceId;
          return (
            <Button
              key={choice.choiceId}
              variant={isSelected ? 'contained' : 'outlined'}
              color={isSelected ? 'primary' : 'inherit'}
              onClick={() => onSubmitAnswer(choice.choiceId)}
              disabled={waitingForBuzz || isSubmitting || isAnswered}
              sx={{ justifyContent: 'flex-start' }}
            >
              {choice.text}
            </Button>
          );
        })}
      </Stack>

      {isAnswered && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Alert severity={isCorrect ? 'success' : 'error'}>
            {isCorrect ? '正解です。' : '不正解です。'}
          </Alert>
          <Button variant="contained" onClick={onProceedNext}>
            {questionNumber >= totalQuestions ? '結果へ進む' : '次の問題へ進む'}
          </Button>
        </Box>
      )}
    </Paper>
  );
}
