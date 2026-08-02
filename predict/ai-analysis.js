import {
  renderTradeMemoryLearningPanel,
} from "./learning/trade-memory-learning-ui.js";

import {
  getTradeMemory,
} from "./trading/trade-memory.js";
import { ARK_API_BASE } from "./config.js";
import { createDecisionDashboard } from "./analysis/ai-decision-dashboard.js";

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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
      discoveryScore: state.analysis.discoveryScore,
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

  if (isLoading) {
    elements.status.textContent = "生成中";
  }

  elements.status.classList.toggle("loading", isLoading);
}

function setError(message) {
  elements.error.hidden = !message;
  elements.error.textContent = message || "";
}

function appendListSection(container, title, items, icon = "", className = "") {
  const section = document.createElement("section");
  section.className = `aiAnalysisSection ${className}`.trim();

  const heading = document.createElement("h3");
  heading.textContent = `${icon} ${title}`.trim();
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

function appendSection(container, title, text, className = "") {
  const section = document.createElement("section");
  section.className = `aiAnalysisSection ${className}`.trim();

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


export function renderAiAnalysis(
  result,
) {
  const analysis =
    result?.analysis;

  if (!analysis) {
    throw new Error(
      "AI分析結果が空です。",
    );
  }

  const overallScore =
    finite(
      analysis.overallAiScore,
    )
      ? `${analysis.overallAiScore} / 100`
      : "--";

  const confidenceText =
    analysis.confidence
      ? `${analysis.confidence.score} / 100（${analysis.confidence.label}）`
      : "--";

  elements.result
    .replaceChildren();

  const decision =
    document.createElement(
      "section",
    );

  decision.className =
    `aiDecisionHero ${analysis.recommendation?.key || "neutral"}`;

  decision.innerHTML = `
    <div class="aiDecisionMain">
      <span class="aiDecisionEyebrow">
        AI総合診断
      </span>

      <strong class="aiDecisionLabel">
        ${escapeHtml(
          analysis
            .recommendation
            ?.label ||
          analysis.stance ||
          "中立",
        )}
      </strong>

      <span class="aiDecisionNote">
        ${escapeHtml(
          analysis
            .recommendation
            ?.note || "",
        )}
      </span>
    </div>

    <div class="aiDecisionScores">
      <div>
        <span>AIスコア</span>
        <strong>
          ${escapeHtml(
            overallScore,
          )}
        </strong>
      </div>

      <div>
        <span>信頼度</span>
        <strong>
          ${escapeHtml(
            confidenceText,
          )}
        </strong>
      </div>

      <div>
        <span>市場環境</span>
        <strong>
          ${escapeHtml(
            `${analysis.marketEnvironment?.score ?? 50} / 100`,
          )}
        </strong>
      </div>
    </div>

    <p class="aiDecisionSummary">
      ${escapeHtml(
        analysis.overallAssessment ||
        "",
      )}
    </p>
  `;

  elements.result
    .append(decision);

  const factors =
    document.createElement(
      "div",
    );

  factors.className =
    "aiAnalysisGrid";

  appendListSection(
    factors,
    "買い要因",
    analysis.buyFactors,
    "✅",
    "positive",
  );

  appendListSection(
    factors,
    "リスク要因",
    analysis.riskFactors,
    "⚠",
    "negative",
  );

  elements.result
    .append(factors);

  const scoreSection =
    document.createElement(
      "section",
    );

  scoreSection.className =
    "aiIndicatorPanel";

  const scoreRows =
    (
      analysis
        .indicatorScores ||
      []
    )
      .map(
        (item) => `
          <div class="aiIndicatorRow">
            <div class="aiIndicatorMeta">
              <strong>
                ${escapeHtml(
                  item.label,
                )}
              </strong>

              <span>
                ${escapeHtml(
                  item.reason,
                )}
              </span>
            </div>

            <div class="aiIndicatorBar">
              <i
                class="${escapeHtml(
                  item.status,
                )}"
                style="width:${Math.max(
                  4,
                  Math.min(
                    100,
                    item.score,
                  ),
                )}%"
              ></i>
            </div>

            <b
              class="aiIndicatorScore ${escapeHtml(
                item.status,
              )}"
            >
              ${escapeHtml(
                item.score,
              )}
            </b>
          </div>
        `,
      )
      .join("");

  scoreSection.innerHTML =
    `
      <h3>指標別スコア</h3>
      <div class="aiIndicatorList">
        ${scoreRows}
      </div>
    `;

  elements.result
    .append(scoreSection);

  const plan =
    analysis.tradePlan || {};

  const strategy =
    document.createElement(
      "section",
    );

  strategy.className =
    "aiStrategyPanel";

  strategy.innerHTML = `
    <div class="aiStrategyHeader">
      <div>
        <span>AI戦略</span>
        <h3>価格シナリオ</h3>
      </div>

      <div class="aiRiskReward">
        <span>RR</span>
        <strong>
          ${escapeHtml(
            plan.riskReward ??
            "--",
          )}
        </strong>
      </div>
    </div>

    <div class="aiStrategyGrid">
      <div>
        <span>エントリー候補</span>
        <strong>
          ${escapeHtml(
            plan.entryLabel ||
            "--",
          )}
        </strong>
      </div>

      <div>
        <span>損切り目安</span>
        <strong class="negativeText">
          ${escapeHtml(
            plan.stopLossLabel ||
            "--",
          )}
        </strong>
      </div>

      <div>
        <span>第一利確</span>
        <strong>
          ${escapeHtml(
            plan.firstTargetLabel ||
            "--",
          )}
        </strong>
      </div>

      <div>
        <span>第二利確</span>
        <strong>
          ${escapeHtml(
            plan.secondTargetLabel ||
            "--",
          )}
        </strong>
      </div>
    </div>
  `;

  elements.result
    .append(strategy);

  const outlook =
    document.createElement(
      "div",
    );

  outlook.className =
    "aiAnalysisGrid";

  appendSection(
    outlook,
    "短期見通し",
    analysis
      .shortTermOutlook,
  );

  appendSection(
    outlook,
    "中期見通し",
    analysis
      .midTermOutlook,
  );

  appendSection(
    outlook,
    "市場環境",

    `${analysis.marketEnvironment?.regime || "中立"}：${analysis.marketEnvironment?.explanation || ""}`,
  );

  elements.result
    .append(outlook);

  const focus =
    document.createElement(
      "section",
    );

  focus.className =
    "aiFocusPanel";

  focus.innerHTML = `
    <h3>AIが重視した要因</h3>

    <div class="aiFocusList">
      ${(
        analysis
          .focusFactors ||
        []
      )
        .map(
          (item) => `
            <div>
              <span class="aiFocusRank">
                ${item.rank}
              </span>

              <p>
                <strong>
                  ${escapeHtml(
                    item.label,
                  )} ·
                  ${escapeHtml(
                    item.score,
                  )}点
                </strong>

                <small>
                  ${escapeHtml(
                    item.reason,
                  )}
                </small>
              </p>

              <em class="${item.score >= 50 ? "positive" : "negative"}">
                ${escapeHtml(
                  item.direction,
                )}
              </em>
            </div>
          `,
        )
        .join("")}
    </div>
  `;

  elements.result
    .append(focus);
  const learningPanel =
    renderTradeMemoryLearningPanel({
      records:
        getTradeMemory(),

      baseWeights: {},
    });

  if (learningPanel) {
    elements.result.append(
      learningPanel,
    );
  }

  const footer =
    document.createElement(
      "div",
    );

  footer.className =
    "aiAnalysisFooter";

  footer.textContent =
    analysis.disclaimer ||
    "表示価格はテクニカル指標から算出した参考シナリオです。利益や約定を保証しません。";

  elements.result
    .append(footer);

  elements.status.textContent =
    result.meta?.model
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
    const result = { analysis: createDecisionDashboard(getLatestState()) };
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

export function buildLearningPanel(report={}){

    const summary=report.summary??{};

    return{

        learningStatus:
            summary.status??"Unknown",

        learningTrend:
            summary.trend??"NONE",

        learningScore:
            summary.score??0,

        learningConfidence:
            summary.confidence??0,

        weightVersion:
            report.dashboard?.latest?.id??"-",

        lastLearning:
            report.dashboard?.latest?.createdAt??"-"

    };

}

export function renderLearningPanel(report={}){

    const panel=
        buildLearningPanel(report);

    return`

<div class="learning-panel">

<div class="learning-card">

<h3>Learning Status</h3>

<strong>${panel.learningStatus}</strong>

</div>

<div class="learning-card">

<h3>Trend</h3>

<strong>${panel.learningTrend}</strong>

</div>

<div class="learning-card">

<h3>Learning Score</h3>

<strong>${panel.learningScore}</strong>

</div>

<div class="learning-card">

<h3>Confidence</h3>

<strong>${panel.learningConfidence}</strong>

</div>

<div class="learning-card">

<h3>Weight Version</h3>

<strong>${panel.weightVersion}</strong>

</div>

</div>

`;

}

