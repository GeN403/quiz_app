// app/page.tsx

"use client";

import { useState } from "react"; // useStateをインポート
import { Box, Button, TextField, Typography, Paper } from "@mui/material";

export default function Home() {
  // ユーザーが入力したURLを保存するための箱
  const [url, setUrl] = useState<string>("");
  // AIからの返事を保存するための箱
  const [response, setResponse] = useState<string>("");

  const handleGenerate = async () => {
    setResponse("生成中です..."); // ローディング表示
    try {
      const res = await fetch("http://localhost:8000/generate-quiz", { // 作成したAPIを呼び出す
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: url }), // 入力されたURLを送信
      });

      if (!res.ok) {
        throw new Error("APIリクエストに失敗しました");
      }

      const data = await res.json();
      setResponse(data.result); // AIの返事を箱に入れる
    } catch (error) {
      console.error(error);
      setResponse("エラーが発生しました。");
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
      }}
    >
      <Typography variant="h4" component="h1" gutterBottom>
        クイズ自動生成プロトタイプ
      </Typography>
      <TextField
        id="url-input"
        label="クイズ生成元のURL"
        variant="outlined"
        sx={{ width: "100%", maxWidth: "600px" }}
        value={url} // 入力値をurlの箱と連動
        onChange={(e) => setUrl(e.target.value)} // 入力されたらurlの箱を更新
      />
      <Button variant="contained" size="large" onClick={handleGenerate}>
        生成
      </Button>

      {/* AIからの返事があれば表示するエリア */}
      {response && (
        <Paper
          elevation={3}
          sx={{
            p: 2,
            mt: 2,
            width: "100%",
            maxWidth: "600px",
            whiteSpace: "pre-wrap", // 改行をそのまま表示
          }}
        >
          {response}
        </Paper>
      )}
    </Box>
  );
}