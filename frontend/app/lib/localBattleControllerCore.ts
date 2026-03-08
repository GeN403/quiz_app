export type BattlePhase = 'set_selection' | 'player_setup' | 'playing' | 'result';
export type PlayerSlot = 'player1' | 'player2';
export type QuestionAnswerStatus = 'unanswered' | 'answered';
export type StartBlockReasonCode = 'NO_ELIGIBLE_MULTIPLE_CHOICE';

export interface BattleSetListItem {
  setId: string;
  setName: string;
  quizCount: number;
}

export interface BattleChoice {
  choiceId: string;
  text: string;
}

export interface BattleQuestion {
  questionId: string;
  sourceSavedQuizId: string;
  prompt: string;
  choices: BattleChoice[];
  correctChoiceId: string;
}

export interface AnswerResult {
  selectedChoiceId: string;
  isCorrect: boolean;
}

export interface BattleState {
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
  preparedQuestions: BattleQuestion[];
  shuffledQuestions: BattleQuestion[];
  currentQuestionIndex: number;
  questionAnswerStatus: QuestionAnswerStatus;
  answerResult: AnswerResult | null;
  scores: Record<PlayerSlot, number>;
  winner: PlayerSlot | 'draw' | null;
}

export type BattleAction =
  | { type: 'LOAD_SETS_START' }
  | { type: 'LOAD_SETS_SUCCESS'; items: BattleSetListItem[] }
  | { type: 'LOAD_SETS_FAILURE'; message: string }
  | { type: 'SELECT_SET'; setId: string; setName: string }
  | {
      type: 'SET_PREVIEW_RESULT';
      eligibleQuestionCount: number;
      startBlockedMessage: string | null;
    }
  | { type: 'SET_START_BLOCKED_MESSAGE'; message: string | null }
  | { type: 'SET_PLAYER_NAME'; player: PlayerSlot; name: string }
  | { type: 'SET_IS_PREPARING'; value: boolean }
  | { type: 'SET_IS_STARTING'; value: boolean }
  | { type: 'SET_IS_SUBMITTING'; value: boolean }
  | {
      type: 'START_PLAYING';
      preparedQuestions: BattleQuestion[];
      shuffledQuestions: BattleQuestion[];
    }
  | {
      type: 'SUBMIT_ANSWER';
      selectedChoiceId: string;
      isCorrect: boolean;
      answerer: PlayerSlot;
    }
  | { type: 'NEXT_QUESTION' }
  | { type: 'SHOW_RESULT'; winner: PlayerSlot | 'draw' }
  | { type: 'REMATCH'; shuffledQuestions: BattleQuestion[] }
  | { type: 'BACK_TO_SELECTION' };

export function createInitialBattleState(): BattleState {
  return {
    phase: 'set_selection',
    setItems: [],
    isLoadingSets: false,
    listError: null,
    isPreparing: false,
    isStarting: false,
    isSubmitting: false,
    selectedSetId: null,
    selectedSetName: null,
    playerNames: {
      player1: '',
      player2: '',
    },
    eligibleQuestionCount: 0,
    startBlockedMessage: null,
    preparedQuestions: [],
    shuffledQuestions: [],
    currentQuestionIndex: 0,
    questionAnswerStatus: 'unanswered',
    answerResult: null,
    scores: {
      player1: 0,
      player2: 0,
    },
    winner: null,
  };
}

export function localBattleReducer(state: BattleState, action: BattleAction): BattleState {
  switch (action.type) {
    case 'LOAD_SETS_START':
      return { ...state, isLoadingSets: true, listError: null };
    case 'LOAD_SETS_SUCCESS':
      return { ...state, isLoadingSets: false, setItems: action.items, listError: null };
    case 'LOAD_SETS_FAILURE':
      return { ...state, isLoadingSets: false, listError: action.message };
    case 'SELECT_SET':
      return {
        ...state,
        phase: 'player_setup',
        selectedSetId: action.setId,
        selectedSetName: action.setName,
        eligibleQuestionCount: 0,
        startBlockedMessage: null,
      };
    case 'SET_PREVIEW_RESULT':
      return {
        ...state,
        eligibleQuestionCount: action.eligibleQuestionCount,
        startBlockedMessage: action.startBlockedMessage,
      };
    case 'SET_START_BLOCKED_MESSAGE':
      return { ...state, startBlockedMessage: action.message };
    case 'SET_PLAYER_NAME':
      return {
        ...state,
        playerNames: {
          ...state.playerNames,
          [action.player]: action.name,
        },
      };
    case 'SET_IS_PREPARING':
      return { ...state, isPreparing: action.value };
    case 'SET_IS_STARTING':
      return { ...state, isStarting: action.value };
    case 'SET_IS_SUBMITTING':
      return { ...state, isSubmitting: action.value };
    case 'START_PLAYING':
      return {
        ...state,
        phase: 'playing',
        startBlockedMessage: null,
        preparedQuestions: action.preparedQuestions,
        shuffledQuestions: action.shuffledQuestions,
        currentQuestionIndex: 0,
        questionAnswerStatus: 'unanswered',
        answerResult: null,
        scores: { player1: 0, player2: 0 },
        winner: null,
      };
    case 'SUBMIT_ANSWER': {
      if (state.phase !== 'playing' || state.questionAnswerStatus === 'answered') {
        return state;
      }

      const nextScores = { ...state.scores };
      if (action.isCorrect) {
        nextScores[action.answerer] += 1;
      }

      return {
        ...state,
        questionAnswerStatus: 'answered',
        answerResult: {
          selectedChoiceId: action.selectedChoiceId,
          isCorrect: action.isCorrect,
        },
        scores: nextScores,
      };
    }
    case 'NEXT_QUESTION':
      return {
        ...state,
        currentQuestionIndex: state.currentQuestionIndex + 1,
        questionAnswerStatus: 'unanswered',
        answerResult: null,
      };
    case 'SHOW_RESULT':
      return {
        ...state,
        phase: 'result',
        winner: action.winner,
      };
    case 'REMATCH':
      return {
        ...state,
        phase: 'playing',
        shuffledQuestions: action.shuffledQuestions,
        currentQuestionIndex: 0,
        questionAnswerStatus: 'unanswered',
        answerResult: null,
        scores: { player1: 0, player2: 0 },
        winner: null,
        startBlockedMessage: null,
      };
    case 'BACK_TO_SELECTION':
      return {
        ...state,
        phase: 'set_selection',
        selectedSetId: null,
        selectedSetName: null,
        eligibleQuestionCount: 0,
        startBlockedMessage: null,
        preparedQuestions: [],
        shuffledQuestions: [],
        currentQuestionIndex: 0,
        questionAnswerStatus: 'unanswered',
        answerResult: null,
        scores: { player1: 0, player2: 0 },
        winner: null,
      };
    default:
      return state;
  }
}

export function shuffleQuestions(questions: BattleQuestion[]): BattleQuestion[] {
  const copied = [...questions];
  for (let i = copied.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copied[i], copied[j]] = [copied[j], copied[i]];
  }
  return copied;
}

export function getCurrentAnswerer(index: number): PlayerSlot {
  return index % 2 === 0 ? 'player1' : 'player2';
}

export function validatePlayerNames(player1: string, player2: string): string | null {
  if (!player1.trim() || !player2.trim()) {
    return 'プレイヤー1とプレイヤー2の名前を入力してください。';
  }
  return null;
}

export function mapReasonCode(reasonCode: StartBlockReasonCode | null): string {
  if (reasonCode === 'NO_ELIGIBLE_MULTIPLE_CHOICE') {
    return '対戦に使用可能な選択肢型クイズがありません。';
  }
  return '対戦を開始できません。';
}

export function mapHttpErrorStatus(status: number): string {
  if (status === 404) {
    return 'クイズセットが見つかりません。';
  }
  if (status === 502) {
    return '通信エラーが発生しました。しばらくしてから再試行してください。';
  }
  return `通信エラーが発生しました。(HTTP ${status})`;
}

export function mapUnknownStartError(): string {
  return '対戦準備中にエラーが発生しました。';
}

export function computeWinner(scores: Record<PlayerSlot, number>): PlayerSlot | 'draw' {
  if (scores.player1 > scores.player2) {
    return 'player1';
  }
  if (scores.player2 > scores.player1) {
    return 'player2';
  }
  return 'draw';
}
