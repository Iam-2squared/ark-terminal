function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
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

function formatNumber(value, digits = 0) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    return "--";
  }

  return parsed.toLocaleString(
    "ja-JP",
    {
      minimumFractionDigits:
        digits,

      maximumFractionDigits:
        digits,
    },
  );
}

function actionClass(action = "HOLD") {
  const normalized =
    String(action)
      .toUpperCase();

  if (
    normalized === "BUY" ||
    normalized === "STRONG BUY"
  ) {
    return "positive";
  }

  if (
    normalized === "SELL" ||
    normalized === "REDUCE" ||
    normalized === "NO TRADE"
  ) {
    return "negative";
  }

  return "neutral";
}

export function buildMarketIntelligenceView(
  report = {},
) {
  const predictions =
    (Array.isArray(report.predictions)
      ? report.predictions
      : [])
      .map((prediction) => ({
        horizon:
          finiteNumber(
            prediction?.horizon,
            0,
          ),

        direction:
          prediction?.direction ??
          "判定不能",

        score:
          prediction?.score !== null &&
          prediction?.score !== undefined &&
          prediction?.score !== "" &&
          Number.isFinite(
            Number(prediction.score),
          )
            ? Number(
                prediction.score,
              )
            : null,

        confidence:
          finiteNumber(
            prediction?.confidence,
            0,
          ),

        status:
          prediction?.status ??
          "unavailable",
      }))
      .filter(
        (prediction) =>
          prediction.horizon > 0,
      );

  return {
    enabled:
      report.enabled === true,

    status:
      report.status ??
      "not_requested",

    participating:
      report.participating === true,

    selectedHorizon:
      finiteNumber(
        report.selectedHorizon,
        5,
      ),

    featureConfidence:
      finiteNumber(
        report.featureConfidence,
        0,
      ),

    featureCoverage:
      finiteNumber(
        report.featureCoverage,
        0,
      ),

    predictions,
  };
}

export function buildPredictionLabV3ViewModel({
  analysis = {},
  tradePlan = {},
  alerts = {},
  runtime = {},
  learning = {},
  marketIntelligence = {},
} = {}) {
  const dashboard =
    analysis.dashboard ??
    analysis.analysis?.dashboard ??
    {};

  const decision =
    analysis.decision ??
    analysis.analysis?.decision ??
    {};

  const action =
    tradePlan.action ??
    dashboard.action ??
    "HOLD";

  return {
    version:
      "prediction-lab-v3-dashboard-v1",

    action,

    actionClass:
      actionClass(action),

    score:
      finiteNumber(
        dashboard.score ??
        analysis.score,
        50,
      ),

    confidence:
      finiteNumber(
        dashboard.confidence ??
        analysis.confidence,
        0,
      ),

    macro:
      dashboard.macro ??
      analysis.macro?.sentiment ??
      "NEUTRAL",

    regime:
      dashboard.regime ??
      analysis.regime?.regime ??
      "RANGE",

    buyFactors:
      Array.isArray(
        decision.buyFactors,
      )
        ? decision.buyFactors
        : [],

    riskFactors:
      Array.isArray(
        decision.riskFactors,
      )
        ? decision.riskFactors
        : [],

    tradePlan: {
      executable:
        tradePlan.executable === true,

      shares:
        finiteNumber(
          tradePlan.sizing?.shares,
          0,
        ),

      entryPrice:
        finiteNumber(
          tradePlan.levels?.entryPrice,
          0,
        ),

      stopPrice:
        finiteNumber(
          tradePlan.levels?.stopPrice,
          0,
        ),

      targetPrice:
        finiteNumber(
          tradePlan.levels?.targetPrice,
          0,
        ),

      estimatedCost:
        finiteNumber(
          tradePlan.sizing?.estimatedCost,
          0,
        ),
    },

    alerts: {
      total:
        finiteNumber(
          alerts.total,
          0,
        ),

      unread:
        finiteNumber(
          alerts.unread,
          0,
        ),

      highSeverity:
        finiteNumber(
          alerts.highSeverity,
          0,
        ),
    },

    runtime: {
      cache:
        finiteNumber(
          runtime.cache,
          0,
        ),

      queueCompleted:
        finiteNumber(
          runtime.queue?.completed,
          0,
        ),

      averageDuration:
        finiteNumber(
          runtime.performance?.average,
          0,
        ),
    },

    marketIntelligence:
      buildMarketIntelligenceView(
        marketIntelligence,
      ),

    learning: {
      score:
        finiteNumber(
          learning.score,
          0,
        ),

      confidence:
        finiteNumber(
          learning.confidence,
          0,
        ),

      trend:
        learning.trend ??
        "NONE",
    },
  };
}

export function renderPredictionLabV3Dashboard(
  input = {},
) {
  const view =
    buildPredictionLabV3ViewModel(
      input,
    );

  const buyFactors =
    view.buyFactors.length
      ? view.buyFactors
          .map(
            (item) =>
              `<li>✓ ${escapeHtml(item)}</li>`,
          )
          .join("")
      : "<li>明確な買い要因なし</li>";

  const riskFactors =
    view.riskFactors.length
      ? view.riskFactors
          .map(
            (item) =>
              `<li>⚠ ${escapeHtml(item)}</li>`,
          )
          .join("")
      : "<li>重大なリスク要因なし</li>";

  const marketIntelligence =
    view.marketIntelligence.enabled
      ? `
        <section class="predictionLabV3MarketIntelligence">
          <header>
            <div>
              <span>MARKET INTELLIGENCE</span>
              <h3>マルチホライズン予測</h3>
            </div>

            <strong>
              ${
                view.marketIntelligence.participating
                  ? "合意形成に参加"
                  : "参考データ"
              }
            </strong>
          </header>

          <div class="predictionLabV3MarketGrid">
            ${view.marketIntelligence.predictions
              .map(
                (prediction) => `
                  <article class="${
                    prediction.horizon ===
                    view.marketIntelligence.selectedHorizon
                      ? "selected"
                      : ""
                  }">
                    <span>${formatNumber(prediction.horizon)}日先</span>
                    <strong>${escapeHtml(prediction.direction)}</strong>
                    <small>
                      Score ${formatNumber(prediction.score)} ·
                      Quality ${formatNumber(prediction.confidence)}%
                    </small>
                  </article>
                `,
              )
              .join("") ||
              "<p>利用可能な市場特徴量がありません。</p>"}
          </div>

          <p>
            特徴量カバレッジ
            ${formatNumber(view.marketIntelligence.featureCoverage)}% ·
            信頼度は確率ではなくデータ品質です。
          </p>
        </section>
      `
      : "";

  return `
    <section class="predictionLabV3">
      <header class="predictionLabV3Header">
        <div>
          <span class="predictionLabV3Eyebrow">
            ARK TERMINAL
          </span>

          <h2>
            Prediction Lab v3
          </h2>
        </div>

        <span class="predictionLabV3Action ${escapeHtml(
          view.actionClass,
        )}">
          ${escapeHtml(view.action)}
        </span>
      </header>

      <div class="predictionLabV3Hero">
        <article>
          <span>総合スコア</span>
          <strong>${formatNumber(view.score)}</strong>
        </article>

        <article>
          <span>信頼度</span>
          <strong>${formatNumber(view.confidence)}%</strong>
        </article>

        <article>
          <span>Macro</span>
          <strong>${escapeHtml(view.macro)}</strong>
        </article>

        <article>
          <span>Regime</span>
          <strong>${escapeHtml(view.regime)}</strong>
        </article>
      </div>

      ${marketIntelligence}

      <div class="predictionLabV3Columns">
        <article class="predictionLabV3Card">
          <h3>買い要因</h3>
          <ul>${buyFactors}</ul>
        </article>

        <article class="predictionLabV3Card">
          <h3>リスク要因</h3>
          <ul>${riskFactors}</ul>
        </article>
      </div>

      <div class="predictionLabV3TradePlan">
        <article>
          <span>推奨株数</span>
          <strong>
            ${formatNumber(view.tradePlan.shares)}株
          </strong>
        </article>

        <article>
          <span>エントリー</span>
          <strong>
            ¥${formatNumber(view.tradePlan.entryPrice)}
          </strong>
        </article>

        <article>
          <span>損切り</span>
          <strong>
            ¥${formatNumber(view.tradePlan.stopPrice)}
          </strong>
        </article>

        <article>
          <span>利確目標</span>
          <strong>
            ¥${formatNumber(view.tradePlan.targetPrice)}
          </strong>
        </article>

        <article>
          <span>必要資金</span>
          <strong>
            ¥${formatNumber(view.tradePlan.estimatedCost)}
          </strong>
        </article>
      </div>

      <div class="predictionLabV3System">
        <article>
          <span>未読アラート</span>
          <strong>${formatNumber(view.alerts.unread)}</strong>
        </article>

        <article>
          <span>高重要度</span>
          <strong>${formatNumber(view.alerts.highSeverity)}</strong>
        </article>

        <article>
          <span>Cache</span>
          <strong>${formatNumber(view.runtime.cache)}</strong>
        </article>

        <article>
          <span>平均処理時間</span>
          <strong>
            ${formatNumber(
              view.runtime.averageDuration,
              2,
            )}ms
          </strong>
        </article>

        <article>
          <span>Learning</span>
          <strong>
            ${escapeHtml(view.learning.trend)}
          </strong>
        </article>
      </div>

      <p class="predictionLabV3Disclaimer">
        本表示は分析支援用です。売買判断と損失管理は利用者自身で行ってください。
      </p>
    </section>
  `;
}

export function mountPredictionLabV3Dashboard({
  input = {},
  documentRef = globalThis.document,
} = {}) {
  if (!documentRef) {
    return {
      mounted: false,
      reason:
        "document_unavailable",
    };
  }

  let container =
    documentRef.querySelector(
      "#arkPredictionLabV3",
    );

  if (!container) {
    container =
      documentRef.createElement(
        "section",
      );

    container.id =
      "arkPredictionLabV3";

    container.className =
      "arkPredictionLabV3Root";

    const anchor =
      documentRef.querySelector(
        "#arkPredictionLabV2, #arkFinalTradePlan, #arkIntegratedAiDashboard",
      );

    if (
      anchor &&
      typeof anchor
        .insertAdjacentElement ===
        "function"
    ) {
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
    renderPredictionLabV3Dashboard(
      input,
    );

  container.dataset
    .predictionLabV3Status =
    "ready";

  return {
    mounted: true,
    container,
  };
}
