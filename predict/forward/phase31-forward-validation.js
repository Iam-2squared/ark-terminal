const PHASE31_SAFETY = Object.freeze({
  mode: "FORWARD_VALIDATION_ONLY",
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  humanApprovalRequired: true,
});

function finiteNumber(value, fallback = null) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function normalizeSignal(value) {
  const signal = String(value ?? "").toUpperCase();
  return ["BUY", "SELL", "HOLD", "NO_TRADE"].includes(signal) ? signal : "NO_TRADE";
}

function assertValidationContext(context) {
  if (!context || typeof context !== "object") throw new TypeError("validation context is required");
  if (context.outOfSample !== true) throw new Error("BLOCKED_NOT_OUT_OF_SAMPLE");
  if (context.paperOnly !== true) throw new Error("BLOCKED_NOT_PAPER_ONLY");
  if (context.futureLeakCheckPassed !== true) throw new Error("BLOCKED_FUTURE_LEAK_CHECK");
  if (context.sameDataContract !== true) throw new Error("BLOCKED_DATA_CONTRACT_MISMATCH");
  if (context.sameCostContract !== true) throw new Error("BLOCKED_COST_CONTRACT_MISMATCH");
  if (context.sameHoldingPeriodContract !== true) throw new Error("BLOCKED_HOLDING_PERIOD_MISMATCH");
}

function normalizeRow(row, role) {
  if (!row || typeof row !== "object") throw new TypeError(`${role} row is required`);
  const symbol = String(row.symbol ?? "").toUpperCase();
  const session = String(row.session ?? "");
  const horizonDays = Math.max(1, Math.trunc(finiteNumber(row.horizonDays, 1)));
  const actualReturn = finiteNumber(row.actualReturn, null);
  if (!symbol || !session || actualReturn == null) throw new TypeError(`${role} row is incomplete`);
  return {
    symbol,
    session,
    horizonDays,
    signal: normalizeSignal(row.signal),
    confidence: finiteNumber(row.confidence, null),
    predictedReturn: finiteNumber(row.predictedReturn, null),
    actualReturn,
    netReturn: finiteNumber(row.netReturn, actualReturn),
    drawdown: Math.max(0, finiteNumber(row.drawdown, 0)),
  };
}

function keyOf(row) {
  return `${row.symbol}|${row.session}|${row.horizonDays}`;
}

function directionalCorrect(row) {
  if (row.signal === "BUY") return row.actualReturn > 0;
  if (row.signal === "SELL") return row.actualReturn < 0;
  return null;
}

function summarize(rows) {
  const directional = rows.filter((row) => ["BUY", "SELL"].includes(row.signal));
  const correct = directional.filter((row) => directionalCorrect(row) === true).length;
  const grossProfit = directional.filter((row) => row.netReturn > 0).reduce((sum, row) => sum + row.netReturn, 0);
  const grossLoss = Math.abs(directional.filter((row) => row.netReturn < 0).reduce((sum, row) => sum + row.netReturn, 0));
  return {
    sampleCount: rows.length,
    directionalSampleCount: directional.length,
    accuracy: directional.length ? correct / directional.length : null,
    averageNetReturn: rows.length ? rows.reduce((sum, row) => sum + row.netReturn, 0) / rows.length : null,
    totalNetReturn: rows.reduce((sum, row) => sum + row.netReturn, 0),
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : null,
    maxDrawdown: rows.reduce((max, row) => Math.max(max, row.drawdown), 0),
  };
}

export function createPhase31ForwardRun({ championRows = [], candidateRows = [], context, metadata = {} } = {}) {
  assertValidationContext(context);
  const champion = championRows.map((row) => normalizeRow(row, "champion"));
  const candidate = candidateRows.map((row) => normalizeRow(row, "candidate"));
  const championByKey = new Map(champion.map((row) => [keyOf(row), row]));
  const candidateByKey = new Map(candidate.map((row) => [keyOf(row), row]));
  const sharedKeys = [...championByKey.keys()].filter((key) => candidateByKey.has(key));
  const pairs = sharedKeys.map((key) => {
    const championRow = championByKey.get(key);
    const candidateRow = candidateByKey.get(key);
    if (championRow.actualReturn !== candidateRow.actualReturn) {
      throw new Error(`BLOCKED_ACTUAL_RETURN_MISMATCH:${key}`);
    }
    return { key, champion: championRow, candidate: candidateRow };
  });
  const runId = metadata.runId ?? `phase31-${Date.now()}`;
  return {
    runId,
    createdAt: metadata.createdAt ?? new Date().toISOString(),
    championModelId: metadata.championModelId ?? null,
    candidateModelId: metadata.candidateModelId ?? null,
    context: { ...context },
    pairs,
    unmatchedChampion: champion.length - pairs.length,
    unmatchedCandidate: candidate.length - pairs.length,
    immutable: true,
    safety: { ...PHASE31_SAFETY },
  };
}

export function validatePhase31RunIntegrity(run) {
  const blockers = [];
  if (!run?.immutable) blockers.push("RUN_NOT_IMMUTABLE");
  if (!Array.isArray(run?.pairs) || !run.pairs.length) blockers.push("NO_PAIRED_SAMPLES");
  for (const pair of run?.pairs ?? []) {
    if (keyOf(pair.champion) !== keyOf(pair.candidate)) blockers.push(`PAIR_KEY_MISMATCH:${pair.key}`);
    if (pair.champion.actualReturn !== pair.candidate.actualReturn) blockers.push(`ACTUAL_RETURN_MISMATCH:${pair.key}`);
  }
  return {
    status: blockers.length ? "BLOCKED" : "VALID",
    blockers,
    safety: { ...PHASE31_SAFETY },
  };
}

export function comparePhase31ForwardPerformance(run, options = {}) {
  const integrity = validatePhase31RunIntegrity(run);
  if (integrity.status !== "VALID") {
    return { status: "BLOCKED", integrity, safety: { ...PHASE31_SAFETY } };
  }
  const minPairedSamples = Math.max(1, Math.trunc(finiteNumber(options.minPairedSamples, 30)));
  const championRows = run.pairs.map((pair) => pair.champion);
  const candidateRows = run.pairs.map((pair) => pair.candidate);
  const champion = summarize(championRows);
  const candidate = summarize(candidateRows);
  const deltas = {
    accuracy: (candidate.accuracy ?? 0) - (champion.accuracy ?? 0),
    averageNetReturn: (candidate.averageNetReturn ?? 0) - (champion.averageNetReturn ?? 0),
    totalNetReturn: candidate.totalNetReturn - champion.totalNetReturn,
    maxDrawdown: candidate.maxDrawdown - champion.maxDrawdown,
  };
  const blockers = [];
  if (run.pairs.length < minPairedSamples) blockers.push("INSUFFICIENT_PAIRED_SAMPLES");
  if (candidate.directionalSampleCount === 0) blockers.push("NO_CANDIDATE_DIRECTIONAL_SAMPLES");
  return {
    status: blockers.length ? "CONTINUE_FORWARD_TEST" : "READY_FOR_STATISTICAL_REVIEW",
    pairedSamples: run.pairs.length,
    champion,
    candidate,
    deltas,
    blockers,
    approved: false,
    promotionAllowed: false,
    safety: { ...PHASE31_SAFETY },
  };
}

export function runPhase31ForwardValidation(input = {}) {
  const run = createPhase31ForwardRun(input);
  const integrity = validatePhase31RunIntegrity(run);
  const comparison = comparePhase31ForwardPerformance(run, input.options ?? {});
  return {
    status: comparison.status,
    run,
    integrity,
    comparison,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE31_SAFETY },
  };
}

export { PHASE31_SAFETY };
