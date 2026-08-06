export const CORPORATE_ACTIONS_VERSION = "corporate-actions-v1";

function finite(value) {
  return Number.isFinite(Number(value));
}

function dateKey(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new TypeError("invalid date");
  return date.toISOString().slice(0, 10);
}

function normalizeAction(action = {}) {
  const type = String(action.type ?? "").trim().toUpperCase();
  const effectiveDate = dateKey(action.effectiveDate ?? action.date);
  if (!["SPLIT", "REVERSE_SPLIT", "DIVIDEND", "RIGHTS"].includes(type)) {
    throw new TypeError(`unsupported corporate action: ${type}`);
  }

  if (["SPLIT", "REVERSE_SPLIT"].includes(type)) {
    const ratio = Number(action.ratio);
    if (!finite(ratio) || ratio <= 0) throw new TypeError("split ratio must be positive");
    return { type, effectiveDate, ratio };
  }

  const cashAmount = Number(action.cashAmount ?? action.amount ?? 0);
  if (!finite(cashAmount) || cashAmount < 0) throw new TypeError("cash amount must be non-negative");
  return { type, effectiveDate, cashAmount };
}

export function buildCorporateActionLedger(actions = []) {
  const normalized = actions.map(normalizeAction).sort((a, b) => a.effectiveDate.localeCompare(b.effectiveDate));

  function actionsFor(symbol, throughDate) {
    const target = dateKey(throughDate);
    return normalized.filter((action) => {
      const actionSymbol = String(action.symbol ?? symbol ?? "").toUpperCase();
      return (!action.symbol || actionSymbol === String(symbol ?? "").toUpperCase()) && action.effectiveDate <= target;
    });
  }

  function adjustmentFactor(symbol, throughDate) {
    return actionsFor(symbol, throughDate).reduce((factor, action) => {
      if (action.type === "SPLIT") return factor / action.ratio;
      if (action.type === "REVERSE_SPLIT") return factor * action.ratio;
      return factor;
    }, 1);
  }

  function adjustPrice({ symbol, price, date, throughDate }) {
    if (!finite(price)) throw new TypeError("price must be finite");
    const sourceDate = dateKey(date);
    const targetDate = dateKey(throughDate ?? date);
    if (sourceDate > targetDate) throw new RangeError("source date must not be after throughDate");
    const factor = normalized.reduce((current, action) => {
      if (action.effectiveDate <= sourceDate || action.effectiveDate > targetDate) return current;
      if (action.type === "SPLIT") return current / action.ratio;
      if (action.type === "REVERSE_SPLIT") return current * action.ratio;
      return current;
    }, 1);
    return Number(price) * factor;
  }

  function auditRow(row = {}, throughDate) {
    const issues = [];
    if (!row.symbol) issues.push("MISSING_SYMBOL");
    if (!row.date) issues.push("MISSING_DATE");
    if (!finite(row.close)) issues.push("INVALID_CLOSE");
    if (finite(row.adjustedClose) && finite(row.close)) {
      const expected = adjustPrice({ symbol: row.symbol, price: row.close, date: row.date, throughDate: throughDate ?? row.date });
      const actual = Number(row.adjustedClose);
      const relativeError = expected === 0 ? Math.abs(actual) : Math.abs((actual - expected) / expected);
      if (relativeError > 0.001) issues.push("ADJUSTED_CLOSE_MISMATCH");
    }
    return { valid: issues.length === 0, issues };
  }

  return Object.freeze({
    version: CORPORATE_ACTIONS_VERSION,
    actions: normalized,
    actionsFor,
    adjustmentFactor,
    adjustPrice,
    auditRow,
  });
}

export default buildCorporateActionLedger;
