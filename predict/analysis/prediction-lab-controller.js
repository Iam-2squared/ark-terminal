import {
  buildPredictionLabEngine,
} from "./prediction-lab-engine.js";

function finite(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function actionClass(action) {
  const normalized =
    String(action ?? "")
      .toUpperCase();

  if (
    normalized === "BUY" ||
    normalized === "STRONG BUY"
  ) {
    return "positive";
  }

  if (
    normalized === "SELL" ||
    normalized === "REDUCE"
  ) {
    return "negative";
  }

  return "neutral";
}

export function normalizePredictionLabInput(
  source = {},
) {
  const state =
    source.state ??
    source.analysisState ??
    source;

  return {
    state,

    macroInput:
      source.macroInput ??
      state.macroInput ??
      {},

    marketInput:
      source.marketInput ??
      state.marketInput ??
      {},

    portfolioPlan:
      source.portfolioPlan ??
      state.portfolioPlan ??
      {},

    history:
      Array.isArray(source.history)
        ? source.history
        : Array.isArray(
            state.history,
          )
          ? state.history
          : [],
  };
}

export function buildPredictionLabViewModel(
  source = {},
) {
  const input =
    normalizePredictionLabInput(
      source,
    );

  const engine =
    buildPredictionLabEngine(
      input,
    );

  return {
    version:
      engine.version,

    action:
      engine.dashboard.action,

    actionClass:
      actionClass(
        engine.dashboard.action,
      ),

    score:
      finite(
        engine.dashboard.score,
        50,
      ),

    confidence:
      finite(
        engine.dashboard.confidence,
        0,
      ),

    performanceGrade:
      engine.dashboard.grade ??
      "E",

    walkForwardStable:
      engine.dashboard.walkForward ===
      true,

    macro:
      engine.analysis
        ?.dashboard
        ?.macro ??
      "NEUTRAL",

    regime:
      engine.analysis
        ?.dashboard
        ?.regime ??
      "RANGE",

    buyFactors:
      engine.analysis
        ?.decision
        ?.buyFactors ??
      [],

    riskFactors:
      engine.analysis
        ?.decision
        ?.riskFactors ??
      [],

    performance: {
      total:
        engine.performance
          ?.report
          ?.total ??
        0,

      winRate:
        engine.performance
          ?.report
          ?.winRate ??
        0,

      averageReturn:
        engine.performance
          ?.report
          ?.averageReturn ??
        0,
    },

    generatedAt:
      engine.generatedAt,
  };
}

export function renderPredictionLabV2(
  source = {},
) {
  const view =
    buildPredictionLabViewModel(
      source,
    );

  const buyFactors =
    view.buyFactors
      .map(
        (factor) =>
          `<li>✓ ${escapeHtml(factor)}</li>`,
      )
      .join("");

  const riskFactors =
    view.riskFactors
      .map(
        (factor) =>
          `<li>⚠ ${escapeHtml(factor)}</li>`,
      )
      .join("");

  return `
    <section class="predictionLabV2">
      <header class="predictionLabV2Header">
        <div>
          <span class="predictionLabV2Eyebrow">
            PREDICTION LAB v2
          </span>

          <h2>
            AI総合分析
          </h2>
        </div>

        <span class="predictionLabV2Action ${escapeHtml(
          view.actionClass,
        )}">
          ${escapeHtml(view.action)}
        </span>
      </header>

      <div class="predictionLabV2Metrics">
        <article>
          <span>総合スコア</span>
          <strong>${view.score}</strong>
        </article>

        <article>
          <span>補正信頼度</span>
          <strong>${view.confidence}%</strong>
        </article>

        <article>
          <span>実績グレード</span>
          <strong>${escapeHtml(
            view.performanceGrade,
          )}</strong>
        </article>

        <article>
          <span>Walk Forward</span>
          <strong>
            ${
              view.walkForwardStable
                ? "安定"
                : "要検証"
            }
          </strong>
        </article>

        <article>
          <span>Macro</span>
          <strong>${escapeHtml(
            view.macro,
          )}</strong>
        </article>

        <article>
          <span>Regime</span>
          <strong>${escapeHtml(
            view.regime,
          )}</strong>
        </article>
      </div>

      <div class="predictionLabV2Factors">
        <article>
          <h3>買い要因</h3>
          <ul>
            ${
              buyFactors ||
              "<li>明確な買い要因なし</li>"
            }
          </ul>
        </article>

        <article>
          <h3>リスク要因</h3>
          <ul>
            ${
              riskFactors ||
              "<li>重大なリスク要因なし</li>"
            }
          </ul>
        </article>
      </div>

      <div class="predictionLabV2Performance">
        <span>
          学習件数
          <strong>${view.performance.total}</strong>
        </span>

        <span>
          勝率
          <strong>${view.performance.winRate}%</strong>
        </span>

        <span>
          平均リターン
          <strong>${view.performance.averageReturn}%</strong>
        </span>
      </div>

      <p class="predictionLabV2Disclaimer">
        本表示は分析支援用です。将来の利益や価格変動を保証しません。
      </p>
    </section>
  `;
}

export function mountPredictionLabV2({
  source = {},
  documentRef = globalThis.document,
} = {}) {
  if (!documentRef) {
    return {
      mounted: false,
      reason: "document_unavailable",
    };
  }

  let container =
    documentRef.querySelector(
      "#arkPredictionLabV2",
    );

  if (!container) {
    container =
      documentRef.createElement(
        "section",
      );

    container.id =
      "arkPredictionLabV2";

    container.className =
      "arkPredictionLabV2Root";

    const anchor =
      documentRef.querySelector(
        "#arkIntegratedAiDashboard, #aiAnalysisResult, .ai-analysis-result",
      );

    if (anchor) {
      anchor.insertAdjacentElement(
        "afterend",
        container,
      );
    }
    else {
      documentRef.body?.appendChild(
        container,
      );
    }
  }

  container.innerHTML =
    renderPredictionLabV2(
      source,
    );

  container.dataset
    .predictionLabV2Status =
    "ready";

  return {
    mounted: true,
    container,
  };
}

export function connectPredictionLabV2({
  eventTarget = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  if (
    !eventTarget ||
    !documentRef
  ) {
    return () => {};
  }

  const handler =
    (event) => {
      const source =
        event?.detail ??
        eventTarget
          .__ARK_ANALYSIS_STATE__ ??
        {};

      mountPredictionLabV2({
        source,
        documentRef,
      });
    };

  eventTarget.addEventListener(
    "ark:analysis-ready",
    handler,
  );

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    handler,
  );

  const initial =
    eventTarget
      .__ARK_ANALYSIS_STATE__;

  if (initial) {
    mountPredictionLabV2({
      source: initial,
      documentRef,
    });
  }

  return () => {
    eventTarget.removeEventListener(
      "ark:analysis-ready",
      handler,
    );

    eventTarget.removeEventListener(
      "ark:ai-analysis-complete",
      handler,
    );
  };
}

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined"
) {
  window.ArkPredictionLabV2 = {
    buildPredictionLabViewModel,
    mountPredictionLabV2,
    renderPredictionLabV2,
  };

  const start = () => {
    connectPredictionLabV2();
  };

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      start,
      {
        once: true,
      },
    );
  }
  else {
    start();
  }
}