export const TRANSACTION_COST_ENGINE_V3_VERSION =
  "transaction-cost-engine-v3";

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function positiveNumber(
  value,
  fallback = 0,
) {
  return Math.max(
    0,
    finiteNumber(
      value,
      fallback,
    ),
  );
}

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function round(
  value,
  digits = 6,
) {
  if (!Number.isFinite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value *
      factor,
    ) /
    factor
  );
}

function normalizeTimestamp(value) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Transaction cost timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeSymbol(value) {
  const symbol =
    String(
      value ??
      "",
    )
      .trim()
      .toUpperCase();

  if (!symbol) {
    throw new TypeError(
      "Transaction cost symbol is required.",
    );
  }

  return symbol;
}

function normalizeSide(value) {
  const side =
    String(
      value ??
      "",
    )
      .trim()
      .toUpperCase();

  if (
    side !== "BUY" &&
    side !== "SELL"
  ) {
    throw new TypeError(
      `Unsupported transaction side: ${side}`,
    );
  }

  return side;
}

function normalizeMarket(value) {
  const market =
    String(
      value ??
      "JP",
    )
      .trim()
      .toUpperCase();

  return market || "JP";
}

function normalizeTrade(
  trade = {},
) {
  const quantity =
    Math.floor(
      positiveNumber(
        trade.quantity,
        0,
      ),
    );

  const price =
    positiveNumber(
      trade.price,
      0,
    );

  if (quantity <= 0) {
    throw new TypeError(
      "Transaction quantity must be greater than zero.",
    );
  }

  if (price <= 0) {
    throw new TypeError(
      "Transaction price must be greater than zero.",
    );
  }

  return {
    symbol:
      normalizeSymbol(
        trade.symbol,
      ),

    side:
      normalizeSide(
        trade.side,
      ),

    market:
      normalizeMarket(
        trade.market,
      ),

    quantity,

    price,

    referencePrice:
      positiveNumber(
        trade.referencePrice,
        price,
      ),

    bid:
      positiveNumber(
        trade.bid,
        price,
      ),

    ask:
      positiveNumber(
        trade.ask,
        price,
      ),

    dailyVolume:
      positiveNumber(
        trade.dailyVolume,
        0,
      ),

    volatilityPercent:
      positiveNumber(
        trade.volatilityPercent,
        0,
      ),

    settlementCurrency:
      String(
        trade.settlementCurrency ??
        "JPY",
      )
        .trim()
        .toUpperCase(),

    fxRate:
      positiveNumber(
        trade.fxRate,
        1,
      ),

    metadata:
      clone(
        trade.metadata ??
        {},
      ),
  };
}

function calculateCommission({
  grossValue,
  rate,
  minimum,
  maximum,
  fixed,
}) {
  const variable =
    grossValue *
    rate;

  let commission =
    Math.max(
      minimum,
      variable +
      fixed,
    );

  if (
    maximum !== null &&
    Number.isFinite(maximum)
  ) {
    commission =
      Math.min(
        commission,
        maximum,
      );
  }

  return Math.max(
    0,
    commission,
  );
}

function calculateSpreadCost({
  side,
  quantity,
  bid,
  ask,
  executionPrice,
}) {
  if (
    bid <= 0 ||
    ask <= 0 ||
    ask < bid
  ) {
    return 0;
  }

  const midpoint =
    (
      bid +
      ask
    ) /
    2;

  const adversePrice =
    side === "BUY"
      ? Math.max(
          0,
          executionPrice -
          midpoint,
        )
      : Math.max(
          0,
          midpoint -
          executionPrice,
        );

  return (
    adversePrice *
    quantity
  );
}

function calculateSlippageCost({
  side,
  quantity,
  executionPrice,
  referencePrice,
}) {
  const adversePrice =
    side === "BUY"
      ? Math.max(
          0,
          executionPrice -
          referencePrice,
        )
      : Math.max(
          0,
          referencePrice -
          executionPrice,
        );

  return (
    adversePrice *
    quantity
  );
}

function calculateMarketImpact({
  grossValue,
  quantity,
  dailyVolume,
  volatilityPercent,
  impactCoefficient,
}) {
  if (
    dailyVolume <= 0 ||
    quantity <= 0
  ) {
    return 0;
  }

  const participationRate =
    quantity /
    dailyVolume;

  const volatility =
    volatilityPercent /
    100;

  const impactRate =
    impactCoefficient *
    Math.sqrt(
      participationRate,
    ) *
    Math.max(
      volatility,
      0.001,
    );

  return (
    grossValue *
    impactRate
  );
}

function calculateExchangeFee({
  grossValue,
  rate,
  fixed,
}) {
  return Math.max(
    0,
    grossValue *
    rate +
    fixed,
  );
}

function calculateTax({
  side,
  grossValue,
  taxRate,
  applyToBuy,
  applyToSell,
}) {
  if (
    side === "BUY" &&
    !applyToBuy
  ) {
    return 0;
  }

  if (
    side === "SELL" &&
    !applyToSell
  ) {
    return 0;
  }

  return Math.max(
    0,
    grossValue *
    taxRate,
  );
}

function calculateFxCost({
  grossValue,
  fxRate,
  fxFeeRate,
}) {
  if (
    fxRate <= 0 ||
    fxFeeRate <= 0
  ) {
    return 0;
  }

  return (
    grossValue *
    fxFeeRate
  );
}

function classifyCostRate(ratePercent) {
  if (ratePercent >= 2) {
    return "EXTREME";
  }

  if (ratePercent >= 1) {
    return "HIGH";
  }

  if (ratePercent >= 0.4) {
    return "MODERATE";
  }

  if (ratePercent >= 0.1) {
    return "LOW";
  }

  return "VERY_LOW";
}

export function estimateTransactionCost({
  trade = {},
  config = {},
  timestamp =
    new Date().toISOString(),
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalized =
    normalizeTrade(
      trade,
    );

  const commissionRate =
    positiveNumber(
      config.commissionRate,
      0.001,
    );

  const minimumCommission =
    positiveNumber(
      config.minimumCommission,
      0,
    );

  const maximumCommission =
    config.maximumCommission ===
      null ||
    config.maximumCommission ===
      undefined
      ? null
      : positiveNumber(
          config.maximumCommission,
          0,
        );

  const fixedCommission =
    positiveNumber(
      config.fixedCommission,
      0,
    );

  const exchangeFeeRate =
    positiveNumber(
      config.exchangeFeeRate,
      0,
    );

  const fixedExchangeFee =
    positiveNumber(
      config.fixedExchangeFee,
      0,
    );

  const regulatoryFeeRate =
    positiveNumber(
      config.regulatoryFeeRate,
      0,
    );

  const taxRate =
    positiveNumber(
      config.taxRate,
      0,
    );

  const applyTaxToBuy =
    config.applyTaxToBuy ===
    true;

  const applyTaxToSell =
    config.applyTaxToSell !==
    false;

  const fxFeeRate =
    positiveNumber(
      config.fxFeeRate,
      0,
    );

  const impactCoefficient =
    positiveNumber(
      config.impactCoefficient,
      0.1,
    );

  const includeSpread =
    config.includeSpread !==
    false;

  const includeSlippage =
    config.includeSlippage !==
    false;

  const includeMarketImpact =
    config.includeMarketImpact !==
    false;

  const grossValue =
    normalized.quantity *
    normalized.price;

  const commission =
    calculateCommission({
      grossValue,

      rate:
        commissionRate,

      minimum:
        minimumCommission,

      maximum:
        maximumCommission,

      fixed:
        fixedCommission,
    });

  const spreadCost =
    includeSpread
      ? calculateSpreadCost({
          side:
            normalized.side,

          quantity:
            normalized.quantity,

          bid:
            normalized.bid,

          ask:
            normalized.ask,

          executionPrice:
            normalized.price,
        })
      : 0;

  const slippageCost =
    includeSlippage
      ? calculateSlippageCost({
          side:
            normalized.side,

          quantity:
            normalized.quantity,

          executionPrice:
            normalized.price,

          referencePrice:
            normalized.referencePrice,
        })
      : 0;

  const marketImpactCost =
    includeMarketImpact
      ? calculateMarketImpact({
          grossValue,

          quantity:
            normalized.quantity,

          dailyVolume:
            normalized.dailyVolume,

          volatilityPercent:
            normalized.volatilityPercent,

          impactCoefficient,
        })
      : 0;

  const exchangeFee =
    calculateExchangeFee({
      grossValue,

      rate:
        exchangeFeeRate,

      fixed:
        fixedExchangeFee,
    });

  const regulatoryFee =
    normalized.side === "SELL"
      ? grossValue *
        regulatoryFeeRate
      : 0;

  const tax =
    calculateTax({
      side:
        normalized.side,

      grossValue,

      taxRate,

      applyToBuy:
        applyTaxToBuy,

      applyToSell:
        applyTaxToSell,
    });

  const fxCost =
    calculateFxCost({
      grossValue,

      fxRate:
        normalized.fxRate,

      fxFeeRate,
    });

  const explicitCost =
    commission +
    exchangeFee +
    regulatoryFee +
    tax +
    fxCost;

  const implicitCost =
    spreadCost +
    slippageCost +
    marketImpactCost;

  const totalCost =
    explicitCost +
    implicitCost;

  const totalCostPercent =
    grossValue <= 0
      ? 0
      : totalCost /
        grossValue *
        100;

  const netCashFlow =
    normalized.side === "BUY"
      ? -(
          grossValue +
          totalCost
        )
      : grossValue -
        totalCost;

  const breakEvenPrice =
    normalized.side === "BUY"
      ? (
          grossValue +
          totalCost
        ) /
        normalized.quantity
      : (
          grossValue -
          totalCost
        ) /
        normalized.quantity;

  const warnings = [];

  if (
    totalCostPercent >= 1
  ) {
    warnings.push(
      "HIGH_TRANSACTION_COST",
    );
  }

  if (
    spreadCost >
    commission
  ) {
    warnings.push(
      "SPREAD_DOMINATES_COMMISSION",
    );
  }

  if (
    marketImpactCost >
    commission
  ) {
    warnings.push(
      "MARKET_IMPACT_DOMINATES_COMMISSION",
    );
  }

  if (
    normalized.dailyVolume > 0 &&
    normalized.quantity /
      normalized.dailyVolume >
      0.1
  ) {
    warnings.push(
      "HIGH_PARTICIPATION_RATE",
    );
  }

  return {
    version:
      TRANSACTION_COST_ENGINE_V3_VERSION,

    evaluatedAt,

    symbol:
      normalized.symbol,

    side:
      normalized.side,

    market:
      normalized.market,

    quantity:
      normalized.quantity,

    price:
      round(
        normalized.price,
      ),

    grossValue:
      round(
        grossValue,
      ),

    explicitCost:
      round(
        explicitCost,
      ),

    implicitCost:
      round(
        implicitCost,
      ),

    totalCost:
      round(
        totalCost,
      ),

    totalCostPercent:
      round(
        totalCostPercent,
      ),

    level:
      classifyCostRate(
        totalCostPercent,
      ),

    netCashFlow:
      round(
        netCashFlow,
      ),

    breakEvenPrice:
      round(
        breakEvenPrice,
      ),

    components: {
      commission:
        round(
          commission,
        ),

      spreadCost:
        round(
          spreadCost,
        ),

      slippageCost:
        round(
          slippageCost,
        ),

      marketImpactCost:
        round(
          marketImpactCost,
        ),

      exchangeFee:
        round(
          exchangeFee,
        ),

      regulatoryFee:
        round(
          regulatoryFee,
        ),

      tax:
        round(
          tax,
        ),

      fxCost:
        round(
          fxCost,
        ),
    },

    warnings: [
      ...new Set(
        warnings,
      ),
    ],

    config: {
      commissionRate,

      minimumCommission,

      maximumCommission,

      fixedCommission,

      exchangeFeeRate,

      fixedExchangeFee,

      regulatoryFeeRate,

      taxRate,

      applyTaxToBuy,

      applyTaxToSell,

      fxFeeRate,

      impactCoefficient,

      includeSpread,

      includeSlippage,

      includeMarketImpact,
    },
  };
}

export function compareTransactionCosts({
  baseline,
  candidate,
} = {}) {
  if (
    !baseline ||
    !candidate
  ) {
    return {
      changed:
        false,

      cheaper:
        null,

      difference:
        0,

      differencePercent:
        0,
    };
  }

  const baselineCost =
    positiveNumber(
      baseline.totalCost,
      0,
    );

  const candidateCost =
    positiveNumber(
      candidate.totalCost,
      0,
    );

  const difference =
    candidateCost -
    baselineCost;

  return {
    changed:
      Math.abs(
        difference,
      ) >
      0.000001,

    cheaper:
      difference < 0
        ? "CANDIDATE"
        : difference > 0
          ? "BASELINE"
          : "EQUAL",

    difference:
      round(
        difference,
      ),

    differencePercent:
      baselineCost <= 0
        ? 0
        : round(
            difference /
            baselineCost *
            100,
          ),
  };
}

export class TransactionCostEngineV3 {
  constructor(config = {}) {
    this.config = {
      commissionRate:
        0.001,

      minimumCommission:
        0,

      maximumCommission:
        null,

      fixedCommission:
        0,

      exchangeFeeRate:
        0,

      fixedExchangeFee:
        0,

      regulatoryFeeRate:
        0,

      taxRate:
        0,

      applyTaxToBuy:
        false,

      applyTaxToSell:
        true,

      fxFeeRate:
        0,

      impactCoefficient:
        0.1,

      includeSpread:
        true,

      includeSlippage:
        true,

      includeMarketImpact:
        true,

      ...config,
    };

    this.history = [];
  }

  estimate(input = {}) {
    const result =
      estimateTransactionCost({
        ...input,

        config: {
          ...this.config,
          ...input.config,
        },
      });

    this.history.push(
      clone(
        result,
      ),
    );

    return clone(
      result,
    );
  }

  estimateRoundTrip({
    entry,
    exit,
    timestamp =
      new Date().toISOString(),
  } = {}) {
    const entryResult =
      this.estimate({
        trade:
          entry,

        timestamp,
      });

    const exitResult =
      this.estimate({
        trade:
          exit,

        timestamp,
      });

    return {
      entry:
        entryResult,

      exit:
        exitResult,

      totalCost:
        round(
          entryResult.totalCost +
          exitResult.totalCost,
        ),

      totalGrossValue:
        round(
          entryResult.grossValue +
          exitResult.grossValue,
        ),

      totalCostPercent:
        entryResult.grossValue +
          exitResult.grossValue <=
        0
          ? 0
          : round(
              (
                entryResult.totalCost +
                exitResult.totalCost
              ) /
              (
                entryResult.grossValue +
                exitResult.grossValue
              ) *
              100,
            ),
    };
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  latest() {
    return clone(
      this.history.at(-1) ??
      null,
    );
  }

  reset() {
    this.history = [];

    return [];
  }
}

export const transactionCostEngineV3 =
  new TransactionCostEngineV3();

export default TransactionCostEngineV3;