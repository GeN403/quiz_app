/**
 * ローカル対戦 API クライアント
 */

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

export type StartBlockReasonCode = 'NO_ELIGIBLE_MULTIPLE_CHOICE';

export interface BattleReadySet {
  setId: string;
  setName: string;
  totalItemCount: number;
  deletedExcludedCount: number;
  activeItemCount: number;
  nonMultipleChoiceExcludedCount: number;
  eligibleQuestionCount: number;
  startable: boolean;
  reasonCode: StartBlockReasonCode | null;
  questions: BattleQuestion[];
}

interface RawQuizSetListResponse {
  items: Array<{
    id: string;
    name: string;
    quiz_count: number;
  }>;
}

interface RawBattleReadySet {
  set_id: string;
  set_name: string;
  total_item_count: number;
  deleted_excluded_count: number;
  active_item_count: number;
  non_multiple_choice_excluded_count: number;
  eligible_question_count: number;
  startable: boolean;
  reason_code: StartBlockReasonCode | null;
  questions: Array<{
    question_id: string;
    source_saved_quiz_id: string;
    prompt: string;
    choices: Array<{
      choice_id: string;
      text: string;
    }>;
    correct_choice_id: string;
  }>;
}

export class NotFoundError extends Error {
  constructor(id: string) {
    super(`クイズセットが見つかりません: ${id}`);
    this.name = 'NotFoundError';
  }
}

export class UpstreamError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'UpstreamError';
    this.status = status;
  }
}

function mapBattleSetListItem(data: {
  id: string;
  name: string;
  quiz_count: number;
}): BattleSetListItem {
  return {
    setId: data.id,
    setName: data.name,
    quizCount: data.quiz_count,
  };
}

function mapBattleReadySet(raw: RawBattleReadySet): BattleReadySet {
  return {
    setId: raw.set_id,
    setName: raw.set_name,
    totalItemCount: raw.total_item_count,
    deletedExcludedCount: raw.deleted_excluded_count,
    activeItemCount: raw.active_item_count,
    nonMultipleChoiceExcludedCount: raw.non_multiple_choice_excluded_count,
    eligibleQuestionCount: raw.eligible_question_count,
    startable: raw.startable,
    reasonCode: raw.reason_code,
    questions: raw.questions.map((question) => ({
      questionId: question.question_id,
      sourceSavedQuizId: question.source_saved_quiz_id,
      prompt: question.prompt,
      choices: question.choices.map((choice) => ({
        choiceId: choice.choice_id,
        text: choice.text,
      })),
      correctChoiceId: question.correct_choice_id,
    })),
  };
}

export async function getQuizSets(): Promise<BattleSetListItem[]> {
  const res = await fetch('/api/quiz-sets', { cache: 'no-store' });

  if (!res.ok) {
    throw new UpstreamError(res.status, `HTTP ${res.status}`);
  }

  const data: RawQuizSetListResponse = await res.json();
  return data.items.map(mapBattleSetListItem);
}

export async function getBattleReadySet(setId: string): Promise<BattleReadySet> {
  const res = await fetch(`/api/quiz-sets/${setId}/battle-ready`, { cache: 'no-store' });

  if (res.status === 404) {
    throw new NotFoundError(setId);
  }

  if (!res.ok) {
    throw new UpstreamError(res.status, `HTTP ${res.status}`);
  }

  const data: RawBattleReadySet = await res.json();
  return mapBattleReadySet(data);
}
