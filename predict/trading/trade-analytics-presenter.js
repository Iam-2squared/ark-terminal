export const TRADE_ANALYTICS_PRESENTER_VERSION =
  "trade-analytics-presenter-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function round(value, digits = 2) {
  if (!finite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      Number(value) *
      factor,
    ) /
    factor
  );
}

function formatNumber(
  value,
  {
    digits = 2,
    fallback = "--",
  } = {},
) {
  const rounded =
    round(value, digits);

  if (!finite(rounded)) {
    return fallback;
  }

  return rounded.toLocaleString(
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
  {
    fallback = "--",
  } = {},
) {
  if (!finite(value)) {
    return fallback;
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

function formatSignedCurrency(
  value,
  {
    fallback = "--",
  } = {},
) {
  if (!finite(value)) {
    return fallback;
  }

  const resolved =
    Math.round(
      Number(value),
    );

  if (resolved > 0) {
    return (
      "+¥" +
      resolved.toLocaleString(
        "ja-JP",
      )
    );
  }

  if (resolved < 0) {
    return (
      "-¥" +
      Math.abs(
        resolved,
      ).toLocaleString(
        "ja-JP",
      )
    );
  }

  return "¥0";
}

function formatPercent(
  value,
  {
    signed = false,
    digits = 2,
    fallback = "--",
  } = {},
) {
  if (!finite(value)) {
    return fallback;
  }

  const rounded =
    round(value, digits);

  const prefix =
    signed &&
    rounded > 0
      ? "+"
      : "";

  return (
    prefix +
    formatNumber(
      rounded,
      {
        digits,
        fallback,
      },
    ) +
    "%"
  );
}

function metricCard({
  id,
  label,
  value,
  rawValue,
  tone = "neutral",
  description = "",
}) {
  return {
    id,
    label,
    value,
    rawValue:
      finite(rawValue)
        ? Number(rawValue)
        : rawValue ?? null,
    tone,
    description,
  };
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

function ratioTone(
  value,
  {
    good = 1,
    weak = 0,
  } = {},
) {
  if (!finite(value)) {
    return "neutral";
  }

  if (Number(value) >= good) {
    return "positive";
  }

  if (Number(value) <= weak) {
    return "negative";
  }

  return "warning";
}

function buildExitReasonRows(
  byExitReason = {},
) {
  return Object.entries(
    byExitReason || {},
  )
    .map(
      ([reason, stats]) => ({
        reason,
        count:
          Number(
            stats?.count || 0,
          ),
        winCount:
          Number(
            stats?.winCount || 0,
          ),
        winRate:
          finite(
            stats?.winRate,
          )
            ? Number(
                stats.winRate,
              )
            : null,
        totalNetPnl:
          finite(
            stats
              ?.totalNetPnl,
          )
            ? Number(
                stats.totalNetPnl,
              )
            : null,
        averageNetPnl:
          finite(
            stats
              ?.averageNetPnl,
          )
            ? Number(
                stats.averageNetPnl,
              )
            : null,
        averageReturnPercent:
          finite(
            stats
              ?.averageReturnPercent,
          )
            ? Number(
                stats
                  .averageReturnPercent,
              )
            : null,
        averageHoldingBars:
          finite(
            stats
              ?.averageHoldingBars,
          )
            ? Number(
                stats
                  .averageHoldingBars,
              )
            : null,
      }),
    )
    .sort(
      (a, b) =>
        b.count -
        a.count,
    )
    .map(
      (row) => ({
        ...row,
        display: {
          winRate:
            formatPercent(
              row.winRate,
            ),
          totalNetPnl:
            formatSignedCurrency(
              row.totalNetPnl,
            ),
          averageNetPnl:
            formatSignedCurrency(
              row.averageNetPnl,
            ),
          averageReturnPercent:
            formatPercent(
              row.averageReturnPercent,
              {
                signed: true,
              },
            ),
          averageHoldingBars:
            finite(
              row.averageHoldingBars,
            )
              ? (
                  formatNumber(
                    row.averageHoldingBars,
                    {
                      digits: 1,
                    },
                  ) +
                  "本"
                )
              : "--",
        },
        tone:
          pnlTone(
            row.totalNetPnl,
          ),
      }),
    );
}

export function createTradeAnalyticsViewModel(
  analytics = {},
) {
  const tradeCount =
    Number(
      analytics.tradeCount || 0,
    );

  const winCount =
    Number(
      analytics.winCount || 0,
    );

  const lossCount =
    Number(
      analytics.lossCount || 0,
    );

  const cards = [
    metricCard({
      id: "trade-count",
      label: "取引回数",
      value:
        tradeCount.toLocaleString(
          "ja-JP",
        ),
      rawValue:
        tradeCount,
      description:
        "確定済み取引の総数",
    }),

    metricCard({
      id: "win-rate",
      label: "勝率",
      value:
        formatPercent(
          analytics.winRate,
        ),
      rawValue:
        analytics.winRate,
      tone:
        finite(
          analytics.winRate,
        )
          ? (
              Number(
                analytics.winRate,
              ) >= 50
                ? "positive"
                : "warning"
            )
          : "neutral",
      description:
        "利益で終了した取引の割合",
    }),

    metricCard({
      id: "profit-factor",
      label: "Profit Factor",
      value:
        analytics.profitFactor ===
        Infinity
          ? "∞"
          : formatNumber(
              analytics.profitFactor,
              {
                digits: 2,
              },
            ),
      rawValue:
        analytics.profitFactor,
      tone:
        analytics.profitFactor ===
        Infinity
          ? "positive"
          : ratioTone(
              analytics.profitFactor,
              {
                good: 1.2,
                weak: 1,
              },
            ),
      description:
        "総利益 ÷ 総損失",
    }),

    metricCard({
      id: "expectancy",
      label: "1取引期待値",
      value:
        formatSignedCurrency(
          analytics.expectancy,
        ),
      rawValue:
        analytics.expectancy,
      tone:
        pnlTone(
          analytics.expectancy,
        ),
      description:
        "1回の取引で期待される平均損益",
    }),

    metricCard({
      id: "payoff-ratio",
      label: "平均損益比",
      value:
        formatNumber(
          analytics.payoffRatio,
          {
            digits: 2,
          },
        ),
      rawValue:
        analytics.payoffRatio,
      tone:
        ratioTone(
          analytics.payoffRatio,
          {
            good: 1.2,
            weak: 1,
          },
        ),
      description:
        "平均利益 ÷ 平均損失の絶対値",
    }),

    metricCard({
      id: "average-win",
      label: "平均利益",
      value:
        formatSignedCurrency(
          analytics.averageWin,
        ),
      rawValue:
        analytics.averageWin,
      tone:
        pnlTone(
          analytics.averageWin,
        ),
    }),

    metricCard({
      id: "average-loss",
      label: "平均損失",
      value:
        formatSignedCurrency(
          analytics.averageLoss,
        ),
      rawValue:
        analytics.averageLoss,
      tone:
        pnlTone(
          analytics.averageLoss,
        ),
    }),

    metricCard({
      id: "maximum-win",
      label: "最大利益",
      value:
        formatSignedCurrency(
          analytics.maximumWin,
        ),
      rawValue:
        analytics.maximumWin,
      tone:
        pnlTone(
          analytics.maximumWin,
        ),
    }),

    metricCard({
      id: "maximum-loss",
      label: "最大損失",
      value:
        formatSignedCurrency(
          analytics.maximumLoss,
        ),
      rawValue:
        analytics.maximumLoss,
      tone:
        pnlTone(
          analytics.maximumLoss,
        ),
    }),

    metricCard({
      id: "average-holding-bars",
      label: "平均保有15分足",
      value:
        finite(
          analytics
            .averageHoldingBars,
        )
          ? (
              formatNumber(
                analytics
                  .averageHoldingBars,
                {
                  digits: 1,
                },
              ) +
              "本"
            )
          : "--",
      rawValue:
        analytics
          .averageHoldingBars,
      description:
        "1本は15分",
    }),

    metricCard({
      id: "average-mfe",
      label: "平均MFE",
      value:
        formatPercent(
          analytics
            .averageMfePercent,
          {
            signed: true,
          },
        ),
      rawValue:
        analytics
          .averageMfePercent,
      tone:
        pnlTone(
          analytics
            .averageMfePercent,
        ),
      description:
        "保有中の最大含み益",
    }),

    metricCard({
      id: "average-mae",
      label: "平均MAE",
      value:
        formatPercent(
          analytics
            .averageMaePercent,
          {
            signed: true,
          },
        ),
      rawValue:
        analytics
          .averageMaePercent,
      tone:
        pnlTone(
          analytics
            .averageMaePercent,
        ),
      description:
        "保有中の最大含み損",
    }),

    metricCard({
      id: "gross-pnl",
      label: "コスト控除前損益",
      value:
        formatSignedCurrency(
          analytics
            .grossPnlBeforeCosts,
        ),
      rawValue:
        analytics
          .grossPnlBeforeCosts,
      tone:
        pnlTone(
          analytics
            .grossPnlBeforeCosts,
        ),
    }),

    metricCard({
      id: "trading-cost",
      label: "総取引コスト",
      value:
        formatCurrency(
          analytics
            .totalTradingCost,
        ),
      rawValue:
        analytics
          .totalTradingCost,
      tone:
        finite(
          analytics
            .totalTradingCost,
        ) &&
        Number(
          analytics
            .totalTradingCost,
        ) > 0
          ? "warning"
          : "neutral",
    }),

    metricCard({
      id: "net-pnl",
      label: "コスト控除後損益",
      value:
        formatSignedCurrency(
          analytics
            .totalNetPnl,
        ),
      rawValue:
        analytics
          .totalNetPnl,
      tone:
        pnlTone(
          analytics
            .totalNetPnl,
        ),
    }),

    metricCard({
      id: "cost-drag",
      label: "コスト負担率",
      value:
        formatPercent(
          analytics
            .costDragPercent,
        ),
      rawValue:
        analytics
          .costDragPercent,
      tone:
        finite(
          analytics
            .costDragPercent,
        ) &&
        Number(
          analytics
            .costDragPercent,
        ) > 30
          ? "negative"
          : "neutral",
    }),
  ];

  const hasTrades =
    tradeCount > 0;

  return {
    version:
      TRADE_ANALYTICS_PRESENTER_VERSION,

    status:
      hasTrades
        ? "ready"
        : "empty",

    statusLabel:
      hasTrades
        ? "分析済み"
        : "取引データ待ち",

    summary: {
      tradeCount,
      winCount,
      lossCount,
      flatCount:
        Number(
          analytics.flatCount ||
          0,
        ),

      headline:
        hasTrades
          ? (
              `${tradeCount}件中 ` +
              `${winCount}勝 ` +
              `${lossCount}敗`
            )
          : "確定取引がありません",

      diagnosis:
        !hasTrades
          ? "取引が確定すると損益分析が表示されます。"
          : (
              finite(
                analytics
                  .expectancy,
              ) &&
              Number(
                analytics
                  .expectancy,
              ) > 0
                ? "1取引期待値はプラスです。"
                : "1取引期待値はマイナスです。エントリーまたは決済条件の改善が必要です。"
            ),
    },

    cards,

    exitReasons:
      buildExitReasonRows(
        analytics.byExitReason,
      ),

    raw:
      analytics,
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

export function renderTradeAnalyticsHtml(
  analytics = {},
) {
  const viewModel =
    createTradeAnalyticsViewModel(
      analytics,
    );

  const cardsHtml =
    viewModel.cards
      .map(
        (card) => `
          <article
            class="trade-analytics-card"
            data-tone="${escapeHtml(card.tone)}"
            data-metric-id="${escapeHtml(card.id)}"
          >
            <div class="trade-analytics-card__label">
              ${escapeHtml(card.label)}
            </div>
            <div class="trade-analytics-card__value">
              ${escapeHtml(card.value)}
            </div>
            ${
              card.description
                ? `
                  <div class="trade-analytics-card__description">
                    ${escapeHtml(card.description)}
                  </div>
                `
                : ""
            }
          </article>
        `,
      )
      .join("");

  const exitRowsHtml =
    viewModel.exitReasons
      .map(
        (row) => `
          <tr data-tone="${escapeHtml(row.tone)}">
            <td>${escapeHtml(row.reason)}</td>
            <td>${escapeHtml(row.count)}</td>
            <td>${escapeHtml(row.display.winRate)}</td>
            <td>${escapeHtml(row.display.totalNetPnl)}</td>
            <td>${escapeHtml(row.display.averageNetPnl)}</td>
            <td>${escapeHtml(row.display.averageHoldingBars)}</td>
          </tr>
        `,
      )
      .join("");

  return `
    <section
      class="trade-analytics"
      data-status="${escapeHtml(viewModel.status)}"
    >
      <header class="trade-analytics__header">
        <div>
          <p class="trade-analytics__eyebrow">
            TRADE PERFORMANCE
          </p>
          <h3>
            売買損益分析
          </h3>
        </div>

        <span class="trade-analytics__status">
          ${escapeHtml(viewModel.statusLabel)}
        </span>
      </header>

      <p class="trade-analytics__headline">
        ${escapeHtml(viewModel.summary.headline)}
      </p>

      <p class="trade-analytics__diagnosis">
        ${escapeHtml(viewModel.summary.diagnosis)}
      </p>

      <div class="trade-analytics__grid">
        ${cardsHtml}
      </div>

      ${
        viewModel.exitReasons.length
          ? `
            <div class="trade-analytics__exit-reasons">
              <h4>決済理由別成績</h4>

              <div class="trade-analytics__table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>決済理由</th>
                      <th>件数</th>
                      <th>勝率</th>
                      <th>合計損益</th>
                      <th>平均損益</th>
                      <th>平均保有</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${exitRowsHtml}
                  </tbody>
                </table>
              </div>
            </div>
          `
          : ""
      }
    </section>
  `;
}

export const TradeAnalyticsPresenterInternals = {
  finite,
  round,
  formatNumber,
  formatCurrency,
  formatSignedCurrency,
  formatPercent,
  pnlTone,
  ratioTone,
  buildExitReasonRows,
  escapeHtml,
};