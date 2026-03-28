'use client';

import { useCallback, useEffect, useMemo, useReducer } from 'react';
import {
  getBattleReadySet,
  getQuizSets,
  NotFoundError,
  UpstreamError,
} from '../lib/localBattleApi';
import { normalizeAnswer } from '../lib/utils';

async function judgeAnswerWithAI(
  question: string,
  correctAnswer: string,
  userAnswer: string,
): Promise<boolean> {
  const res = await fetch('/api/judge-answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, correct_answer: correctAnswer, user_answer: userAnswer }),
  });
  if (!res.ok) {
    throw new Error(`judge-answer failed: ${res.status}`);
  }
  const data = await res.json();
  return Boolean(data.is_correct);
}
import {
  BattlePhase,
  BattleQuestion,
  BattleSetListItem,
  PlayerSlot,
  QuestionAnswerStatus,
  AnswerResult,
  computeWinner,
  createInitialBattleState,
  localBattleReducer,
  mapHttpErrorStatus,
  mapReasonCode,
  mapUnknownStartError,
  shuffleQuestions,
  validatePlayerNames,
} from '../lib/localBattleControllerCore';

function mapStartError(error: unknown): string {
  if (error instanceof NotFoundError) {
    return mapHttpErrorStatus(404);
  }

  if (error instanceof UpstreamError) {
    return mapHttpErrorStatus(error.status);
  }

  return mapUnknownStartError();
}

export interface LocalBattleController {
  phase: BattlePhase;
  setItems: BattleSetListItem[];
  isLoadingSets: boolean;
  listError: string | null;
  isPreparing: boolean;
  isStarting: boolean;
  isSubmitting: boolean;
  selectedSetId: string | null;
  selectedSetName: string | null;
  playerNames: Record<PlayerSlot, string>;
  eligibleQuestionCount: number;
  startBlockedMessage: string | null;
  currentQuestion: BattleQuestion | null;
  currentQuestionNumber: number;
  totalQuestions: number;
  currentAnswerer: PlayerSlot | null;
  questionAnswerStatus: QuestionAnswerStatus;
  answerResult: AnswerResult | null;
  scores: Record<PlayerSlot, number>;
  winner: PlayerSlot | 'draw' | null;
  selectSet: (setId: string, setName: string) => Promise<void>;
  updatePlayerName: (player: PlayerSlot, name: string) => void;
  startBattle: () => Promise<void>;
  lockAnswerer: (answerer: PlayerSlot) => void;
  submitAnswer: (answerText: string) => Promise<void>;
  proceedNext: () => void;
  rematch: () => void;
  backToSelection: () => void;
  refetchSets: () => Promise<void>;
}

export function useLocalBattleController(): LocalBattleController {
  const [state, dispatch] = useReducer(localBattleReducer, undefined, createInitialBattleState);

  const refetchSets = useCallback(async () => {
    dispatch({ type: 'LOAD_SETS_START' });
    try {
      const items = await getQuizSets();
      dispatch({ type: 'LOAD_SETS_SUCCESS', items });
    } catch {
      dispatch({
        type: 'LOAD_SETS_FAILURE',
        message: 'クイズセット一覧の取得に失敗しました。',
      });
    }
  }, []);

  useEffect(() => {
    refetchSets();
  }, [refetchSets]);

  const selectSet = useCallback(async (setId: string, setName: string) => {
    dispatch({ type: 'SELECT_SET', setId, setName });
    dispatch({ type: 'SET_IS_PREPARING', value: true });

    try {
      const ready = await getBattleReadySet(setId);
      dispatch({
        type: 'SET_PREVIEW_RESULT',
        eligibleQuestionCount: ready.eligibleQuestionCount,
        startBlockedMessage: ready.startable ? null : mapReasonCode(ready.reasonCode),
      });
    } catch (error) {
      dispatch({
        type: 'SET_PREVIEW_RESULT',
        eligibleQuestionCount: 0,
        startBlockedMessage: mapStartError(error),
      });
    } finally {
      dispatch({ type: 'SET_IS_PREPARING', value: false });
    }
  }, []);

  const updatePlayerName = useCallback((player: PlayerSlot, name: string) => {
    dispatch({ type: 'SET_PLAYER_NAME', player, name });
  }, []);

  const startBattle = useCallback(async () => {
    if (!state.selectedSetId) {
      dispatch({ type: 'SET_START_BLOCKED_MESSAGE', message: 'クイズセットを選択してください。' });
      return;
    }

    const nameValidationMessage = validatePlayerNames(state.playerNames.player1, state.playerNames.player2);
    if (nameValidationMessage !== null) {
      dispatch({ type: 'SET_START_BLOCKED_MESSAGE', message: nameValidationMessage });
      return;
    }

    dispatch({ type: 'SET_START_BLOCKED_MESSAGE', message: null });
    dispatch({ type: 'SET_IS_STARTING', value: true });

    try {
      const ready = await getBattleReadySet(state.selectedSetId);
      dispatch({
        type: 'SET_PREVIEW_RESULT',
        eligibleQuestionCount: ready.eligibleQuestionCount,
        startBlockedMessage: ready.startable ? null : mapReasonCode(ready.reasonCode),
      });

      if (!ready.startable || ready.eligibleQuestionCount === 0 || ready.questions.length === 0) {
        dispatch({
          type: 'SET_START_BLOCKED_MESSAGE',
          message: mapReasonCode(ready.reasonCode),
        });
        return;
      }

      dispatch({
        type: 'START_PLAYING',
        preparedQuestions: ready.questions,
        shuffledQuestions: shuffleQuestions(ready.questions),
      });
    } catch (error) {
      dispatch({ type: 'SET_START_BLOCKED_MESSAGE', message: mapStartError(error) });
    } finally {
      dispatch({ type: 'SET_IS_STARTING', value: false });
    }
  }, [state.playerNames.player1, state.playerNames.player2, state.selectedSetId]);

  const lockAnswerer = useCallback(
    (answerer: PlayerSlot) => {
      if (
        state.phase !== 'playing' ||
        state.questionAnswerStatus === 'answered' ||
        state.isSubmitting ||
        state.currentAnswerer !== null
      ) {
        return;
      }

      dispatch({ type: 'LOCK_ANSWERER', answerer });
    },
    [
      state.currentAnswerer,
      state.isSubmitting,
      state.phase,
      state.questionAnswerStatus,
    ]
  );

  const submitAnswer = useCallback(
    async (answerText: string) => {
      if (
        state.phase !== 'playing' ||
        state.questionAnswerStatus === 'answered' ||
        state.isSubmitting ||
        state.currentAnswerer === null
      ) {
        return;
      }

      const currentQuestion = state.shuffledQuestions[state.currentQuestionIndex];
      if (!currentQuestion) {
        return;
      }

      dispatch({ type: 'SET_IS_SUBMITTING', value: true });

      try {
        const isCorrect = await judgeAnswerWithAI(
          currentQuestion.prompt,
          currentQuestion.correctAnswerText,
          answerText,
        );
        dispatch({ type: 'SUBMIT_ANSWER', submittedText: answerText, isCorrect });
      } catch {
        // AI 判定失敗時はテキスト正規化比較にフォールバック
        const isCorrect =
          normalizeAnswer(answerText) === normalizeAnswer(currentQuestion.correctAnswerText);
        dispatch({ type: 'SUBMIT_ANSWER', submittedText: answerText, isCorrect });
      } finally {
        dispatch({ type: 'SET_IS_SUBMITTING', value: false });
      }
    },
    [
      state.currentAnswerer,
      state.currentQuestionIndex,
      state.isSubmitting,
      state.phase,
      state.questionAnswerStatus,
      state.shuffledQuestions,
    ]
  );

  const proceedNext = useCallback(() => {
    if (state.phase !== 'playing' || state.questionAnswerStatus !== 'answered') {
      return;
    }

    const isLastQuestion = state.currentQuestionIndex >= state.shuffledQuestions.length - 1;
    if (isLastQuestion) {
      dispatch({ type: 'SHOW_RESULT', winner: computeWinner(state.scores) });
      return;
    }

    dispatch({ type: 'NEXT_QUESTION' });
  }, [
    state.currentQuestionIndex,
    state.phase,
    state.questionAnswerStatus,
    state.scores,
    state.shuffledQuestions.length,
  ]);

  const rematch = useCallback(() => {
    if (state.preparedQuestions.length === 0) {
      return;
    }

    dispatch({
      type: 'REMATCH',
      shuffledQuestions: shuffleQuestions(state.preparedQuestions),
    });
  }, [state.preparedQuestions]);

  const backToSelection = useCallback(() => {
    dispatch({ type: 'BACK_TO_SELECTION' });
  }, []);

  const currentQuestion = useMemo(() => {
    if (state.phase !== 'playing') {
      return null;
    }
    return state.shuffledQuestions[state.currentQuestionIndex] ?? null;
  }, [state.currentQuestionIndex, state.phase, state.shuffledQuestions]);

  const currentAnswerer = useMemo(() => {
    if (state.phase !== 'playing') {
      return null;
    }
    return state.currentAnswerer;
  }, [state.currentAnswerer, state.phase]);

  return {
    phase: state.phase,
    setItems: state.setItems,
    isLoadingSets: state.isLoadingSets,
    listError: state.listError,
    isPreparing: state.isPreparing,
    isStarting: state.isStarting,
    isSubmitting: state.isSubmitting,
    selectedSetId: state.selectedSetId,
    selectedSetName: state.selectedSetName,
    playerNames: state.playerNames,
    eligibleQuestionCount: state.eligibleQuestionCount,
    startBlockedMessage: state.startBlockedMessage,
    currentQuestion,
    currentQuestionNumber: state.currentQuestionIndex + 1,
    totalQuestions: state.shuffledQuestions.length,
    currentAnswerer,
    questionAnswerStatus: state.questionAnswerStatus,
    answerResult: state.answerResult,
    scores: state.scores,
    winner: state.winner,
    selectSet,
    updatePlayerName,
    startBattle,
    lockAnswerer,
    submitAnswer,
    proceedNext,
    rematch,
    backToSelection,
    refetchSets,
  };
}
