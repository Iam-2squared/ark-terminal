import {
  ARK_API_BASE,
} from "../config.js";

const AI_TRADE_GATE_TIMEOUT_MS =
  35_000;

const MAX_ARRAY_ITEMS =
  16;

const MAX_OBJECT_ENTRIES =
  80;

const MAX_TEXT_LENGTH =
  1_200;

const elements = {};

let initialized = false;
let stateProvider = () => null;
let latestDecision = null;
let gateController = null;

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(
      Number(value),
    )
  );
}

function sanitizeForAi(
  value,
  depth = 0,
  seen = new WeakSet(),
) {
  if (
    value === null ||
    value === undefined
  ) {
    return null;
  }

  if (
    typeof value === "number"
  ) {
    return finite(value)
      ? Number(value)
      : null;
  }

  if (
    typeof value === "string"
  ) {
    return value.slice(
      0,
      MAX_TEXT_LENGTH,
    );
  }

  if (
    typeof value === "boolean"
  ) {
    return value;
  }

  if (depth >= 4) {
    return null;
  }

  if (
    Array.isArray(value)
  ) {
    return value
      .slice(
        0,
        MAX_ARRAY_ITEMS,
      )
      .map((item) =>
        sanitizeForAi(
          item,
          depth + 1,
          seen,
        ),
      )
      .filter(
        (item) =>
          item !== null,
      );
  }

  if (
    typeof value === "object"
  ) {
    if (seen.has(value)) {
      return null;
    }

    seen.add(value);

    return Object.fromEntries(
      Object.entries(value)
        .slice(
          0,
          MAX_OBJECT_ENTRIES,
        )
        .map(
          ([key, item]) => [
            key,

            sanitizeForAi(
              item,
              depth + 1,
              seen,
            ),
          ],
        )
        .filter(
          ([_key, item]) =>
            item !== null,
        ),
    );
  }

  return null;
}

function summarizeFactors(
  factors = [],
) {
  return factors
    .filter(
      (factor) =>
        factor?.available,
    )
    .slice(0, 20)
    .map((factor) => ({
      key:
        factor.key,

      label:
        factor.label,

      score:
        finite(factor.score)
          ? Number(
              factor.score,
            )
          : null,

      maximum:
        finite(factor.maximum)
          ? Number(
              factor.maximum,
            )
          : null,

      reason:
        String(
          factor.reason || "",
        ).slice(0, 500),
    }));
}

export function buildAiTradeGatePayload(
  state,
  decision,
) {
  if (!state?.symbol) {
    throw new Error(
      "先に通常分析を実行してください。",
    );
  }

  if (
    !decision ||
    decision.paperCandidate !==
      true ||
    decision.action !==
      "enter_long" ||
    decision.plan?.side !==
      "long"
  ) {
    throw new Error(
      "OpenAI審査は現在の現物買い候補だけを対象にします。",
    );
  }

  if (
    String(
      decision.symbol || "",
    ).toUpperCase() !==
    String(
      state.symbol || "",
    ).toUpperCase()
  ) {
    throw new Error(
      "通常分析と短期判断の銘柄が一致しません。",
    );
  }

  const indicators =
    state.indicators || {};

  const analysis =
    decision.analysis || {};

  const plan =
    decision.plan || {};

  return {
    symbol:
      state.symbol,

    companyName:
      state.context
        ?.company
        ?.name ||
      state.companyName ||
      "",

    policy: {
      executionMode:
        "paper",

      cashBuyOnly:
        true,

      shortSellingEnabled:
        false,

      aiCanCreateCandidate:
        false,

      aiCanOnlyReviewCandidate:
        true,

      liveExecutionAllowed:
        false,
    },

    tradeDecision: {
      version:
        decision.version,

      paperCandidate:
        true,

      action:
        decision.action,

      setup:
        analysis.setup,

      setupLabel:
        decision.setupLabel,

      reasons:
        sanitizeForAi(
          decision.reasons,
        ),

      warnings:
        sanitizeForAi(
          decision.warnings,
        ),

      analysis:
        sanitizeForAi({
          currentPrice:
            analysis.currentPrice,

          vwap:
            analysis.vwap,

          atr:
            analysis.atr,

          volumeRatio:
            analysis.volumeRatio,

          priorHigh:
            analysis.priorHigh,

          priorLow:
            analysis.priorLow,

          setupStrengthScore:
            analysis
              .setupStrengthScore,

          dataQualityScore:
            analysis
              .dataQualityScore,

          dataAgeSeconds:
            analysis
              .dataAgeSeconds,

          entryCondition:
            analysis
              .entryCondition,

          sessionBarCount:
            analysis
              .sessionBarCount,

          historyBarCount:
            analysis
              .historyBarCount,

          aboveVwap:
            analysis.aboveVwap,

          breakoutLong:
            analysis
              .breakoutLong,

          reclaimLong:
            analysis
              .reclaimLong,

          pullbackLong:
            analysis
              .pullbackLong,

          volumeSurge:
            analysis
              .volumeSurge,
        }),

      plan:
        sanitizeForAi({
          action:
            plan.action,

          side:
            plan.side,

          entryPrice:
            plan.entryPrice,

          stopPrice:
            plan.stopPrice,

          firstTargetPrice:
            plan
              .firstTargetPrice,

          secondTargetPrice:
            plan
              .secondTargetPrice,

          riskReward:
            plan.riskReward,

          riskAmount:
            plan.riskAmount,

          quantity:
            plan.quantity,

          maximumHoldingBars:
            plan
              .maximumHoldingBars,
        }),
    },

    dailyContext: {
      indicators:
        sanitizeForAi({
          currentPrice:
            indicators
              .currentPrice,

          movingAverages:
            indicators
              .movingAverages,

          rsi:
            indicators.rsi,

          macd:
            indicators.macd,

          adx:
            indicators.adx,

          atr:
            indicators.atr,

          vwap:
            indicators.vwap,

          bollingerBands:
            indicators
              .bollingerBands,

          stochastic:
            indicators
              .stochastic,

          volumeRatio:
            indicators
              .volumeRatio,

          distanceFrom52WeekHigh:
            indicators
              .distanceFrom52WeekHigh,

          distanceFrom52WeekLow:
            indicators
              .distanceFrom52WeekLow,
        }),

      overallAnalysis:
        sanitizeForAi({
          totalScore:
            state.analysis
              ?.totalScore,

          technicalScore:
            state.analysis
              ?.technicalScore,

          verdict:
            state.analysis
              ?.verdict,

          categoryScores:
            state.analysis
              ?.categoryScores,

          factors:
            summarizeFactors(
              state.analysis
                ?.factors,
            ),
        }),

      prediction:
        sanitizeForAi(
          state.prediction,
        ),

      marketEnvironment:
        sanitizeForAi(
          state
            .marketEnvironment,
        ),

      dataQuality:
        sanitizeForAi({
          status:
            state.quality
              ?.status,

          qualityScore:
            state.quality
              ?.qualityScore,

          missingRate:
            state.quality
              ?.missingRate,

          issues:
            state.quality
              ?.issues,
        }),
    },
  };
}

async function fetchAiTradeGate(
  payload,
  signal,
) {
  const url =
    new URL(
      "/api/ai-trade-gate",
      ARK_API_BASE,
    );

  const response =
    await fetch(url, {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      cache: "no-store",

      body:
        JSON.stringify(
          payload,
        ),

      signal,
    });

  const result =
    await response
      .json()
      .catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      result.error ||
      `AI審査 API HTTP ${response.status}`,
    );
  }

  return result;
}

export function gateDecisionLabel(
  decision,
) {
  const labels = {
    approve:
      "承認",

    wait:
      "待機",

    reject:
      "拒否",
  };

  return labels[decision] ||
    "判定不能";
}

export function gateDecisionClass(
  decision,
) {
  const classes = {
    approve:
      "approve",

    wait:
      "wait",

    reject:
      "reject",
  };

  return classes[decision] ||
    "unknown";
}

function setError(message) {
  elements.error.hidden =
    !message;

  elements.error.textContent =
    message || "";
}

function setLoading(loading) {
  elements.button.disabled =
    loading ||
    !latestDecision
      ?.paperCandidate;

  elements.button.textContent =
    loading
      ? "OpenAI審査中..."
      : "OpenAIで買い候補を審査";

  elements.status
    .classList
    .toggle(
      "loading",
      loading,
    );

  if (loading) {
    elements.status.textContent =
      "審査中";
  }
}

function renderList(
  container,
  title,
  items = [],
) {
  const section =
    document.createElement(
      "section",
    );

  section.className =
    "aiTradeGateSection";

  const heading =
    document.createElement(
      "h4",
    );

  heading.textContent =
    title;

  const list =
    document.createElement(
      "ul",
    );

  const resolvedItems =
    items.length
      ? items
      : [
          "該当項目なし",
        ];

  resolvedItems.forEach(
    (item) => {
      const row =
        document.createElement(
          "li",
        );

      row.textContent =
        item;

      list.append(row);
    },
  );

  section.append(
    heading,
    list,
  );

  container.append(section);
}

export function renderAiTradeGate(
  result,
) {
  const gate =
    result?.gate;

  if (!gate) {
    throw new Error(
      "AI審査結果が空です。",
    );
  }

  elements.result
    .replaceChildren();

  const hero =
    document.createElement(
      "div",
    );

  hero.className =
    "aiTradeGateHero";

  const badge =
    document.createElement(
      "span",
    );

  badge.className =
    `aiTradeGateDecision ${gateDecisionClass(
      gate.decision,
    )}`;

  badge.textContent =
    gateDecisionLabel(
      gate.decision,
    );

  const content =
    document.createElement(
      "div",
    );

  const summary =
    document.createElement(
      "p",
    );

  summary.textContent =
    gate.summary ||
    "審査理由がありません。";

  const confidence =
    document.createElement(
      "small",
    );

  confidence.textContent =
    `審査根拠の一貫性 ${Number(
      gate.confidence || 0,
    )} / 100`;

  content.append(
    summary,
    confidence,
  );

  hero.append(
    badge,
    content,
  );

  const grid =
    document.createElement(
      "div",
    );

  grid.className =
    "aiTradeGateGrid";

  renderList(
    grid,
    "審査理由",
    gate.reasons,
  );

  renderList(
    grid,
    "リスクフラグ",
    gate.riskFlags,
  );

  renderList(
    grid,
    "承認に必要な条件",
    gate.conditionsToApprove,
  );

  const footer =
    document.createElement(
      "p",
    );

  footer.className =
    "aiTradeGateFooter";

  footer.textContent =
    gate.disclaimer ||
    "AI審査は注文ではなく、Paper候補の補助評価です。";

  elements.result.append(
    hero,
    grid,
    footer,
  );

  elements.status.textContent =
    result.meta?.model
      ? `完了・${result.meta.model}`
      : "完了";
}

export function resetAiTradeGate() {
  if (!initialized) {
    return;
  }

  gateController?.abort();
  gateController = null;

  setError("");

  elements.status.textContent =
    latestDecision
      ?.paperCandidate
      ? "審査待ち"
      : "対象なし";

  elements.result.innerHTML =
    latestDecision
      ?.paperCandidate
      ? '<p class="emptyState">現在の買い候補をOpenAIで審査できます。</p>'
      : '<p class="emptyState">現物買い候補が出たときだけAI審査を実行できます。</p>';

  elements.button.disabled =
    !latestDecision
      ?.paperCandidate;
}

export function setAiTradeGateDecision(
  decision,
) {
  latestDecision =
    decision?.paperCandidate ===
      true &&
    decision.action ===
      "enter_long"
      ? decision
      : null;

  if (!initialized) {
    return;
  }

  elements.description.textContent =
    latestDecision
      ? `${latestDecision.setupLabel}の買い候補を、日足環境と15分足の整合性から審査します。`
      : "買い候補がないため、OpenAI審査は実行しません。";

  resetAiTradeGate();
}

export async function runAiTradeGate() {
  const state =
    stateProvider?.();

  const decision =
    latestDecision;

  let payload;

  try {
    payload =
      buildAiTradeGatePayload(
        state,
        decision,
      );
  } catch (error) {
    setError(
      error.message,
    );

    return null;
  }

  gateController?.abort();

  gateController =
    new AbortController();

  const timeout =
    setTimeout(
      () =>
        gateController.abort(),
      AI_TRADE_GATE_TIMEOUT_MS,
    );

  setError("");
  setLoading(true);

  try {
    const result =
      await fetchAiTradeGate(
        payload,
        gateController.signal,
      );

    if (
      decision !==
      latestDecision
    ) {
      throw new Error(
        "短期判断が更新されたため、古いAI審査結果を破棄しました。",
      );
    }

    renderAiTradeGate(
      result,
    );

    return result;
  } catch (error) {
    const message =
      error.name ===
        "AbortError"
        ? "AI審査がタイムアウトしました。"
        : error.message;

    setError(message);

    elements.status.textContent =
      "失敗";

    return null;
  } finally {
    clearTimeout(timeout);
    setLoading(false);
  }
}

export function initAiTradeGate(
  getState,
) {
  stateProvider =
    getState;

  elements.button =
    document.getElementById(
      "runAiTradeGateButton",
    );

  elements.status =
    document.getElementById(
      "aiTradeGateStatus",
    );

  elements.description =
    document.getElementById(
      "aiTradeGateDescription",
    );

  elements.result =
    document.getElementById(
      "aiTradeGateResult",
    );

  elements.error =
    document.getElementById(
      "aiTradeGateError",
    );

  if (
    Object.values(elements)
      .some(
        (element) =>
          !element,
      )
  ) {
    console.warn(
      "AI買い候補審査UIが見つかりません。",
    );

    return;
  }

  elements.button
    .addEventListener(
      "click",
      () => {
        void runAiTradeGate();
      },
    );

  initialized = true;

  resetAiTradeGate();
}

export const AiTradeGateUiInternals = {
  finite,
  gateDecisionClass,
  gateDecisionLabel,
  sanitizeForAi,
  summarizeFactors,
};