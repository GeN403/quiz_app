# クイズ自動生成アプリ（MVP版）

## 概要
WebページのURLを入力すると、AI（Gemini API）がその内容を基に競技クイズレベルの問題を自動生成するアプリケーションです。

## 技術スタック
- **フロントエンド**: Next.js 15.5.4 + TypeScript + Material UI
- **バックエンド**: FastAPI (Python) + Google Gemini API
- **スクレイピング**: BeautifulSoup4

## 必要な環境
- Python 3.12以上
- Node.js 20以上
- Gemini APIキー（[こちら](https://aistudio.google.com/app/apikey)から取得）

## 環境変数一覧

### バックエンド（backend/.env）- 必須
| 変数名 | 説明 | 必須 | デフォルト値 | 取得先 |
|--------|------|------|--------------|--------|
| `GEMINI_API_KEY` | Google Gemini APIキー | ✅ | なし | [Google AI Studio](https://aistudio.google.com/app/apikey) |

### フロントエンド（frontend/.env.local）- 任意
| 変数名 | 説明 | 必須 | デフォルト値 | 備考 |
|--------|------|------|--------------|------|
| `NEXT_PUBLIC_API_URL` | FastAPIバックエンドのURL | ❌ | `http://localhost:8000` | 本番環境では変更が必要 |

**重要な注意事項**:
- `.env` ファイルは `.gitignore` で除外されており、**Gitにコミットされません**
- APIキーなどの機密情報は絶対にGitHubにプッシュしないでください
- チーム開発時は `.env.example` を共有し、各自で `.env` を作成してください`


## リポジトリ構造

```plaintext
quiz_app/
├── frontend/              # Next.js フロントエンド
│   ├── app/              # Next.js App Router
│   │   ├── page.tsx      # メインページ（URL入力・クイズ表示）
│   │   └── layout.tsx    # レイアウト
│   └── ...
│
├── backend/              # FastAPI バックエンド
│   ├── main.py          # APIサーバー本体
│   ├── requirements.txt # Python依存関係
│   ├── .env.example     # 環境変数テンプレート
│   └── venv/            # Python仮想環境（セットアップ後）
│
├── package.json         # フロントエンド依存関係
└── README.md
```

---

## セットアップ手順（10分で完了）

### 1. リポジトリのクローン
```bash
git clone https://github.com/GeN403/quiz_app.git
cd quiz_app
```

### 2. 環境変数の設定

#### 2-1. バックエンドの環境変数設定（必須）
```bash
cd backend
cp .env.example .env
```

`.env`ファイルを開き、Gemini APIキーを設定してください：
```env
# backend/.env
GEMINI_API_KEY=あなたのAPIキーをここに貼り付け
```

**APIキーの取得方法**:
1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. 「Create API Key」をクリック
3. 生成されたAPIキーをコピーして上記の`.env`ファイルに貼り付け

#### 2-2. フロントエンドの環境変数設定（任意）
```bash
cd ../frontend  # または cd ..してから cd frontend
cp .env.example .env.local
```

デフォルト設定で動作しますが、本番環境や別のポートでバックエンドを起動する場合は変更してください：
```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000  # バックエンドのURL
```

### 3. バックエンドのセットアップ

#### 3-1. 仮想環境の作成とライブラリインストール
```bash
cd backend  # まだbackend/にいない場合
python -m venv venv
```

**Windowsの場合:**
```bash
venv\Scripts\activate
```

**Mac/Linuxの場合:**
```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### 4. フロントエンドのセットアップ

ルートディレクトリ（quiz_app/）に戻り、依存関係をインストール：
```bash
cd ..  # quiz_app/ に戻る
npm install
```

---

## 起動方法

### ターミナル1: バックエンド起動
```bash
cd backend
venv\Scripts\activate  # Windowsの場合
# source venv/bin/activate  # Mac/Linuxの場合
uvicorn main:app --reload
```
→ `http://localhost:8000` でAPIサーバーが起動します

### ターミナル2: フロントエンド起動
```bash
# quiz_app/ のルートディレクトリで実行
npx next dev frontend --turbopack
```
→ `http://localhost:3000` でWebアプリが起動します

---

## 動作確認手順

ブラウザで `http://localhost:3000` を開き、以下の手順で動作を確認してください：

### 1. URLの入力
「クイズ生成元のURL」欄に、クイズの元となるWebページのURLを入力します。

**テスト用URL例:**
```
https://kotobank.jp/word/%E5%B1%B1%E6%9D%B1%E4%BA%AC%E4%BC%9D-18131
```

### 2. クイズ生成
「生成」ボタンをクリックします。
- ローディングスピナーが表示され、AI がクイズを生成します（約5〜15秒）

### 3. 問題の確認
生成されたクイズ問題が表示されます。
- 問題文が表示される
- 「答えと解説を見る」ボタンが表示される

### 4. 解答の確認
「答えと解説を見る」ボタンをクリックすると、以下が表示されます：
- 正解
- 別解/正誤判定基準
- 解説
- 出典（元のWebページへのリンク）

### 5. 再度クイズ生成
別のURLで再度クイズを生成できます。

---

## エラーハンドリング

アプリケーションは以下のエラーを適切に検出し、ユーザーフレンドリーなメッセージを表示します：

### バックエンド未起動・接続不可
**症状**: 「生成」ボタンをクリックしてもクイズが生成されず、エラーメッセージが表示される

**表示されるメッセージ**:
```
バックエンドサーバーに接続できません。サーバーが起動しているか確認してください。
起動方法: backend/ で「uvicorn main:app --reload」を実行
```

**対処方法**:
1. バックエンドが起動しているか確認
2. 起動していない場合は、上記の「起動方法」セクションを参照してバックエンドを起動
3. エラーメッセージ内の「再試行」ボタンをクリックして再実行

### タイムアウトエラー
**症状**: 30秒以上応答がない場合

**表示されるメッセージ**:
```
リクエストがタイムアウトしました。ネットワーク接続を確認するか、時間をおいて再度お試しください。
```

**対処方法**:
- ネットワーク接続を確認
- 対象のWebページが重すぎる可能性があるため、別のURLを試す
- 「再試行」ボタンをクリック

### サーバーエラー（5xx）
**表示されるメッセージ**:
```
バックエンドサーバーでエラーが発生しました。時間をおいて再度お試しください。
```

**対処方法**:
- バックエンドのターミナルでエラーログを確認
- 時間をおいて再試行
- 環境変数（`GEMINI_API_KEY`）が正しく設定されているか確認

### 無効なURL（400）
**表示されるメッセージ**:
```
入力されたURLが無効です。正しいURLを入力してください。
```

**対処方法**:
- URLの形式が正しいか確認（`http://` または `https://` で始まる必要があります）
- アクセス可能なWebページか確認

---

## トラブルシューティング

### ❌ エラー: `Could not import module "main"`
**原因**: ルートディレクトリ (`quiz_app/`) で `uvicorn main:app --reload` を実行している

**解決方法**: 必ず `backend/` ディレクトリに移動してから実行してください
```bash
cd backend
uvicorn main:app --reload
```

### ❌ エラー: `TypeError: Failed to fetch` (フロントエンド)
**症状**: Next.jsのブラウザコンソールに「TypeError: Failed to fetch」が表示され、クイズ生成が失敗する

**原因**: バックエンド（FastAPI）が500 Internal Server Errorを返している
- **根本原因**: Windows環境でPythonの`print()`関数が絵文字（例: 📄, ✅, ❌）を出力しようとすると、デフォルトのcp932エンコーディングで処理できずUnicodeEncodeErrorが発生

**解決済み**: `backend/main.py`のprint文から絵文字を削除し、シンプルなテキスト（`[INFO]`, `[OK]`, `[ERROR]`）に置き換え済み

**確認方法**:
```powershell
# バックエンドが正常に動作しているか確認
curl -X POST http://127.0.0.1:8000/generate-quiz -H "Content-Type: application/json" -d '{"url":"https://example.com"}'
# ステータスコード200が返ればOK
```

### ❌ 複数の仮想環境（venv）が混在している
**症状**: `.venv/` と `backend/venv/` の両方が存在する

**推奨**: `backend/venv/` を使用してください
- `.venv/` は削除しても問題ありません（または無視してください）
- `.gitignore` で両方とも無視されるよう設定済みです

**正しい手順**:
```bash
cd backend
# 仮想環境が存在しない場合のみ作成
python -m venv venv

# 仮想環境を有効化
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 依存関係をインストール
pip install -r requirements.txt

# サーバー起動
uvicorn main:app --reload
```

### ❌ 環境変数が設定されていない
**症状**: バックエンド起動時に「GEMINI_API_KEY is not set」などのエラーが表示される

**解決方法**:
1. `backend/.env` ファイルが存在するか確認
   ```bash
   ls backend/.env  # ファイルが存在するか確認
   ```
2. 存在しない場合は `.env.example` からコピー
   ```bash
   cd backend
   cp .env.example .env
   ```
3. `.env` ファイルを開き、APIキーを設定
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```
4. APIキーが正しく設定されているか確認
   ```bash
   cat backend/.env  # 内容を確認（Windowsの場合: type backend\.env）
   ```

### バックエンドが起動しない
- `GEMINI_API_KEY` が正しく設定されているか確認（上記参照）
- `backend/.env` ファイルが存在するか確認
- 仮想環境が有効化されているか確認（`(venv)` がターミナルに表示される）
- **作業ディレクトリが `backend/` であることを確認**

### フロントエンドが起動しない
- `npm install` が完了しているか確認
- Node.js のバージョンが 20 以上か確認: `node -v`

### クイズ生成時にエラーが出る
- バックエンド（`http://localhost:8000`）が起動しているか確認
- ブラウザの開発者ツール（F12）でエラーメッセージを確認
- バックエンドのターミナルでエラーログを確認

---

## 📩 Author
**GeN403**
GitHub: [https://github.com/GeN403](https://github.com/GeN403)
