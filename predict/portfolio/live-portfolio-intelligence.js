const READ_ONLY_SAFETY = Object.freeze({
  mode: "READ_ONLY_ADVISORY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  automaticExecutionAllowed: false,
  humanApprovalRequired: true,
});

function finiteNumber(value, fallback = null) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function normalizeSymbol(value) {
  const symbol = String(value ?? "").trim().toUpperCase();
  if (!symbol) throw new TypeError("position.symbol is required");
  return /^\d+$/.test(symbol) ? `${symbol}.T` : symbol;
}

function assertHealthySnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    throw new TypeError("broker snapshot is required");
  }
  if (snapshot.readOnly !== true) {
    throw new Error("live portfolio intelligence accepts READ ONLY snapshots only");
  }
  if (snapshot.synchronized !== true || snapshot.connection?.connected !== true) {
    throw new Error("broker snapshot is disconnected or not synchronized");
  }
  if (!Array.isArray(snapshot.positions)) {
    throw new TypeError("snapshot.positions must be an array");
  }
}

export function normalizeLivePortfolioSnapshot(snapshot, options = {}) {
  assertHealthySnapshot(snapshot);
  const sectorBySymbol = options.sectorBySymbol ?? {};
  const aiBySymbol = options.aiBySymbol ?? {};
  const positions = snapshot.positions.map((position) => {
    const symbol = normalizeSymbol(position.symbol);
    const quantity = Math.max(0, finiteNumber(position.quantity, 0));
    const marketPrice = finiteNumber(position.marketPrice, 0);
    const averagePrice = finiteNumber(position.averagePrice, null);
    const marketValue = finiteNumber(position.marketValue, marketPrice * quantity);
    const unrealizedPnl = finiteNumber(
      position.unrealizedPnl,
      averagePrice == null ? null : (marketPrice - averagePrice) * quantity,
    );
    return {
      symbol,
      name: String(position.name ?? symbol),
      sector: String(sectorBySymbol[symbol] ?? "UNKNOWN"),
      quantity,
      availableQuantity: Math.max(0, finiteNumber(position.availableQuantity, quantity)),
      averagePrice,
      marketPrice,
      marketValue,
      unrealizedPnl,
      unrealizedPnlPercent: finiteNumber(position.unrealizedPnlPercent, null),
      aiScore: finiteNumber(aiBySymbol[symbol]?.score, null),
      confidence: finiteNumber(aiBySymbol[symbol]?.confidence, null),
      aiSignal: String(aiBySymbol[symbol]?.signal ?? "UNAVAILABLE").toUpperCase(),
      updatedAt: position.updatedAt ?? snapshot.synchronizedAt ?? null,
      sourceMode: position.sourceMode ?? snapshot.sourceMode ?? "unknown",
      readOnly: true,
    };
  });

  const totalMarketValue = positions.reduce((sum, position) => sum + Math.max(0, position.marketValue || 0), 0);
  return {
    generatedAt: options.now ?? new Date().toISOString(),
    source: snapshot.source ?? "MARKETSPEED II RSS / Excel",
    sourceMode: snapshot.sourceMode ?? "unknown",
    synchronizedAt: snapshot.synchronizedAt ?? null,
    account: {
      buyingPower: finiteNumber(snapshot.account?.buyingPower, null),
      marketValue: finiteNumber(snapshot.account?.marketValue, totalMarketValue),
      unrealizedPnl: finiteNumber(snapshot.account?.unrealizedPnl, null),
      currency: snapshot.account?.currency ?? "JPY",
    },
    positions,
    totalMarketValue,
    safety: { ...READ_ONLY_SAFETY },
  };
}

export function analyzeLivePortfolioRisk(portfolio, limits = {}) {
  const maxSinglePositionWeight = finiteNumber(limits.maxSinglePositionWeight, 0.35);
  const maxSectorWeight = finiteNumber(limits.maxSectorWeight, 0.5);
  const warningLossPercent = finiteNumber(limits.warningLossPercent, -10);
  const total = Math.max(0, finiteNumber(portfolio.totalMarketValue, 0));
  const sectorValues = new Map();
  const positionRisks = portfolio.positions.map((position) => {
    const weight = total > 0 ? Math.max(0, position.marketValue) / total : 0;
    sectorValues.set(position.sector, (sectorValues.get(position.sector) ?? 0) + Math.max(0, position.marketValue));
    const flags = [];
    if (weight > maxSinglePositionWeight) flags.push("POSITION_CONCENTRATION");
    if (position.unrealizedPnlPercent != null && position.unrealizedPnlPercent <= warningLossPercent) {
      flags.push("LOSS_THRESHOLD");
    }
    if (position.marketPrice <= 0 || position.quantity <= 0) flags.push("INVALID_POSITION_DATA");
    return { symbol: position.symbol, weight, flags };
  });
  const sectorRisks = [...sectorValues.entries()].map(([sector, value]) => {
    const weight = total > 0 ? value / total : 0;
    return { sector, value, weight, flags: weight > maxSectorWeight ? ["SECTOR_CONCENTRATION"] : [] };
  });
  const blockers = [
    ...positionRisks.flatMap((item) => item.flags.map((flag) => `${item.symbol}:${flag}`)),
    ...sectorRisks.flatMap((item) => item.flags.map((flag) => `${item.sector}:${flag}`)),
  ];
  return {
    status: blockers.length ? "WARNING" : "HEALTHY",
    totalMarketValue: total,
    positionRisks,
    sectorRisks,
    blockers,
    safety: { ...READ_ONLY_SAFETY },
  };
}

export function buildLivePortfolioAdvice(portfolio, riskReport, options = {}) {
  const minimumConfidence = finiteNumber(options.minimumConfidence, 0.65);
  const items = portfolio.positions.map((position) => {
    const risk = riskReport.positionRisks.find((item) => item.symbol === position.symbol);
    const reasons = [...(risk?.flags ?? [])];
    let action = "HOLD_REVIEW";
    if (position.confidence == null || position.confidence < minimumConfidence) {
      reasons.push("INSUFFICIENT_AI_CONFIDENCE");
    } else if (position.aiSignal === "SELL" && risk?.flags.includes("LOSS_THRESHOLD")) {
      action = "REDUCE_REVIEW";
      reasons.push("AI_SELL_AND_LOSS_RISK");
    } else if (position.aiSignal === "BUY" && !(risk?.flags ?? []).length) {
      action = "HOLD_OR_ADD_REVIEW";
      reasons.push("AI_BUY_WITHIN_RISK_LIMITS");
    } else if (risk?.flags.includes("POSITION_CONCENTRATION")) {
      action = "REBALANCE_REVIEW";
    }
    return {
      symbol: position.symbol,
      action,
      reasons,
      aiSignal: position.aiSignal,
      aiScore: position.aiScore,
      confidence: position.confidence,
      executable: false,
      orderCandidateCreated: false,
      humanReviewRequired: true,
    };
  });
  return {
    status: riskReport.status === "HEALTHY" ? "READY_FOR_HUMAN_REVIEW" : "RISK_REVIEW_REQUIRED",
    items,
    executionAllowed: false,
    safety: { ...READ_ONLY_SAFETY },
  };
}

export { READ_ONLY_SAFETY };
