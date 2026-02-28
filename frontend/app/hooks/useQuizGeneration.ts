/**
 * クイズ生成とstate管理のカスタムフック
 */

import { useState, useEffect } from "react";
import { QuizData, QuizHistory, ResolvedSource } from "../lib/types";
import {
  CATEGORIES,
  DIFFICULTY_OPTIONS,
  LENGTH_OPTIONS,
  MAX_ANSWER_LENGTH,
  TOPIC_MAX_LENGTH,
} from "../lib/constants";
import { getHistory, addHistoryEntry, clearHistory } from "../lib/storage";
import {
  fetchResolveSource,
  fetchGenerateQuiz,
  GenerateQuizFieldErrors,
} from "../lib/api";
import { normalizeAnswer } from "../lib/utils";
import { validateGenerateOptionalFields } from "../lib/generateOptions";

export function useQuizGeneration() {
  // カテゴリとオプション
  const [category, setCategory] = useState<string>("");
  const [sourceUrl, setSourceUrl] = useState<string>("");
  const [questionCount, setQuestionCount] = useState<number>(1);

  // 生成オプション（新フィールド）
  const [difficulty, setDifficulty] = useState<string>("");
  const [length, setLength] = useState<string>("");
  const [genre, setGenre] = useState<string>("");
  const [topic, setTopic] = useState<string>("");

  // クイズデータ
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [questions, setQuestions] = useState<QuizData[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);

  // URL解決
  const [resolvedSource, setResolvedSource] = useState<ResolvedSource | null>(null);
  const [selectedQuote, setSelectedQuote] = useState<string>("");

  // UI状態
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<GenerateQuizFieldErrors>({});

  // 回答と判定
  const [userAnswer, setUserAnswer] = useState<string>("");
  const [judgmentResult, setJudgmentResult] = useState<"correct" | "incorrect" | null>(null);
  const [showAnswer, setShowAnswer] = useState<boolean>(false);

  // 履歴
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [history, setHistory] = useState<QuizHistory[]>([]);

  const handleDifficultyChange = (value: string) => {
    setDifficulty(value);
    setFieldErrors((prev) => ({ ...prev, difficulty: undefined }));
  };

  const handleLengthChange = (value: string) => {
    setLength(value);
    setFieldErrors((prev) => ({ ...prev, length: undefined }));
  };

  const handleGenreChange = (value: string) => {
    setGenre(value);
    setFieldErrors((prev) => ({ ...prev, genre: undefined }));
  };

  const handleTopicChange = (value: string) => {
    setTopic(value);
    const trimmed = value.trim();
    setFieldErrors((prev) => ({
      ...prev,
      topic: /[\r\n]/.test(trimmed)
        ? "トピックは改行せず1行で入力してください。"
        : trimmed.length > TOPIC_MAX_LENGTH
          ? `トピックは${TOPIC_MAX_LENGTH}文字以内で入力してください。`
          : undefined,
    }));
  };

  // 初回レンダリング時に履歴を読み込む
  useEffect(() => {
    setHistory(getHistory());
  }, []);

  // URL本文取得（二段階フロー：ステップ1）
  const handleResolveSource = async () => {
    console.log("[DEBUG] handleResolveSource started");
    console.log("[DEBUG] sourceUrl:", sourceUrl);

    if (!sourceUrl.trim()) {
      setError("URLを入力してください。");
      return;
    }

    setError("");
    setIsLoading(true);
    setResolvedSource(null);
    setSelectedQuote("");

    try {
      const data = await fetchResolveSource(sourceUrl);
      setResolvedSource(data);

      // 最初のquoteをデフォルト選択
      if (data.quotes && data.quotes.length > 0) {
        setSelectedQuote(data.quotes[0]);
        console.log("[DEBUG] Default quote selected");
      }
    } catch (error: any) {
      console.error("[DEBUG] handleResolveSource error:", error);
      setError(
        error.message || "URL本文の取得に失敗しました。URLが正しいか、サーバーが起動しているか確認してください。"
      );
    } finally {
      setIsLoading(false);
      console.log("[DEBUG] handleResolveSource finished");
    }
  };

  // URL未入力時にジャンルからURLを補完する関数
  const ensureSourceUrl = async (
    inputUrl: string,
    selectedGenre: string,
    selectedTopic?: string,
  ): Promise<string> => {
    // URL入力済みの場合はそのまま返す
    if (inputUrl && inputUrl.trim()) {
      console.log("[URL補完] URL入力済み、補完不要");
      return inputUrl.trim();
    }

    // URL未入力の場合、ジャンルからURL候補を取得
    console.log("[URL補完] URL未入力、ジャンルから補完:", selectedGenre);

    try {
      const params = new URLSearchParams({
        genre: selectedGenre,
        k: "1",
      });
      if (selectedTopic && selectedTopic.trim()) {
        params.set("topic", selectedTopic.trim());
      }
      const res = await fetch(`/api/suggest-source?${params.toString()}`);

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      if (!data.urls || data.urls.length === 0) {
        throw new Error(`ジャンル「${selectedGenre}」にはURLが登録されていません`);
      }

      const suggestedUrl = data.urls[0];
      console.log("[URL補完] 補完されたURL:", suggestedUrl);

      return suggestedUrl;
    } catch (error: any) {
      console.error("[URL補完] エラー:", error);
      throw new Error(
        error.message || `ジャンル「${selectedGenre}」からのURL取得に失敗しました`
      );
    }
  };

  // クイズ生成
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

    const optionalValidation = validateGenerateOptionalFields({
      difficulty,
      length,
      genre,
      topic,
    });
    const hasFieldError = Object.values(optionalValidation.errors).some(Boolean);

    setFieldErrors(optionalValidation.errors);
    if (hasFieldError) {
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

    try {
      // カテゴリから日本語ジャンル名を取得
      const selectedGenre = CATEGORIES.find(cat => cat.value === category)?.label || "";
      if (!selectedGenre) {
        setError("無効なカテゴリが選択されています。");
        setIsLoading(false);
        return;
      }

      // URL未入力の場合、ジャンルからURLを補完
      let effectiveUrl = sourceUrl;
      if (!sourceUrl || !sourceUrl.trim()) {
        console.log("[クイズ生成] URL未入力、補完を試みます...");
        try {
          effectiveUrl = await ensureSourceUrl(
            sourceUrl,
            selectedGenre,
            optionalValidation.payload.topic,
          );
          // UI上のsourceUrlに反映（ユーザーに見えるようにする）
          setSourceUrl(effectiveUrl);
          console.log("[クイズ生成] URL補完完了:", effectiveUrl);
        } catch (error: any) {
          setError(error.message || "URLの補完に失敗しました。");
          setIsLoading(false);
          return;
        }
      }

      // URLが確定したので、本文を取得
      console.log("[クイズ生成] URL確定:", effectiveUrl);

      // resolvedSourceが未設定、または異なるURLの場合は、本文を取得
      if (!resolvedSource || resolvedSource.url !== effectiveUrl) {
        console.log("[クイズ生成] 本文を取得中...");
        try {
          const data = await fetchResolveSource(effectiveUrl);
          setResolvedSource(data);

          // 最初のquoteをデフォルト選択
          if (data.quotes && data.quotes.length > 0) {
            setSelectedQuote(data.quotes[0]);
          }
        } catch (error: any) {
          setError(error.message || "URL本文の取得に失敗しました。");
          setIsLoading(false);
          return;
        }
      }

      // resolvedSourceが未設定の場合（通常は上のロジックで設定されているはず）
      if (!resolvedSource) {
        setError("URL本文の取得に失敗しました。内部エラーです。");
        setIsLoading(false);
        return;
      }

      // クイズ生成APIを呼び出す
      // difficulty/length は "" → undefined に変換して union 型と整合させる（Req 4.5）
      const data = await fetchGenerateQuiz({
        category,
        questionCount,
        sourceUrl: effectiveUrl,  // 補完されたURLまたは入力されたURLを使用
        selectedQuote,
        difficulty: optionalValidation.payload.difficulty as (typeof DIFFICULTY_OPTIONS)[number] | undefined,
        length: optionalValidation.payload.length as (typeof LENGTH_OPTIONS)[number] | undefined,
        genre: optionalValidation.payload.genre,
        topic: optionalValidation.payload.topic,
      });

      // レスポンス形式に応じた処理
      if (questionCount === 1) {
        // 単問の場合: オブジェクトをそのまま保存
        setQuiz(data as QuizData);
      } else {
        // 複数問の場合: {"questions": [...]} 形式
        const responseData = data as { questions: QuizData[] };
        if (responseData.questions && Array.isArray(responseData.questions)) {
          setQuestions(responseData.questions);
          setCurrentQuestionIndex(0);
          // 最初の問題を表示
          if (responseData.questions.length > 0) {
            setQuiz(responseData.questions[0]);
          }
        } else {
          throw new Error("複数問生成のレスポンス形式が不正です。");
        }
      }
    } catch (error: any) {
      console.error(error);
      setError(error.message || "不明なエラーが発生しました。");
    } finally {
      setIsLoading(false); // ローディング終了
    }
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

  // 履歴クリア
  const handleClearHistory = () => {
    if (confirm("本当に履歴をすべて削除しますか？")) {
      clearHistory();
      setHistory([]);
    }
  };

  // 問題ナビゲーション（複数問モード）
  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      const newIndex = currentQuestionIndex - 1;
      setCurrentQuestionIndex(newIndex);
      setQuiz(questions[newIndex]);
      setUserAnswer("");
      setJudgmentResult(null);
      setShowAnswer(false);
    }
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      const newIndex = currentQuestionIndex + 1;
      setCurrentQuestionIndex(newIndex);
      setQuiz(questions[newIndex]);
      setUserAnswer("");
      setJudgmentResult(null);
      setShowAnswer(false);
    }
  };

  return {
    // State
    category,
    setCategory,
    sourceUrl,
    setSourceUrl,
    questionCount,
    setQuestionCount,

    // 生成オプション（新フィールド）
    difficulty,
    setDifficulty: handleDifficultyChange,
    length,
    setLength: handleLengthChange,
    genre,
    setGenre: handleGenreChange,
    topic,
    setTopic: handleTopicChange,
    fieldErrors,

    quiz,
    questions,
    currentQuestionIndex,
    resolvedSource,
    selectedQuote,
    setSelectedQuote,
    isLoading,
    error,
    setError,
    userAnswer,
    setUserAnswer,
    judgmentResult,
    showAnswer,
    showHistory,
    setShowHistory,
    history,

    // Handlers
    handleResolveSource,
    handleGenerate,
    handleSubmitAnswer,
    handleClearHistory,
    handlePreviousQuestion,
    handleNextQuestion,
  };
}
