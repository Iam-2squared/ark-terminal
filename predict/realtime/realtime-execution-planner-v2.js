export const REALTIME_EXECUTION_PLANNER_V2_VERSION =
  "realtime-execution-planner-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function clamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  const number =
    finiteOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      number,
    ),
  );
}

function round(
  value,
  digits = 4,
) {
  if (!Number.isFinite(value)) {
    return value;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value * factor,
    ) / factor
  );
}

function normalizeDirection(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "BULLISH",
      "UP",
      "1",
    ].includes(text)
  ) {
    return "BUY";
  }

  if (
    [
      "SELL",
      "SHORT",
      "BEARISH",
      "DOWN",
      "-1",
    ].includes(text)
  ) {
    return "SELL";
  }

  return "NEUTRAL";
}

function normalizeGate(
  gate = {},
) {
  return {
    version:
      gate.version ??
      null,

    ready:
      gate.ready === true,

    decision:
      String(
        gate.decision ??
        "BLOCK",
      )
        .trim()
        .toUpperCase(),

    tradable:
      gate.tradable === true,

    reason:
      String(
        gate.reason ??
        "UNKNOWN",
      ),

    symbol:
      String(
        gate.symbol ??
        gate.signal?.symbol ??
        "",
      ).trim(),

    direction:
      normalizeDirection(
        gate.direction ??
        gate.signal?.direction,
      ),

    gateScore:
      clamp(
        gate.gateScore,
      ) ?? 0,

    positionMultiplier:
      clamp(
        gate.positionMultiplier,
      ) ?? 0,

    blockers:
      Array.isArray(
        gate.blockers,
      )
        ? [
            ...gate.blockers,
          ]
        : [],

    executionAllowed:
      gate.executionPlan
        ?.allowed === true,

    requireHumanConfirmation:
      gate.executionPlan
        ?.requireHumanConfirmation !==
      false,
  };
}

function normalizeMarket(
  market = {},
) {
  const bid =
    finiteOrNull(
      market.bid,
    );

  const ask =
    finiteOrNull(
      market.ask,
    );

  const lastPrice =
    finiteOrNull(
      market.lastPrice ??
      market.price ??
      market.close,
    );

  const midpoint =
    bid !== null &&
    ask !== null &&
    bid > 0 &&
    ask > 0
      ? (
          bid +
          ask
        ) /
        2
      : lastPrice;

  const spreadPercent =
    bid !== null &&
    ask !== null &&
    midpoint !== null &&
    midpoint > 0
      ? (
          (
            ask -
            bid
          ) /
          midpoint
        ) *
        100
      : null;

  return {
    bid,
    ask,
    lastPrice,
    midpoint,

    spreadPercent:
      spreadPercent === null
        ? null
        : round(
            spreadPercent,
          ),

    averageVolume:
      Math.max(
        0,
        finiteOrNull(
          market.averageVolume,
        ) ?? 0,
      ),

    currentVolume:
      Math.max(
        0,
        finiteOrNull(
          market.currentVolume ??
          market.volume,
        ) ?? 0,
      ),

    lotSize:
      Math.max(
        1,
        Math.floor(
          finiteOrNull(
            market.lotSize,
          ) ?? 100,
        ),
      ),

    tickSize:
      Math.max(
        0.0001,
        finiteOrNull(
          market.tickSize,
        ) ?? 1,
      ),

    halted:
      market.halted === true,

    session:
      String(
        market.session ??
        "REGULAR",
      )
        .trim()
        .toUpperCase(),
  };
}

function normalizePortfolio(
  portfolio = {},
) {
  return {
    availableCash:
      Math.max(
        0,
        finiteOrNull(
          portfolio.availableCash ??
          portfolio.cash,
        ) ?? 0,
      ),

    totalEquity:
      Math.max(
        0,
        finiteOrNull(
          portfolio.totalEquity ??
          portfolio.equity,
        ) ?? 0,
      ),

    currentPosition:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            portfolio.currentPosition ??
            portfolio.quantity,
          ) ?? 0,
        ),
      ),

    maximumPositionValue:
      Math.max(
        0,
        finiteOrNull(
          portfolio.maximumPositionValue,
        ) ?? Infinity,
      ),

    maximumOrderValue:
      Math.max(
        0,
        finiteOrNull(
          portfolio.maximumOrderValue,
        ) ?? Infinity,
      ),
  };
}

function normalizeRisk(
  risk = {},
) {
  return {
    atr:
      Math.max(
        0,
        finiteOrNull(
          risk.atr,
        ) ?? 0,
      ),

    stopLossPercent:
      Math.max(
        0.1,
        finiteOrNull(
          risk.stopLossPercent,
        ) ?? 3,
      ),

    takeProfitPercent:
      Math.max(
        0.1,
        finiteOrNull(
          risk.takeProfitPercent,
        ) ?? 6,
      ),

    maximumRiskPerTradePercent:
      Math.max(
        0.1,
        finiteOrNull(
          risk.maximumRiskPerTradePercent,
        ) ?? 1,
      ),

    maximumSpreadPercent:
      Math.max(
        0.01,
        finiteOrNull(
          risk.maximumSpreadPercent,
        ) ?? 1.5,
      ),

    maximumVolumeParticipationPercent:
      Math.max(
        0.1,
        finiteOrNull(
          risk.maximumVolumeParticipationPercent,
        ) ?? 5,
      ),
  };
}

function floorToLot(
  quantity,
  lotSize,
) {
  if (
    !Number.isFinite(quantity) ||
    quantity <= 0
  ) {
    return 0;
  }

  return (
    Math.floor(
      quantity /
      lotSize,
    ) *
    lotSize
  );
}

function roundToTick(
  price,
  tickSize,
) {
  if (
    !Number.isFinite(price)
  ) {
    return null;
  }

  return round(
    Math.round(
      price /
      tickSize,
    ) *
    tickSize,
    8,
  );
}

function determineReferencePrice({
  direction,
  market,
}) {
  if (direction === "BUY") {
    return (
      market.ask ??
      market.lastPrice ??
      market.midpoint
    );
  }

  if (direction === "SELL") {
    return (
      market.bid ??
      market.lastPrice ??
      market.midpoint
    );
  }

  return null;
}

function calculateStopDistance({
  referencePrice,
  risk,
}) {
  const percentDistance =
    referencePrice *
    (
      risk.stopLossPercent /
      100
    );

  const atrDistance =
    risk.atr > 0
      ? risk.atr * 1.5
      : 0;

  return Math.max(
    percentDistance,
    atrDistance,
  );
}

function calculateRiskBasedQuantity({
  direction,
  referencePrice,
  stopDistance,
  portfolio,
  market,
  risk,
  positionMultiplier,
}) {
  if (
    referencePrice <= 0 ||
    stopDistance <= 0
  ) {
    return 0;
  }

  const equityBase =
    portfolio.totalEquity > 0
      ? portfolio.totalEquity
      : portfolio.availableCash;

  const maximumRiskAmount =
    equityBase *
    (
      risk.maximumRiskPerTradePercent /
      100
    ) *
    (
      positionMultiplier /
      100
    );

  const quantityByRisk =
    maximumRiskAmount /
    stopDistance;

  const quantityByCash =
    direction === "BUY"
      ? portfolio.availableCash /
        referencePrice
      : portfolio.currentPosition;

  const quantityByOrderValue =
    Number.isFinite(
      portfolio.maximumOrderValue,
    )
      ? portfolio.maximumOrderValue /
        referencePrice
      : Infinity;

  const quantityByPositionValue =
    Number.isFinite(
      portfolio.maximumPositionValue,
    )
      ? Math.max(
          0,
          (
            portfolio.maximumPositionValue -
            portfolio.currentPosition *
            referencePrice
          ) /
          referencePrice,
        )
      : Infinity;

  const quantityByLiquidity =
    market.averageVolume > 0
      ? market.averageVolume *
        (
          risk.maximumVolumeParticipationPercent /
          100
        )
      : Infinity;

  const rawQuantity =
    Math.min(
      quantityByRisk,
      quantityByCash,
      quantityByOrderValue,
      quantityByPositionValue,
      quantityByLiquidity,
    );

  return floorToLot(
    rawQuantity,
    market.lotSize,
  );
}

function buildPriceTargets({
  direction,
  referencePrice,
  stopDistance,
  risk,
  market,
}) {
  const profitDistance =
    Math.max(
      referencePrice *
      (
        risk.takeProfitPercent /
        100
      ),
      stopDistance * 1.5,
    );

  if (direction === "BUY") {
    return {
      entryPrice:
        roundToTick(
          referencePrice,
          market.tickSize,
        ),

      stopLossPrice:
        roundToTick(
          referencePrice -
          stopDistance,
          market.tickSize,
        ),

      takeProfitPrice:
        roundToTick(
          referencePrice +
          profitDistance,
          market.tickSize,
        ),
    };
  }

  return {
    entryPrice:
      roundToTick(
        referencePrice,
        market.tickSize,
      ),

    stopLossPrice:
      roundToTick(
        referencePrice +
        stopDistance,
        market.tickSize,
      ),

    takeProfitPrice:
      roundToTick(
        referencePrice -
        profitDistance,
        market.tickSize,
      ),
  };
}

function createBlocker(
  code,
  reason,
) {
  return {
    code,
    reason,
  };
}

function evaluateExecutionBlockers({
  gate,
  market,
  portfolio,
  risk,
  referencePrice,
  quantity,
}) {
  const blockers = [];

  if (!gate.ready) {
    blockers.push(
      createBlocker(
        "GATE_NOT_READY",
        "Realtime decision gate is not ready.",
      ),
    );
  }

  if (
    gate.decision !== "ALLOW" ||
    !gate.tradable ||
    !gate.executionAllowed
  ) {
    blockers.push(
      createBlocker(
        "GATE_BLOCKED_EXECUTION",
        gate.reason,
      ),
    );
  }

  if (!gate.symbol) {
    blockers.push(
      createBlocker(
        "SYMBOL_MISSING",
        "Execution symbol is missing.",
      ),
    );
  }

  if (
    gate.direction ===
    "NEUTRAL"
  ) {
    blockers.push(
      createBlocker(
        "DIRECTION_MISSING",
        "Execution direction is neutral.",
      ),
    );
  }

  if (market.halted) {
    blockers.push(
      createBlocker(
        "MARKET_HALTED",
        "Market is currently halted.",
      ),
    );
  }

  if (
    ![
      "REGULAR",
      "OPEN",
      "CONTINUOUS",
    ].includes(
      market.session,
    )
  ) {
    blockers.push(
      createBlocker(
        "MARKET_SESSION_CLOSED",
        `Unsupported market session: ${market.session}`,
      ),
    );
  }

  if (
    referencePrice === null ||
    referencePrice <= 0
  ) {
    blockers.push(
      createBlocker(
        "INVALID_REFERENCE_PRICE",
        "A valid reference price is required.",
      ),
    );
  }

  if (
    market.spreadPercent !== null &&
    market.spreadPercent >
      risk.maximumSpreadPercent
  ) {
    blockers.push(
      createBlocker(
        "SPREAD_LIMIT_EXCEEDED",
        "Bid-ask spread exceeds the configured limit.",
      ),
    );
  }

  if (
    gate.direction === "BUY" &&
    portfolio.availableCash <= 0
  ) {
    blockers.push(
      createBlocker(
        "INSUFFICIENT_CASH",
        "No available cash for a buy order.",
      ),
    );
  }

  if (
    gate.direction === "SELL" &&
    portfolio.currentPosition <= 0
  ) {
    blockers.push(
      createBlocker(
        "NO_POSITION_TO_SELL",
        "No existing position is available to sell.",
      ),
    );
  }

  if (quantity <= 0) {
    blockers.push(
      createBlocker(
        "ORDER_QUANTITY_ZERO",
        "Risk and liquidity constraints reduced order quantity to zero.",
      ),
    );
  }

  return blockers;
}

export function createRealtimeExecutionPlan({
  gate = {},
  market = {},
  portfolio = {},
  risk = {},
  orderType = "LIMIT",
  timeInForce = "DAY",
  requireHumanConfirmation = true,
} = {}) {
  const normalizedGate =
    normalizeGate(
      gate,
    );

  const normalizedMarket =
    normalizeMarket(
      market,
    );

  const normalizedPortfolio =
    normalizePortfolio(
      portfolio,
    );

  const normalizedRisk =
    normalizeRisk(
      risk,
    );

  const referencePrice =
    determineReferencePrice({
      direction:
        normalizedGate.direction,

      market:
        normalizedMarket,
    });

  const stopDistance =
    referencePrice !== null
      ? calculateStopDistance({
          referencePrice,

          risk:
            normalizedRisk,
        })
      : 0;

  const quantity =
    referencePrice !== null
      ? calculateRiskBasedQuantity({
          direction:
            normalizedGate.direction,

          referencePrice,

          stopDistance,

          portfolio:
            normalizedPortfolio,

          market:
            normalizedMarket,

          risk:
            normalizedRisk,

          positionMultiplier:
            normalizedGate
              .positionMultiplier,
        })
      : 0;

  const blockers =
    evaluateExecutionBlockers({
      gate:
        normalizedGate,

      market:
        normalizedMarket,

      portfolio:
        normalizedPortfolio,

      risk:
        normalizedRisk,

      referencePrice,

      quantity,
    });

  const allowed =
    blockers.length === 0;

  const prices =
    allowed
      ? buildPriceTargets({
          direction:
            normalizedGate.direction,

          referencePrice,

          stopDistance,

          risk:
            normalizedRisk,

          market:
            normalizedMarket,
        })
      : {
          entryPrice:
            null,

          stopLossPrice:
            null,

          takeProfitPrice:
            null,
        };

  const orderValue =
    allowed
      ? quantity *
        prices.entryPrice
      : 0;

  const maximumLoss =
    allowed
      ? quantity *
        Math.abs(
          prices.entryPrice -
          prices.stopLossPrice,
        )
      : 0;

  const expectedProfit =
    allowed
      ? quantity *
        Math.abs(
          prices.takeProfitPrice -
          prices.entryPrice,
        )
      : 0;

  const rewardRiskRatio =
    maximumLoss > 0
      ? expectedProfit /
        maximumLoss
      : null;

  const confirmationRequired =
    allowed &&
    (
      requireHumanConfirmation === true ||
      normalizedGate
        .requireHumanConfirmation
    );

  return {
    version:
      REALTIME_EXECUTION_PLANNER_V2_VERSION,

    ready:
      normalizedGate.ready &&
      referencePrice !== null,

    allowed,

    status:
      allowed
        ? confirmationRequired
          ? "AWAITING_HUMAN_CONFIRMATION"
          : "READY"
        : "BLOCKED",

    symbol:
      normalizedGate.symbol,

    direction:
      normalizedGate.direction,

    order: {
      type:
        String(
          orderType,
        )
          .trim()
          .toUpperCase(),

      timeInForce:
        String(
          timeInForce,
        )
          .trim()
          .toUpperCase(),

      quantity:
        allowed
          ? quantity
          : 0,

      lotSize:
        normalizedMarket.lotSize,

      entryPrice:
        prices.entryPrice,

      estimatedValue:
        round(
          orderValue,
          2,
        ),
    },

    protection: {
      stopLossPrice:
        prices.stopLossPrice,

      takeProfitPrice:
        prices.takeProfitPrice,

      stopDistance:
        round(
          stopDistance,
          4,
        ),

      estimatedMaximumLoss:
        round(
          maximumLoss,
          2,
        ),

      estimatedProfit:
        round(
          expectedProfit,
          2,
        ),

      rewardRiskRatio:
        rewardRiskRatio === null
          ? null
          : round(
              rewardRiskRatio,
              2,
            ),
    },

    humanConfirmation: {
      required:
        confirmationRequired,

      confirmed:
        false,

      executable:
        allowed &&
        !confirmationRequired,
    },

    blockers,

    gate:
      normalizedGate,

    market:
      normalizedMarket,

    portfolio:
      normalizedPortfolio,

    risk:
      normalizedRisk,

    audit: {
      createdAt:
        new Date().toISOString(),

      source:
        "REALTIME_DECISION_GATE_V2",

      gateScore:
        normalizedGate.gateScore,

      positionMultiplier:
        normalizedGate
          .positionMultiplier,

      blockerCount:
        blockers.length,

      automaticExecution:
        false,
    },
  };
}

export function confirmRealtimeExecutionPlan({
  plan,
  confirmedBy,
  confirmationNote = null,
} = {}) {
  if (
    !plan ||
    typeof plan !== "object"
  ) {
    throw new TypeError(
      "Realtime execution plan is required.",
    );
  }

  if (!plan.allowed) {
    return {
      ...plan,

      confirmation: {
        accepted:
          false,

        reason:
          "BLOCKED_PLAN_CANNOT_BE_CONFIRMED",
      },
    };
  }

  const approver =
    String(
      confirmedBy ??
      "",
    ).trim();

  if (!approver) {
    throw new TypeError(
      "Execution confirmation requires confirmedBy.",
    );
  }

  return {
    ...plan,

    status:
      "CONFIRMED",

    humanConfirmation: {
      required:
        true,

      confirmed:
        true,

      executable:
        true,
    },

    confirmation: {
      accepted:
        true,

      confirmedBy:
        approver,

      confirmedAt:
        new Date().toISOString(),

      note:
        confirmationNote,
    },

    audit: {
      ...plan.audit,

      automaticExecution:
        false,

      humanConfirmed:
        true,

      confirmedBy:
        approver,
    },
  };
}

export class RealtimeExecutionPlannerV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  create(input = {}) {
    return createRealtimeExecutionPlan({
      ...this.config,

      ...input,
    });
  }

  confirm(input = {}) {
    return confirmRealtimeExecutionPlan(
      input,
    );
  }
}

export const realtimeExecutionPlannerV2 =
  new RealtimeExecutionPlannerV2();

export default createRealtimeExecutionPlan;