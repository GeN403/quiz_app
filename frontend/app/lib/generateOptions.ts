import { CATEGORIES, DIFFICULTY_OPTIONS, LENGTH_OPTIONS, TOPIC_MAX_LENGTH } from "./constants";
import {
  GenerateQuizFieldErrors,
  GenerateQuizOptionalFields,
  buildOptionalGeneratePayload,
} from "./api";

const ALLOWED_GENRES: readonly string[] = CATEGORIES.map((category) => category.label);

const hasText = (value?: string): boolean => {
  return typeof value === "string" && value.trim().length > 0;
};

export function validateGenerateOptionalFields(
  fields: GenerateQuizOptionalFields
): {
  errors: GenerateQuizFieldErrors;
  payload: GenerateQuizOptionalFields;
} {
  const errors: GenerateQuizFieldErrors = {};
  const normalized = buildOptionalGeneratePayload(fields);

  if (
    hasText(fields.difficulty) &&
    !DIFFICULTY_OPTIONS.includes(normalized.difficulty as (typeof DIFFICULTY_OPTIONS)[number])
  ) {
    errors.difficulty = "難易度が不正です。未指定または選択肢から選び直してください。";
  }

  if (
    hasText(fields.length) &&
    !LENGTH_OPTIONS.includes(normalized.length as (typeof LENGTH_OPTIONS)[number])
  ) {
    errors.length = "問題文の長さが不正です。未指定または選択肢から選び直してください。";
  }

  if (hasText(fields.genre) && !ALLOWED_GENRES.includes(normalized.genre || "")) {
    errors.genre = "ジャンルが不正です。未指定または選択肢から選び直してください。";
  }

  if (/[\r\n]/.test(normalized.topic || "")) {
    errors.topic = "トピックは改行せず1行で入力してください。";
  } else if ((normalized.topic || "").length > TOPIC_MAX_LENGTH) {
    errors.topic = `トピックは${TOPIC_MAX_LENGTH}文字以内で入力してください。`;
  }

  return {
    errors,
    payload: normalized,
  };
}
