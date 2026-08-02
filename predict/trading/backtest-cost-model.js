export const BACKTEST_COST_MODEL_VERSION =
  "backtest-cost-model-v1";

export const COST_PRESETS = Object.freeze({
  rakuten_zero_cash: Object.freeze({
    id: "rakuten_zero_cash",
    label: "楽天証券・国内現物・手数料0円",
    commissionPercentPerSide: 0,
    minimumCommission: 0,
    spreadPercent: 0.02,
    slippagePercentPerSide: 0.01,
  }),

  zero_cost: Object.freeze({
    id: "zero_cost",
    label: "完全ゼロコスト",
    commissionPercentPerSide: 0,
    minimumCommission: 0,
    spreadPercent: 0,
    slippagePercentPerSide: 0,
  }),

  conservative: Object.freeze({
    id: "conservative",
    label: "保守的コスト",
    commissionPercentPerSide: 0.05,
    minimumCommission: 0,
    spreadPercent: 0.1,
    slippagePercentPerSide: 0.05,
  }),
});

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function nonNegative(value, fallback = 0) {
  if (!finite(value)) {
    return fallback;
  }

  return Math.max(0, Number(value));
}

export function resolveBacktestCostPolicy(policy = {}) {
  const presetId =
    String(
      policy.costPreset ||
        policy.costPresetId ||
        "rakuten_zero_cash",
    ).trim();

  const preset =
    COST_PRESETS[presetId] ||
    COST_PRESETS.rakuten_zero_cash;

  return {
    version: BACKTEST_COST_MODEL_VERSION,
    presetId: preset.id,
    presetLabel: preset.label,

    commissionPercentPerSide:
      nonNegative(
        policy.commissionPercentPerSide,
        preset.commissionPercentPerSide,
      ),

    minimumCommission:
      nonNegative(
        policy.minimumCommission,
        preset.minimumCommission,
      ),

    spreadPercent:
      nonNegative(
        policy.spreadPercent,
        preset.spreadPercent,
      ),

    slippagePercentPerSide:
      nonNegative(
        policy.slippagePercentPerSide,
        preset.slippagePercentPerSide,
      ),
  };
}

export function calculateCommission({
  notional,
  policy = {},
}) {
  const resolved =
    resolveBacktestCostPolicy(policy);

  const absoluteNotional =
    Math.abs(Number(notional) || 0);

  const variableCommission =
    absoluteNotional *
    (
      resolved.commissionPercentPerSide /
      100
    );

  return Math.max(
    resolved.minimumCommission,
    variableCommission,
  );
}

export function calculateSpreadCost({
  referencePrice,
  quantity,
  policy = {},
}) {
  const resolved =
    resolveBacktestCostPolicy(policy);

  const price =
    Math.max(0, Number(referencePrice) || 0);

  const resolvedQuantity =
    Math.max(0, Number(quantity) || 0);

  return (
    price *
    resolvedQuantity *
    (
      resolved.spreadPercent /
      200
    )
  );
}

export function calculateSlippageCost({
  referencePrice,
  quantity,
  policy = {},
}) {
  const resolved =
    resolveBacktestCostPolicy(policy);

  const price =
    Math.max(0, Number(referencePrice) || 0);

  const resolvedQuantity =
    Math.max(0, Number(quantity) || 0);

  return (
    price *
    resolvedQuantity *
    (
      resolved.slippagePercentPerSide /
      100
    )
  );
}

export function calculateFillPrice({
  referencePrice,
  side,
  phase,
  policy = {},
}) {
  const resolved =
    resolveBacktestCostPolicy(policy);

  const price = Number(referencePrice);

  if (!Number.isFinite(price) || price <= 0) {
    throw new TypeError(
      "referencePrice must be a positive number.",
    );
  }

  const halfSpreadRate =
    resolved.spreadPercent /
    200;

  const slippageRate =
    resolved.slippagePercentPerSide /
    100;

  const adverseRate =
    halfSpreadRate +
    slippageRate;

  const buying =
    (
      phase === "entry" &&
      side === "long"
    ) ||
    (
      phase === "exit" &&
      side === "short"
    );

  return buying
    ? price * (1 + adverseRate)
    : price * (1 - adverseRate);
}

export function calculateExecutionCostBreakdown({
  entryReferencePrice,
  entryFillPrice,
  exitReferencePrice,
  exitFillPrice,
  quantity,
  entryCommission = 0,
  exitCommission = 0,
}) {
  const resolvedQuantity =
    Math.max(0, Number(quantity) || 0);

  const entrySpreadAndSlippage =
    Math.abs(
      Number(entryFillPrice) -
      Number(entryReferencePrice),
    ) *
    resolvedQuantity;

  const exitSpreadAndSlippage =
    Math.abs(
      Number(exitFillPrice) -
      Number(exitReferencePrice),
    ) *
    resolvedQuantity;

  const commissionCost =
    Math.max(0, Number(entryCommission) || 0) +
    Math.max(0, Number(exitCommission) || 0);

  const executionCost =
    entrySpreadAndSlippage +
    exitSpreadAndSlippage;

  return {
    commissionCost,
    executionCost,
    totalTradingCost:
      commissionCost +
      executionCost,
  };
}

export function describeBacktestCostPolicy(
  policy = {},
) {
  const resolved =
    resolveBacktestCostPolicy(policy);

  return {
    ...resolved,

    estimatedRoundTripPercent:
      (
        resolved.commissionPercentPerSide *
        2
      ) +
      resolved.spreadPercent +
      (
        resolved.slippagePercentPerSide *
        2
      ),
  };
}
