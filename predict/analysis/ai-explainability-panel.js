function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function finiteNumber(
  value,
  fallback = 0,
) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function normalizeFactors(value) {
  return Array.isArray(value)
    ? value.filter(Boolean)
    : [];
}

export function buildExplainabilityViewModel(
  result = {},
) {
  const buyFactors =
    normalizeFactors(
      result.buyFactors,
    );

  const riskFactors =
    normalizeFactors(
      result.riskFactors,
    );

  const score =
    finiteNumber(
      result.score,
      50,
    );

  const confidence =
    finiteNumber(
      result.confidence,
      0,
    );

  const agreementRate =
    finiteNumber(
      result.agreementRate,
      0,
    );

  const strengths = [
    {
      label: "総合スコア",
      value: score,
      maximum: 100,
    },
    {
      label: "信頼度",
      value: confidence,
      maximum: 100,
    },
    {
      label: "エンジン合意率",
      value: agreementRate,
      maximum: 100,
    },
  ];

  return {
    symbol:
      result.symbol ??
      "--",

    action:
      result.action ??
      "HOLD",

    score,

    confidence,

    agreementRate,

    approved:
      result.approved === true,

    executable:
      result.executable === true,

    buyFactors,

    riskFactors,

    strengths,

    conclusion:
      result.executable === true
        ? "条件を満たしたため、売買計画の候補として採用されました。"
        : result.approved === true
          ? "分析条件は通過しましたが、実行条件を満たしていません。"
          : "リスクまたは信頼度の条件により、売買候補から除外されました。",
  };
}

export function renderAIExplainabilityPanel(
  result = {},
) {
  const view =
    buildExplainabilityViewModel(
      result,
    );

  const strengthRows =
    view.strengths
      .map(
        (item) => `
          <div class="arkExplainabilityMetric">
            <div>
              <span>${escapeHtml(item.label)}</span>
              <strong>${item.value}%</strong>
            </div>

            <div class="arkExplainabilityBar">
              <i
                style="width:${Math.max(
                  0,
                  Math.min(
                    100,
                    item.value,
                  ),
                )}%"
              ></i>
            </div>
          </div>
        `,
      )
      .join("");

  const buyFactors =
    view.buyFactors.length
      ? view.buyFactors
          .map(
            (factor) =>
              `<li>✓ ${escapeHtml(factor)}</li>`,
          )
          .join("")
      : "<li>明確な強気要因は検出されていません</li>";

  const riskFactors =
    view.riskFactors.length
      ? view.riskFactors
          .map(
            (factor) =>
              `<li>⚠ ${escapeHtml(factor)}</li>`,
          )
          .join("")
      : "<li>重大な警戒要因は検出されていません</li>";

  return `
    <section class="arkExplainabilityPanel">
      <header class="arkExplainabilityHeader">
        <div>
          <span class="arkExplainabilityEyebrow">
            EXPLAINABLE AI
          </span>

          <h3>
            AI判断の根拠
          </h3>
        </div>

        <span class="arkExplainabilityAction">
          ${escapeHtml(view.action)}
        </span>
      </header>

      <div class="arkExplainabilityMetrics">
        ${strengthRows}
      </div>

      <div class="arkExplainabilityColumns">
        <article>
          <h4>プラス要因</h4>
          <ul>${buyFactors}</ul>
        </article>

        <article>
          <h4>警戒要因</h4>
          <ul>${riskFactors}</ul>
        </article>
      </div>

      <div class="arkExplainabilityConclusion">
        <strong>最終判断</strong>
        <p>${escapeHtml(view.conclusion)}</p>
      </div>

      <p class="arkExplainabilitySymbol">
        対象銘柄：${escapeHtml(view.symbol)}
      </p>
    </section>
  `;
}

export function resolveExplainabilityContainer(
  documentRef = globalThis.document,
) {
  if (!documentRef) {
    return null;
  }

  const existing =
    documentRef.querySelector(
      "#arkAIExplainability",
    );

  if (existing) {
    return existing;
  }

  const container =
    documentRef.createElement(
      "section",
    );

  container.id =
    "arkAIExplainability";

  container.className =
    "arkAIExplainabilityRoot";

  const anchor =
    documentRef.querySelector(
      "#arkAIResultPresenter, #aiAnalysisResult, #arkPredictionLabV3",
    );

  if (
    anchor &&
    typeof anchor.insertAdjacentElement ===
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

  return container;
}

export function mountAIExplainability({
  result = {},
  documentRef = globalThis.document,
} = {}) {
  const container =
    resolveExplainabilityContainer(
      documentRef,
    );

  if (!container) {
    return {
      mounted: false,
      reason: "document_unavailable",
    };
  }

  container.innerHTML =
    renderAIExplainabilityPanel(
      result,
    );

  container.dataset
    .aiExplainabilityState =
    "ready";

  return {
    mounted: true,
    container,
  };
}

export function connectAIExplainabilityPanel({
  eventTarget = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  if (
    !eventTarget ||
    !documentRef
  ) {
    return () => {};
  }

  const completeHandler =
    (event) => {
      mountAIExplainability({
        result:
          event?.detail ?? {},

        documentRef,
      });
    };

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    completeHandler,
  );

  return () => {
    eventTarget.removeEventListener(
      "ark:ai-analysis-complete",
      completeHandler,
    );
  };
}