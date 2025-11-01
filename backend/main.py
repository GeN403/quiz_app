# main.py
import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
import json

# FastAPI関連のインポート
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーを設定
genai.configure(api_key=api_key)

# FastAPIアプリケーションの初期化
app = FastAPI()

# CORSミドルウェアの設定（Next.jsのlocalhost:3000からのアクセスを許可する）
origins = [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------------------------------------
# ↓↓↓ プロンプトとルールの定義 ↓↓↓
# ----------------------------------------------------

# リクエストボディの型を定義
class QuizRequest(BaseModel):
    url: str

# # 使用するモデルを選択（実際に利用可能なモデル名にしてください）
# model = genai.GenerativeModel('gemini-2.5-flash')

# # クイズの生成元となるページのURL
# target_url = "https://kotobank.jp/word/%E5%B1%B1%E6%9D%B1%E4%BA%AC%E4%BC%9D-18131"

# # 制約条件を独立した変数として定義（再利用するため）
# CONSTRAINT_RULES = """
# ・必ず「問題文」「正解」「別解/正誤判定基準」「解説」「出典」の要素を含めてください。
# ・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation","source"
# ・"source"にはウェブページタイトルとURLを含めてください。
# ・"question"では問題の後半で問題の答えを一意に絞れるような情報を盛り込んでください。
# ・"Alternative Solutions/Correctness Judgment Criteria"については日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
# ・"question"の文末は「～でしょう？」としてください。
# ・"question"の中でも、「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
# ・"question"の中でも、パラレル問題では対照的なキーワードを**強調**してください。
# ・体言止めは避けてください。
# ・作品名は『』（2重鍵かっこ）で囲んでください。
# ・"question"では問題文は80文字以内にしてください。
# ・漢字検定2級程度の語彙には後ろから()でルビを追加してください。
# ・最初は広い情報から入り、徐々に狭い情報に絞ってください。
# ・前半に知名度が低い情報、後半に知名度が高い情報を配置してください。
# """

# # --- ① 生成フェーズ用のプロンプト ---
# prompt_template_generate = f"""
# # 役割
# あなたはプロのクイズ作家です。

# # タスク
# 以下の文章を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# # 制約条件
# {CONSTRAINT_RULES}

# # 文章
# {{source_text}}
# """

# # --- ② 自己評価・修正フェーズ用のプロンプト ---
# prompt_template_refine = f"""
# # 役割
# あなたは、AIが生成したクイズを評価し、修正する品質保証の専門家です。

# # タスク
# AIが生成した以下の「生成物」が、「制約条件」を完全に満たしているか厳密にチェックしてください。
# もし一つでも違反があれば、すべての違反箇所を修正し、制約条件を完全に満たした**最終的なJSONオブジェクトのみを出力**してください。
# もし違反がなければ、元の「生成物」を**そのままJSONオブジェクトとして出力**してください。

# **重要：あなたの応答は、解説や挨拶を一切含んではいけません。あなたの応答は、JSONオブジェクトそのものである必要があります。**

# # 制約条件
# {CONSTRAINT_RULES}

# # AIによる生成物
# {{draft_quiz}}
# """

# 使用するモデルを選択
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# 制約条件を独立した変数として定義
CONSTRAINT_RULES = """
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」「出典」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation","source"
・"source"にはウェブページタイトルとURLを含めてください。
・問題の後半で問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・パラレル問題では対照的なキーワードを**強調**してください。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は80文字以内にしてください。
・漢字検定2級程度の語彙には後ろから()でルビを追加してください。
・最初は広い情報から入り、徐々に狭い情報に絞ってください。
・前半に知名度が低い情報、後半に知名度が高い情報を配置してください。
"""

# --- ① AIへの最終的な指示プロンプト（これ一本にします） ---
prompt_template = f"""
# 役割
あなたはプロのクイズ作家であり、JSONの専門家です。

# タスク
以下の「文章」と「出典情報」を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# 制約条件
{CONSTRAINT_RULES}

# 最重要ルール
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**「制約条件」をすべて満たしたJSONオブジェクトそのもの**である必要があります。

# 出典情報
・タイトル: {{source_title}}
・URL: {{source_url}}

# 文章
{{source_text}}
"""

# ----------------------------------------------------
# ↑↑↑ プロンプトとルールの定義ここまで ↑↑↑
# ----------------------------------------------------

def get_web_info(url: str):
    """URLから本文テキストとタイトルを抽出する関数"""
    try:
        print(f"📄 '{url}' から情報を取得中...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # タイトルを取得
        title = soup.title.string if soup.title else "タイトル不明"
        
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        
        body_text = soup.get_text(separator='\n', strip=True)
        print("✅ 情報の取得完了！")
        return body_text, title
    except requests.RequestException as e:
        print(f"❌ URLの取得に失敗しました: {e}")
        return None, None
    

@app.post("/generate-quiz")
async def generate_quiz(request: QuizRequest):
    """
    URLを受け取り、スクレイピングとGemini API呼び出しを行ってクイズを生成する
    """
    print(f"リクエスト受信: URL = {request.url}")
    
    # 1. URLから本文とタイトルを取得
    source_text, source_title = get_web_info(request.url)
    if not source_text:
        raise HTTPException(status_code=400, detail="URLからコンテンツを取得できませんでした。")

    # テキストが長すぎるとタイムアウトするため、先頭8000文字程度に制限する
    MAX_LENGTH = 8000
    if len(source_text) > MAX_LENGTH:
        print(f"⚠️ テキストが長すぎたため、{MAX_LENGTH}文字に短縮します。")
        source_text = source_text[:MAX_LENGTH]

    try:
        # --- AI呼び出し（1回だけ） ---
        print("\n--- ① 生成フェーズ ---")
        full_prompt = prompt_template.format(
            source_title=source_title,
            source_url=request.url,
            source_text=source_text
        )
        print("🤖 AIにクイズを生成させています...")
        response = model.generate_content(full_prompt)
        
        # AIの生の応答をクリーンアップ
        final_text = response.text.strip()
        
        print("--- 🤖 AIの最終RAW応答 (デバッグ用) ---")
        print(final_text)
        print("---------------------------------")

        # AIがJSONを```で囲んでいる場合、それを取り除く
        if final_text.startswith("```json"):
            final_text = final_text[7:].strip() # "```json\n" を削除
        if final_text.startswith("```"):
            final_text = final_text[3:].strip()
        if final_text.endswith("```"):
            final_text = final_text[:-3].strip()
        
        print("✅ 最終版が完成しました！(クリーンアップ後)")
        
        # JSON文字列をPythonの辞書に変換して返す
        final_json = json.loads(final_text)
        return final_json
        
    # エラーキャッチをより具体的にする
    except json.JSONDecodeError as e:
        print(f"❌ JSONデコードエラー: {e}")
        print("--- 失敗したテキスト (上記ログ参照) ---")
        raise HTTPException(status_code=500, detail=f"AIが有効なJSONを返しませんでした。RAW: {final_text}")
    except Exception as e:
        print(f"❌ API処理中にエラーが発生しました: {e}")
        raise HTTPException(status_code=500, detail="AIによるクイズ生成中にエラーが発生しました。")

# --- メインの処理 ---
# 1. URLから本文とタイトルを取得
# source_text, source_title = get_web_info(target_url)

# if source_text:
#     # --- ① 生成フェーズ ---
#     print("\n--- ① 生成フェーズ ---")
#     prompt_generate = prompt_template_generate.format(source_text=source_text)
#     print("🤖 AIにクイズの初稿を生成させています...")
#     response_generate = model.generate_content(prompt_generate)
#     first_draft_text = response_generate.text
#     print("✅ 初稿が完成しました！")
#     print(first_draft_text)

#     # --- ② 自己評価・修正フェーズ ---
#     print("\n--- ② 自己評価・修正フェーズ ---")
#     prompt_refine = prompt_template_refine.format(draft_quiz=first_draft_text)
#     print("🧐 AIが生成結果を自己評価し、必要なら修正します...")
#     response_refine = model.generate_content(prompt_refine)
    
#     # 最終的な出力を整形
#     final_text = response_refine.text.strip().replace("```json\n", "").replace("\n```", "")
    
#     print("✅ 最終版が完成しました！")
#     print("\n--- 最終出力結果 ---")
    
#     # JSONとしてきれいに整形して表示
#     try:
#         final_json = json.loads(final_text)
#         print(json.dumps(final_json, indent=2, ensure_ascii=False))
#     except json.JSONDecodeError:
#         print("エラー: 最終出力が有効なJSONではありません。")
#         print(final_text)
# APIエンドポイントの作成
# ----------------------------------------------------
# 

    # # AIの生の応答をクリーンアップ
    #     final_text = response_refine.text.strip()
        
    #     # (!!!) デバッグのために、AIの生の応答をログに出力 (!!!)
    #     print("--- 🤖 AIの最終RAW応答 (デバッグ用) ---")
    #     print(final_text)
    #     print("---------------------------------")

    #     # AIがJSONを```で囲んでいる場合、それを取り除く
    #     if final_text.startswith("```json"):
    #         final_text = final_text[7:].strip() # "```json\n" を削除
    #     if final_text.startswith("```"):
    #         final_text = final_text[3:].strip()
    #     if final_text.endswith("```"):
    #         final_text = final_text[:-3].strip()
        
    #     print("✅ 最終版が完成しました！(クリーンアップ後)")
        
    #     # JSON文字列をPythonの辞書に変換して返す
    #     final_json = json.loads(final_text)
    #     return final_json
        
    # # エラーキャッチをより具体的にする
    # except json.JSONDecodeError as e:
    #     print(f"❌ JSONデコードエラー: {e}")
    #     print("--- 失敗したテキスト (上記ログ参照) ---")
    #     raise HTTPException(status_code=500, detail=f"AIが有効なJSONを返しませんでした。RAW: {final_text}")
    # except Exception as e:
    #     print(f"❌ API処理中にエラーが発生しました: {e}")
    #     raise HTTPException(status_code=500, detail="AIによるクイズ生成中にエラーが発生しました。")