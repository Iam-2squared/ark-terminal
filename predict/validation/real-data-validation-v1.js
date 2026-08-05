import { runBacktestForwardValidationV2 } from "./backtest-forward-validation-v2.js";

export const REAL_DATA_VALIDATION_V1 = "real-data-validation-v1";

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalizeRecord(record = {}, index = 0) {
  const timestamp = record.timestamp ?? record.date ?? record.datetime ?? null;
  const parsedTime = timestamp ? Date.parse(timestamp) : Number.NaN;
  return {
    ...record,
    __index: index,
    symbol: String(record.symbol ?? record.ticker ?? "").trim(),
    timestamp: Number.isFinite(parsedTime) ? new Date(parsedTime).toISOString() : null,
    close: finite(record.close ?? record.adjustedClose ?? record.price),
    volume: finite(record.volume),
  };
}

function auditDataset(records = [], { minimumRecords = 250, minimumSymbols = 1 } = {}) {
  const normalized = (Array.isArray(records) ? records : []).map(normalizeRecord);
  const valid = normalized.filter((record) =>
    record.symbol &&
    record.timestamp &&
    record.close !== null &&
    record.close > 0,
  );

  const symbols = [...new Set(valid.map((record) => record.symbol))];
  const duplicateKeys = new Set();
  const seen = new Set();
  for (const record of valid) {
    const key = `${record.symbol}:${record.timestamp}`;
    if (seen.has(key)) duplicateKeys.add(key);
    seen.add(key);
  }

  const sorted = [...valid].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const start = sorted[0]?.timestamp ?? null;
  const end = sorted.at(-1)?.timestamp ?? null;
  const blockers = [];
  if (valid.length < minimumRecords) blockers.push("INSUFFICIENT_RECORDS");
  if (symbols.length < minimumSymbols) blockers.push("INSUFFICIENT_SYMBOLS");
  if (duplicateKeys.size > 0) blockers.push("DUPLICATE_SYMBOL_TIMESTAMP");
  if (valid.length !== normalized.length) blockers.push("INVALID_RECORDS_PRESENT");

  return {
    inputCount: normalized.length,
    validCount: valid.length,
    invalidCount: normalized.length - valid.length,
    symbolCount: symbols.length,
    symbols,
    duplicateCount: duplicateKeys.size,
    period: { start, end },
    ready: blockers.length === 0,
    blockers,
    records: sorted,
  };
}

function groupBySymbol(records = []) {
  const groups = new Map();
  for (const record of records) {
    if (!groups.has(record.symbol)) groups.set(record.symbol, []);
    groups.get(record.symbol).push(record);
  }
  return groups;
}

export async function runRealDataValidation({
  records = [],
  candidateModel,
  productionBaseline,
  evaluator,
  splitterOptions = {},
  thresholds = {},
  datasetRules = {},
  source = {},
  futureLeakChecked = false,
} = {}) {
  if (typeof evaluator !== "function") throw new TypeError("evaluator must be a function");
  const dataset = auditDataset(records, datasetRules);
  const sourceVerified = Boolean(source.provider && source.datasetId && source.retrievedAt);
  const symbolReports = [];

  if (dataset.ready && sourceVerified) {
    for (const [symbol, symbolRecords] of groupBySymbol(dataset.records)) {
      const validation = await runBacktestForwardValidationV2({
        records: symbolRecords,
        candidateModel,
        productionBaseline,
        evaluator,
        splitterOptions,
        thresholds,
        futureLeakChecked,
      });
      symbolReports.push({ symbol, recordCount: symbolRecords.length, validation });
    }
  }

  const validatedSymbols = symbolReports.filter((report) => report.validation.outOfSample === true);
  const blockers = [
    ...dataset.blockers,
    ...(!sourceVerified ? ["SOURCE_PROVENANCE_REQUIRED"] : []),
    ...(dataset.ready && sourceVerified && validatedSymbols.length === 0
      ? ["NO_OUT_OF_SAMPLE_SYMBOL_REPORT"]
      : []),
  ];

  return {
    version: REAL_DATA_VALIDATION_V1,
    generatedAt: new Date().toISOString(),
    source: {
      provider: source.provider ?? null,
      datasetId: source.datasetId ?? null,
      retrievedAt: source.retrievedAt ?? null,
      adjustedPrices: source.adjustedPrices === true,
      verified: sourceVerified,
    },
    dataset: {
      inputCount: dataset.inputCount,
      validCount: dataset.validCount,
      invalidCount: dataset.invalidCount,
      symbolCount: dataset.symbolCount,
      symbols: dataset.symbols,
      duplicateCount: dataset.duplicateCount,
      period: dataset.period,
      ready: dataset.ready,
    },
    symbols: symbolReports,
    summary: {
      evaluatedSymbols: symbolReports.length,
      outOfSampleSymbols: validatedSymbols.length,
      promotableSymbols: symbolReports.filter((report) =>
        report.validation.status === "PROMOTABLE_REQUIRES_HUMAN_APPROVAL",
      ).length,
    },
    ready: blockers.length === 0,
    status: blockers.length === 0 ? "VALIDATED" : "BLOCKED",
    blockers,
    safety: {
      futureLeakChecked: futureLeakChecked === true,
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerExecutionAllowed: false,
    },
  };
}

export default runRealDataValidation;
