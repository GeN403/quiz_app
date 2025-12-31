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

export default function Home() {
  // ユーザーが入力したURLを保存するための箱
  const [url, setUrl] = useState<string>("");
  // クイズデータ（オブジェクト）を保存する箱
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  // ローディング状態を管理する箱
  const [isLoading, setIsLoading] = useState<boolean>(false);
  // エラーメッセージを保存する箱
  const [error, setError] = useState<string>("");
  // 答えを表示するかどうかを管理する箱
  const [showAnswer, setShowAnswer] = useState<boolean>(false);

  const handleGenerate = async () => {
    setQuiz(null); // 前のクイズをリセット
    setError(""); // 前のエラーをリセット
    setIsLoading(true); // ローディング開始
    setShowAnswer(false); // 答えを隠す

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
        body: JSON.stringify({ url: url }), // 入力されたURLを送信
        signal: controller.signal, // タイムアウト用
      });

      clearTimeout(timeoutId); // タイムアウトをクリア

      if (!res.ok) {
        // HTTPステータスコードに応じたエラーメッセージ
        if (res.status >= 500) {
          throw new Error(
            "バックエンドサーバーでエラーが発生しました。時間をおいて再度お試しください。"
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

      {/* --- 入力エリア --- */}
      <Paper
        sx={{
          p: 2,
          width: "100%",
          maxWidth: "700px",
          display: "flex",
          gap: 2,
        }}
      >
        <TextField
          id="url-input"
          label="クイズ生成元のURL"
          variant="outlined"
          fullWidth
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isLoading} // 生成中は無効化
        />
        <Button
          variant="contained"
          size="large"
          onClick={handleGenerate}
          disabled={isLoading} // 生成中は無効化
          sx={{ whiteSpace: "nowrap" }}
        >
          {isLoading ? <CircularProgress size={24} /> : "生成"}
        </Button>
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
          {/* 質問文 */}
          <Typography variant="h5" component="h2" sx={{ fontWeight: "bold" }}>
            問題
          </Typography>
          <Typography
            variant="body1"
            sx={{ fontSize: "1.2rem", whiteSpace: "pre-wrap", lineHeight: 1.8 }}
          >
            {quiz.question}
          </Typography>

          <Button
            variant="outlined"
            onClick={() => setShowAnswer(!showAnswer)}
          >
            {showAnswer ? "答えを隠す" : "答えと解説を見る"}
          </Button>

          {/* 答えと解説 (アコーディオンで表示) */}
          <Collapse in={showAnswer}>
            {/* 正解 */}
            <Typography variant="h6" component="h3" sx={{ mt: 2 }}>
              正解
            </Typography>
            <Typography variant="body1" sx={{ fontSize: "1.1rem", color: "green", fontWeight: "bold" }}>
              {quiz.answer}
            </Typography>

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
          </Collapse>
        </Paper>
      )}
    </Box>
  );
}