"use client";

import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
} from "@mui/material";
import { DIFFICULTY_OPTIONS, LENGTH_OPTIONS } from "../../app/lib/constants";

export type Difficulty = (typeof DIFFICULTY_OPTIONS)[number] | "";
export type QuizLength = (typeof LENGTH_OPTIONS)[number] | "";

export interface QuizOptionsFieldsProps {
  questionCount: number;
  onQuestionCountChange: (value: number) => void;
  difficulty: Difficulty;
  onDifficultyChange: (value: Difficulty) => void;
  length: QuizLength;
  onLengthChange: (value: QuizLength) => void;
  disabled?: boolean;
}

const DIFFICULTY_LABELS: Record<(typeof DIFFICULTY_OPTIONS)[number], string> = {
  easy: "かんたん",
  normal: "ふつう",
  hard: "むずかしい",
};

const LENGTH_LABELS: Record<(typeof LENGTH_OPTIONS)[number], string> = {
  short: "短い（40文字以内）",
  medium: "ふつう（80文字以内）",
  long: "長い（150文字以内）",
};

export function QuizOptionsFields({
  questionCount,
  onQuestionCountChange,
  difficulty,
  onDifficultyChange,
  length,
  onLengthChange,
  disabled,
}: QuizOptionsFieldsProps) {
  return (
    <>
      <TextField
        label="問題数"
        value={String(questionCount)}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (!Number.isNaN(n) && n >= 1 && n <= 5) {
            onQuestionCountChange(n);
          }
        }}
        disabled={disabled}
        helperText="1〜5問まで指定可能"
        sx={{ width: "200px" }}
      />

      <FormControl fullWidth>
        <InputLabel id="tab-difficulty-label">難易度（任意）</InputLabel>
        <Select
          labelId="tab-difficulty-label"
          value={difficulty}
          label="難易度（任意）"
          onChange={(e) => onDifficultyChange(e.target.value as Difficulty)}
          disabled={disabled}
        >
          <MenuItem value="">未指定</MenuItem>
          {DIFFICULTY_OPTIONS.map((opt) => (
            <MenuItem key={opt} value={opt}>
              {DIFFICULTY_LABELS[opt]}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <FormControl fullWidth>
        <InputLabel id="tab-length-label">問題文の長さ（任意）</InputLabel>
        <Select
          labelId="tab-length-label"
          value={length}
          label="問題文の長さ（任意）"
          onChange={(e) => onLengthChange(e.target.value as QuizLength)}
          disabled={disabled}
        >
          <MenuItem value="">未指定</MenuItem>
          {LENGTH_OPTIONS.map((opt) => (
            <MenuItem key={opt} value={opt}>
              {LENGTH_LABELS[opt]}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </>
  );
}
