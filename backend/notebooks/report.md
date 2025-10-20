# Gemini APIを用いたクイズ問題作成
(1) プロンプトやモデルを変えることで、LLMから返ってくる出力が意図するものになるよう工夫することができる。今回、作成に厳しい制約がある競技クイズの問題を作成させるタスクを題材に様々な方法で推論に工夫を行った。  
(2) 本検証はローカル環境で実験を行うため、まず、デスクトップで実験のためのフォルダー(prompt-lab)を作成した。さらに、venvという名前の仮想環境を作り、仮想環境を有効にした。さらにGemini APIをたたくためのライブラリとAPIキーを安全に管理するためのライブラリ、のちに使うWebスクレイピングを行うライブラリをインストールしました。Geminiにテンプレートを作らせ、各ファイルを以下のように編集した。

```
pip install google-generativeai python-dotenv
pip install requests beautifulsoup4
```
さらに、prompt-lab直下に.envとmain.pyを作成した。

```
# .env
GEMINI_API_KEY=ここにコピーしたGeminiのAPIキーを貼り付ける
```

```Python
# main.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーを設定
genai.configure(api_key=api_key)

# ----------------------------------------------------
# ↓↓↓ ここから下を書き換えて実験する ↓↓↓
# ----------------------------------------------------

# 使用するモデルを選択
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# クイズの生成元となる文章
source_text = """
日本で最も高い山は富士山であり、その標高は3,776メートルである。
静岡県と山梨県にまたがる活火山であり、美しい円錐状の形から日本の象徴として広く知られている。
2013年には、関連する文化財群とともに「富士山-信仰の対象と芸術の源泉」として世界文化遺産に登録された。
"""

# AIへの指示（プロンプト）
# ここを色々書き換えて、出力がどう変わるか試してみましょう！
prompt = f"""
あなたはプロのクイズ作家です。
以下の文章を基にして、競技クイズで使えるような本格的な4択クイズを1問作成してください。

【制約条件】
・必ず「問題文」「正解の選択肢」「不正解の選択肢3つ」「解説」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "options", "answer", "explanation"
・optionsは4つの選択肢を含む配列にしてください。

【文章】
{source_text}
"""

# ----------------------------------------------------
# ↑↑↑ ここまでを書き換えて実験する ↑↑↑
# ----------------------------------------------------


# Gemini APIを呼び出し
print("🤖 AIにクイズを生成させています...")
response = model.generate_content(prompt)
print("✅ 生成が完了しました！")
print("--- 出力結果 ---")
print(response.text)
```
Gemini API Keyの取得が必要だったので、Google AI Studioにクレジットカードを紐づけ済みのGoogleアカウントでログインし、Create API key in new projectからAPI Keyを取得しました。  
まず、素直に`gemini-flash-1.5-latest`は現在利用できなくなっているので`model = genai.get_generative_model('gemini-1.5-flash-latest')`を`model = genai.get_generative_model('gemini-2.0-flash')`にモデルを変更し、そのまま実行しました。

```
🤖 AIにクイズを生成させています...
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
E0000 00:00:1760403570.495688   32908 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
✅ 生成が完了しました！
--- 出力結果 ---
{
  "question": "2013年に世界文化遺産に登録された富士山ですが、文化遺産として の登録名は何でしょう？",
  "options": [
    "富士山-自然の驚異",
    "富士山-信仰の対象と芸術の源泉",
    "富士山-日本の魂",
    "富士山-活火山の象徴"
  ],
  "answer": "富士山-信仰の対象と芸術の源泉",
  "explanation": "富士山は2013年に「富士山-信仰の対象と芸術の源泉」として世 界文化遺産に登録されました。これは、富士山が古来より信仰の対象であり、また多くの芸術作品の源泉となってきた文化的価値を評価されたものです。"
}
```



次に、問題の形式を競技クイズに寄せるため、ABC（有名なクイズ大会）の「abc/EQIDEN クイズ問題作成の手引き」を参考に制約条件を変更しました。

```Python
# 使用するモデルを選択
model = genai.GenerativeModel('gemini-2.0-flash')

# クイズの生成元となる文章
source_text = """
日本で最も高い山は富士山であり、その標高は3,776メートルである。
静岡県と山梨県にまたがる活火山であり、美しい円錐状の形から日本の象徴として広く知られている。
2013年には、関連する文化財群とともに「富士山-信仰の対象と芸術の源泉」として世界文化遺産に登録された。
"""

# AIへの指示（プロンプト）
# ここを色々書き換えて、出力がどう変わるか試してみましょう！
prompt = f"""
# 役割
あなたはプロのクイズ作家です。

# タスク
以下の文章を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# 制約条件
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」「出典」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation","source"
・"source"にはウェブページタイトルとURLを含めてください。
・問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は60文字以内にしてください。

【文章】
{source_text}
"""
```

```
🤖 AIにクイズを生成させています...
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
E0000 00:00:1760407171.227077   30684 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
✅ 生成が完了しました！
--- 出力結果 ---
```json
{
  "question": "『霊峰の象徴』日本最高峰であり、静岡県と山梨県に跨る活火山は何でしょう？",
  "answer": "富士山",
  "Alternative Solutions/Correctness Judgment Criteria": "不採用",
  "explanation": "富士山は標高3,776mを誇る日本最高峰の山であり、美しい円錐形の形状から日本の象徴として広く知られています。2013年には世界文化遺産に登録されました。",
  "source": {
    "title": "富士山 - Wikipedia",
    "url": "https://ja.wikipedia.org/wiki/%E5%AF%8C%E5%A3%AB%E5%B1%B1"
  }
}
```
『霊峰の象徴』というように作品名でないものを『』で囲ってしまっている。Wikipediaではだれでも編集することができてしまい情報の信憑性が担保できない。後半については、対策として、利用するウェブページを指定した。
```Python
# main.py
import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーを設定
genai.configure(api_key=api_key)

# ----------------------------------------------------
# ↓↓↓ ここから下を書き換えて実験する ↓↓↓
# ----------------------------------------------------

# 使用するモデルを選択
model = genai.GenerativeModel('gemini-2.0-flash') # もしくは 'gemini-pro'

# クイズの生成元となるページのURL
target_url = "https://kotobank.jp/word/%E9%A2%A8%E7%AB%8B%E3%81%A1%E3%81%AC-44764#:~:text=%E3%81%8B%E3%81%9C%E3%81%9F%E3%81%A1%E3%81%AC%E3%80%90%E9%A2%A8%E7%AB%8B%E3%81%A1%E3%81%AC%E3%80%91,-%E5%B0%8F%E8%AA%AC%E3%80%82&text=%E5%A0%80%E8%BE%B0%E9%9B%84%E4%BD%9C%E3%80%82,%E8%A9%A9%E5%8F%A5%E3%81%8B%E3%82%89%E3%81%A8%E3%81%A3%E3%81%9F%E3%82%82%E3%81%AE%E3%80%82" # ← ここを好きなURLに変えて試す

# AIへの指示（プロンプト）
# ここを色々書き換えて、出力がどう変わるか試してみましょう！
prompt_template = """
# 役割
あなたはプロのクイズ作家です。

# タスク
以下の文章を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# 制約条件
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」「出典」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation","source"
・"source"にはウェブページタイトルとURLを含めてください。
・問題の公判で問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・パラレル問題では対照的なキーワードを**強調**してください。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は80文字以内にしてください。
・漢字検定2級以上の語彙には後ろから()でルビを追加してください。
・最初は広い情報から入り、徐々に狭い情報に絞ってください。
・前半に知名度が低い情報、後半に知名度が高い情報を配置してください。

【文章】
{source_text}
"""

# ----------------------------------------------------
# ↑↑↑ ここまでを書き換えて実験する ↑↑↑
# ----------------------------------------------------

def get_text_from_url(url):
    """URLから本文テキストを抽出する関数"""
    try:
        print(f"📄 '{url}' から本文を取得中...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 不要なタグ（スクリプト、スタイルシート、ヘッダー、フッターなど）を削除
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        
        # 本文テキストを取得し、余分な空白を整理
        body_text = soup.get_text(separator='\n', strip=True)
        print("✅ 本文の取得完了！")
        return body_text
    except requests.RequestException as e:
        print(f"❌ URLの取得に失敗しました: {e}")
        return None

# --- メインの処理 ---
# 1. URLから本文を取得
source_text = get_text_from_url(target_url)

if source_text:
    # 2. プロンプトを組み立て
    full_prompt = prompt_template.format(source_text=source_text)

    # 3. Gemini APIを呼び出し
    print("🤖 AIにクイズを生成させています...")
    response = model.generate_content(full_prompt)
    print("✅ 生成が完了しました！")
    print("--- 出力結果 ---")
    print(response.text)
```
```
{
  "question": "堀辰雄(ホリタツオ)の小説で、**婚約者**との生活を通して生の**意味**と幸福感を確立する過程を描き、フランスの詩人バレリーの詩句 から書名をとった作品は何でしょう？",
  "answer": "風立ちぬ",
  "Alternative Solutions/Correctness Judgment Criteria": "カゼタチヌ",
  "explanation": "『風立ちぬ』は堀辰雄の小説で、作者自身の体験を基に、死に直面した状況下での生の意味を追求した作品です。タイトルの由来は、フランスの詩人ポール・ヴァレリーの詩の一節「Le vent se lève!…Il faut tenter de vivre!（風立ちぬ、いざ生きめやも）」から取られています。",
  "source": {
    "ウェブページタイトル": "風立ちぬ(カゼタチヌ)とは？ 意味や使い方 - コトバンク",
    "URL": "https://kotobank.jp/word/%E9%A2%A8%E7%AB%8B%E3%81%A1%E3%81%AC-487863"
  }
}
```
太字の部分が適切ではありません。制約条件が適切に守られていないというところが課題になりました。Self-Refineの仕組みを取り込み、制約条件が適用できているか評価とともに評価させます。
```python
# main.py
import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
import json

# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーを設定
genai.configure(api_key=api_key)

# ----------------------------------------------------
# ↓↓↓ プロンプトとルールの定義 ↓↓↓
# ----------------------------------------------------

# 使用するモデルを選択（実際に利用可能なモデル名にしてください）
model = genai.GenerativeModel('gemini-2.0-flash')

# クイズの生成元となるページのURL
target_url = "https://kotobank.jp/word/%E7%9B%B8%E5%AF%BE%E6%80%A7%E7%90%86%E8%AB%96-89557"

# 制約条件を独立した変数として定義（再利用するため）
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

# --- ① 生成フェーズ用のプロンプト ---
prompt_template_generate = f"""
# 役割
あなたはプロのクイズ作家です。

# タスク
以下の文章を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# 制約条件
{CONSTRAINT_RULES}

# 文章
{{source_text}}
"""

# --- ② 自己評価・修正フェーズ用のプロンプト ---
prompt_template_refine = f"""
# 役割
あなたは、AIが生成したクイズを評価し、修正する品質保証の専門家です。

# タスク
AIが生成した以下の「生成物」が、「制約条件」を完全に満たしているか厳密にチェックしてください。
もし一つでも違反があれば、すべての違反箇所を修正し、制約条件を完全に満たした最終的なJSONオブジェクトのみを出力してください。
もし違反がなければ、元の「生成物」をそのまま出力してください。

# 制約条件
{CONSTRAINT_RULES}

# AIによる生成物
{{draft_quiz}}
"""

# ----------------------------------------------------
# ↑↑↑ プロンプトとルールの定義ここまで ↑↑↑
# ----------------------------------------------------

def get_web_info(url):
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

# --- メインの処理 ---
# 1. URLから本文とタイトルを取得
source_text, source_title = get_web_info(target_url)

if source_text:
    # --- ① 生成フェーズ ---
    print("\n--- ① 生成フェーズ ---")
    prompt_generate = prompt_template_generate.format(source_text=source_text)
    print("🤖 AIにクイズの初稿を生成させています...")
    response_generate = model.generate_content(prompt_generate)
    first_draft_text = response_generate.text
    print("✅ 初稿が完成しました！")
    print(first_draft_text)

    # --- ② 自己評価・修正フェーズ ---
    print("\n--- ② 自己評価・修正フェーズ ---")
    prompt_refine = prompt_template_refine.format(draft_quiz=first_draft_text)
    print("🧐 AIが生成結果を自己評価し、必要なら修正します...")
    response_refine = model.generate_content(prompt_refine)
    
    # 最終的な出力を整形
    final_text = response_refine.text.strip().replace("```json\n", "").replace("\n```", "")
    
    print("✅ 最終版が完成しました！")
    print("\n--- 最終出力結果 ---")
    
    # JSONとしてきれいに整形して表示
    try:
        final_json = json.loads(final_text)
        print(json.dumps(final_json, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("エラー: 最終出力が有効なJSONではありません。")
        print(final_text)
```
```
📄 'https://kotobank.jp/word/%E7%9B%B8%E5%AF%BE%E6%80%A7%E7%90%86%E8%AB%96-89557' から情報を取得中...
✅ 情報の取得完了！

--- ① 生成フェーズ ---
🤖 AIにクイズの初稿を生成させています...
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
E0000 00:00:1760540051.617953   14800 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
✅ 初稿が完成しました！
```json
{
"question": "1905年に発表された**特殊**相対性理論は、光速度不変(コウソクドフヘン)の原理と何という原理に基づいているでしょう？",
"answer": "相対性原理",
"Alternative Solutions/Correctness Judgment Criteria": "相対原理は不可。",
"explanation": "特殊相対性理論は、光速度不変の原理と相対性原理の二つを基本原理としています。一方、一般相対性理論は等価原理と相対性原理に基づいています。",
"source": {
"ウェブページタイトル": "相対性理論(ソウタイセイリロン)とは？ 意味や使い方 - コトバンク",
"URL": "https://kotobank.jp/word/%E7%9B%B8%E5%AF%BE%E6%80%A7%E7%90%86%E8%AB%96-159012"
}
}
```

--- ② 自己評価・修正フェーズ ---
🧐 AIが生成結果を自己評価し、必要なら修正します...
✅ 最終版が完成しました！

--- 最終出力結果 ---
{
  "question": "アインシュタインが1905年に発表した**特殊**相対性理論は、光速度(コウソクド)不変の原理ともう一つは何という原理に基づくでしょう？",
  "answer": "相対性原理",
  "Alternative Solutions/Correctness Judgment Criteria": "相対原理は不可。",
  "explanation": "特殊相対性理論は、光速度不変の原理と相対性原理を基本原理とします。一般相対性理論は等価原理と相対性原理に基づいています。",
  "source": {
    "ウェブページタイトル": "相対性理論とは？ 意味や使い方 - コトバンク",
    "URL": "https://kotobank.jp/word/%E7%9B%B8%E5%AF%BE%E6%80%A7%E7%90%86%E8%AB%96-159012"
  }
}
```
ほかのページでは次のような問題が出力された。
```
{
  "question": "古代ギリシアで都市国家を指す言葉で、アクロポリスやアゴラを中心に発展しましたが、英語で警察を意味する言葉は何でしょう？",
  "answer": "ポリス",
  "Alternative Solutions/Correctness Judgment Criteria": "「ポリス(polis)」「ポリス(police)」の区別は問わない。",
  "explanation": "ポリス（Polis）は古代ギリシアの都市国家を指します。都市の中心部にはアクロポリスやアゴラが設けられました。一方、英語のpoliceは警察を意味します。",      
  "source": [
    {
      "ウェブページタイトル": "ポリス(ぽりす)とは？ 意味や使い方 - コトバンク",
      "URL": "https://kotobank.jp/word/%E3%83%9D%E3%83%AA%E3%82%B9-135644"
    }
  ]
}
{
  "question": "『まんがタイムきららMAX』で連載された、『きららファンタジア』にも登場する、**陰キャ**(いんキャ)な少女が主人公の音楽アニメは何でしょう？",
  "answer": "ぼっち・ざ・ろっく！",
  "Alternative Solutions/Correctness Judgment Criteria": "ぼざろ",
  "explanation": "『ぼっち・ざ・ろっく！』は、はまじあきによる4コマ漫画が原作。2022年にアニメ化。主人公は極度の人見知りの少女、後藤(ごとう)ひとりです。",
  "source": {
    "ウェブページタイトル": "NEWS | 劇場総集編ぼっち・ざ・ろっく！",
    "URL": "https://bocchi.rocks/news/"
  }
}
```
ポリスの問題は構造がうまくできていません。前半では古代ギリシアの都市国家の話をしていて、後半では警察の英名の話をしています。パラレル問題ではないのですが、パラレル問題の形式をとってしまっています。次はLLMのモデルをより上位の`gemini-2.5-flash`にしました。回答は以下の通りです。
```
{
  "question": "人気アニメ『ぼっち・ざ・ろっく！』に登場するバンド『結束バンド』。メンバーの喜多（きた）郁代（いくよ）は**ボーカルとギター**を担当していますが、**ベース**を担当しているのは誰でしょう？",
  "answer": "山田リョウ",
  "Alternative Solutions/Correctness Judgment Criteria": "氏名表記（山田リョウ、やまだりょう、リョウ、りょうなど）のみを正解とします。",
  "explanation": "『ぼっち・ざ・ろっく！』に登場するバンド『結束バンド』は、後藤ひとりがギター、伊地知虹夏がドラム、喜多郁代がボーカルとギター、そして山田リョウがベース を担当しています。彼女はクールな雰囲気で、独特な食生活を送っていることでも知られていますでしょう？",
  "source": {
    "title": "『ぼっち・ざ・ろっく！』公式サイト",
    "url": "https://bocchi.rocks/"
  }
}
```
制約条件の文末表現について、'question'だと指定していなかったので`explanation`の文末が意図せず疑問形になっていました。以下、修正したものです。
```
{
  "question": "政治学の母胎（ぼたい）ともなった古代ギリシアの**都市国家**ですが、スティングがボーカルのイギリスの**ロックバンド**は何でしょう？",
  "answer": "ポリス",
  "Alternative Solutions/Correctness Judgment Criteria": "カタカナ表記の「ポリス」で正解とします。",
  "explanation": "「ポリス（polis）」は、紀元前8世紀頃に成立し、紀元前5世紀を頂点として繁栄した古代ギリシアの都市国家を指します。中心市と周辺の農村から成り、自由と自治を理想としました。アテネやスパルタなどがその典型として知られ、政治学（politics）の語源にもなっています。\n一方、イギリスのロックバンド「ポリス（The Police）」は、スティン グ（ボーカル、ベース）、アンディ・サマーズ（ギター）、スチュアート・コープランド（ドラム）からなるニュー・ウェーブの代表的なグループです。1978年にデビューし、レゲエのリ ズムを取り入れた楽曲と卓越した演奏技術で人気を博しました。『白いレガッタ』や『シンクロニシティー』などのヒットアルバムを残しています。",
  "source": {
    "title": "ポリス(ぽりす)とは？ 意味や使い方 - コトバンク",
    "url": "https://kotobank.jp/word/%E3%83%9D%E3%83%BC%E3%83%AA%E3%82%B9-623253"
  }
}
{
  "question": "**日本では**鼓手長（こしゅちょう）とも呼ばれますが、鼓笛隊の先頭で指揮杖（しきじょう）を持つ者を、**英語では**何と呼ぶでしょう？",
  "answer": "ドラム・メジャー",
  "Alternative Solutions/Correctness Judgment Criteria": "カタカナ表記の「ドラム・メジャー」を正解とします。英語表記の「Drum Major」も正解とします。日本語の「鼓手長（こ しゅちょう）」は不正解です。",
  "explanation": "ドラム・メジャーは、鼓笛隊（こてきたい）やマーチングバンドの先頭に立ち、指揮杖（バトン）を振って行進のテンポや演技全体を指揮する役割を担います。日本語 では「鼓手長（こしゅちょう）」とも呼ばれることがあります。",
  "source": {
    "title": "ドラム・メジャー(どらむめじゃー)とは？ 意味や使い方 - コトバンク",
    "url": "https://kotobank.jp/word/ドラム・メジャー-101150"
  }
}
```
パラレル問題に関して、やはり制約を守らせるのは難しかった。`gemini-2.5-pro`にすると以下のようになった。
```
{
  "question": "パレードで華やかに**バトンを回す人**をバトン・トワラーと言いますが、先頭でバンド全体を導く**杖を持った指揮者**のことを何というでしょう？",
  "answer": "ドラム・メジャー",
  "Alternative Solutions/Correctness Judgment Criteria": "別解はありません。",
  "explanation": "ドラム・メジャーは、鼓笛隊やマーチングバンドの行進の際に先頭に立ち、指揮杖（メイスやバトン）を使い指揮をする人のことです。日本語では「鼓手長（こしゅち ょう）」と呼ばれます。問題文に出てきたバトン・トワラーは、指揮ではなく、バトンを回すなどの演技（トワーリング）を専門に行う人を指します。",
  "source": {
    "title": "ドラム・メジャー(どらむめじゃー)とは？ 意味や使い方 - コトバンク",
    "url": "https://kotobank.jp/word/ドラム・メジャー-104449"
  }
}
{
  "question": "**浮世絵師**としての名は北尾政演ですが、**戯作者**(げさくしゃ)として『江戸生艶気樺焼』などを著し、寛政の改革で処罰(しょばつ)されたのは誰でしょう？",      
  "answer": "山東京伝",
  "Alternative Solutions/Correctness Judgment Criteria": "「さんとうきょうでん」とひらがなでの解答も正解とします。本名である「岩瀬醒（いわせさむる）」は不可とします。", 
  "explanation": "山東京伝は江戸時代後期の戯作者(げさくしゃ)、浮世絵師です。浮世絵師としては北尾重政に師事(しじ)し、北尾政演（きたお まさのぶ）と名乗りました。戯作者(げ さくしゃ)としては黄表紙の『江戸生艶気樺焼（えどうまれうわきのかばやき）』や洒落本の『通言総籬（つうげんそうまがき）』などの代表作があります。1791年、寛政の改革における出版統制令に触れ、洒落本3部作を出版した罪で手鎖(てじょう)50日の刑罰を受けました。",
  "source": {
    "title": "山東京伝(サントウキョウデン)とは？ 意味や使い方 - コトバンク",
    "url": "https://kotobank.jp/word/%E5%B1%B1%E6%9D%B1%E4%BA%AC%E4%BC%9D-69830"
  }
}
```
(3)
## 分かったこと・わからなかったこと
### わかったこと
- プロンプトの具体性と構造が品質を大きく左右しました。単純な指示では、意図しない形式や質の低い問題が生成されがちでしたが、具体的な制作手引きを制約条件に組み込むことで出力の質が向上しました。
- Webスクレイピングによる情報提供が不可欠でした。モデル内部の知識に頼ると、不確かな情報源から引用をしたり、ハルシネーションを起こすことがありました。
- Self-Refineは制約条件の適用漏れに対して有効でした。

# わからなかったこと
- 言語を理解しているわけではないので、文構造が一部不自然になることが多かった。対比構造でないのに文法的には対比構造であることや対比構造の後に文章が続いて質問になることが多発した。文法的に不自然でない文章を生成する方法がわからなかった。
- コストとバランスについては未調査
- 説明文などについても検証不足。変であるところは多々あった。
- 現状では、参考情報がGemini内部の情報とURLのサイトの情報だけでした。ほかのページを絡ませれば今より幅が広がりそうです。

# 工夫するには何をすればいいのか
- LLMの仕組みを理解し、どんなプロンプトや手順を利用するのが有効かを探る