export type TabGenerateOptions = {
  questionCount: number;
  difficulty: string;
  length: string;
};

export type TabGenerateRequest =
  | { mode: "category"; options: TabGenerateOptions }
  | { mode: "url"; options: TabGenerateOptions }
  | { mode: "keyword"; keyword: string; options: TabGenerateOptions };

export const DEFAULT_CATEGORY = "non_section" as const;
