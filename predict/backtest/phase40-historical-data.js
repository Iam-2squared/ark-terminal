const PHASE40_SAFETY = Object.freeze({
  mode: "HISTORICAL_DATA_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

function finite(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeTime(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value > 10_000_000_000 ? Math.trunc(value / 1000) : Math.trunc(value);
  }
  const parsed = Date.parse(String(value ?? ""));
  return Number.isFinite(parsed) ? Math.trunc(parsed / 1000) : null;
}

function normalizeSymbol(value) {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeSourceRow(row, index, symbol) {
  if (!row || typeof row !== "object") throw new TypeError(`row ${index} is required`);
  const time = normalizeTime(row.time ?? row.date ?? row.timestamp);
  const open = finite(row.open);
  const high = finite(row.high);
  const low = finite(row.low);
  const close = finite(row.close);
  const adjustedClose = finite(row.adjustedClose ?? row.adjClose ?? row.adjusted_close);
  const volume = finite(row.volume);
  const rowSymbol = normalizeSymbol(row.symbol || symbol);

  return {
    symbol: rowSymbol,
    time,
    open,
    high,
    low,
    close,
    adjustedClose,
    volume,
    adjustmentFactor: close && adjustedClose ? adjustedClose / close : 1,
    sourceIndex: index,
  };
}

export function normalizeHistoricalRows({ symbol, rows = [], source = "UNKNOWN", datasetId = null } = {}) {
  const normalizedSymbol = normalizeSymbol(symbol);
  if (!normalizedSymbol) throw new TypeError("symbol is required");
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");

  const normalized = rows
    .map((row, index) => normalizeSourceRow(row, index, normalizedSymbol))
    .sort((a, b) => (a.time ?? Infinity) - (b.time ?? Infinity));

  return {
    datasetId: datasetId || `phase40-${normalizedSymbol}-${Date.now()}`,
    symbol: normalizedSymbol,
    source: String(source || "UNKNOWN"),
    rowCount: normalized.length,
    rows: normalized,
    immutable: true,
    safety: { ...PHASE40_SAFETY },
  };
}

export function validateAdjustedPrices(dataset, options = {}) {
  const tolerance = Math.max(0, Number(options.tolerance ?? 0.02));
  const blockers = [];
  const warnings = [];
  const factors = [];

  for (const row of dataset?.rows ?? []) {
    if (![row.open, row.high, row.low, row.close].every((value) => Number.isFinite(value) && value > 0)) {
      blockers.push(`INVALID_OHLC:${row.sourceIndex}`);
      continue;
    }
    if (!(row.high >= row.open && row.high >= row.close && row.high >= row.low)) blockers.push(`HIGH_INCONSISTENT:${row.sourceIndex}`);
    if (!(row.low <= row.open && row.low <= row.close && row.low <= row.high)) blockers.push(`LOW_INCONSISTENT:${row.sourceIndex}`);

    if (Number.isFinite(row.adjustedClose) && row.adjustedClose > 0) {
      const factor = row.adjustedClose / row.close;
      factors.push({ time: row.time, factor });
      const projected = row.close * factor;
      const relativeError = Math.abs(projected - row.adjustedClose) / row.adjustedClose;
      if (relativeError > tolerance) blockers.push(`ADJUSTMENT_FACTOR_MISMATCH:${row.sourceIndex}`);
    } else {
      warnings.push(`ADJUSTED_CLOSE_MISSING:${row.sourceIndex}`);
    }
  }

  for (let index = 1; index < factors.length; index += 1) {
    const previous = factors[index - 1].factor;
    const current = factors[index].factor;
    if (previous > 0 && current > 0) {
      const ratio = Math.max(previous, current) / Math.min(previous, current);
      if (ratio >= 1.8) warnings.push(`CORPORATE_ACTION_CANDIDATE:${factors[index].time}`);
    }
  }

  return {
    status: blockers.length ? "BLOCKED" : warnings.length ? "WARNING" : "VALID",
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
    adjustedCloseCoverage: dataset?.rows?.length
      ? dataset.rows.filter((row) => Number.isFinite(row.adjustedClose) && row.adjustedClose > 0).length / dataset.rows.length
      : 0,
    safety: { ...PHASE40_SAFETY },
  };
}

export function auditHistoricalDataQuality(dataset, options = {}) {
  const minimumRows = Math.max(1, Math.trunc(Number(options.minimumRows ?? 100)));
  const maximumMissingRate = Math.max(0, Number(options.maximumMissingRate ?? 0.02));
  const blockers = [];
  const warnings = [];
  const rows = dataset?.rows ?? [];

  if (!dataset?.immutable) blockers.push("DATASET_NOT_IMMUTABLE");
  if (!dataset?.symbol) blockers.push("SYMBOL_MISSING");
  if (rows.length < minimumRows) blockers.push("INSUFFICIENT_HISTORY");

  let invalidRows = 0;
  let duplicateDates = 0;
  let nonIncreasingDates = 0;
  const seen = new Set();
  let previousTime = null;

  for (const row of rows) {
    const valid = Number.isFinite(row.time)
      && Number.isFinite(row.open)
      && Number.isFinite(row.high)
      && Number.isFinite(row.low)
      && Number.isFinite(row.close)
      && Number.isFinite(row.volume)
      && row.open > 0 && row.high > 0 && row.low > 0 && row.close > 0 && row.volume >= 0;
    if (!valid) invalidRows += 1;
    if (Number.isFinite(row.time)) {
      if (seen.has(row.time)) duplicateDates += 1;
      seen.add(row.time);
      if (previousTime != null && row.time <= previousTime) nonIncreasingDates += 1;
      previousTime = row.time;
    }
  }

  const missingRate = rows.length ? invalidRows / rows.length : 1;
  if (missingRate > maximumMissingRate) blockers.push("MISSING_RATE_EXCEEDED");
  if (duplicateDates > 0) blockers.push("DUPLICATE_TRADING_DATES");
  if (nonIncreasingDates > 0) blockers.push("NON_INCREASING_TRADING_DATES");

  const adjustment = validateAdjustedPrices(dataset, options);
  blockers.push(...adjustment.blockers);
  warnings.push(...adjustment.warnings);
  if (adjustment.adjustedCloseCoverage < Number(options.minimumAdjustedCoverage ?? 0.95)) {
    warnings.push("LOW_ADJUSTED_CLOSE_COVERAGE");
  }

  return {
    status: blockers.length ? "BLOCKED" : warnings.length ? "WARNING" : "VALID",
    canBacktest: blockers.length === 0,
    symbol: dataset?.symbol ?? null,
    source: dataset?.source ?? null,
    rowCount: rows.length,
    invalidRows,
    missingRate,
    duplicateDates,
    nonIncreasingDates,
    adjustedCloseCoverage: adjustment.adjustedCloseCoverage,
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
    survivorshipBiasControlled: options.survivorshipBiasControlled === true,
    corporateActionsVerified: options.corporateActionsVerified === true,
    safety: { ...PHASE40_SAFETY },
  };
}

export function buildBacktestReadyCandles(dataset, audit) {
  if (!audit?.canBacktest) throw new Error(`BLOCKED_HISTORICAL_DATA:${(audit?.blockers ?? []).join(",")}`);
  return (dataset?.rows ?? []).map((row) => {
    const factor = Number.isFinite(row.adjustmentFactor) && row.adjustmentFactor > 0 ? row.adjustmentFactor : 1;
    return {
      time: row.time,
      open: row.open * factor,
      high: row.high * factor,
      low: row.low * factor,
      close: Number.isFinite(row.adjustedClose) && row.adjustedClose > 0 ? row.adjustedClose : row.close,
      volume: row.volume,
      adjustedCloseProvided: Number.isFinite(row.adjustedClose) && row.adjustedClose > 0,
      sourceClose: row.close,
      adjustmentFactor: factor,
    };
  });
}

export function runPhase40HistoricalDataFoundation(input = {}) {
  const dataset = normalizeHistoricalRows(input);
  const audit = auditHistoricalDataQuality(dataset, input.options ?? {});
  const candles = audit.canBacktest ? buildBacktestReadyCandles(dataset, audit) : [];
  return {
    status: audit.canBacktest ? "READY_FOR_BATCH_BACKTEST" : "BLOCKED",
    dataset,
    audit,
    candles,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE40_SAFETY },
  };
}

export { PHASE40_SAFETY };
