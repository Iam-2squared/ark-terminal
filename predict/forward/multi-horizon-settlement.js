export const MULTI_HORIZON_SETTLEMENT_VERSION = "phase25-multi-horizon-settlement-v1";

const DEFAULT_HORIZONS = Object.freeze([1, 3, 5, 10, 20]);
const finite = (value) => Number.isFinite(Number(value));

function normalizeHorizon(value) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function normalizeDate(value) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

export function buildSettlementSchedule(prediction = {}, horizons = DEFAULT_HORIZONS) {
  const createdAt = normalizeDate(prediction.createdAt ?? prediction.marketDate ?? prediction.timestamp);
  const normalizedHorizons = [...new Set((Array.isArray(horizons) ? horizons : DEFAULT_HORIZONS)
    .map(normalizeHorizon)
    .filter((value) => value !== null))].sort((a, b) => a - b);

  return normalizedHorizons.map((horizon) => ({
    horizon,
    dueAt: createdAt ? addDays(createdAt, horizon).toISOString() : null,
    status: "PENDING",
  }));
}

export function settlePredictionHorizons({ prediction = {}, prices = {}, asOf, feePercent = 0.1, slippagePercent = 0.15 } = {}) {
  const entryPrice = finite(prediction.entryPrice ?? prediction.price) ? Number(prediction.entryPrice ?? prediction.price) : null;
  const action = String(prediction.signal ?? prediction.action ?? "").toUpperCase();
  const asOfDate = normalizeDate(asOf);
  const schedule = buildSettlementSchedule(prediction, Object.keys(prices));

  return schedule.map((item) => {
    const targetPrice = finite(prices[item.horizon]) ? Number(prices[item.horizon]) : null;
    const dueDate = normalizeDate(item.dueAt);
    const isDue = Boolean(asOfDate && dueDate && asOfDate >= dueDate);

    if (!isDue || entryPrice === null || targetPrice === null || !["BUY", "SELL"].includes(action)) {
      return { ...item, status: "PENDING", targetPrice };
    }

    const directionalGross = action === "BUY"
      ? ((targetPrice - entryPrice) / entryPrice) * 100
      : ((entryPrice - targetPrice) / entryPrice) * 100;
    const totalCost = Number(feePercent) + Number(slippagePercent);
    const netReturnPercent = directionalGross - totalCost;

    return {
      ...item,
      status: "RESOLVED",
      entryPrice,
      targetPrice,
      grossReturnPercent: directionalGross,
      netReturnPercent,
      success: netReturnPercent > 0,
      costs: { feePercent: Number(feePercent), slippagePercent: Number(slippagePercent), totalPercent: totalCost },
    };
  });
}

export default settlePredictionHorizons;
