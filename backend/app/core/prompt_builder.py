"""
プロンプト生成ロジック
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.agent.state import ClaimEntry, EvidenceEntry


def build_constraint_rules(max_length: int = 80) -> str:
    """
    制約条件文字列を生成する。
    max_length で問題文の文字数制限を動的に変更できる（デフォルト 80 で既存動作を維持）。
    """
    return f"""
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation"
・sourceについては後述の指示に従ってください。
・問題の後半で問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・問題文は1文で作成してください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・パラレル問題では対照的なキーワードを**強調**してください。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は{max_length}文字以内にしてください。
・漢字検定2級程度の語彙には後ろから()でルビを追加してください。
・最初は広い情報から入り、徐々に狭い情報に絞ってください。
・前半に知名度が低い情報、後半に知名度が高い情報を配置してください。
"""


def build_prompt_url_mode(
    category_name: str,
    url: str,
    title: str,
    text_excerpt: str,
    quotes: List[str],
    question_count: int,
    difficulty: str = "normal",
    length_option: str = "medium",
    topic: Optional[str] = None,
) -> str:
    """
    URLモード用のプロンプトを生成

    重要: LLMには「URLとquoteを選ぶ」責任を与えない。
           サーバが決めたURL・quote候補のみを使わせる。
    """
    # length_option に応じた文字数制限
    length_map = {"short": 40, "medium": 80, "long": 150}
    max_length = length_map.get(length_option, 80)
    constraint_rules = build_constraint_rules(max_length=max_length)

    # difficulty 別指示文
    difficulty_instructions = {
        "easy": "一般の人が答えられる、広く知られた事実に基づく問題を生成してください。（かんたんレベル）",
        "normal": "競技クイズで使えるような、特定の専門知識を要するレベルの問題を生成してください。（ふつうレベル）",
        "hard": "専門家のみが知るような詳細またはニッチな知識を要する問題を生成してください。（むずかしいレベル）",
    }
    difficulty_text = difficulty_instructions.get(difficulty, difficulty_instructions["normal"])

    if question_count == 1:
        output_format = """
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**厳密なJSON形式のオブジェクト**である必要があります。
・JSONのキーは必ずダブルクオート（"）で囲んでください。シングルクオート（'）は使用禁止です。
・JSONの最後の要素の後にカンマ（,）を付けないでください。
・形式: {"question": "...", "answer": "...", "Alternative Solutions/Correctness Judgment Criteria": "...", "explanation": "...", "source": {"title": "...", "url": "...", "quote": "..."}}
"""
    else:
        output_format = f"""
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**{question_count}問のクイズを含むJSON配列**である必要があります。
・JSONのキーは必ずダブルクオート（"）で囲んでください。シングルクオート（'）は使用禁止です。
・JSONの最後の要素の後にカンマ（,）を付けないでください。
・形式: [{{"question": "...", "answer": "...", ...}}, {{"question": "...", "answer": "...", ...}}]
"""

    # quote候補をリスト化
    quote_list = "\n".join([f"  {i+1}. {q[:100]}..." for i, q in enumerate(quotes[:5])])

    # topic 指示セクション（指定がある場合のみ追加）
    topic_section = ""
    if topic is not None:
        topic_section = f"""
# トピック指示
・このクイズは「{topic}」に絞ったトピックで作成してください。
・問題文と解答は、必ず下記「ページ本文（抜粋）」で裏付け可能な情報に限定してください。本文中に存在しない外部知識は、たとえトピックに関連していても使用しないこと。
"""

    prompt = f"""
# 役割
あなたはプロのクイズ作家であり、厳密なJSONの専門家です。

# タスク
以下のURL本文**のみ**を根拠に、競技クイズで使えるような本格的なクイズを作成してください。

# 難易度指示
{difficulty_text}

# 制約条件
{constraint_rules}
{topic_section}
# 参照元（サーバ指定・変更禁止）
・URL: {url}
・タイトル: {title}
・カテゴリ: {category_name}

# ページ本文（抜粋）
```
{text_excerpt[:3000]}
```

# source フィールドの指示（重要）
・"source" は以下の形式で出力してください：
  {{"title": "{title}", "url": "{url}", "quote": "..."}}
・"source"."url" は必ず上記のURL（{url}）をそのままコピーしてください。**絶対に変更・捏造しないでください**。
・"source"."title" は必ず上記のタイトル（{title}）をそのままコピーしてください。
・"source"."quote" には、上記ページ本文から引用した**実際に存在する文章**を30〜150文字程度で設定してください。
・**重要**: "quote"は、上記「ページ本文（抜粋）」に**完全一致する部分文字列**でなければなりません。存在しない文章を作らないでください。
・以下の候補から選ぶか、本文中の別の部分を使用してください：
{quote_list}

{output_format}

# 最重要ルール
・あなたの応答は、**厳密なJSON RFC 8259準拠**である必要があります。
・キーは必ずダブルクオート（"）で囲む。
・文字列値も必ずダブルクオート（"）で囲む。
・末尾カンマ禁止。
・制御文字禁止。
"""
    return prompt


def build_prompt_category_mode(category_name: str, question_count: int) -> str:
    """
    カテゴリモード用のプロンプトを生成

    カテゴリモードでは、LLMに参照元URLを選ばせる（既存の動作を維持）
    """
    constraint_rules = build_constraint_rules()

    if question_count == 1:
        output_format = """
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**厳密なJSON形式のオブジェクト**である必要があります。
・形式: {"question": "...", "answer": "...", "Alternative Solutions/Correctness Judgment Criteria": "...", "explanation": "...", "source": {"title": "...", "url": "...", "quote": ""}}
"""
    else:
        output_format = f"""
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**{question_count}問のクイズを含むJSON配列**である必要があります。
・形式: [{{"question": "...", "answer": "...", ...}}, {{"question": "...", "answer": "...", ...}}]
"""

    prompt = f"""
# 役割
あなたはプロのクイズ作家であり、厳密なJSONの専門家です。

# タスク
「{category_name}」のカテゴリで、競技クイズで使えるような本格的なクイズを作成してください。

# 制約条件
{constraint_rules}

# source フィールドの指示
・"source" は以下の形式で出力してください：
  {{"title": "トピック名", "url": "参照URL", "quote": ""}}
・"source"."url" には、必ずコトバンク（https://kotobank.jp）または公式サイト（*.go.jp、*.ac.jp）のURLを使用してください。
・ブログ、まとめサイト、SNS、Q&Aサイトは使用禁止です。
・適切なURLが見つからない場合は、"url"に「参照URLを提示できません」と記載してください。
・"quote" はカテゴリモードでは空文字列（""）で構いません。

{output_format}

# 最重要ルール
・あなたの応答は、**厳密なJSON RFC 8259準拠**である必要があります。
・キーは必ずダブルクオート（"）で囲む。
・文字列値も必ずダブルクオート（"）で囲む。
・末尾カンマ禁止。
"""
    return prompt


# ---- 検証ループ用プロンプトビルダー (Task 2.1 / 2.2 / 2.3) ----

def build_prompt_decompose_claims(quiz_text: str) -> str:
    """
    quiz_text から原子的主張リストを生成するプロンプトを返す。

    Args:
        quiz_text: QUESTION / EXPLANATION / ALTERNATIVE を固定区切りで結合した文字列

    Returns:
        LLM に送信するプロンプト文字列。
        LLM は [{"text": "..."}, ...] 形式の JSON 配列を返す。
    """
    return f"""以下のクイズから、検証可能な原子的主張（事実の命題）を日本語で列挙してください。

【クイズ】
{quiz_text}

【指示】
- 各主張は「主語＋述語」を含む1文の自然言語で表現してください。
- 主張は最大5件まで抽出してください。
- 重複や自明な主張は除外してください。

【出力形式】
JSON配列のみを出力してください（説明文・コードブロック不要）:
[{{"text": "主張の文章"}}, ...]
"""


def build_prompt_verify_claim(claim: ClaimEntry, evidences: list[EvidenceEntry]) -> str:
    """
    1つの主張と根拠エントリ群から pass/fail 判定プロンプトを返す。

    Args:
        claim: 検証対象の主張（ClaimEntry）
        evidences: 根拠エントリのリスト（rank 昇順・最大 3 件を使用、quote は先頭 500 文字に切り詰め）

    Returns:
        LLM に送信するプロンプト文字列。
        LLM は {"verdict": "pass"|"fail", "reason": "..."} を返す。
    """
    # rank 昇順で最大 3 件、quote を先頭 500 文字に切り詰め
    sorted_evidences = sorted(evidences, key=lambda e: e["rank"])[:3]

    evidence_text = ""
    for i, ev in enumerate(sorted_evidences, 1):
        quote = ev["quote"][:500]
        evidence_text += f"\n【根拠{i}】URL: {ev['url']}\n引用: {quote}\n"

    if not evidence_text:
        evidence_text = "\n（根拠なし）\n"

    return f"""以下の主張が根拠に基づいて正しいかどうか判定してください。

【主張】
{claim['text']}

【根拠】{evidence_text}
【指示】
- 根拠テキストに基づいて主張の正確性を判定してください。
- 根拠がない場合や根拠が主張を支持しない場合は fail としてください。

【出力形式】
JSONオブジェクトのみを出力してください（説明文・コードブロック不要）:
{{"verdict": "pass" または "fail", "reason": "判定理由（fail の場合は必須・非空）"}}
"""


def build_prompt_rewrite_quiz(quiz_text: str, failed_claims: list[dict]) -> str:
    """
    fail した主張情報を踏まえて問題を書き換えるプロンプトを返す。

    Args:
        quiz_text: 現在の問題文（QUESTION / EXPLANATION / ALTERNATIVE 区切り形式）
        failed_claims: [{"claim_id": str, "text": str, "reason": str}] の失敗主張リスト

    Returns:
        LLM に送信するプロンプト文字列。
        LLM は QuizData 互換 JSON を返す。
    """
    failed_text = ""
    for fc in failed_claims:
        failed_text += f"\n- 主張: {fc['text']}\n  理由: {fc['reason']}\n"

    return f"""以下のクイズに事実誤認が含まれています。事実誤認を修正した新しいクイズを生成してください。

【現在のクイズ】
{quiz_text}

【事実誤認の主張と理由】{failed_text}
【指示】
- 上記の事実誤認を修正してください。
- クイズの形式（問題文・正解・別解・解説）を維持してください。
- 修正後も事実的に正確な内容にしてください。

【出力形式】
JSONオブジェクトのみを出力してください（説明文・コードブロック不要）:
{{"question": "問題文", "answer": "正解", "Alternative Solutions/Correctness Judgment Criteria": "別解/正誤判定基準", "explanation": "解説", "source": {{"url": "URL", "quote": "引用"}}}}
"""
