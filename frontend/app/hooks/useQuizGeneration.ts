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
import { TabGenerateRequest, DEFAULT_CATEGORY } from "../lib/tabGenerate";

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
  const [answerPackage, setAnswerPackage] = useState<Record<string, unknown> | null>(null);
  const [lastInputParams, setLastInputParams] = useState<Record<string, unknown> | null>(null);
  const [questionAnswerPackages, setQuestionAnswerPackages] = useState<Record<string, unknown>[]>([]);
  const [questionInputParams, setQuestionInputParams] = useState<Record<string, unknown>[]>([]);

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

  // URL候補をジャンルから取得する関数
  const suggestSourceUrls = async (
    selectedGenre: string,
    k: number,
    selectedTopic?: string,
  ): Promise<string[]> => {
    try {
      const params = new URLSearchParams({
        genre: selectedGenre,
        k: String(k),
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

      const urls = Array.from(
        new Set(
          (data.urls as string[])
            .map((url) => url.trim())
            .filter((url) => url.length > 0)
        )
      );

      if (urls.length === 0) {
        throw new Error(`ジャンル「${selectedGenre}」には有効なURLが登録されていません`);
      }

      return urls;
    } catch (error: any) {
      console.error("[URL補完] エラー:", error);
      throw new Error(
        error.message || `ジャンル「${selectedGenre}」からのURL取得に失敗しました`
      );
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
    const suggestedUrls = await suggestSourceUrls(selectedGenre, 1, selectedTopic);
    return suggestedUrls[0];
  };

  const resolvePackageId = (pkg: Record<string, unknown>, fallback: string): string => {
    const raw = pkg.package_id;
    if (typeof raw === "string" && raw.trim()) {
      return raw;
    }
    return fallback;
  };

  const buildInputParams = (params: {
    mode: "category" | "url" | "keyword";
    category: string;
    sourceUrl: string;
    selectedQuote: string;
    difficulty?: string;
    length?: string;
    keyword?: string;
  }): Record<string, unknown> => ({
    mode: params.mode,
    category: params.category,
    source_url: params.sourceUrl,
    selected_quote: params.selectedQuote,
    question_count: 1,
    difficulty: params.difficulty,
    length: params.length,
    keyword: params.keyword,
  });

  // クイズ生成（タブ別 dispatch）
  const handleGenerate = async (request: TabGenerateRequest) => {
    if (isLoading) {
      return;
    }

    setQuiz(null);
    setQuestions([]);
    setCurrentQuestionIndex(0);
    setAnswerPackage(null);
    setLastInputParams(null);
    setQuestionAnswerPackages([]);
    setQuestionInputParams([]);
    setError("");
    setIsLoading(true);
    setShowAnswer(false);
    setUserAnswer("");
    setJudgmentResult(null);

    try {
      if (request.mode === "category") {
        // category mode: category state が空なら終了
        if (!category) {
          setError("カテゴリを選択してください。");
          setIsLoading(false);
          return;
        }
        const genre = CATEGORIES.find((c) => c.value === category)?.label;
        if (!genre) {
          setError("無効なカテゴリが選択されています。");
          setIsLoading(false);
          return;
        }

        if (request.options.questionCount === 1) {
          const suggestedUrl = await ensureSourceUrl("", genre);
          const resolveData = await fetchResolveSource(suggestedUrl);
          setResolvedSource(resolveData);
          const quoteToSend = resolveData.quotes[0] ?? "";
          setSelectedQuote(quoteToSend);
          const data = await fetchGenerateQuiz({
            category,
            questionCount: 1,
            sourceUrl: suggestedUrl,
            selectedQuote: quoteToSend,
            difficulty: (request.options.difficulty || undefined) as (typeof DIFFICULTY_OPTIONS)[number] | undefined,
            length: (request.options.length || undefined) as (typeof LENGTH_OPTIONS)[number] | undefined,
          });
          applyQuizResponse(data, 1);

          const singlePackage = data as Record<string, unknown>;
          const singleInputParams = buildInputParams({
            mode: "category",
            category,
            sourceUrl: suggestedUrl,
            selectedQuote: quoteToSend,
            difficulty: request.options.difficulty || undefined,
            length: request.options.length || undefined,
          });
          setAnswerPackage(singlePackage);
          setLastInputParams(singleInputParams);
          setQuestionAnswerPackages([singlePackage]);
          setQuestionInputParams([singleInputParams]);
        } else {
          const requestedCount = request.options.questionCount;
          const rawUrls = await suggestSourceUrls(genre, Math.min(10, requestedCount * 2));
          const uniqueUrls = Array.from(new Set(rawUrls));

          if (uniqueUrls.length < requestedCount) {
            throw new Error(
              `カテゴリ「${genre}」で重複なしに${requestedCount}問を作るための参照ページが不足しています（利用可能: ${uniqueUrls.length}件）。問題数を減らしてください。`
            );
          }

          const selectedUrls = uniqueUrls.slice(0, requestedCount);
          const generatedQuestions: QuizData[] = [];
          const generatedPackages: Record<string, unknown>[] = [];
          const generatedInputParams: Record<string, unknown>[] = [];

          for (const sourceUrl of selectedUrls) {
            const resolveData = await fetchResolveSource(sourceUrl);
            const quoteToSend = resolveData.quotes[0] ?? "";
            const oneQuestionData = await fetchGenerateQuiz({
              category,
              questionCount: 1,
              sourceUrl,
              selectedQuote: quoteToSend,
              difficulty: (request.options.difficulty || undefined) as (typeof DIFFICULTY_OPTIONS)[number] | undefined,
              length: (request.options.length || undefined) as (typeof LENGTH_OPTIONS)[number] | undefined,
            });

            const rawPackage = oneQuestionData as Record<string, unknown>;
            const fallbackId = `pkg_${Date.now()}_${generatedPackages.length + 1}`;
            const packageId = resolvePackageId(rawPackage, fallbackId);
            const normalizedPackage = {
              ...rawPackage,
              package_id: packageId,
            };

            generatedQuestions.push(normalizedPackage as unknown as QuizData);
            generatedPackages.push(normalizedPackage);
            generatedInputParams.push(
              buildInputParams({
                mode: "category",
                category,
                sourceUrl,
                selectedQuote: quoteToSend,
                difficulty: request.options.difficulty || undefined,
                length: request.options.length || undefined,
              })
            );
            setResolvedSource(resolveData);
            setSelectedQuote(quoteToSend);
          }

          setQuestions(generatedQuestions);
          setCurrentQuestionIndex(0);
          setQuiz(generatedQuestions[0] ?? null);
          setQuestionAnswerPackages(generatedPackages);
          setQuestionInputParams(generatedInputParams);
          setAnswerPackage(generatedPackages[0] ?? null);
          setLastInputParams(generatedInputParams[0] ?? null);
        }

      } else if (request.mode === "url") {
        // url mode: sourceUrl state が空なら終了
        if (!sourceUrl.trim()) {
          setError("URLを入力してください。");
          setIsLoading(false);
          return;
        }
        let quoteToSend: string;
        if (resolvedSource?.url !== sourceUrl) {
          const resolveData = await fetchResolveSource(sourceUrl);
          setResolvedSource(resolveData);
          quoteToSend = resolveData.quotes[0] ?? "";
          setSelectedQuote(quoteToSend);
        } else {
          quoteToSend = selectedQuote;
        }
        const data = await fetchGenerateQuiz({
          category: DEFAULT_CATEGORY,
          questionCount: request.options.questionCount,
          sourceUrl,
          selectedQuote: quoteToSend,
          difficulty: (request.options.difficulty || undefined) as (typeof DIFFICULTY_OPTIONS)[number] | undefined,
          length: (request.options.length || undefined) as (typeof LENGTH_OPTIONS)[number] | undefined,
        });

        if (request.options.questionCount === 1) {
          applyQuizResponse(data, 1);
          const singlePackage = data as Record<string, unknown>;
          const singleInputParams = buildInputParams({
            mode: "url",
            category: DEFAULT_CATEGORY,
            sourceUrl,
            selectedQuote: quoteToSend,
            difficulty: request.options.difficulty || undefined,
            length: request.options.length || undefined,
          });
          setAnswerPackage(singlePackage);
          setLastInputParams(singleInputParams);
          setQuestionAnswerPackages([singlePackage]);
          setQuestionInputParams([singleInputParams]);
        } else {
          const responseData = data as { questions: QuizData[]; package_id?: string };
          if (!responseData.questions || !Array.isArray(responseData.questions)) {
            throw new Error("複数問生成のレスポンス形式が不正です。");
          }

          const basePackageId =
            typeof responseData.package_id === "string" && responseData.package_id.trim()
              ? responseData.package_id
              : `pkg_${Date.now()}`;

          const generatedPackages = responseData.questions.map((q, index) => ({
            ...q,
            package_id: `${basePackageId}_q${index + 1}`,
          }));

          const generatedInputParams = responseData.questions.map((q) =>
            buildInputParams({
              mode: "url",
              category: DEFAULT_CATEGORY,
              sourceUrl: q.source?.url || sourceUrl,
              selectedQuote: q.source?.quote || quoteToSend,
              difficulty: request.options.difficulty || undefined,
              length: request.options.length || undefined,
            })
          );

          setQuestions(responseData.questions);
          setCurrentQuestionIndex(0);
          setQuiz(responseData.questions[0] ?? null);
          setQuestionAnswerPackages(generatedPackages);
          setQuestionInputParams(generatedInputParams);
          setAnswerPackage(generatedPackages[0] ?? null);
          setLastInputParams(generatedInputParams[0] ?? null);
        }

      } else {
        // keyword mode: request.keyword が空なら終了
        if (!request.keyword.trim()) {
          setError("キーワードを入力してください。");
          setIsLoading(false);
          return;
        }
        const nonSectionLabel = CATEGORIES.find((c) => c.value === DEFAULT_CATEGORY)?.label ?? "";
        const suggestedUrl = await ensureSourceUrl("", nonSectionLabel, request.keyword);
        const resolveData = await fetchResolveSource(suggestedUrl);
        setResolvedSource(resolveData);
        const quoteToSend = resolveData.quotes[0] ?? "";
        setSelectedQuote(quoteToSend);
        const data = await fetchGenerateQuiz({
          category: DEFAULT_CATEGORY,
          questionCount: request.options.questionCount,
          sourceUrl: suggestedUrl,
          selectedQuote: quoteToSend,
          difficulty: (request.options.difficulty || undefined) as (typeof DIFFICULTY_OPTIONS)[number] | undefined,
          length: (request.options.length || undefined) as (typeof LENGTH_OPTIONS)[number] | undefined,
          topic: request.keyword,
        });

        if (request.options.questionCount === 1) {
          applyQuizResponse(data, 1);
          const singlePackage = data as Record<string, unknown>;
          const singleInputParams = buildInputParams({
            mode: "keyword",
            category: DEFAULT_CATEGORY,
            sourceUrl: suggestedUrl,
            selectedQuote: quoteToSend,
            difficulty: request.options.difficulty || undefined,
            length: request.options.length || undefined,
            keyword: request.keyword,
          });
          setAnswerPackage(singlePackage);
          setLastInputParams(singleInputParams);
          setQuestionAnswerPackages([singlePackage]);
          setQuestionInputParams([singleInputParams]);
        } else {
          const responseData = data as { questions: QuizData[]; package_id?: string };
          if (!responseData.questions || !Array.isArray(responseData.questions)) {
            throw new Error("複数問生成のレスポンス形式が不正です。");
          }

          const basePackageId =
            typeof responseData.package_id === "string" && responseData.package_id.trim()
              ? responseData.package_id
              : `pkg_${Date.now()}`;

          const generatedPackages = responseData.questions.map((q, index) => ({
            ...q,
            package_id: `${basePackageId}_q${index + 1}`,
          }));

          const generatedInputParams = responseData.questions.map((q) =>
            buildInputParams({
              mode: "keyword",
              category: DEFAULT_CATEGORY,
              sourceUrl: q.source?.url || suggestedUrl,
              selectedQuote: q.source?.quote || quoteToSend,
              difficulty: request.options.difficulty || undefined,
              length: request.options.length || undefined,
              keyword: request.keyword,
            })
          );

          setQuestions(responseData.questions);
          setCurrentQuestionIndex(0);
          setQuiz(responseData.questions[0] ?? null);
          setQuestionAnswerPackages(generatedPackages);
          setQuestionInputParams(generatedInputParams);
          setAnswerPackage(generatedPackages[0] ?? null);
          setLastInputParams(generatedInputParams[0] ?? null);
        }
      }
    } catch (error: any) {
      console.error(error);
      setError(error.message || "不明なエラーが発生しました。");
    } finally {
      setIsLoading(false);
    }
  };

  const applyQuizResponse = (data: any, questionCount: number) => {
    if (questionCount === 1) {
      setQuiz(data as QuizData);
    } else {
      const responseData = data as { questions: QuizData[] };
      if (responseData.questions && Array.isArray(responseData.questions)) {
        setQuestions(responseData.questions);
        setCurrentQuestionIndex(0);
        if (responseData.questions.length > 0) {
          setQuiz(responseData.questions[0]);
        }
      } else {
        throw new Error("複数問生成のレスポンス形式が不正です。");
      }
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

  const handleRevealAnswer = () => {
    if (!quiz) return;
    setError("");
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
      setAnswerPackage(questionAnswerPackages[newIndex] ?? null);
      setLastInputParams(questionInputParams[newIndex] ?? null);
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
      setAnswerPackage(questionAnswerPackages[newIndex] ?? null);
      setLastInputParams(questionInputParams[newIndex] ?? null);
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
    answerPackage,
    lastInputParams,
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
    handleRevealAnswer,
    handleClearHistory,
    handlePreviousQuestion,
    handleNextQuestion,
  };
}
