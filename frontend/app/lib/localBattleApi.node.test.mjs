import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getBattleReadySet,
  getQuizSets,
  NotFoundError,
  UpstreamError,
} from './localBattleApi.ts';

const originalFetch = globalThis.fetch;

test('getQuizSets は id/name/quiz_count を setId/setName/quizCount に変換する', async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        items: [{ id: 'set-1', name: 'セットA', quiz_count: 3 }],
      }),
      { status: 200 }
    );

  const items = await getQuizSets();

  assert.deepEqual(items, [{ setId: 'set-1', setName: 'セットA', quizCount: 3 }]);
});

test('getBattleReadySet は battle-ready 契約をフロント形式へ変換する', async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        set_id: 'set-1',
        set_name: 'セットA',
        total_item_count: 3,
        deleted_excluded_count: 1,
        active_item_count: 2,
        non_multiple_choice_excluded_count: 1,
        eligible_question_count: 1,
        startable: false,
        reason_code: 'NO_ELIGIBLE_QUESTIONS',
        questions: [
          {
            question_id: 'q-1',
            source_saved_quiz_id: 'saved-1',
            prompt: 'Q',
            correct_answer_text: '東京',
          },
        ],
      }),
      { status: 200 }
    );

  const ready = await getBattleReadySet('set-1');

  assert.equal(ready.setId, 'set-1');
  assert.equal(ready.reasonCode, 'NO_ELIGIBLE_QUESTIONS');
  assert.equal(ready.questions[0].questionId, 'q-1');
  assert.equal(ready.questions[0].correctAnswerText, '東京');
});

test('getBattleReadySet は 404 を NotFoundError として扱う', async () => {
  globalThis.fetch = async () => new Response('{}', { status: 404 });

  await assert.rejects(() => getBattleReadySet('missing'), NotFoundError);
});

test('getQuizSets は上位エラーを UpstreamError で返す', async () => {
  globalThis.fetch = async () => new Response('{}', { status: 502 });

  await assert.rejects(
    async () => {
      await getQuizSets();
    },
    (err) => err instanceof UpstreamError && err.status === 502
  );
});

test.after(() => {
  globalThis.fetch = originalFetch;
});
