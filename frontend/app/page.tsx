// app/page.tsx

"use client";

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
  FormHelperText,
} from "@mui/material";
import { CATEGORIES, MAX_ANSWER_LENGTH, TOPIC_MAX_LENGTH } from "./lib/constants";
import { useQuizGeneration } from "./hooks/useQuizGeneration";
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

        {/* カテゴリ選択 */}
        <FormControl fullWidth>
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

        {/* 生成オプション */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          <Typography variant="subtitle2" color="text.secondary">
            生成オプション（任意）
          </Typography>

          {/* URL指定 */}
          <TextField
            label="URL指定（任意）"
            placeholder="https://kotobank.jp/..."
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            disabled={isLoading}
            helperText="未入力の場合、選択したジャンルから参照URLを自動選択します（コトバンク、*.go.jp、*.ac.jp のみ許可）"
            fullWidth
          />

          {/* 本文を取得ボタン */}
          <Button
            variant="outlined"
            onClick={handleResolveSource}
            disabled={isLoading || !sourceUrl.trim()}
            fullWidth
          >
            {isLoading ? "取得中..." : "本文を取得"}
          </Button>

          {/* 取得結果の表示 */}
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
            </Box>
          )}

          {/* 問題数指定 */}
          <TextField
            label="問題数"
            type="number"
            value={questionCount}
            onChange={(e) => {
              const val = parseInt(e.target.value);
              if (val >= 1 && val <= 5) {
                setQuestionCount(val);
              }
            }}
            disabled={isLoading}
            inputProps={{ min: 1, max: 5 }}
            helperText="1〜5問まで指定可能"
            sx={{ width: "200px" }}
          />

          {/* 難易度セレクタ（Approach B: 未指定選択肢あり） */}
          <FormControl fullWidth error={Boolean(fieldErrors.difficulty)}>
            <InputLabel id="difficulty-select-label">難易度（任意）</InputLabel>
            <Select
              labelId="difficulty-select-label"
              id="difficulty-select"
              value={difficulty}
              label="難易度（任意）"
              onChange={(e) => setDifficulty(e.target.value)}
              disabled={isLoading}
            >
              <MenuItem value="">未指定</MenuItem>
              <MenuItem value="easy">かんたん</MenuItem>
              <MenuItem value="normal">ふつう</MenuItem>
              <MenuItem value="hard">むずかしい</MenuItem>
            </Select>
            {fieldErrors.difficulty && (
              <FormHelperText>{fieldErrors.difficulty}</FormHelperText>
            )}
          </FormControl>

          {/* 問題文の長さセレクタ（Approach B: 未指定選択肢あり） */}
          <FormControl fullWidth error={Boolean(fieldErrors.length)}>
            <InputLabel id="length-select-label">問題文の長さ（任意）</InputLabel>
            <Select
              labelId="length-select-label"
              id="length-select"
              value={length}
              label="問題文の長さ（任意）"
              onChange={(e) => setLength(e.target.value)}
              disabled={isLoading}
            >
              <MenuItem value="">未指定</MenuItem>
              <MenuItem value="short">短い（40文字以内）</MenuItem>
              <MenuItem value="medium">ふつう（80文字以内）</MenuItem>
              <MenuItem value="long">長い（150文字以内）</MenuItem>
            </Select>
            {fieldErrors.length && (
              <FormHelperText>{fieldErrors.length}</FormHelperText>
            )}
          </FormControl>

          {/* ジャンルセレクタ */}
          <FormControl fullWidth error={Boolean(fieldErrors.genre)}>
            <InputLabel id="genre-select-label">ジャンル（任意）</InputLabel>
            <Select
              labelId="genre-select-label"
              id="genre-select"
              value={genre}
              label="ジャンル（任意）"
              onChange={(e) => setGenre(e.target.value)}
              disabled={isLoading}
            >
              <MenuItem value="">未指定</MenuItem>
              {CATEGORIES.map((cat) => (
                <MenuItem key={cat.value} value={cat.label}>
                  {cat.label}
                </MenuItem>
              ))}
            </Select>
            {fieldErrors.genre && (
              <FormHelperText>{fieldErrors.genre}</FormHelperText>
            )}
          </FormControl>

          {/* トピック入力（自由記述） */}
          <TextField
            label="トピック（任意）"
            placeholder="例: 富士山、相対性理論（本文内の情報に限定して出題されます）"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            disabled={isLoading}
            error={Boolean(fieldErrors.topic)}
            helperText={
              fieldErrors.topic
                ? fieldErrors.topic
                : `${topic.trim().length}/${TOPIC_MAX_LENGTH}文字`
            }
            fullWidth
          />
        </Box>

        {/* 生成ボタン */}
        <Button
          variant="contained"
          size="large"
          onClick={handleGenerate}
          disabled={isLoading || !category}
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
              onClick={handleGenerate}
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

          {/* 回答入力エリア */}
          {judgmentResult === null && (
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

          {/* 正解例と解説（判定後に自動表示） */}
          {judgmentResult !== null && (
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
