import {
  buildTradePlanSummary,
} from "./final-trade-plan-engine.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function numberLabel(
  value,
  digits = 0,
) {
  const number =
    Number(value);

  if (!Number.isFinite(number)) {
    return "--";
  }

  return number.toLocaleString(
    "ja-JP",
    {
      minimumFractionDigits:
        digits,

      maximumFractionDigits:
        digits,
    },
  );
}

function priceLabel(value) {
  const number =
    Number(value);

  if (!Number.isFinite(number)) {
    return "--";
  }

  return `¥${numberLabel(
    number,
    number % 1 === 0
      ? 0
      : 2,
  )}`;
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
    normalized === "NO TRADE" ||
    normalized === "SELL" ||
    normalized === "REDUCE"
  ) {
    return "negative";
  }

  return "neutral";
}

export function createTradePlanViewModel(
  plan = {},
) {
  const summary =
    buildTradePlanSummary(
      plan,
    );

  return {
    symbol:
      summary.symbol ??
      "--",

    action:
      summary.action ??
      "NO TRADE",

    actionClass:
      actionClass(
        summary.action,
      ),

    executable:
      summary.executable === true,

    shares:
      Number(
        summary.shares ?? 0,
      ),

    entryPrice:
      Number(
        summary.entryPrice ?? 0,
      ),

    stopPrice:
      Number(
        summary.stopPrice ?? 0,
      ),

    targetPrice:
      Number(
        summary.targetPrice ?? 0,
      ),

    riskRewardRatio:
      summary.riskRewardRatio,

    estimatedCost:
      Number(
        summary.estimatedCost ?? 0,
      ),

    estimatedLoss:
      Number(
        summary.estimatedLoss ?? 0,
      ),

    estimatedProfit:
      Number(
        summary.estimatedProfit ?? 0,
      ),

    reasons:
      Array.isArray(
        plan.reasons,
      )
        ? plan.reasons
        : [],

    labels: {
      shares:
        `${numberLabel(
          summary.shares,
        )}株`,

      entryPrice:
        priceLabel(
          summary.entryPrice,
        ),

      stopPrice:
        priceLabel(
          summary.stopPrice,
        ),

      targetPrice:
        priceLabel(
          summary.targetPrice,
        ),

      riskRewardRatio:
        summary
          .riskRewardRatio === null ||
        summary
          .riskRewardRatio === undefined
          ? "--"
          : `1 : ${numberLabel(
              summary.riskRewardRatio,
              2,
            )}`,

      estimatedCost:
        priceLabel(
          summary.estimatedCost,
        ),

      estimatedLoss:
        priceLabel(
          summary.estimatedLoss,
        ),

      estimatedProfit:
        priceLabel(
          summary.estimatedProfit,
        ),
    },
  };
}

export function renderFinalTradePlan(
  plan = {},
) {
  const view =
    createTradePlanViewModel(
      plan,
    );

  const reasons =
    view.reasons.length
      ? `
        <ul class="finalTradePlanReasons">
          ${view.reasons
            .map(
              (reason) =>
                `<li>${escapeHtml(reason)}</li>`,
            )
            .join("")}
        </ul>
      `
      : "";

  return `
    <section class="finalTradePlan">
      <header class="finalTradePlanHeader">
        <div>
          <span class="finalTradePlanEyebrow">
            FINAL TRADE PLAN
          </span>

          <h3>
            ${escapeHtml(view.symbol)}
          </h3>
        </div>

        <span class="finalTradePlanAction ${escapeHtml(
          view.actionClass,
        )}">
          ${escapeHtml(view.action)}
        </span>
      </header>

      <div class="finalTradePlanGrid">
        <article>
          <span>推奨株数</span>
          <strong>
            ${escapeHtml(
              view.labels.shares,
            )}
          </strong>
        </article>

        <article>
          <span>エントリー</span>
          <strong>
            ${escapeHtml(
              view.labels.entryPrice,
            )}
          </strong>
        </article>

        <article>
          <span>損切り</span>
          <strong>
            ${escapeHtml(
              view.labels.stopPrice,
            )}
          </strong>
        </article>

        <article>
          <span>利確目標</span>
          <strong>
            ${escapeHtml(
              view.labels.targetPrice,
            )}
          </strong>
        </article>

        <article>
          <span>リスクリワード</span>
          <strong>
            ${escapeHtml(
              view.labels.riskRewardRatio,
            )}
          </strong>
        </article>

        <article>
          <span>必要資金</span>
          <strong>
            ${escapeHtml(
              view.labels.estimatedCost,
            )}
          </strong>
        </article>

        <article>
          <span>想定損失</span>
          <strong class="loss">
            ${escapeHtml(
              view.labels.estimatedLoss,
            )}
          </strong>
        </article>

        <article>
          <span>想定利益</span>
          <strong class="profit">
            ${escapeHtml(
              view.labels.estimatedProfit,
            )}
          </strong>
        </article>
      </div>

      ${reasons}

      <p class="finalTradePlanDisclaimer">
        売買数量と価格水準は分析支援用です。
        実際の注文前に板・出来高・決算日・許容損失を確認してください。
      </p>
    </section>
  `;
}

export function mountFinalTradePlan({
  plan = {},
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
      "#arkFinalTradePlan",
    );

  if (!container) {
    container =
      documentRef.createElement(
        "section",
      );

    container.id =
      "arkFinalTradePlan";

    container.className =
      "arkFinalTradePlanRoot";

    const anchor =
      documentRef.querySelector(
        "#arkPredictionLabV2, #arkIntegratedAiDashboard, #aiAnalysisResult",
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
    renderFinalTradePlan(
      plan,
    );

  container.dataset
    .finalTradePlanStatus =
    "ready";

  return {
    mounted: true,
    container,
  };
}