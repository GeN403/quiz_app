// app/page.tsx

"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { CATEGORIES, MAX_ANSWER_LENGTH } from "./lib/constants";
import { useQuizGeneration } from "./hooks/useQuizGeneration";
import { type TabGenerateRequest } from "./lib/tabGenerate";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import {
  QuizOptionsFields,
  type Difficulty,
  type QuizLength,
} from "../components/quiz/QuizOptionsFields";
import { SaveButton } from "./components/SaveButton";
import type { GenerationInputParams } from "./lib/savedQuizzesApi";

type InputMode = "category" | "url" | "keyword";

type TabOptions = {
  questionCount: number;
  difficulty: Difficulty;
  length: QuizLength;
};

const DEFAULT_TAB_OPTIONS: TabOptions = {
  questionCount: 1,
  difficulty: "",
  length: "",
};

export default function Home() {
  const [inputMode, setInputMode] = useState<InputMode>("category");
  const [keyword, setKeyword] = useState<string>("");
  const [tabOptions, setTabOptions] = useState<Record<InputMode, TabOptions>>({
    category: { ...DEFAULT_TAB_OPTIONS },
    url: { ...DEFAULT_TAB_OPTIONS },
    keyword: { ...DEFAULT_TAB_OPTIONS },
  });

  const updateTabOption = (mode: InputMode, patch: Partial<TabOptions>) => {
    setTabOptions((prev) => ({
      ...prev,
      [mode]: { ...prev[mode], ...patch },
    }));
  };

  const {
    category,
    setCategory,
    sourceUrl,
    setSourceUrl,
    questionCount,
    setQuestionCount,
    difficulty,
    setDifficulty,
    length,
    setLength,
    genre,
    setGenre,
    topic,
    setTopic,
    fieldErrors,
    quiz,
    questions,
    currentQuestionIndex,
    answerPackage,
    lastInputParams,
    resolvedSource,
    selectedQuote,
    setSelectedQuote,
    isLoading,
    error,
    setError,
    userAnswer,
    setUserAnswer,
    judgmentResult,
    showAnswer,
    showHistory,
    setShowHistory,
    history,
    handleResolveSource,
    handleGenerate,
    handleSubmitAnswer,
    handleRevealAnswer,
    handleClearHistory,
    handlePreviousQuestion,
    handleNextQuestion,
  } = useQuizGeneration();

  return (
    <Box
      component="main"
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        minHeight: "100vh",
        padding: 4,
        gap: 2,
        backgroundColor: "#f5f5f5",
      }}
    >
      <Typography variant="h4" component="h1" gutterBottom>
        クイズ自動生成プロトタイプ
      </Typography>
      <Box sx={{ width: "100%", maxWidth: "700px", display: "flex", justifyContent: "flex-end", gap: 1 }}>
        <Link href="/saved-quizzes" passHref>
          <Button variant="outlined" size="small">Saved Quizzes</Button>
        </Link>
        <Link href="/quiz-sets" passHref>
          <Button variant="outlined" size="small">Quiz Sets</Button>
        </Link>
        <Link href="/local-battle" passHref>
          <Button variant="outlined" size="small">Local Battle</Button>
        </Link>
      </Box>

      {/* --- カテゴリ選択エリア --- */}
      <Paper
        sx={{
          p: 3,
          width: "100%",
          maxWidth: "700px",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        <Typography variant="h6" component="h2">
          クイズ生成
        </Typography>

        {/* --- 入力モード タブ (PR1: 構造のみ。結線は後続 PR) --- */}
        <Tabs
          value={inputMode}
          onValueChange={(v) => setInputMode(v as InputMode)}
        >
          <TabsList>
            <TabsTrigger value="category">カテゴリ</TabsTrigger>
            <TabsTrigger value="url">URL</TabsTrigger>
            <TabsTrigger value="keyword">キーワード</TabsTrigger>
          </TabsList>
          <TabsContent value="category">
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel id="category-select-label">カテゴリ</InputLabel>
              <Select
                labelId="category-select-label"
                id="category-select"
                value={category}
                label="カテゴリ"
                onChange={(e) => setCategory(e.target.value)}
                disabled={isLoading}
              >
                {CATEGORIES.map((cat) => (
                  <MenuItem key={cat.value} value={cat.value}>
                    {cat.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <QuizOptionsFields
              questionCount={tabOptions.category.questionCount}
              onQuestionCountChange={(v) => updateTabOption("category", { questionCount: v })}
              difficulty={tabOptions.category.difficulty}
              onDifficultyChange={(v) => updateTabOption("category", { difficulty: v })}
              length={tabOptions.category.length}
              onLengthChange={(v) => updateTabOption("category", { length: v })}
              disabled={isLoading}
            />
          </TabsContent>
          <TabsContent value="url">
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mb: 2 }}>
              <TextField
                label="URL"
                placeholder="https://kotobank.jp/..."
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                disabled={isLoading}
                fullWidth
              />
              <Button
                variant="outlined"
                onClick={handleResolveSource}
                disabled={isLoading || !sourceUrl.trim()}
                fullWidth
              >
                {isLoading ? "取得中..." : "本文を取得"}
              </Button>
              {resolvedSource && (
                <Box sx={{ p: 2, bgcolor: "#e8f5e9", borderRadius: 1 }}>
                  <Typography variant="subtitle2" color="success.main" gutterBottom>
                    ✓ 本文を取得しました
                  </Typography>
                  <Typography variant="caption" display="block">
                    タイトル: {resolvedSource.title}
                  </Typography>
                  <Typography variant="caption" display="block">
                    引用候補: {resolvedSource.quotes.length}件
                  </Typography>
                  {resolvedSource.quotes.length > 0 && (
                    <FormControl fullWidth sx={{ mt: 1 }}>
                      <InputLabel id="quote-select-label">引用候補</InputLabel>
                      <Select
                        labelId="quote-select-label"
                        value={selectedQuote}
                        label="引用候補"
                        onChange={(e) => setSelectedQuote(e.target.value)}
                        disabled={isLoading}
                      >
                        {resolvedSource.quotes.map((q, i) => (
                          <MenuItem key={i} value={q}>
                            {q.length > 60 ? q.slice(0, 60) + "…" : q}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}
                </Box>
              )}
            </Box>
            <QuizOptionsFields
              questionCount={tabOptions.url.questionCount}
              onQuestionCountChange={(v) => updateTabOption("url", { questionCount: v })}
              difficulty={tabOptions.url.difficulty}
              onDifficultyChange={(v) => updateTabOption("url", { difficulty: v })}
              length={tabOptions.url.length}
              onLengthChange={(v) => updateTabOption("url", { length: v })}
              disabled={isLoading}
            />
          </TabsContent>
          <TabsContent value="keyword">
            <Box sx={{ mb: 2 }}>
              <TextField
                label="キーワード"
                placeholder="例: 富士山、相対性理論"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                disabled={isLoading}
                fullWidth
              />
            </Box>
            <QuizOptionsFields
              questionCount={tabOptions.keyword.questionCount}
              onQuestionCountChange={(v) => updateTabOption("keyword", { questionCount: v })}
              difficulty={tabOptions.keyword.difficulty}
              onDifficultyChange={(v) => updateTabOption("keyword", { difficulty: v })}
              length={tabOptions.keyword.length}
              onLengthChange={(v) => updateTabOption("keyword", { length: v })}
              disabled={isLoading}
            />
          </TabsContent>
        </Tabs>

        {/* 生成ボタン */}
        <Button
          variant="contained"
          size="large"
          onClick={() => {
            const activeOptions = tabOptions[inputMode];
            const request: TabGenerateRequest =
              inputMode === "category"
                ? { mode: "category", options: activeOptions }
                : inputMode === "url"
                  ? { mode: "url", options: activeOptions }
                  : { mode: "keyword", keyword, options: activeOptions };
            handleGenerate(request);
          }}
          disabled={
            inputMode === "category"
              ? isLoading || !category
              : inputMode === "url"
                ? isLoading || !sourceUrl.trim()
                : isLoading || !keyword.trim()
          }
          fullWidth
          sx={{ mt: 2 }}
        >
          {isLoading ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={20} color="inherit" />
              <span>生成中...</span>
            </Box>
          ) : (
            "生成"
          )}
        </Button>
      </Paper>

      {/* --- 履歴表示ボタン --- */}
      <Button
        variant="outlined"
        onClick={() => setShowHistory(!showHistory)}
        sx={{ alignSelf: "flex-start", ml: "auto", mr: "auto", maxWidth: "700px" }}
      >
        {showHistory ? "履歴を隠す" : `履歴を見る (${history.length}件)`}
      </Button>

      {/* --- 履歴表示エリア --- */}
      {showHistory && (
        <Paper
          elevation={2}
          sx={{
            p: 3,
            width: "100%",
            maxWidth: "700px",
          }}
        >
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6" component="h2">
              回答履歴
            </Typography>
            {history.length > 0 && (
              <Button
                variant="text"
                color="error"
                size="small"
                onClick={handleClearHistory}
              >
                履歴をクリア
              </Button>
            )}
          </Box>

          {history.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              まだ履歴がありません。クイズに挑戦してみましょう！
            </Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {history.map((entry) => (
                <Paper
                  key={entry.id}
                  variant="outlined"
                  sx={{
                    p: 2,
                    backgroundColor: entry.isCorrect ? "#f1f8f4" : "#fef5f5",
                    borderColor: entry.isCorrect ? "#4caf50" : "#f44336",
                  }}
                >
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(entry.timestamp).toLocaleString("ja-JP")}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        color: entry.isCorrect ? "success.main" : "error.main",
                        fontWeight: "bold",
                      }}
                    >
                      {entry.categoryLabel} - {entry.isCorrect ? "正解" : "不正解"}
                    </Typography>
                  </Box>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: "bold" }}>
                    問題: {entry.question}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    あなたの回答: {entry.userAnswer}
                  </Typography>
                  {!entry.isCorrect && (
                    <Typography variant="body2" color="success.dark" sx={{ mt: 0.5 }}>
                      正解: {entry.correctAnswer}
                    </Typography>
                  )}
                </Paper>
              ))}
            </Box>
          )}
        </Paper>
      )}

      {/* --- エラー表示エリア --- */}
      {error && (
        <Alert
          severity="error"
          sx={{
            width: "100%",
            maxWidth: "700px",
            whiteSpace: "pre-wrap",
          }}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => {
                const activeOptions = tabOptions[inputMode];
                const request: TabGenerateRequest =
                  inputMode === "category"
                    ? { mode: "category", options: activeOptions }
                    : inputMode === "url"
                      ? { mode: "url", options: activeOptions }
                      : { mode: "keyword", keyword, options: activeOptions };
                handleGenerate(request);
              }}
              disabled={isLoading}
            >
              再試行
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {/* --- クイズ表示エリア --- */}
      {quiz && (
        <Paper
          elevation={3}
          sx={{
            p: 3,
            mt: 2,
            width: "100%",
            maxWidth: "700px",
            "& > *": { mb: 2 },
          }}
        >
          {/* 複数問の場合の進捗表示 */}
          {questions.length > 1 && (
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">
                問題 {currentQuestionIndex + 1} / {questions.length}
              </Typography>
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  size="small"
                  onClick={handlePreviousQuestion}
                  disabled={currentQuestionIndex === 0}
                >
                  前へ
                </Button>
                <Button
                  size="small"
                  onClick={handleNextQuestion}
                  disabled={currentQuestionIndex === questions.length - 1}
                >
                  次へ
                </Button>
              </Box>
            </Box>
          )}

          {/* 問題文 */}
          <Typography variant="h5" component="h2" sx={{ fontWeight: "bold", color: "primary.main" }}>
            問題文
          </Typography>
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              backgroundColor: "#f9f9f9",
            }}
          >
            <Typography
              variant="body1"
              sx={{ fontSize: "1.2rem", whiteSpace: "pre-wrap", lineHeight: 1.8 }}
            >
              {quiz.question}
            </Typography>
          </Paper>
          <Box sx={{ mt: 2 }}>
            <SaveButton
              answerPackage={answerPackage}
              inputParams={lastInputParams as GenerationInputParams | null}
            />
          </Box>

          {/* 回答入力エリア */}
          {judgmentResult === null && !showAnswer && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
                <TextField
                  id="answer-input"
                  label="あなたの回答"
                  variant="outlined"
                  fullWidth
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter" && !isLoading) {
                      handleSubmitAnswer();
                    }
                  }}
                  placeholder="回答を入力してください"
                  disabled={isLoading}
                  inputProps={{ maxLength: MAX_ANSWER_LENGTH }}
                  helperText={`${userAnswer.length}/${MAX_ANSWER_LENGTH}文字`}
                  error={userAnswer.length > MAX_ANSWER_LENGTH}
                />
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleSubmitAnswer}
                  disabled={isLoading}
                  sx={{ whiteSpace: "nowrap", minWidth: "100px" }}
                >
                  回答する
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={handleRevealAnswer}
                  disabled={isLoading}
                  sx={{ whiteSpace: "nowrap", minWidth: "150px" }}
                >
                  回答せずに見る
                </Button>
              </Box>
            </Box>
          )}

          {/* 判定結果表示 */}
          {judgmentResult !== null && (
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                mt: 2,
                backgroundColor: judgmentResult === "correct" ? "#e8f5e9" : "#ffebee",
                borderColor: judgmentResult === "correct" ? "#4caf50" : "#f44336",
                borderWidth: 2,
              }}
            >
              <Typography
                variant="h6"
                sx={{
                  fontWeight: "bold",
                  color: judgmentResult === "correct" ? "success.dark" : "error.dark",
                }}
              >
                {judgmentResult === "correct" ? "正解！" : "不正解"}
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                あなたの回答: {userAnswer}
              </Typography>
            </Paper>
          )}

          {/* 正解例と解説（判定後、または回答スキップ時に表示） */}
          {(judgmentResult !== null || showAnswer) && (
            <>
              {/* 想定解答（正解例） */}
              <Typography variant="h6" component="h3" sx={{ mt: 2, fontWeight: "bold" }}>
                想定解答（正解例）
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  backgroundColor: "#e8f5e9",
                }}
              >
                <Typography variant="body1" sx={{ fontSize: "1.1rem", color: "success.dark", fontWeight: "bold" }}>
                  {quiz.answer}
                </Typography>
              </Paper>

              {/* 別解 */}
              <Typography variant="h6" component="h3" sx={{ mt: 2 }}>
                別解/正誤判定基準
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {quiz["Alternative Solutions/Correctness Judgment Criteria"]}
              </Typography>

              {/* 解説 */}
              <Typography variant="h6" component="h3" sx={{ mt: 2 }}>
                解説
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {quiz.explanation}
              </Typography>

              {/* 出典 */}
              <Typography variant="h6" component="h3" sx={{ mt: 2 }}>
                出典
              </Typography>
              <Typography variant="body2">
                <a href={quiz.source.url} target="_blank" rel="noopener noreferrer">
                  {quiz.source.title}
                </a>
              </Typography>
            </>
          )}
        </Paper>
      )}
    </Box>
  );
}
