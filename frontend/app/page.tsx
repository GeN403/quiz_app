// app/page.tsx

"use client";

import { useState, useEffect } from "react"; // useStateとuseEffectをインポート
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  CircularProgress, // ローディングスピナー用
  Collapse, // アコーディオン用
  Alert, // エラー表示用
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";

// AIから返ってくるJSONの型を定義
interface QuizData {
  question: string;
  answer: string;
  "Alternative Solutions/Correctness Judgment Criteria": string;
  explanation: string;
  source: {
    title: string;
    url: string;
  };
}

// 履歴データの型を定義
interface QuizHistory {
  id: string; // 一意のID
  category: string; // カテゴリ
  categoryLabel: string; // カテゴリの日本語名
  question: string; // 問題文
  correctAnswer: string; // 想定解答
  userAnswer: string; // ユーザーの回答
  isCorrect: boolean; // 正誤
  timestamp: number; // タイムスタンプ（UNIXタイム）
}

// カテゴリの定義
const CATEGORIES = [
  { value: "history", label: "歴史" },
  { value: "science", label: "科学" },
  { value: "literature", label: "文学" },
  { value: "geography", label: "地理" },
  { value: "sports", label: "スポーツ" },
  { value: "arts", label: "芸術" },
  { value: "general", label: "一般知識" },
] as const;

// LocalStorageのキー名
const HISTORY_STORAGE_KEY = "quiz_app_history";

// 回答の最大文字数
const MAX_ANSWER_LENGTH = 200;

// LocalStorageから履歴を取得
const getHistory = (): QuizHistory[] => {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error("履歴の読み込みに失敗しました:", error);
    return [];
  }
};

// LocalStorageに履歴を保存
const saveHistory = (history: QuizHistory[]) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  } catch (error) {
    console.error("履歴の保存に失敗しました:", error);
  }
};

// 履歴に新しいエントリを追加
const addHistoryEntry = (entry: QuizHistory) => {
  const history = getHistory();
  // 新しいエントリを先頭に追加（最新が最初）
  history.unshift(entry);
  // 最大100件まで保存
  if (history.length > 100) {
    history.pop();
  }
  saveHistory(history);
};

// 履歴をクリア
const clearHistory = () => {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
  } catch (error) {
    console.error("履歴のクリアに失敗しました:", error);
  }
};

export default function Home() {
  // ユーザーが選択したカテゴリを保存するための箱
  const [category, setCategory] = useState<string>("");
  // クイズデータ（オブジェクト）を保存する箱
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  // ローディング状態を管理する箱
  const [isLoading, setIsLoading] = useState<boolean>(false);
  // エラーメッセージを保存する箱
  const [error, setError] = useState<string>("");
  // ユーザーの回答を保存する箱
  const [userAnswer, setUserAnswer] = useState<string>("");
  // 判定結果を保存する箱（null: 未判定, "correct": 正解, "incorrect": 不正解）
  const [judgmentResult, setJudgmentResult] = useState<"correct" | "incorrect" | null>(null);
  // 答えを表示するかどうかを管理する箱
  const [showAnswer, setShowAnswer] = useState<boolean>(false);
  // 履歴を表示するかどうか
  const [showHistory, setShowHistory] = useState<boolean>(false);
  // 履歴データ
  const [history, setHistory] = useState<QuizHistory[]>([]);

  // === 生成オプション用の状態 ===
  // URL指定（任意）
  const [sourceUrl, setSourceUrl] = useState<string>("");
  // 問題数指定（デフォルト1）
  const [questionCount, setQuestionCount] = useState<number>(1);
  // 複数問生成時のクイズデータ配列
  const [questions, setQuestions] = useState<QuizData[]>([]);
  // 複数問生成時の現在の問題インデックス
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);

  // 初回レンダリング時に履歴を読み込む
  useEffect(() => {
    setHistory(getHistory());
  }, []);

  // 回答を正規化する関数（スペース削除、小文字変換、全角→半角）
  const normalizeAnswer = (text: string): string => {
    return text
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "") // スペース削除
      .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (s) => String.fromCharCode(s.charCodeAt(0) - 0xfee0)); // 全角→半角
  };

  // 回答の正誤判定
  const handleSubmitAnswer = () => {
    if (!quiz) return;

    // 空回答チェック
    if (!userAnswer.trim()) {
      setError("回答を入力してください。");
      return;
    }

    // 文字数制限チェック
    if (userAnswer.length > MAX_ANSWER_LENGTH) {
      setError(`回答は${MAX_ANSWER_LENGTH}文字以内で入力してください。（現在: ${userAnswer.length}文字）`);
      return;
    }

    setError(""); // エラーをクリア

    // 正規化した回答と正解を比較
    const normalizedUserAnswer = normalizeAnswer(userAnswer);
    const normalizedCorrectAnswer = normalizeAnswer(quiz.answer);

    // 完全一致で判定
    const isCorrect = normalizedUserAnswer === normalizedCorrectAnswer;
    setJudgmentResult(isCorrect ? "correct" : "incorrect");

    // 履歴に保存
    const categoryLabel = CATEGORIES.find(cat => cat.value === category)?.label || category;
    const historyEntry: QuizHistory = {
      id: `${Date.now()}_${Math.random()}`, // 一意のID
      category: category,
      categoryLabel: categoryLabel,
      question: quiz.question,
      correctAnswer: quiz.answer,
      userAnswer: userAnswer,
      isCorrect: isCorrect,
      timestamp: Date.now(),
    };
    addHistoryEntry(historyEntry);

    // 履歴を再読み込み
    setHistory(getHistory());

    // 判定後は自動的に正解例を表示
    setShowAnswer(true);
  };

  const handleGenerate = async () => {
    // 既にローディング中の場合は何もしない（二重送信防止）
    if (isLoading) {
      return;
    }

    // カテゴリ未選択の場合はエラー表示
    if (!category) {
      setError("カテゴリを選択してください。");
      return;
    }

    setQuiz(null); // 前のクイズをリセット
    setQuestions([]); // 前の複数問クイズをリセット
    setCurrentQuestionIndex(0); // インデックスリセット
    setError(""); // 前のエラーをリセット
    setIsLoading(true); // ローディング開始
    setShowAnswer(false); // 答えを隠す
    setUserAnswer(""); // ユーザーの回答をリセット
    setJudgmentResult(null); // 判定結果をリセット

    // タイムアウト設定（30秒）
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      // リクエストボディを構築
      const requestBody: any = {
        category: category,
        question_count: questionCount,
      };

      // URL指定がある場合
      if (sourceUrl.trim()) {
        requestBody.source_type = "url";
        requestBody.source_value = sourceUrl.trim();
      }

      const res = await fetch(`${apiUrl}/generate-quiz`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal, // タイムアウト用
      });

      clearTimeout(timeoutId); // タイムアウトをクリア

      if (!res.ok) {
        // レスポンスボディからエラーメッセージを取得
        let errorDetail = "";
        try {
          const errorData = await res.json();
          errorDetail = errorData.detail || "";
        } catch {
          // JSON解析に失敗した場合は空文字列のまま
        }

        // HTTPステータスコードとエラーメッセージに応じた処理
        if (res.status === 401 || errorDetail.includes("GEMINI_API_KEY_INVALID")) {
          throw new Error(
            "Gemini APIキーが無効です。\n" +
            "管理者にお問い合わせください。\n\n" +
            "開発者向け: backend/.envファイルのGEMINI_API_KEYを確認してください。"
          );
        } else if (res.status === 403 || errorDetail.includes("GEMINI_API_KEY_PERMISSION_DENIED")) {
          throw new Error(
            "Gemini APIキーの権限が不足しています。\n" +
            "管理者にお問い合わせください。"
          );
        } else if (res.status === 429 || errorDetail.includes("GEMINI_RATE_LIMIT")) {
          throw new Error(
            "Gemini APIのリクエスト制限に達しました。\n" +
            "しばらく待ってから再度お試しください。"
          );
        } else if (res.status === 503 || errorDetail.includes("GEMINI_SERVICE_UNAVAILABLE")) {
          throw new Error(
            "Gemini AIサービスが一時的に利用できません。\n" +
            "しばらく待ってから再度お試しください。"
          );
        } else if (res.status === 504 || errorDetail.includes("GEMINI_TIMEOUT")) {
          throw new Error(
            "Gemini APIへのリクエストがタイムアウトしました。\n" +
            "もう一度お試しください。"
          );
        } else if (errorDetail.includes("GEMINI_API_KEY_NOT_SET")) {
          throw new Error(
            "Gemini APIキーが設定されていません。\n" +
            "管理者にお問い合わせください。\n\n" +
            "開発者向け: backend/.envファイルにGEMINI_API_KEYを設定してください。"
          );
        } else if (errorDetail.includes("AI_INVALID_JSON")) {
          throw new Error(
            "AIの応答形式が不正です。\n" +
            "もう一度お試しください。"
          );
        } else if (errorDetail.includes("SOURCE_RESTRICTION_VIOLATION")) {
          throw new Error(
            "参照元が制限（コトバンク/公式サイト）に一致しないため、生成結果を表示できません。\n" +
            "別のカテゴリで再試行してください。"
          );
        } else if (res.status >= 500) {
          throw new Error(
            "バックエンドサーバーでエラーが発生しました。\n" +
            "時間をおいて再度お試しください。"
          );
        } else if (res.status === 400) {
          throw new Error(
            "リクエストが無効です。もう一度お試しください。"
          );
        } else {
          throw new Error(`APIエラー: ${res.status} ${res.statusText}`);
        }
      }

      const data = await res.json();

      // レスポンス形式に応じた処理
      if (questionCount === 1) {
        // 単問の場合: オブジェクトをそのまま保存
        setQuiz(data);
      } else {
        // 複数問の場合: {"questions": [...]} 形式
        if (data.questions && Array.isArray(data.questions)) {
          setQuestions(data.questions);
          setCurrentQuestionIndex(0);
          // 最初の問題を表示
          if (data.questions.length > 0) {
            setQuiz(data.questions[0]);
          }
        } else {
          throw new Error("複数問生成のレスポンス形式が不正です。");
        }
      }
    } catch (error: any) {
      console.error(error);

      // エラーの種類に応じたメッセージ
      if (error.name === "AbortError") {
        setError(
          "リクエストがタイムアウトしました。ネットワーク接続を確認するか、時間をおいて再度お試しください。"
        );
      } else if (error.message.includes("Failed to fetch") || error.message.includes("fetch")) {
        setError(
          "バックエンドサーバーに接続できません。サーバーが起動しているか確認してください。\n" +
          "起動方法: backend/ で「uvicorn main:app --reload」を実行"
        );
      } else {
        setError(error.message || "不明なエラーが発生しました。");
      }
    } finally {
      clearTimeout(timeoutId);
      setIsLoading(false); // ローディング終了
    }
  };

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
        backgroundColor: "#f5f5f5", // 背景色を少しつける
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
          カテゴリを選択してクイズを生成
        </Typography>

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
            helperText="URLを指定すると、そのページの内容を元に問題を生成します"
            fullWidth
          />

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
                onClick={() => {
                  if (confirm("本当に履歴をすべて削除しますか？")) {
                    clearHistory();
                    setHistory([]);
                  }
                }}
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
            whiteSpace: "pre-wrap", // 改行を反映
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
            "& > *": { mb: 2 }, // 各要素の間にマージン
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
                  onClick={() => {
                    if (currentQuestionIndex > 0) {
                      const newIndex = currentQuestionIndex - 1;
                      setCurrentQuestionIndex(newIndex);
                      setQuiz(questions[newIndex]);
                      setUserAnswer("");
                      setJudgmentResult(null);
                      setShowAnswer(false);
                    }
                  }}
                  disabled={currentQuestionIndex === 0}
                >
                  前へ
                </Button>
                <Button
                  size="small"
                  onClick={() => {
                    if (currentQuestionIndex < questions.length - 1) {
                      const newIndex = currentQuestionIndex + 1;
                      setCurrentQuestionIndex(newIndex);
                      setQuiz(questions[newIndex]);
                      setUserAnswer("");
                      setJudgmentResult(null);
                      setShowAnswer(false);
                    }
                  }}
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