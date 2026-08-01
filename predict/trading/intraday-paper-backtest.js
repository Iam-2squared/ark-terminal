import {
  normalizeIntradayCandles,
} from "./intraday-market.js";

import {
  createIntradayTradingDecision,
} from "./intraday-trading-decision.js";

import {
  createShortTermTradePlan,
  evaluateOpenPosition,
  POSITION_SIDES,
  TRADE_ACTIONS,
} from "./short-term-core.js";

export const INTRADAY_PAPER_BACKTEST_VERSION =
  "intraday-paper-backtest-v1";

export const DEFAULT_INTRADAY_BACKTEST_POLICY =
  Object.freeze({
    initialEquity: 1_000_000,
    minimumWarmupBars: 20,
    lotSize: 100,
    maximumTrades: 1_000,

    closeAtSessionEnd: true,
    allowOvernightEntry: false,

    commissionPercentPerSide: 0.05,
    spreadPercent: 0.1,
    slippagePercentPerSide: 0.05,
    minimumCommission: 0,
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

function clamp(value, minimum, maximum) {
  return Math.min(
    maximum,
    Math.max(minimum, Number(value)),
  );
}

function percentChange(value, base) {
  if (!finite(value) || !positive(base)) {
    return null;
  }

  return (
    ((Number(value) - Number(base)) /
      Number(base)) *
    100
  );
}

function resolvePolicy(policy = {}) {
  return {
    ...DEFAULT_INTRADAY_BACKTEST_POLICY,
    ...(policy || {}),
  };
}

function commissionFor(
  notional,
  policy,
) {
  const variable =
    Math.abs(Number(notional)) *
    (Number(
      policy.commissionPercentPerSide,
    ) /
      100);

  return Math.max(
    Number(policy.minimumCommission) || 0,
    variable,
  );
}

function adverseFillPrice({
  referencePrice,
  side,
  phase,
  policy,
}) {
  const price = Number(referencePrice);

  const halfSpread =
    Number(policy.spreadPercent) /
    200;

  const slippage =
    Number(
      policy.slippagePercentPerSide,
    ) / 100;

  const adverseRate =
    halfSpread + slippage;

  const buying =
    (phase === "entry" &&
      side === POSITION_SIDES.LONG) ||
    (phase === "exit" &&
      side === POSITION_SIDES.SHORT);

  return buying
    ? price * (1 + adverseRate)
    : price * (1 - adverseRate);
}

function grossPnl({
  side,
  entryPrice,
  exitPrice,
  quantity,
}) {
  const raw =
    (Number(exitPrice) -
      Number(entryPrice)) *
    Number(quantity);

  return side === POSITION_SIDES.SHORT
    ? -raw
    : raw;
}

function sideFromDecision(decision) {
  if (
    decision?.plan?.side ===
      POSITION_SIDES.LONG ||
    decision?.action ===
      TRADE_ACTIONS.ENTER_LONG
  ) {
    return POSITION_SIDES.LONG;
  }

  if (
    decision?.plan?.side ===
      POSITION_SIDES.SHORT ||
    decision?.action ===
      TRADE_ACTIONS.ENTER_SHORT
  ) {
    return POSITION_SIDES.SHORT;
  }

  return POSITION_SIDES.FLAT;
}

function directionFromSide(side) {
  if (side === POSITION_SIDES.LONG) {
    return "強気";
  }

  if (side === POSITION_SIDES.SHORT) {
    return "弱気";
  }

  return "中立";
}

function incrementCounter(
  target,
  key,
) {
  const resolvedKey =
    String(key || "unknown");

  target[resolvedKey] =
    Number(
      target[resolvedKey] || 0,
    ) + 1;
}

function createDecisionDiagnostics() {
  return {
    setupCounts: {},
    reasonCounts: {},

    featurePassCounts: {
      aboveVwap: 0,
      belowVwap: 0,
      volumeSurge: 0,

      breakoutLong: 0,
      breakoutShort: 0,

      reclaimLong: 0,
      reclaimShort: 0,

      pullbackLong: 0,
      pullbackShort: 0,
    },

    analysisReadyCount: 0,
    marketBlockedCount: 0,
    insufficientDataCount: 0,
    waitSetupCount: 0,

    candidateDecisionCount: 0,
    planRejectedCount: 0,

    maximumVolumeRatio: null,
    maximumSetupStrength: null,
    minimumDataQuality: null,
  };
}

function observeDecisionDiagnostics(
  diagnostics,
  decision,
) {
  const analysis =
    decision?.analysis || {};

  const plan =
    decision?.plan || {};

  const setup =
    analysis.setup || "unknown";

  incrementCounter(
    diagnostics.setupCounts,
    setup,
  );

  if (analysis.ready === true) {
    diagnostics.analysisReadyCount += 1;
  }

  if (
    analysis.marketBlocked === true
  ) {
    diagnostics.marketBlockedCount += 1;
  }

  if (
    setup === "insufficient_data"
  ) {
    diagnostics.insufficientDataCount += 1;
  }

  if (setup === "wait") {
    diagnostics.waitSetupCount += 1;
  }

  [
    "aboveVwap",
    "belowVwap",
    "volumeSurge",
    "breakoutLong",
    "breakoutShort",
    "reclaimLong",
    "reclaimShort",
    "pullbackLong",
    "pullbackShort",
  ].forEach((key) => {
    if (analysis[key] === true) {
      diagnostics
        .featurePassCounts[key] += 1;
    }
  });

  if (
    finite(analysis.volumeRatio)
  ) {
    diagnostics.maximumVolumeRatio =
      diagnostics.maximumVolumeRatio === null
        ? Number(analysis.volumeRatio)
        : Math.max(
            diagnostics.maximumVolumeRatio,
            Number(analysis.volumeRatio),
          );
  }

  if (
    finite(
      analysis.setupStrengthScore,
    )
  ) {
    diagnostics.maximumSetupStrength =
      diagnostics.maximumSetupStrength === null
        ? Number(
            analysis.setupStrengthScore,
          )
        : Math.max(
            diagnostics.maximumSetupStrength,
            Number(
              analysis.setupStrengthScore,
            ),
          );
  }

  if (
    finite(
      analysis.dataQualityScore,
    )
  ) {
    diagnostics.minimumDataQuality =
      diagnostics.minimumDataQuality === null
        ? Number(
            analysis.dataQualityScore,
          )
        : Math.min(
            diagnostics.minimumDataQuality,
            Number(
              analysis.dataQualityScore,
            ),
          );
  }

  if (
    decision?.paperCandidate === true
  ) {
    diagnostics.candidateDecisionCount += 1;
  } else if (
    ![
      "wait",
      "stale_data",
      "insufficient_data",
      "unknown",
    ].includes(setup)
  ) {
    diagnostics.planRejectedCount += 1;
  }

  const reasons = new Set([
    ...(decision?.reasons || []),
    ...(analysis.reasons || []),
    ...(plan.reasons || []),
  ]);

  reasons.forEach((reason) => {
    if (
      typeof reason === "string" &&
      reason.trim()
    ) {
      incrementCounter(
        diagnostics.reasonCounts,
        reason.trim(),
      );
    }
  });

  return diagnostics;
}

function resolvePositionEvent({
  position,
  candle,
}) {
  const stopGap =
    position.side === POSITION_SIDES.LONG
      ? Number(candle.open) <=
        Number(position.stopPrice)
      : Number(candle.open) >=
        Number(position.stopPrice);

  if (stopGap) {
    return {
      action: TRADE_ACTIONS.EXIT,
      exitPrice: Number(candle.open),
      reason: "損切りギャップ",
    };
  }

  return evaluateOpenPosition({
    position,
    candle,
    barsHeld: position.barsHeld,
    policy: {
      maximumHoldingBars:
        position.maximumHoldingBars,
      intrabarPriority: "risk_first",
    },
  });
}

function partialExitQuantity(
  position,
  exitFraction,
) {
  const lotSize = Math.max(
    1,
    Number(position.lotSize) || 1,
  );

  const raw =
    Number(position.remainingQuantity) *
    Number(exitFraction || 0.5);

  const rounded =
    Math.floor(raw / lotSize) *
    lotSize;

  if (
    rounded <= 0 ||
    rounded >=
      Number(position.remainingQuantity)
  ) {
    return Number(
      position.remainingQuantity,
    );
  }

  return rounded;
}

function markToMarket({
  balance,
  position,
  candle,
  policy,
}) {
  if (!position) {
    return {
      equity: Number(balance),
      unrealizedPnl: 0,
      estimatedExitCommission: 0,
    };
  }

  const estimatedExitPrice =
    adverseFillPrice({
      referencePrice: candle.close,
      side: position.side,
      phase: "exit",
      policy,
    });

  const unrealizedPnl =
    grossPnl({
      side: position.side,
      entryPrice:
        position.entryPrice,
      exitPrice:
        estimatedExitPrice,
      quantity:
        position.remainingQuantity,
    });

  const estimatedExitCommission =
    commissionFor(
      estimatedExitPrice *
        position.remainingQuantity,
      policy,
    );

  return {
    equity:
      Number(balance) +
      unrealizedPnl -
      estimatedExitCommission,

    unrealizedPnl,
    estimatedExitCommission,
  };
}

export function summarizeIntradayBacktest({
  trades = [],
  equityCurve = [],
  initialEquity,
  endingEquity,
  exposedBars = 0,
  totalBars = 0,
}) {
  const winners = trades.filter(
    (trade) => trade.netPnl > 0,
  );

  const losers = trades.filter(
    (trade) => trade.netPnl < 0,
  );

  const grossProfit = winners.reduce(
    (sum, trade) =>
      sum + Number(trade.netPnl),
    0,
  );

  const grossLoss = losers.reduce(
    (sum, trade) =>
      sum + Number(trade.netPnl),
    0,
  );

  const peak = {
    value: Number(initialEquity),
  };

  let maximumDrawdownPercent = 0;

  equityCurve.forEach((point) => {
    peak.value = Math.max(
      peak.value,
      Number(point.equity),
    );

    const drawdown =
      peak.value > 0
        ? ((Number(point.equity) -
            peak.value) /
            peak.value) *
          100
        : 0;

    maximumDrawdownPercent =
      Math.min(
        maximumDrawdownPercent,
        drawdown,
      );
  });

  const totalNetPnl = trades.reduce(
    (sum, trade) =>
      sum + Number(trade.netPnl),
    0,
  );

  const averageHoldingBars =
    trades.length > 0
      ? trades.reduce(
          (sum, trade) =>
            sum +
            Number(
              trade.holdingBars || 0,
            ),
          0,
        ) / trades.length
      : null;

  return {
    tradeCount: trades.length,
    winCount: winners.length,
    lossCount: losers.length,

    winRate:
      trades.length > 0
        ? (winners.length /
            trades.length) *
          100
        : null,

    totalNetPnl,

    totalReturnPercent:
      percentChange(
        endingEquity,
        initialEquity,
      ),

    averageNetPnl:
      trades.length > 0
        ? totalNetPnl /
          trades.length
        : null,

    averageHoldingBars,

    grossProfit,
    grossLoss,

    profitFactor:
      grossLoss < 0
        ? grossProfit /
          Math.abs(grossLoss)
        : null,

    profitFactorState:
      grossLoss < 0
        ? "calculated"
        : grossProfit > 0
          ? "no_losses"
          : "unavailable",

    maximumDrawdownPercent,

    exposureRate:
      totalBars > 0
        ? (Number(exposedBars) /
            Number(totalBars)) *
          100
        : 0,
  };
}

function benchmarkReturnPercent({
  candles,
  policy,
}) {
  if (candles.length < 2) {
    return null;
  }

  const entry =
    adverseFillPrice({
      referencePrice:
        candles[0].open,
      side: POSITION_SIDES.LONG,
      phase: "entry",
      policy,
    });

  const exit =
    adverseFillPrice({
      referencePrice:
        candles.at(-1).close,
      side: POSITION_SIDES.LONG,
      phase: "exit",
      policy,
    });

  const entryWithCommission =
    entry *
    (1 +
      Number(
        policy.commissionPercentPerSide,
      ) /
        100);

  const exitAfterCommission =
    exit *
    (1 -
      Number(
        policy.commissionPercentPerSide,
      ) /
        100);

  return percentChange(
    exitAfterCommission,
    entryWithCommission,
  );
}

export function runIntradayPaperBacktest({
  symbol,
  intradayHistory,
  policy = {},
  strategyPolicy = {},
  decisionProvider =
    createIntradayTradingDecision,
} = {}) {
  const resolvedPolicy =
    resolvePolicy(policy);

  const sourceCandles =
    Array.isArray(
      intradayHistory?.candles,
    )
      ? intradayHistory.candles
      : [];

  const candles =
    normalizeIntradayCandles(
      sourceCandles,
    ).filter(
      (candle) =>
        candle.isClosed !== false,
    );

  if (
    candles.length <
    Number(
      resolvedPolicy.minimumWarmupBars,
    ) +
      1
  ) {
    throw new Error(
      "短期バックテストに必要な確定済み15分足が不足しています。",
    );
  }

  const initialEquity =
    positive(
      resolvedPolicy.initialEquity,
    )
      ? Number(
          resolvedPolicy.initialEquity,
        )
      : 1_000_000;

  const lotSize = Math.max(
    1,
    Math.floor(
      Number(resolvedPolicy.lotSize) ||
        1,
    ),
  );

  const state = {
    balance: initialEquity,
    position: null,
    pendingEntry: null,

    trades: [],
    fills: [],
    equityCurve: [],

    candidateCount: 0,
    skippedCandidateCount: 0,
    signalEvaluationCount: 0,
    exposedBars: 0,

    consecutiveLosses: 0,
    sessionStartBalance:
      initialEquity,
    activeSessionDate:
      candles[0].sessionDate,

    totalCommission: 0,
    totalImpactCost: 0,

    diagnostics:
      createDecisionDiagnostics(),
  };

  let runningPeak =
    initialEquity;

  function addFill({
    phase,
    reason,
    referencePrice,
    fillPrice,
    quantity,
    time,
  }) {
    const notional =
      Number(fillPrice) *
      Number(quantity);

    const commission =
      commissionFor(
        notional,
        resolvedPolicy,
      );

    const impactCost =
      Math.abs(
        Number(fillPrice) -
          Number(referencePrice),
      ) * Number(quantity);

    const fill = {
      phase,
      reason,
      time,
      referencePrice:
        Number(referencePrice),
      fillPrice:
        Number(fillPrice),
      quantity:
        Number(quantity),
      commission,
      impactCost,
    };

    state.fills.push(fill);
    state.totalCommission +=
      commission;
    state.totalImpactCost +=
      impactCost;

    return fill;
  }

  function openPendingEntry(
    candle,
    index,
  ) {
    const pending =
      state.pendingEntry;

    if (!pending) {
      return;
    }

    state.pendingEntry = null;

    if (
      !resolvedPolicy.allowOvernightEntry &&
      pending.sessionDate !==
        candle.sessionDate
    ) {
      state.skippedCandidateCount += 1;
      return;
    }

    const side =
      sideFromDecision(
        pending.decision,
      );

    if (
      ![
        POSITION_SIDES.LONG,
        POSITION_SIDES.SHORT,
      ].includes(side)
    ) {
      state.skippedCandidateCount += 1;
      return;
    }

    const entryPrice =
      adverseFillPrice({
        referencePrice:
          candle.open,
        side,
        phase: "entry",
        policy:
          resolvedPolicy,
      });

    const sourceSignal = {
      ...(
        pending.decision
          ?.analysis
          ?.tradeSignal || {}
      ),

      direction:
        directionFromSide(side),

      currentPrice:
        entryPrice,

      atr:
        pending.decision
          ?.analysis
          ?.atr ??
        pending.decision
          ?.analysis
          ?.tradeSignal
          ?.atr,

      confidenceScore:
        pending.decision
          ?.analysis
          ?.setupStrengthScore ??
        90,

      dataQualityScore:
        pending.decision
          ?.analysis
          ?.dataQualityScore ??
        100,

      spreadPercent:
        Number(
          resolvedPolicy.spreadPercent,
        ),

      dataAgeSeconds: 0,

      setup:
        pending.decision
          ?.analysis
          ?.setup ||
        "backtest",

      entryCondition:
        pending.decision
          ?.analysis
          ?.entryCondition ||
        "次足始値でPaper約定",

      marketBlocked: false,
      marketBlockReason: null,
    };

    const plan =
      createShortTermTradePlan({
        signal: sourceSignal,

        account: {
          executionMode: "paper",
          equity:
            state.balance,
          openPositions: 0,

          dailyPnlPercent:
            percentChange(
              state.balance,
              state.sessionStartBalance,
            ) || 0,

          consecutiveLosses:
            state.consecutiveLosses,
        },

        lotSize,

        policy: {
          requireSpreadData: false,
          maximumDataAgeSeconds:
            Number.MAX_SAFE_INTEGER,

          ...(
            strategyPolicy.trading ||
            {}
          ),
        },
      });

    if (!plan.executable) {
      state.skippedCandidateCount += 1;
      return;
    }

    const entryFill =
      addFill({
        phase: "entry",
        reason: "次足始値",
        referencePrice:
          candle.open,
        fillPrice:
          entryPrice,
        quantity:
          plan.quantity,
        time:
          candle.time,
      });

    state.balance -=
      entryFill.commission;

    state.position = {
      side,
      setup: plan.setup,

      signalTime:
        pending.signalTime,

      entryTime:
        candle.time,

      entryIndex:
        index,

      entryPrice:
        entryPrice,

      stopPrice:
        plan.stopPrice,

      firstTargetPrice:
        plan.firstTargetPrice,

      secondTargetPrice:
        plan.secondTargetPrice,

      firstExitFraction:
        plan.firstExitFraction,

      firstTargetTaken: false,

      initialQuantity:
        plan.quantity,

      remainingQuantity:
        plan.quantity,

      lotSize,

      maximumHoldingBars:
        plan.maximumHoldingBars,

      barsHeld: 0,

      entryCommission:
        entryFill.commission,

      entryImpactCost:
        entryFill.impactCost,

      exitCommission: 0,
      exitImpactCost: 0,
      realizedGrossPnl: 0,

      fills: [
        entryFill,
      ],
    };
  }

  function finalizeTrade({
    exitTime,
    exitReason,
  }) {
    const position =
      state.position;

    if (!position) {
      return;
    }

    const netPnl =
      Number(
        position.realizedGrossPnl,
      ) -
      Number(
        position.entryCommission,
      ) -
      Number(
        position.exitCommission,
      );

    const investedValue =
      Number(position.entryPrice) *
      Number(
        position.initialQuantity,
      );

    const trade = {
      symbol,
      side:
        position.side,

      setup:
        position.setup,

      signalTime:
        position.signalTime,

      entryTime:
        position.entryTime,

      exitTime,

      entryPrice:
        position.entryPrice,

      exitPrice:
        position.fills.at(-1)
          ?.fillPrice ?? null,

      initialQuantity:
        position.initialQuantity,

      holdingBars:
        position.barsHeld,

      exitReason,

      grossPnl:
        position.realizedGrossPnl,

      netPnl,

      returnPercent:
        investedValue > 0
          ? (netPnl /
              investedValue) *
            100
          : null,

      commission:
        position.entryCommission +
        position.exitCommission,

      spreadAndSlippageCost:
        position.entryImpactCost +
        position.exitImpactCost,

      fills:
        position.fills,
    };

    state.trades.push(trade);

    state.consecutiveLosses =
      netPnl < 0
        ? state.consecutiveLosses +
          1
        : 0;

    state.position = null;
  }

  function executeExit({
    candle,
    event,
  }) {
    const position =
      state.position;

    if (!position) {
      return;
    }

    const isPartial =
      event.action ===
      TRADE_ACTIONS.TAKE_PARTIAL;

    const quantity =
      isPartial
        ? partialExitQuantity(
            position,
            event.exitFraction,
          )
        : position.remainingQuantity;

    const exitPrice =
      adverseFillPrice({
        referencePrice:
          event.exitPrice,
        side:
          position.side,
        phase: "exit",
        policy:
          resolvedPolicy,
      });

    const exitFill =
      addFill({
        phase: "exit",
        reason:
          event.reason,
        referencePrice:
          event.exitPrice,
        fillPrice:
          exitPrice,
        quantity,
        time:
          candle.time,
      });

    const pnl =
      grossPnl({
        side:
          position.side,
        entryPrice:
          position.entryPrice,
        exitPrice,
        quantity,
      });

    state.balance +=
      pnl -
      exitFill.commission;

    position.realizedGrossPnl +=
      pnl;

    position.exitCommission +=
      exitFill.commission;

    position.exitImpactCost +=
      exitFill.impactCost;

    position.remainingQuantity -=
      quantity;

    position.fills.push(
      exitFill,
    );

    if (
      isPartial &&
      position.remainingQuantity > 0
    ) {
      position.firstTargetTaken =
        true;

      return;
    }

    finalizeTrade({
      exitTime:
        candle.time,
      exitReason:
        event.reason,
    });
  }

  function recordEquity(
    candle,
  ) {
    const marked =
      markToMarket({
        balance:
          state.balance,
        position:
          state.position,
        candle,
        policy:
          resolvedPolicy,
      });

    runningPeak = Math.max(
      runningPeak,
      marked.equity,
    );

    const drawdownPercent =
      runningPeak > 0
        ? ((marked.equity -
            runningPeak) /
            runningPeak) *
          100
        : 0;

    state.equityCurve.push({
      time:
        candle.time,

      sessionDate:
        candle.sessionDate,

      balance:
        state.balance,

      equity:
        marked.equity,

      unrealizedPnl:
        marked.unrealizedPnl,

      drawdownPercent,
    });
  }

  for (
    let index = 0;
    index < candles.length;
    index += 1
  ) {
    const candle =
      candles[index];

    const next =
      candles[index + 1] ||
      null;

    if (
      candle.sessionDate !==
      state.activeSessionDate
    ) {
      state.activeSessionDate =
        candle.sessionDate;

      state.sessionStartBalance =
        state.balance;
    }

    openPendingEntry(
      candle,
      index,
    );

    const exposedThisBar =
      Boolean(
        state.position,
      );

    if (state.position) {
      state.position.barsHeld += 1;

      const event =
        resolvePositionEvent({
          position:
            state.position,
          candle,
        });

      if (
        event.action ===
          TRADE_ACTIONS.EXIT ||
        event.action ===
          TRADE_ACTIONS.TAKE_PARTIAL
      ) {
        executeExit({
          candle,
          event,
        });
      }
    }

    const sessionEnds =
      !next ||
      next.sessionDate !==
        candle.sessionDate;

    if (
      state.position &&
      sessionEnds &&
      (
        resolvedPolicy
          .closeAtSessionEnd ||
        !next
      )
    ) {
      executeExit({
        candle,

        event: {
          action:
            TRADE_ACTIONS.EXIT,

          exitPrice:
            Number(
              candle.close,
            ),

          reason:
            next
              ? "セッション終了"
              : "データ終端",
        },
      });
    }

    if (exposedThisBar) {
      state.exposedBars += 1;
    }

    recordEquity(candle);

    const canEvaluate =
      !state.position &&
      !state.pendingEntry &&
      Boolean(next) &&
      index + 1 >=
        Number(
          resolvedPolicy
            .minimumWarmupBars,
        ) &&
      state.trades.length <
        Number(
          resolvedPolicy
            .maximumTrades,
        );

    if (!canEvaluate) {
      continue;
    }

    state.signalEvaluationCount += 1;

    const prefix =
      candles.slice(
        0,
        index + 1,
      );

    const decision =
      decisionProvider({
        symbol,

        intradayHistory: {
          ...(intradayHistory || {}),
          candles:
            prefix,
        },

        account: {
          executionMode: "paper",
          equity:
            state.balance,
          openPositions: 0,

          dailyPnlPercent:
            percentChange(
              state.balance,
              state.sessionStartBalance,
            ) || 0,

          consecutiveLosses:
            state.consecutiveLosses,
        },

        lotSize,

        spreadPercent:
          resolvedPolicy.spreadPercent,

        nowSeconds:
          Number(candle.time) +
          901,

        policy:
          strategyPolicy,
      });

    observeDecisionDiagnostics(
      state.diagnostics,
      decision,
    );

    if (
      decision?.paperCandidate !==
      true
    ) {
      continue;
    }

    state.candidateCount += 1;

    if (
      !resolvedPolicy
        .allowOvernightEntry &&
      next.sessionDate !==
        candle.sessionDate
    ) {
      state.skippedCandidateCount += 1;
      continue;
    }

    state.pendingEntry = {
      decision,
      signalTime:
        candle.time,
      sessionDate:
        candle.sessionDate,
    };
  }

  const endingEquity =
    state.equityCurve.at(-1)
      ?.equity ??
    state.balance;

  const metrics =
    summarizeIntradayBacktest({
      trades:
        state.trades,

      equityCurve:
        state.equityCurve,

      initialEquity,
      endingEquity,

      exposedBars:
        state.exposedBars,

      totalBars:
        candles.length,
    });

  const buyAndHoldReturnPercent =
    benchmarkReturnPercent({
      candles,
      policy:
        resolvedPolicy,
    });

  return {
    version:
      INTRADAY_PAPER_BACKTEST_VERSION,

    symbol,

    executionMode: "paper",
    liveExecutionAllowed: false,

    dataPolicy: {
      signalUsesClosedBarsOnly:
        true,

      entryTiming:
        "next_bar_open",

      intrabarPriority:
        "risk_first",

      gapStopPolicy:
        "fill_at_open_when_worse",

      closeAtSessionEnd:
        Boolean(
          resolvedPolicy
            .closeAtSessionEnd,
        ),
    },

    costPolicy: {
      commissionPercentPerSide:
        resolvedPolicy
          .commissionPercentPerSide,

      spreadPercent:
        resolvedPolicy
          .spreadPercent,

      slippagePercentPerSide:
        resolvedPolicy
          .slippagePercentPerSide,

      minimumCommission:
        resolvedPolicy
          .minimumCommission,
    },

    meta: {
      sourceBarCount:
        sourceCandles.length,

      closedBarCount:
        candles.length,

      signalEvaluationCount:
        state.signalEvaluationCount,

      candidateCount:
        state.candidateCount,

      skippedCandidateCount:
        state.skippedCandidateCount,

      exposedBars:
        state.exposedBars,
    },

    diagnostics:
      state.diagnostics,

    account: {
      initialEquity,
      endingEquity,
      realizedBalance:
        state.balance,

      openPosition:
        state.position,

      consecutiveLosses:
        state.consecutiveLosses,
    },

    metrics,

    comparison: {
      noTradeReturnPercent: 0,

      buyAndHoldReturnPercent,

      excessVsBuyAndHold:
        finite(
          metrics.totalReturnPercent,
        ) &&
        finite(
          buyAndHoldReturnPercent,
        )
          ? metrics.totalReturnPercent -
            buyAndHoldReturnPercent
          : null,
    },

    estimatedCosts: {
      commission:
        state.totalCommission,

      spreadAndSlippage:
        state.totalImpactCost,

      total:
        state.totalCommission +
        state.totalImpactCost,
    },

    trades:
      state.trades,

    fills:
      state.fills,

    equityCurve:
      state.equityCurve,

    warnings: [
      "結果は過去の15分足を使ったPaper検証で、将来の利益を保証しません。",
      "売買コストは設定値による概算で、実際の約定条件とは異なります。",
      "現在の戦略は現物買いのみです。実注文・注文板の厚さは未反映です。",
    ],
  };
}

export const IntradayPaperBacktestInternals = {
  finite,
  positive,
  clamp,
  percentChange,
  resolvePolicy,
  commissionFor,
  adverseFillPrice,
  grossPnl,
  sideFromDecision,
  directionFromSide,
  resolvePositionEvent,
  partialExitQuantity,
  markToMarket,
  benchmarkReturnPercent,
  createDecisionDiagnostics,
  observeDecisionDiagnostics,
};