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
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function actionClass(action = "HOLD") {
  const normalized =
    String(action)
      .trim()
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

export function buildAIResultViewModel(
  result = {},
) {
  return {
    symbol:
      result.symbol ??
      "--",

    action:
      result.action ??
      "HOLD",

    actionClass:
      actionClass(
        result.action,
      ),

    score:
      finiteNumber(
        result.score,
        50,
      ),

    confidence:
      finiteNumber(
        result.confidence,
        0,
      ),

    agreementRate:
      finiteNumber(
        result.agreementRate,
        0,
      ),

    executable:
      result.executable === true,

    shares:
      finiteNumber(
        result.shares,
        0,
      ),

    entryPrice:
      finiteNumber(
        result.entryPrice,
        0,
      ),

    stopPrice:
      finiteNumber(
        result.stopPrice,
        0,
      ),

    targetPrice:
      finiteNumber(
        result.targetPrice,
        0,
      ),

    estimatedCost:
      finiteNumber(
        result.estimatedCost,
        0,
      ),

    buyFactors:
      Array.isArray(
        result.buyFactors,
      )
        ? result.buyFactors
        : [],

    riskFactors:
      Array.isArray(
        result.riskFactors,
      )
        ? result.riskFactors
        : [],
  };
}

export function renderAIResult(
  result = {},
) {
  const view =
    buildAIResultViewModel(
      result,
    );

  const buyFactors =
    view.buyFactors.length
      ? view.buyFactors
          .map(
            (factor) =>
              `<li>✓ ${escapeHtml(factor)}</li>`,
          )
          .join("")
      : "<li>明確な買い要因なし</li>";

  const riskFactors =
    view.riskFactors.length
      ? view.riskFactors
          .map(
            (factor) =>
              `<li>⚠ ${escapeHtml(factor)}</li>`,
          )
          .join("")
      : "<li>重大なリスク要因なし</li>";

  return `
    <section class="arkAIResultPresenter">
      <header class="arkAIResultHeader">
        <div>
          <span class="arkAIResultEyebrow">
            AI ANALYSIS RESULT
          </span>

          <h2>
            ${escapeHtml(view.symbol)}
          </h2>
        </div>

        <span class="arkAIResultAction ${escapeHtml(
          view.actionClass,
        )}">
          ${escapeHtml(view.action)}
        </span>
      </header>

      <div class="arkAIResultMetrics">
        <article>
          <span>総合スコア</span>
          <strong>${view.score}</strong>
        </article>

        <article>
          <span>信頼度</span>
          <strong>${view.confidence}%</strong>
        </article>

        <article>
          <span>合意率</span>
          <strong>${view.agreementRate}%</strong>
        </article>

        <article>
          <span>実行判定</span>
          <strong>
            ${
              view.executable
                ? "実行候補"
                : "見送り"
            }
          </strong>
        </article>
      </div>

      <div class="arkAIResultTrade">
        <article>
          <span>推奨株数</span>
          <strong>${view.shares}株</strong>
        </article>

        <article>
          <span>エントリー</span>
          <strong>¥${view.entryPrice}</strong>
        </article>

        <article>
          <span>損切り</span>
          <strong>¥${view.stopPrice}</strong>
        </article>

        <article>
          <span>利確目標</span>
          <strong>¥${view.targetPrice}</strong>
        </article>

        <article>
          <span>必要資金</span>
          <strong>¥${view.estimatedCost}</strong>
        </article>
      </div>

      <div class="arkAIResultFactors">
        <article>
          <h3>買い要因</h3>
          <ul>${buyFactors}</ul>
        </article>

        <article>
          <h3>リスク要因</h3>
          <ul>${riskFactors}</ul>
        </article>
      </div>

      <p class="arkAIResultDisclaimer">
        本結果は分析支援用です。将来の利益や価格変動を保証しません。
      </p>
    </section>
  `;
}

export function renderAIResultError(
  error = {},
) {
  return `
    <section class="arkAIResultError">
      <strong>AI分析に失敗しました</strong>
      <p>${escapeHtml(
        error.message ??
        "Unknown error",
      )}</p>
    </section>
  `;
}

export function resolveAIResultContainer(
  documentRef =
    globalThis.document,
) {
  if (!documentRef) {
    return null;
  }

  const selectors = [
    "#arkAIResultPresenter",
    "#aiAnalysisResult",
    "#ai-analysis-result",
    ".ai-analysis-result",
  ];

  for (const selector of selectors) {
    const container =
      documentRef.querySelector(
        selector,
      );

    if (container) {
      return container;
    }
  }

  const container =
    documentRef.createElement(
      "section",
    );

  container.id =
    "arkAIResultPresenter";

  container.className =
    "arkAIResultPresenterRoot";

  const anchor =
    documentRef.querySelector(
      "#arkPredictionLabV3, #arkPredictionLabV2, #arkIntegratedAiDashboard",
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

  return container;
}

export function mountAIResult({
  result = {},
  documentRef =
    globalThis.document,
} = {}) {
  const container =
    resolveAIResultContainer(
      documentRef,
    );

  if (!container) {
    return {
      mounted: false,
      reason:
        "document_unavailable",
    };
  }

  container.innerHTML =
    renderAIResult(
      result,
    );

  container.dataset
    .aiResultState =
    "ready";

  return {
    mounted: true,
    container,
  };
}

export function connectAIResultPresenter({
  eventTarget =
    globalThis.window,

  documentRef =
    globalThis.document,
} = {}) {
  if (
    !eventTarget ||
    !documentRef
  ) {
    return () => {};
  }

  const completeHandler =
    (event) => {
      mountAIResult({
        result:
          event?.detail ?? {},
        documentRef,
      });
    };

  const errorHandler =
    (event) => {
      const container =
        resolveAIResultContainer(
          documentRef,
        );

      if (!container) {
        return;
      }

      container.innerHTML =
        renderAIResultError(
          event?.detail ?? {},
        );

      container.dataset
        .aiResultState =
        "error";
    };

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    completeHandler,
  );

  eventTarget.addEventListener(
    "ark:ai-analysis-error",
    errorHandler,
  );

  return () => {
    eventTarget.removeEventListener(
      "ark:ai-analysis-complete",
      completeHandler,
    );

    eventTarget.removeEventListener(
      "ark:ai-analysis-error",
      errorHandler,
    );
  };
}

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined"
) {
  window.ArkAIResultPresenter = {
    mount:
      mountAIResult,

    render:
      renderAIResult,
  };

  const start = () => {
    connectAIResultPresenter();
  };

  if (
    document.readyState ===
    "loading"
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