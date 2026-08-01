import { ARK_API_BASE } from "./config.js";

const AI_ANALYSIS_TIMEOUT_MS = 35_000;
const MAX_ARRAY_ITEMS = 12;
const MAX_OBJECT_ENTRIES = 60;
const MAX_TEXT_LENGTH = 1_500;

const elements = {};
let initialized = false;
let getLatestState = () => null;

function finite(value) {
  return Number.isFinite(Number(value));
}

function sanitizeForAi(value, depth = 0, seen = new WeakSet()) {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return finite(value) ? Number(value) : null;
  }

  if (typeof value === "string") {
    return value.slice(0, MAX_TEXT_LENGTH);
  }

  if (typeof value === "boolean") {
    return value;
  }

  if (depth >= 3) {
    return null;
  }

  if (Array.isArray(value)) {
    return value
      .slice(0, MAX_ARRAY_ITEMS)
      .map((item) => sanitizeForAi(item, depth + 1, seen))
      .filter((item) => item !== null);
  }

  if (typeof value === "object") {
    if (seen.has(value)) {
      return null;
    }

    seen.add(value);

    return Object.fromEntries(
      Object.entries(value)
        .slice(0, MAX_OBJECT_ENTRIES)
        .map(([key, item]) => [
          key,
          sanitizeForAi(item, depth + 1, seen),
        ])
        .filter(([_key, item]) => item !== null),
    );
  }

  return null;
}

function summarizeFactors(factors = []) {
  return factors
    .filter((factor) => factor?.available)
    .slice(0, 20)
    .map((factor) => ({
      key: factor.key,
      label: factor.label,
      score: finite(factor.score) ? Number(factor.score) : null,
      maximum: finite(factor.maximum) ? Number(factor.maximum) : null,
      reason: String(factor.reason || "").slice(0, 500),
    }));
}

function summarizeNews(news = []) {
  return news.slice(0, 6).map((item) => ({
    headline: String(item.headline || "").slice(0, 300),
    summary: String(item.summary || "").slice(0, 700),
    source: String(item.source || "").slice(0, 120),
    publishedAt: item.publishedAt || null,
  }));
}

export function buildAiAnalysisPayload(state) {
  if (!state?.analysis || !state?.prediction) {
    throw new Error("先に通常分析を実行してください。");
  }

  return {
    symbol: state.symbol,
    companyName: state.context?.company?.name || state.companyName || "",
    period: state.period,
    quote: sanitizeForAi(state.quote),
    analysis: {
      totalScore: state.analysis.totalScore,
      technicalScore: state.analysis.technicalScore,
      verdict: state.analysis.verdict,
      categoryScores: sanitizeForAi(state.analysis.categoryScores),
      factors: summarizeFactors(state.analysis.factors),
    },
    prediction: sanitizeForAi(state.prediction),
    indicators: sanitizeForAi(state.indicators),
    dataQuality: sanitizeForAi({
      status: state.quality?.status,
      qualityScore: state.quality?.qualityScore,
      missingRate: state.quality?.missingRate,
      issues: state.quality?.issues,
    }),
    marketEnvironment: sanitizeForAi(state.marketEnvironment),
    company: sanitizeForAi(state.context?.company),
    news: summarizeNews(state.context?.news),
  };
}

async function fetchAiAnalysis(payload, signal) {
  const url = new URL("/api/ai-analysis", ARK_API_BASE);
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
    body: JSON.stringify(payload),
    signal,
  });

  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(result.error || `AI分析 API HTTP ${response.status}`);
  }

  return result;
}

function setLoading(isLoading) {
  elements.button.disabled = isLoading;
  elements.button.textContent = isLoading ? "AI分析中..." : "AI分析";
  elements.status.textContent = isLoading ? "生成中" : "実行済み";
  elements.status.classList.toggle("loading", isLoading);
}

function setError(message) {
  elements.error.hidden = !message;
  elements.error.textContent = message || "";
}

function appendListSection(container, title, items, className = "") {
  const section = document.createElement("section");
  section.className = `aiAnalysisSection ${className}`.trim();

  const heading = document.createElement("h3");
  heading.textContent = title;
  section.append(heading);

  const list = document.createElement("ul");

  for (const item of items?.length ? items : ["該当する根拠はありません。"]) {
    const listItem = document.createElement("li");
    listItem.textContent = item;
    list.append(listItem);
  }

  section.append(list);
  container.append(section);
}

function appendTextSection(container, title, text) {
  const section = document.createElement("section");
  section.className = "aiAnalysisSection";

  const heading = document.createElement("h3");
  heading.textContent = title;

  const paragraph = document.createElement("p");
  paragraph.textContent = text || "データなし";

  section.append(heading, paragraph);
  container.append(section);
}

function stanceClass(stance) {
  if (stance === "強気" || stance === "やや強気") {
    return "positive";
  }

  if (stance === "弱気" || stance === "やや弱気") {
    return "negative";
  }

  return "neutral";
}

export function renderAiAnalysis(result) {
  const analysis = result?.analysis;

  if (!analysis) {
    throw new Error("AI分析結果が空です。");
  }

  elements.result.replaceChildren();

  const hero = document.createElement("div");
  hero.className = "aiAnalysisHero";

  const stance = document.createElement("span");
  stance.className = `aiStance ${stanceClass(analysis.stance)}`;
  stance.textContent = analysis.stance || "中立";

  const summary = document.createElement("p");
  summary.textContent = analysis.overallAssessment || "分析結果がありません。";

  hero.append(stance, summary);
  elements.result.append(hero);

  const grid = document.createElement("div");
  grid.className = "aiAnalysisGrid";

  appendListSection(grid, "買い要因", analysis.buyFactors, "positive");
  appendListSection(grid, "売り要因", analysis.sellFactors, "negative");
  appendListSection(grid, "主なリスク", analysis.risks, "risk");
  appendListSection(grid, "注目ポイント", analysis.watchPoints);
  appendTextSection(grid, "市場全体との関係", analysis.marketContext);
  appendTextSection(grid, "信頼度の見方", analysis.confidenceComment);

  elements.result.append(grid);

  const footer = document.createElement("div");
  footer.className = "aiAnalysisFooter";
  footer.textContent = analysis.disclaimer ||
    "この分析は参考情報であり、売買や利益を保証するものではありません。";
  elements.result.append(footer);

  elements.status.textContent = result.meta?.model
    ? `完了・${result.meta.model}`
    : "完了";
}

export function resetAiAnalysis() {
  if (!initialized) {
    return;
  }

  setError("");
  elements.status.textContent = "実行待ち";
  elements.status.classList.remove("loading");
  elements.result.innerHTML =
    '<p class="emptyState">通常分析の完了後、「AI分析」を押してください。</p>';
}

async function runAiAnalysis() {
  setError("");

  let payload;

  try {
    payload = buildAiAnalysisPayload(getLatestState());
  } catch (error) {
    setError(error.message);
    return;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), AI_ANALYSIS_TIMEOUT_MS);
  setLoading(true);

  try {
    const result = await fetchAiAnalysis(payload, controller.signal);
    renderAiAnalysis(result);
  } catch (error) {
    const message =
      error.name === "AbortError"
        ? "AI分析がタイムアウトしました。"
        : error.message;

    setError(message);
    elements.status.textContent = "失敗";
  } finally {
    clearTimeout(timeout);
    setLoading(false);
  }
}

export function initAiAnalysis(stateProvider) {
  if (initialized) {
    getLatestState = stateProvider;
    return;
  }

  ["runAiAnalysisButton", "aiAnalysisStatus", "aiAnalysisResult", "aiAnalysisError"].forEach(
    (id) => {
      const key = {
        runAiAnalysisButton: "button",
        aiAnalysisStatus: "status",
        aiAnalysisResult: "result",
        aiAnalysisError: "error",
      }[id];

      elements[key] = document.getElementById(id);
    },
  );

  if (Object.values(elements).some((element) => !element)) {
    console.warn("AI分析UIが見つかりません。");
    return;
  }

  getLatestState = stateProvider;
  elements.button.addEventListener("click", runAiAnalysis);
  initialized = true;
}

export const AiAnalysisUiInternals = {
  sanitizeForAi,
  stanceClass,
  summarizeFactors,
  summarizeNews,
};
