import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createInitialBattleState,
  computeWinner,
  localBattleReducer,
  mapHttpErrorStatus,
  mapReasonCode,
  validatePlayerNames,
} from './localBattleControllerCore.ts';

const questionA = {
  questionId: 'q1',
  sourceSavedQuizId: 'saved-1',
  prompt: 'Q1',
  choices: [
    { choiceId: 'a', text: 'A' },
    { choiceId: 'b', text: 'B' },
  ],
  correctChoiceId: 'a',
};

const questionB = {
  questionId: 'q2',
  sourceSavedQuizId: 'saved-2',
  prompt: 'Q2',
  choices: [
    { choiceId: 'c', text: 'C' },
    { choiceId: 'd', text: 'D' },
  ],
  correctChoiceId: 'd',
};

test('validatePlayerNames は空欄を開始不可にする', () => {
  assert.equal(validatePlayerNames('', 'P2'), 'プレイヤー1とプレイヤー2の名前を入力してください。');
  assert.equal(validatePlayerNames('P1', ''), 'プレイヤー1とプレイヤー2の名前を入力してください。');
  assert.equal(validatePlayerNames('P1', 'P2'), null);
});

test('mapReasonCode / mapHttpErrorStatus は reason_code と HTTP 系を分けて扱う', () => {
  assert.equal(mapReasonCode('NO_ELIGIBLE_MULTIPLE_CHOICE'), '対戦に使用可能な選択肢型クイズがありません。');
  assert.equal(mapHttpErrorStatus(404), 'クイズセットが見つかりません。');
  assert.equal(mapHttpErrorStatus(502), '通信エラーが発生しました。しばらくしてから再試行してください。');
});

test('LOCK_ANSWERER は未回答時に最初の入力だけ有効', () => {
  let state = createInitialBattleState();
  state = localBattleReducer(state, {
    type: 'START_PLAYING',
    preparedQuestions: [questionA],
    shuffledQuestions: [questionA],
  });

  state = localBattleReducer(state, { type: 'LOCK_ANSWERER', answerer: 'player1' });
  state = localBattleReducer(state, { type: 'LOCK_ANSWERER', answerer: 'player2' });

  assert.equal(state.currentAnswerer, 'player1');
});

test('submitAnswer は同一問題で 1 回のみ有効（再回答禁止）', () => {
  let state = createInitialBattleState();
  state = localBattleReducer(state, {
    type: 'START_PLAYING',
    preparedQuestions: [questionA],
    shuffledQuestions: [questionA],
  });

  state = localBattleReducer(state, { type: 'LOCK_ANSWERER', answerer: 'player1' });
  state = localBattleReducer(state, {
    type: 'SUBMIT_ANSWER',
    selectedChoiceId: 'a',
    isCorrect: true,
  });

  const afterFirst = state.scores.player1;

  state = localBattleReducer(state, {
    type: 'SUBMIT_ANSWER',
    selectedChoiceId: 'a',
    isCorrect: true,
  });

  assert.equal(afterFirst, 1);
  assert.equal(state.scores.player1, 1);
});

test('proceedNext 相当の遷移で全問完了時に winner を判定できる', () => {
  const winner = computeWinner({ player1: 1, player2: 0 });
  const draw = computeWinner({ player1: 1, player2: 1 });

  assert.equal(winner, 'player1');
  assert.equal(draw, 'draw');
});

test('REMATCH は名前を維持しつつスコアと進行を初期化する', () => {
  let state = createInitialBattleState();
  state = localBattleReducer(state, { type: 'SET_PLAYER_NAME', player: 'player1', name: 'A' });
  state = localBattleReducer(state, { type: 'SET_PLAYER_NAME', player: 'player2', name: 'B' });
  state = localBattleReducer(state, {
    type: 'START_PLAYING',
    preparedQuestions: [questionA, questionB],
    shuffledQuestions: [questionA, questionB],
  });
  state = localBattleReducer(state, { type: 'LOCK_ANSWERER', answerer: 'player1' });
  state = localBattleReducer(state, {
    type: 'SUBMIT_ANSWER',
    selectedChoiceId: 'a',
    isCorrect: true,
  });

  state = localBattleReducer(state, {
    type: 'REMATCH',
    shuffledQuestions: [questionB, questionA],
  });

  assert.equal(state.playerNames.player1, 'A');
  assert.equal(state.playerNames.player2, 'B');
  assert.equal(state.scores.player1, 0);
  assert.equal(state.currentQuestionIndex, 0);
  assert.equal(state.currentAnswerer, null);
  assert.equal(state.shuffledQuestions[0].questionId, 'q2');
});

test('START_PLAYING はスコアを 0-0 で初期化して playing へ遷移する', () => {
  let state = createInitialBattleState();
  state = localBattleReducer(state, {
    type: 'SET_PLAYER_NAME',
    player: 'player1',
    name: 'P1',
  });
  state = localBattleReducer(state, {
    type: 'SET_PLAYER_NAME',
    player: 'player2',
    name: 'P2',
  });
  state = localBattleReducer(state, {
    type: 'START_PLAYING',
    preparedQuestions: [questionA, questionB],
    shuffledQuestions: [questionA, questionB],
  });

  assert.equal(state.phase, 'playing');
  assert.equal(state.scores.player1, 0);
  assert.equal(state.scores.player2, 0);
  assert.equal(state.currentQuestionIndex, 0);
  assert.equal(state.currentAnswerer, null);
  assert.equal(state.questionAnswerStatus, 'unanswered');
});

test('通し遷移: 早押し→回答→次へ→結果→再戦で仕様どおりに遷移する', () => {
  let state = createInitialBattleState();
  state = localBattleReducer(state, {
    type: 'START_PLAYING',
    preparedQuestions: [questionA, questionB],
    shuffledQuestions: [questionA, questionB],
  });

  state = localBattleReducer(state, { type: 'LOCK_ANSWERER', answerer: 'player1' });
  state = localBattleReducer(state, {
    type: 'SUBMIT_ANSWER',
    selectedChoiceId: 'a',
    isCorrect: true,
  });
  state = localBattleReducer(state, { type: 'NEXT_QUESTION' });

  state = localBattleReducer(state, { type: 'LOCK_ANSWERER', answerer: 'player2' });
  state = localBattleReducer(state, {
    type: 'SUBMIT_ANSWER',
    selectedChoiceId: 'd',
    isCorrect: true,
  });
  state = localBattleReducer(state, {
    type: 'SHOW_RESULT',
    winner: computeWinner(state.scores),
  });

  assert.equal(state.phase, 'result');
  assert.equal(state.scores.player1, 1);
  assert.equal(state.scores.player2, 1);
  assert.equal(state.winner, 'draw');

  state = localBattleReducer(state, {
    type: 'REMATCH',
    shuffledQuestions: [questionB, questionA],
  });

  assert.equal(state.phase, 'playing');
  assert.equal(state.currentQuestionIndex, 0);
  assert.equal(state.currentAnswerer, null);
  assert.equal(state.scores.player1, 0);
  assert.equal(state.scores.player2, 0);
  assert.equal(state.shuffledQuestions[0].questionId, 'q2');
});
