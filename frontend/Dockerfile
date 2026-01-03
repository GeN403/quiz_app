# Frontend Dockerfile for Next.js
FROM node:20-bookworm

WORKDIR /app

# 依存関係をインストール
COPY package*.json ./
RUN npm install

# アプリケーションコードをコピー
COPY . .

# ポート3000を公開
EXPOSE 3000

# Next.jsを開発モードで起動
CMD ["npm", "run", "dev"]
