// app/page.tsx

"use client"; // ブラウザで動くコンポーネントであることを示すおまじない

import { Box, Button, TextField, Typography } from "@mui/material";

export default function Home() {
  return (
    <Box
      component="main"
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: 4,
        gap: 2, // 要素間のスペース
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
      />
      <Button variant="contained" size="large">
        生成
      </Button>
    </Box>
  );
}
