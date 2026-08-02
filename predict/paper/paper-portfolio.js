export const PAPER_PORTFOLIO_VERSION =
  "paper-portfolio-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function numberOr(
  value,
  fallback = 0,
) {
  return finite(value)
    ? Number(value)
    : fallback;
}

export function createPaperPortfolioSummary({
  account = {},
  sectorBySymbol = {},
} = {}) {
  const positions =
    Object.values(
      account.positions || {},
    );

  const equity =
    numberOr(
      account.equity,
      account.cash,
    );

  const cash =
    numberOr(
      account.cash,
      0,
    );

  const marketValue =
    positions.reduce(
      (sum, position) =>
        sum +
        numberOr(
          position.marketValue,
          0,
        ),
      0,
    );

  const sectorValues = {};

  const rows =
    positions.map(
      (position) => {
        const value =
          numberOr(
            position.marketValue,
            0,
          );

        const sector =
          String(
            sectorBySymbol[
              position.symbol
            ] ||
            "未分類",
          );

        sectorValues[sector] =
          numberOr(
            sectorValues[
              sector
            ],
            0,
          ) +
          value;

        return {
          symbol:
            position.symbol,

          quantity:
            numberOr(
              position.quantity,
              0,
            ),

          averagePrice:
            numberOr(
              position.averagePrice,
              0,
            ),

          marketPrice:
            numberOr(
              position.marketPrice,
              0,
            ),

          marketValue:
            value,

          unrealizedPnl:
            numberOr(
              position.unrealizedPnl,
              0,
            ),

          weightPercent:
            equity > 0
              ? (
                  value /
                  equity
                ) * 100
              : 0,

          sector,
        };
      },
    )
    .sort(
      (a, b) =>
        b.marketValue -
        a.marketValue,
    );

  const sectors =
    Object.entries(
      sectorValues,
    )
      .map(
        ([
          sector,
          value,
        ]) => ({
          sector,
          marketValue:
            value,

          weightPercent:
            equity > 0
              ? (
                  value /
                  equity
                ) * 100
              : 0,
        }),
      )
      .sort(
        (a, b) =>
          b.marketValue -
          a.marketValue,
      );

  const concentration =
    rows.reduce(
      (sum, row) => {
        const weight =
          row.weightPercent /
          100;

        return (
          sum +
          weight *
          weight
        );
      },
      0,
    );

  return {
    version:
      PAPER_PORTFOLIO_VERSION,

    positionCount:
      rows.length,

    cash,
    marketValue,
    equity,

    cashRatioPercent:
      equity > 0
        ? (
            cash /
            equity
          ) * 100
        : 0,

    exposurePercent:
      equity > 0
        ? (
            marketValue /
            equity
          ) * 100
        : 0,

    concentrationIndex:
      concentration,

    diversificationScore:
      Math.max(
        0,
        Math.min(
          100,
          (
            1 -
            concentration
          ) * 100,
        ),
      ),

    largestPositionPercent:
      rows.length > 0
        ? rows[0]
            .weightPercent
        : 0,

    positions:
      rows,

    sectors,
  };
}

export function evaluatePortfolioLimits({
  summary,
  maximumPositionPercent = 30,
  maximumSectorPercent = 50,
  minimumCashPercent = 10,
} = {}) {
  const reasons = [];

  if (
    numberOr(
      summary
        ?.largestPositionPercent,
      0,
    ) >
    Number(
      maximumPositionPercent,
    )
  ) {
    reasons.push(
      "position_concentration_high",
    );
  }

  const largestSector =
    summary?.sectors?.[0]
      ?.weightPercent || 0;

  if (
    largestSector >
    Number(
      maximumSectorPercent,
    )
  ) {
    reasons.push(
      "sector_concentration_high",
    );
  }

  if (
    numberOr(
      summary
        ?.cashRatioPercent,
      0,
    ) <
    Number(
      minimumCashPercent,
    )
  ) {
    reasons.push(
      "cash_ratio_low",
    );
  }

  return {
    passed:
      reasons.length === 0,

    reasons,

    metrics: {
      largestPositionPercent:
        numberOr(
          summary
            ?.largestPositionPercent,
          0,
        ),

      largestSectorPercent:
        numberOr(
          largestSector,
          0,
        ),

      cashRatioPercent:
        numberOr(
          summary
            ?.cashRatioPercent,
          0,
        ),
    },
  };
}

export const PaperPortfolioInternals = {
  finite,
  numberOr,
};