'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import LocalBattlePlayPanel from './components/LocalBattlePlayPanel';
import { useLocalBattleController } from '../hooks/useLocalBattleController';

export default function LocalBattlePage() {
  const controller = useLocalBattleController();
  const searchParams = useSearchParams();
  const presetSetId = searchParams.get('setId');
  const autoSelectedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!presetSetId) return;
    if (controller.phase !== 'set_selection') return;
    if (controller.isLoadingSets || controller.isPreparing) return;
    if (autoSelectedRef.current === presetSetId) return;

    const target = controller.setItems.find((item) => item.setId === presetSetId);
    if (!target) return;

    autoSelectedRef.current = presetSetId;
    void controller.selectSet(target.setId, target.setName);
  }, [
    controller.isLoadingSets,
    controller.isPreparing,
    controller.phase,
    controller.selectSet,
    controller.setItems,
    presetSetId,
  ]);

  useEffect(() => {
    if (controller.phase !== 'playing') {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) {
        return;
      }

      const key = event.key.toLowerCase();
      if (key === 'f') {
        event.preventDefault();
        controller.lockAnswerer('player1');
      } else if (key === 'j') {
        event.preventDefault();
        controller.lockAnswerer('player2');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [controller.lockAnswerer, controller.phase]);

  const player1Name = controller.playerNames.player1.trim() || 'プレイヤー1';
  const player2Name = controller.playerNames.player2.trim() || 'プレイヤー2';
  const answererName =
    controller.currentAnswerer === null
      ? ''
      : controller.playerNames[controller.currentAnswerer];

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
      <Box
        sx={{
          width: '100%',
          maxWidth: '760px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Typography variant="h4" component="h1">
          ローカル対戦
        </Typography>
        <Link href="/" passHref>
          <Button variant="outlined" size="small">
            ← ホームへ戻る
          </Button>
        </Link>
      </Box>

      {controller.phase === 'set_selection' && (
        <Paper
          sx={{
            p: 3,
            width: '100%',
            maxWidth: '760px',
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <Typography variant="h6">クイズセットを選択</Typography>

          {controller.isLoadingSets && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress />
            </Box>
          )}

          {controller.listError && (
            <Alert
              severity="error"
              action={
                <Button color="inherit" size="small" onClick={controller.refetchSets}>
                  再試行
                </Button>
              }
            >
              {controller.listError}
            </Alert>
          )}

          {!controller.isLoadingSets && !controller.listError && controller.setItems.length === 0 && (
            <Alert severity="info">利用可能なクイズセットがありません。</Alert>
          )}

          <Stack spacing={1.5}>
            {controller.setItems.map((item) => (
              <Paper key={item.setId} variant="outlined" sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle1">{item.setName}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      クイズ数: {item.quizCount}
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    onClick={() => controller.selectSet(item.setId, item.setName)}
                    disabled={controller.isPreparing}
                  >
                    選択
                  </Button>
                </Box>
              </Paper>
            ))}
          </Stack>
        </Paper>
      )}

      {controller.phase === 'player_setup' && (
        <Paper
          sx={{
            p: 3,
            width: '100%',
            maxWidth: '760px',
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <Typography variant="h6">対戦設定</Typography>
          <Typography variant="body2" color="text.secondary">
            選択セット: {controller.selectedSetName}
          </Typography>
          <Typography variant="body2">
            実使用問題数: {controller.eligibleQuestionCount}
          </Typography>

          <TextField
            label="プレイヤー1"
            value={controller.playerNames.player1}
            onChange={(e) => controller.updatePlayerName('player1', e.target.value)}
          />
          <TextField
            label="プレイヤー2"
            value={controller.playerNames.player2}
            onChange={(e) => controller.updatePlayerName('player2', e.target.value)}
          />

          <Alert severity="info">早押しキー: プレイヤー1はF、プレイヤー2はJ</Alert>

          {controller.startBlockedMessage && (
            <Alert severity="warning">{controller.startBlockedMessage}</Alert>
          )}

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="contained" onClick={controller.startBattle} disabled={controller.isStarting}>
              {controller.isStarting ? '開始準備中...' : '対戦開始'}
            </Button>
            <Button variant="outlined" onClick={controller.backToSelection}>
              セット選択へ戻る
            </Button>
          </Box>
        </Paper>
      )}

      {controller.phase === 'playing' && controller.currentQuestion && (
        <>
          <Paper sx={{ p: 2, width: '100%', maxWidth: '760px' }}>
            <Typography variant="h6" gutterBottom>
              スコア
            </Typography>
            <Typography>{player1Name}: {controller.scores.player1}</Typography>
            <Typography>{player2Name}: {controller.scores.player2}</Typography>
          </Paper>

          <LocalBattlePlayPanel
            question={controller.currentQuestion}
            questionNumber={controller.currentQuestionNumber}
            totalQuestions={controller.totalQuestions}
            answererName={answererName}
            waitingForBuzz={controller.currentAnswerer === null && controller.questionAnswerStatus === 'unanswered'}
            buzzHint={`Fキー: ${player1Name} / Jキー: ${player2Name}`}
            isSubmitting={controller.isSubmitting}
            isAnswered={controller.questionAnswerStatus === 'answered'}
            isCorrect={controller.answerResult?.isCorrect ?? null}
            onSubmitAnswer={controller.submitAnswer}
            onProceedNext={controller.proceedNext}
          />
        </>
      )}

      {controller.phase === 'result' && (
        <Paper sx={{ p: 3, width: '100%', maxWidth: '760px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant="h5">対戦結果</Typography>
          <Typography>{player1Name}: {controller.scores.player1}</Typography>
          <Typography>{player2Name}: {controller.scores.player2}</Typography>
          <Typography variant="h6">
            {controller.winner === 'draw'
              ? '引き分け'
              : controller.winner === 'player1'
              ? `勝者: ${player1Name}`
              : `勝者: ${player2Name}`}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="contained" onClick={controller.rematch}>
              同じセットで再戦
            </Button>
            <Button variant="outlined" onClick={controller.backToSelection}>
              セット選択へ戻る
            </Button>
          </Box>
        </Paper>
      )}
    </Box>
  );
}
