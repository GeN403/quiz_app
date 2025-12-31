// app/page.tsx

"use client";

import { useState } from "react"; // useStateをインポート
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
    if (!userAnswer.trim()) {
      setError("回答を入力してください。");
      return;
    }

    setError(""); // エラーをクリア

    // 正規化した回答と正解を比較
    const normalizedUserAnswer = normalizeAnswer(userAnswer);
    const normalizedCorrectAnswer = normalizeAnswer(quiz.answer);

    // 完全一致で判定
    if (normalizedUserAnswer === normalizedCorrectAnswer) {
      setJudgmentResult("correct");
    } else {
      setJudgmentResult("incorrect");
    }

    // 判定後は自動的に正解例を表示
    setShowAnswer(true);
  };

  const handleGenerate = async () => {
    // カテゴリ未選択の場合はエラー表示
    if (!category) {
      setError("カテゴリを選択してください。");
      return;
    }

    setQuiz(null); // 前のクイズをリセット
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
      const res = await fetch(`${apiUrl}/generate-quiz`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ category: category }), // 選択されたカテゴリを送信
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
        } else if (res.status >= 500) {
          throw new Error(
            "バックエンドサーバーでエラーが発生しました。\n" +
            "時間をおいて再度お試しください。"
          );
        } else if (res.status === 400) {
          throw new Error(
            "入力されたURLが無効です。正しいURLを入力してください。"
          );
        } else {
          throw new Error(`APIエラー: ${res.status} ${res.statusText}`);
        }
      }

      const data = await res.json();
      setQuiz(data); // クイズデータをオブジェクトとして保存
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
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
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
          <Button
            variant="contained"
            size="large"
            onClick={handleGenerate}
            disabled={isLoading || !category}
            sx={{ whiteSpace: "nowrap", minWidth: "120px" }}
          >
            {isLoading ? <CircularProgress size={24} /> : "生成"}
          </Button>
        </Box>
      </Paper>

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
            <Box sx={{ mt: 2, display: "flex", gap: 2, alignItems: "flex-start" }}>
              <TextField
                id="answer-input"
                label="あなたの回答"
                variant="outlined"
                fullWidth
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    handleSubmitAnswer();
                  }
                }}
                placeholder="回答を入力してください"
              />
              <Button
                variant="contained"
                size="large"
                onClick={handleSubmitAnswer}
                sx={{ whiteSpace: "nowrap", minWidth: "100px" }}
              >
                回答する
              </Button>
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