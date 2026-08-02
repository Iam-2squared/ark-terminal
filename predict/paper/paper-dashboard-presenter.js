import {
  createPaperBrokerSnapshot,
} from "./paper-broker.js";

import {
  createPaperPortfolioSummary,
  evaluatePortfolioLimits,
} from "./paper-portfolio.js";

import {
  calculatePaperPerformance,
} from "./paper-performance.js";

export const PAPER_DASHBOARD_PRESENTER_VERSION =
  "paper-dashboard-presenter-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function formatNumber(
  value,
  digits = 0,
) {
  if (!finite(value)) {
    return "--";
  }

  return Number(value)
    .toLocaleString(
      "ja-JP",
      {
        minimumFractionDigits: 0,
        maximumFractionDigits:
          digits,
      },
    );
}

function formatCurrency(
  value,
) {
  if (!finite(value)) {
    return "--";
  }

  const amount =
    Math.round(
      Number(value),
    );

  if (amount > 0) {
    return (
      "+¥" +
      amount.toLocaleString(
        "ja-JP",
      )
    );
  }

  if (amount < 0) {
    return (
      "-¥" +
      Math.abs(amount)
        .toLocaleString(
          "ja-JP",
        )
    );
  }

  return "¥0";
}

function formatUnsignedCurrency(
  value,
) {
  if (!finite(value)) {
    return "--";
  }

  return (
    "¥" +
    Math.round(
      Number(value),
    ).toLocaleString(
      "ja-JP",
    )
  );
}

function formatPercent(
  value,
  signed = false,
) {
  if (!finite(value)) {
    return "--";
  }

  const number =
    Math.round(
      Number(value) * 100,
    ) / 100;

  const prefix =
    signed &&
    number > 0
      ? "+"
      : "";

  return (
    prefix +
    number.toLocaleString(
      "ja-JP",
      {
        maximumFractionDigits:
          2,
      },
    ) +
    "%"
  );
}

function pnlTone(value) {
  if (!finite(value)) {
    return "neutral";
  }

  if (Number(value) > 0) {
    return "positive";
  }

  if (Number(value) < 0) {
    return "negative";
  }

  return "neutral";
}

function card({
  id,
  label,
  value,
  rawValue = null,
  tone = "neutral",
  description = "",
}) {
  return {
    id,
    label,
    value,
    rawValue,
    tone,
    description,
  };
}

export function createPaperDashboardViewModel({
  broker = {},
  sectorBySymbol = {},
  killSwitch = {
    enabled: false,
  },
} = {}) {
  const snapshot =
    createPaperBrokerSnapshot(
      broker,
    );

  const portfolio =
    createPaperPortfolioSummary({
      account:
        broker.account || {},
      sectorBySymbol,
    });

  const portfolioLimits =
    evaluatePortfolioLimits({
      summary:
        portfolio,
    });

  const performance =
    calculatePaperPerformance(
      broker.account || {},
    );

  const cards = [
    card({
      id: "equity",
      label: "総資産",
      value:
        formatUnsignedCurrency(
          snapshot.equity,
        ),
      rawValue:
        snapshot.equity,
    }),

    card({
      id: "cash",
      label: "現金残高",
      value:
        formatUnsignedCurrency(
          snapshot.cash,
        ),
      rawValue:
        snapshot.cash,
    }),

    card({
      id: "buying-power",
      label: "買付余力",
      value:
        formatUnsignedCurrency(
          snapshot.buyingPower,
        ),
      rawValue:
        snapshot.buyingPower,
    }),

    card({
      id: "market-value",
      label: "保有時価",
      value:
        formatUnsignedCurrency(
          snapshot.marketValue,
        ),
      rawValue:
        snapshot.marketValue,
    }),

    card({
      id: "realized-pnl",
      label: "実現損益",
      value:
        formatCurrency(
          snapshot.realizedPnl,
        ),
      rawValue:
        snapshot.realizedPnl,
      tone:
        pnlTone(
          snapshot.realizedPnl,
        ),
    }),

    card({
      id: "unrealized-pnl",
      label: "評価損益",
      value:
        formatCurrency(
          snapshot.unrealizedPnl,
        ),
      rawValue:
        snapshot.unrealizedPnl,
      tone:
        pnlTone(
          snapshot.unrealizedPnl,
        ),
    }),

    card({
      id: "total-return",
      label: "総リターン",
      value:
        formatPercent(
          snapshot.totalReturnPercent,
          true,
        ),
      rawValue:
        snapshot.totalReturnPercent,
      tone:
        pnlTone(
          snapshot.totalReturnPercent,
        ),
    }),

    card({
      id: "cash-ratio",
      label: "現金比率",
      value:
        formatPercent(
          portfolio.cashRatioPercent,
        ),
      rawValue:
        portfolio.cashRatioPercent,
    }),

    card({
      id: "exposure",
      label: "投資比率",
      value:
        formatPercent(
          portfolio.exposurePercent,
        ),
      rawValue:
        portfolio.exposurePercent,
    }),

    card({
      id: "positions",
      label: "保有銘柄数",
      value:
        formatNumber(
          portfolio.positionCount,
        ),
      rawValue:
        portfolio.positionCount,
    }),

    card({
      id: "open-orders",
      label: "未約定注文",
      value:
        formatNumber(
          snapshot.orderSummary
            ?.open || 0,
        ),
      rawValue:
        snapshot.orderSummary
          ?.open || 0,
    }),

    card({
      id: "win-rate",
      label: "勝率",
      value:
        formatPercent(
          performance.winRate,
        ),
      rawValue:
        performance.winRate,
    }),
  ];

  const warnings = [];

  if (
    killSwitch?.enabled
  ) {
    warnings.push({
      level: "danger",
      code: "KILL_SWITCH",
      message:
        "緊急停止スイッチが有効です。新規注文は停止されています。",
    });
  }

  for (
    const reason of
    portfolioLimits.reasons
  ) {
    const messages = {
      position_concentration_high:
        "単一銘柄への集中度が高すぎます。",

      sector_concentration_high:
        "特定セクターへの集中度が高すぎます。",

      cash_ratio_low:
        "現金比率が低下しています。",
    };

    warnings.push({
      level: "warning",
      code:
        reason,
      message:
        messages[reason] ||
        reason,
    });
  }

  return {
    version:
      PAPER_DASHBOARD_PRESENTER_VERSION,

    status:
      killSwitch?.enabled
        ? "stopped"
        : "active",

    statusLabel:
      killSwitch?.enabled
        ? "緊急停止中"
        : "Paper Trading稼働中",

    cards,

    positions:
      portfolio.positions.map(
        (position) => ({
          ...position,

          display: {
            quantity:
              formatNumber(
                position.quantity,
              ),

            averagePrice:
              formatUnsignedCurrency(
                position.averagePrice,
              ),

            marketPrice:
              formatUnsignedCurrency(
                position.marketPrice,
              ),

            marketValue:
              formatUnsignedCurrency(
                position.marketValue,
              ),

            unrealizedPnl:
              formatCurrency(
                position.unrealizedPnl,
              ),

            weightPercent:
              formatPercent(
                position.weightPercent,
              ),
          },

          tone:
            pnlTone(
              position.unrealizedPnl,
            ),
        }),
      ),

    openOrders:
      (
        snapshot.openOrders || []
      ).map(
        (order) => ({
          ...order,

          display: {
            quantity:
              formatNumber(
                order.quantity,
              ),

            remainingQuantity:
              formatNumber(
                order.remainingQuantity,
              ),

            limitPrice:
              order.limitPrice === null
                ? "--"
                : formatUnsignedCurrency(
                    order.limitPrice,
                  ),

            averageFillPrice:
              order.averageFillPrice === null
                ? "--"
                : formatUnsignedCurrency(
                    order.averageFillPrice,
                  ),
          },
        }),
      ),

    warnings,

    portfolio,
    performance,
    snapshot,
  };
}

function escapeHtml(value) {
  return String(
    value ?? "",
  )
    .replaceAll(
      "&",
      "&amp;",
    )
    .replaceAll(
      "<",
      "&lt;",
    )
    .replaceAll(
      ">",
      "&gt;",
    )
    .replaceAll(
      '"',
      "&quot;",
    )
    .replaceAll(
      "'",
      "&#039;",
    );
}

export function renderPaperDashboardHtml({
  broker = {},
  sectorBySymbol = {},
  killSwitch = {
    enabled: false,
  },
} = {}) {
  const view =
    createPaperDashboardViewModel({
      broker,
      sectorBySymbol,
      killSwitch,
    });

  const cardsHtml =
    view.cards
      .map(
        (item) => `
          <article
            class="paper-dashboard-card"
            data-tone="${escapeHtml(item.tone)}"
            data-card-id="${escapeHtml(item.id)}"
          >
            <div class="paper-dashboard-card__label">
              ${escapeHtml(item.label)}
            </div>

            <div class="paper-dashboard-card__value">
              ${escapeHtml(item.value)}
            </div>

            ${
              item.description
                ? `
                  <div class="paper-dashboard-card__description">
                    ${escapeHtml(item.description)}
                  </div>
                `
                : ""
            }
          </article>
        `,
      )
      .join("");

  const positionsHtml =
    view.positions.length
      ? view.positions
          .map(
            (position) => `
              <tr data-tone="${escapeHtml(position.tone)}">
                <td>${escapeHtml(position.symbol)}</td>
                <td>${escapeHtml(position.display.quantity)}</td>
                <td>${escapeHtml(position.display.averagePrice)}</td>
                <td>${escapeHtml(position.display.marketPrice)}</td>
                <td>${escapeHtml(position.display.marketValue)}</td>
                <td>${escapeHtml(position.display.unrealizedPnl)}</td>
                <td>${escapeHtml(position.display.weightPercent)}</td>
              </tr>
            `,
          )
          .join("")
      : `
          <tr>
            <td colspan="7">
              保有銘柄はありません。
            </td>
          </tr>
        `;

  const ordersHtml =
    view.openOrders.length
      ? view.openOrders
          .map(
            (order) => `
              <tr>
                <td>${escapeHtml(order.symbol)}</td>
                <td>${escapeHtml(order.side)}</td>
                <td>${escapeHtml(order.type)}</td>
                <td>${escapeHtml(order.display.quantity)}</td>
                <td>${escapeHtml(order.display.remainingQuantity)}</td>
                <td>${escapeHtml(order.display.limitPrice)}</td>
                <td>${escapeHtml(order.status)}</td>
              </tr>
            `,
          )
          .join("")
      : `
          <tr>
            <td colspan="7">
              未約定注文はありません。
            </td>
          </tr>
        `;

  const warningsHtml =
    view.warnings.length
      ? view.warnings
          .map(
            (warning) => `
              <li
                data-level="${escapeHtml(warning.level)}"
                data-code="${escapeHtml(warning.code)}"
              >
                ${escapeHtml(warning.message)}
              </li>
            `,
          )
          .join("")
      : `
          <li data-level="success">
            現在、重大な警告はありません。
          </li>
        `;

  return `
    <section
      class="paper-dashboard"
      data-status="${escapeHtml(view.status)}"
    >
      <header class="paper-dashboard__header">
        <div>
          <p class="paper-dashboard__eyebrow">
            PAPER TRADING
          </p>

          <h3>
            仮想口座ダッシュボード
          </h3>
        </div>

        <span class="paper-dashboard__status">
          ${escapeHtml(view.statusLabel)}
        </span>
      </header>

      <div class="paper-dashboard__cards">
        ${cardsHtml}
      </div>

      <section class="paper-dashboard__warnings">
        <h4>安全状態</h4>
        <ul>
          ${warningsHtml}
        </ul>
      </section>

      <section class="paper-dashboard__positions">
        <h4>保有銘柄</h4>

        <div class="paper-dashboard__table-wrap">
          <table>
            <thead>
              <tr>
                <th>銘柄</th>
                <th>数量</th>
                <th>平均取得</th>
                <th>現在値</th>
                <th>時価</th>
                <th>評価損益</th>
                <th>比率</th>
              </tr>
            </thead>

            <tbody>
              ${positionsHtml}
            </tbody>
          </table>
        </div>
      </section>

      <section class="paper-dashboard__orders">
        <h4>未約定注文</h4>

        <div class="paper-dashboard__table-wrap">
          <table>
            <thead>
              <tr>
                <th>銘柄</th>
                <th>売買</th>
                <th>注文種別</th>
                <th>注文数量</th>
                <th>残数量</th>
                <th>指値</th>
                <th>状態</th>
              </tr>
            </thead>

            <tbody>
              ${ordersHtml}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  `;
}

export const PaperDashboardPresenterInternals = {
  finite,
  formatNumber,
  formatCurrency,
  formatUnsignedCurrency,
  formatPercent,
  pnlTone,
  escapeHtml,
};