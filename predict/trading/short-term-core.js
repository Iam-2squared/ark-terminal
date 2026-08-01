export const SHORT_TERM_MODEL_VERSION =
  "short-term-trading-core-v1";

export const POSITION_SIDES = Object.freeze({
  FLAT: "flat",
  LONG: "long",
  SHORT: "short",
});

export const TRADE_ACTIONS = Object.freeze({
  WAIT: "wait",
  BLOCKED: "blocked",
  ENTER_LONG: "enter_long",
  ENTER_SHORT: "enter_short",
  HOLD: "hold",
  TAKE_PARTIAL: "take_partial",
  EXIT: "exit",
});

export const DEFAULT_SHORT_TERM_POLICY = Object.freeze({
  paperTradingOnly: true,
  allowLong: true,
  allowShort: true,

  riskPerTradePercent: 0.5,
  maximumPositionPercent: 20,
  maximumOpenPositions: 3,

  maximumDailyLossPercent: 2,
  maximumConsecutiveLosses: 3,

  minimumConfidenceScore: 65,
  minimumDataQualityScore: 85,
  minimumRiskReward: 1.5,

  maximumSpreadPercent: 0.5,
  maximumDataAgeSeconds: 120,

  stopAtrMultiple: 1.2,
  firstTargetAtrMultiple: 1.5,
  secondTargetAtrMultiple: 2.5,

  maximumHoldingBars: 16,
  intrabarPriority: "risk_first",
});

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function positive(value) {
  return finite(value) && Number(value) > 0;
}

function normalizePolicy(policy = {}) {
  return {
    ...DEFAULT_SHORT_TERM_POLICY,
    ...(policy || {}),
  };
}

export function directionToSide(direction) {
  const value = String(direction || "")
    .trim()
    .toLowerCase();

  if (
    [
      "強気",
      "bullish",
      "strong_bullish",
      "up",
      "long",
    ].includes(value)
  ) {
    return POSITION_SIDES.LONG;
  }

  if (
    [
      "弱気",
      "bearish",
      "strong_bearish",
      "down",
      "short",
    ].includes(value)
  ) {
    return POSITION_SIDES.SHORT;
  }

  return POSITION_SIDES.FLAT;
}

export function calculatePositionSize({
  equity,
  entryPrice,
  stopPrice,
  lotSize = 1,
  policy = {},
}) {
  const resolvedPolicy = normalizePolicy(policy);
  const resolvedLotSize = Math.max(
    1,
    Math.floor(Number(lotSize) || 1),
  );

  if (
    !positive(equity) ||
    !positive(entryPrice) ||
    !positive(stopPrice)
  ) {
    return {
      ready: false,
      quantity: 0,
      reason: "資金・エントリー・損切り価格が不正です。",
    };
  }

  const riskPerUnit = Math.abs(
    Number(entryPrice) - Number(stopPrice),
  );

  if (!positive(riskPerUnit)) {
    return {
      ready: false,
      quantity: 0,
      reason: "1株あたりの損失幅を計算できません。",
    };
  }

  const riskBudget =
    Number(equity) *
    (Number(resolvedPolicy.riskPerTradePercent) / 100);

  const maximumPositionValue =
    Number(equity) *
    (Number(resolvedPolicy.maximumPositionPercent) / 100);

  const quantityByRisk = Math.floor(
    riskBudget / riskPerUnit,
  );

  const quantityByValue = Math.floor(
    maximumPositionValue / Number(entryPrice),
  );

  const rawQuantity = Math.min(
    quantityByRisk,
    quantityByValue,
  );

  const quantity =
    Math.floor(rawQuantity / resolvedLotSize) *
    resolvedLotSize;

  if (quantity < resolvedLotSize) {
    return {
      ready: false,
      quantity: 0,
      reason:
        "許容損失または最大投資額の範囲で注文数量を確保できません。",
      riskBudget,
      maximumPositionValue,
      riskPerUnit,
      lotSize: resolvedLotSize,
    };
  }

  return {
    ready: true,
    quantity,
    lotSize: resolvedLotSize,
    riskBudget,
    maximumPositionValue,
    riskPerUnit,
    estimatedMaximumLoss:
      quantity * riskPerUnit,
    positionValue:
      quantity * Number(entryPrice),
  };
}

export function evaluateEntryGate({
  signal = {},
  account = {},
  policy = {},
}) {
  const resolvedPolicy = normalizePolicy(policy);
  const side = directionToSide(signal.direction);
  const reasons = [];

  if (side === POSITION_SIDES.FLAT) {
    return {
      allowed: false,
      wait: true,
      side,
      reasons: ["方向が中立のため待機します。"],
      policy: resolvedPolicy,
    };
  }

  if (
    resolvedPolicy.paperTradingOnly &&
    account.executionMode !== "paper"
  ) {
    reasons.push("v1はPaper Trading専用です。");
  }

  if (
    side === POSITION_SIDES.LONG &&
    !resolvedPolicy.allowLong
  ) {
    reasons.push("買い方向が無効です。");
  }

  if (
    side === POSITION_SIDES.SHORT &&
    !resolvedPolicy.allowShort
  ) {
    reasons.push("空売り方向が無効です。");
  }

  if (!positive(signal.currentPrice)) {
    reasons.push("現在価格を確認できません。");
  }

  if (!positive(signal.atr)) {
    reasons.push("ATRを確認できません。");
  }

  if (!finite(signal.confidenceScore)) {
    reasons.push("信頼度を確認できません。");
  } else if (
    Number(signal.confidenceScore) <
    Number(resolvedPolicy.minimumConfidenceScore)
  ) {
    reasons.push(
      `信頼度が${resolvedPolicy.minimumConfidenceScore}未満です。`,
    );
  }

  if (!finite(signal.dataQualityScore)) {
    reasons.push("データ品質を確認できません。");
  } else if (
    Number(signal.dataQualityScore) <
    Number(resolvedPolicy.minimumDataQualityScore)
  ) {
    reasons.push(
      `データ品質が${resolvedPolicy.minimumDataQualityScore}未満です。`,
    );
  }

  if (!finite(signal.spreadPercent)) {
    reasons.push("スプレッドを確認できません。");
  } else if (
    Number(signal.spreadPercent) >
    Number(resolvedPolicy.maximumSpreadPercent)
  ) {
    reasons.push(
      `スプレッドが${resolvedPolicy.maximumSpreadPercent}%を超えています。`,
    );
  }

  if (!finite(signal.dataAgeSeconds)) {
    reasons.push("データ更新時刻を確認できません。");
  } else if (
    Number(signal.dataAgeSeconds) >
    Number(resolvedPolicy.maximumDataAgeSeconds)
  ) {
    reasons.push("市場データが古いため取引を停止します。");
  }

  if (signal.marketBlocked === true) {
    reasons.push(
      signal.marketBlockReason ||
        "市場環境ゲートが取引を拒否しました。",
    );
  }

  if (!positive(account.equity)) {
    reasons.push("仮想口座資産を確認できません。");
  }

  if (
    Number(account.openPositions || 0) >=
    Number(resolvedPolicy.maximumOpenPositions)
  ) {
    reasons.push("最大同時保有数に達しています。");
  }

  if (
    finite(account.dailyPnlPercent) &&
    Number(account.dailyPnlPercent) <=
      -Math.abs(
        Number(resolvedPolicy.maximumDailyLossPercent),
      )
  ) {
    reasons.push("1日の最大損失に達しています。");
  }

  if (
    Number(account.consecutiveLosses || 0) >=
    Number(resolvedPolicy.maximumConsecutiveLosses)
  ) {
    reasons.push("連敗上限に達しています。");
  }

  return {
    allowed: reasons.length === 0,
    wait: false,
    side,
    reasons,
    policy: resolvedPolicy,
  };
}

function tradePrices({
  side,
  currentPrice,
  atr,
  policy,
}) {
  const price = Number(currentPrice);
  const volatility = Number(atr);

  if (side === POSITION_SIDES.LONG) {
    return {
      entryPrice: price,
      stopPrice:
        price -
        volatility * Number(policy.stopAtrMultiple),
      firstTargetPrice:
        price +
        volatility *
          Number(policy.firstTargetAtrMultiple),
      secondTargetPrice:
        price +
        volatility *
          Number(policy.secondTargetAtrMultiple),
    };
  }

  return {
    entryPrice: price,
    stopPrice:
      price +
      volatility * Number(policy.stopAtrMultiple),
    firstTargetPrice:
      price -
      volatility *
        Number(policy.firstTargetAtrMultiple),
    secondTargetPrice:
      price -
      volatility *
        Number(policy.secondTargetAtrMultiple),
  };
}

export function createShortTermTradePlan({
  signal = {},
  account = {},
  policy = {},
  lotSize = 1,
}) {
  const gate = evaluateEntryGate({
    signal,
    account,
    policy,
  });

  if (gate.wait) {
    return {
      version: SHORT_TERM_MODEL_VERSION,
      executable: false,
      executionMode: "paper",
      action: TRADE_ACTIONS.WAIT,
      side: POSITION_SIDES.FLAT,
      reasons: gate.reasons,
    };
  }

  if (!gate.allowed) {
    return {
      version: SHORT_TERM_MODEL_VERSION,
      executable: false,
      executionMode: "paper",
      action: TRADE_ACTIONS.BLOCKED,
      side: gate.side,
      reasons: gate.reasons,
    };
  }

  const prices = tradePrices({
    side: gate.side,
    currentPrice: signal.currentPrice,
    atr: signal.atr,
    policy: gate.policy,
  });

  const sizing = calculatePositionSize({
    equity: account.equity,
    entryPrice: prices.entryPrice,
    stopPrice: prices.stopPrice,
    lotSize,
    policy: gate.policy,
  });

  if (!sizing.ready) {
    return {
      version: SHORT_TERM_MODEL_VERSION,
      executable: false,
      executionMode: "paper",
      action: TRADE_ACTIONS.BLOCKED,
      side: gate.side,
      reasons: [sizing.reason],
      sizing,
    };
  }

  const risk = Math.abs(
    prices.entryPrice - prices.stopPrice,
  );

  const reward = Math.abs(
    prices.secondTargetPrice - prices.entryPrice,
  );

  const riskReward = reward / risk;

  if (
    !finite(riskReward) ||
    riskReward <
      Number(gate.policy.minimumRiskReward)
  ) {
    return {
      version: SHORT_TERM_MODEL_VERSION,
      executable: false,
      executionMode: "paper",
      action: TRADE_ACTIONS.BLOCKED,
      side: gate.side,
      reasons: [
        `リスクリワードが${gate.policy.minimumRiskReward}未満です。`,
      ],
      riskReward,
      sizing,
    };
  }

  return {
    version: SHORT_TERM_MODEL_VERSION,
    executable: true,
    executionMode: "paper",
    liveExecutionAllowed: false,

    action:
      gate.side === POSITION_SIDES.LONG
        ? TRADE_ACTIONS.ENTER_LONG
        : TRADE_ACTIONS.ENTER_SHORT,

    side: gate.side,
    setup: signal.setup || "未分類",
    entryCondition:
      signal.entryCondition ||
      "短期シグナルの確定待ち",

    ...prices,
    quantity: sizing.quantity,
    sizing,
    riskReward,

    firstExitFraction: 0.5,
    maximumHoldingBars:
      gate.policy.maximumHoldingBars,

    exitRules: {
      stopLoss: prices.stopPrice,
      firstTarget: prices.firstTargetPrice,
      secondTarget: prices.secondTargetPrice,
      timeExitBars:
        gate.policy.maximumHoldingBars,
      intrabarPriority:
        gate.policy.intrabarPriority,
    },

    reasons: [],
  };
}

function positionReturnPercent(
  side,
  entryPrice,
  exitPrice,
) {
  if (
    !positive(entryPrice) ||
    !positive(exitPrice)
  ) {
    return null;
  }

  const raw =
    ((Number(exitPrice) - Number(entryPrice)) /
      Number(entryPrice)) *
    100;

  return side === POSITION_SIDES.SHORT
    ? -raw
    : raw;
}

export function evaluateOpenPosition({
  position = {},
  candle = {},
  barsHeld = 0,
  policy = {},
}) {
  const resolvedPolicy = normalizePolicy(policy);
  const side = position.side;

  if (
    ![
      POSITION_SIDES.LONG,
      POSITION_SIDES.SHORT,
    ].includes(side)
  ) {
    return {
      action: TRADE_ACTIONS.BLOCKED,
      reason: "保有方向が不正です。",
    };
  }

  const required = [
    position.entryPrice,
    position.stopPrice,
    position.firstTargetPrice,
    position.secondTargetPrice,
    candle.high,
    candle.low,
    candle.close,
  ];

  if (!required.every(positive)) {
    return {
      action: TRADE_ACTIONS.BLOCKED,
      reason: "保有評価に必要な価格が不足しています。",
    };
  }

  const stopHit =
    side === POSITION_SIDES.LONG
      ? Number(candle.low) <=
        Number(position.stopPrice)
      : Number(candle.high) >=
        Number(position.stopPrice);

  const secondTargetHit =
    side === POSITION_SIDES.LONG
      ? Number(candle.high) >=
        Number(position.secondTargetPrice)
      : Number(candle.low) <=
        Number(position.secondTargetPrice);

  const firstTargetHit =
    side === POSITION_SIDES.LONG
      ? Number(candle.high) >=
        Number(position.firstTargetPrice)
      : Number(candle.low) <=
        Number(position.firstTargetPrice);

  if (stopHit) {
    return {
      action: TRADE_ACTIONS.EXIT,
      exitPrice: Number(position.stopPrice),
      reason: "損切り",
      returnPercent: positionReturnPercent(
        side,
        position.entryPrice,
        position.stopPrice,
      ),
      intrabarPriority:
        resolvedPolicy.intrabarPriority,
    };
  }

  if (secondTargetHit) {
    return {
      action: TRADE_ACTIONS.EXIT,
      exitPrice:
        Number(position.secondTargetPrice),
      reason: "第2利確",
      returnPercent: positionReturnPercent(
        side,
        position.entryPrice,
        position.secondTargetPrice,
      ),
    };
  }

  if (
    firstTargetHit &&
    position.firstTargetTaken !== true
  ) {
    return {
      action: TRADE_ACTIONS.TAKE_PARTIAL,
      exitPrice:
        Number(position.firstTargetPrice),
      exitFraction:
        Number(position.firstExitFraction || 0.5),
      reason: "第1利確",
      returnPercent: positionReturnPercent(
        side,
        position.entryPrice,
        position.firstTargetPrice,
      ),
    };
  }

  if (
    Number(barsHeld) >=
    Number(resolvedPolicy.maximumHoldingBars)
  ) {
    return {
      action: TRADE_ACTIONS.EXIT,
      exitPrice: Number(candle.close),
      reason: "時間切れ",
      returnPercent: positionReturnPercent(
        side,
        position.entryPrice,
        candle.close,
      ),
    };
  }

  return {
    action: TRADE_ACTIONS.HOLD,
    reason: "保有継続",
  };
}

export function createPaperOrder(
  plan,
  {
    orderId =
      `paper-${Date.now().toString(36)}`,
  } = {},
) {
  if (!plan?.executable) {
    throw new Error(
      "実行可能な取引計画ではありません。",
    );
  }

  if (
    plan.executionMode !== "paper" ||
    plan.liveExecutionAllowed !== false
  ) {
    throw new Error(
      "v1では実注文を作成できません。",
    );
  }

  return {
    orderId,
    version: SHORT_TERM_MODEL_VERSION,
    environment: "paper",
    liveExecutionAllowed: false,
    status: "pending_trigger",

    action: plan.action,
    side:
      plan.side === POSITION_SIDES.LONG
        ? "buy"
        : "sell_short",

    quantity: plan.quantity,
    entryPrice: plan.entryPrice,
    stopPrice: plan.stopPrice,
    firstTargetPrice:
      plan.firstTargetPrice,
    secondTargetPrice:
      plan.secondTargetPrice,

    setup: plan.setup,
    entryCondition: plan.entryCondition,
    maximumHoldingBars:
      plan.maximumHoldingBars,

    createdAt: new Date().toISOString(),
  };
}

export const ShortTermTradingInternals = {
  finite,
  positive,
  normalizePolicy,
  tradePrices,
  positionReturnPercent,
};