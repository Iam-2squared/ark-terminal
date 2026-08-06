export const RISK_GOVERNOR_VERSION = "phase27-risk-governor-v1";

const finite = (value) => Number.isFinite(Number(value));
const number = (value, fallback = 0) => finite(value) ? Number(value) : fallback;
const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;

function resolveLocalHour(value) {
  if (typeof value === "string") {
    const match = value.match(/T(\d{2}):\d{2}/);
    if (match) return Number(match[1]);
  }
  const date = new Date(value ?? Date.now());
  return Number.isNaN(date.getTime()) ? null : date.getHours();
}

export function evaluateRiskGovernor(input = {}, options = {}) {
  const symbol = normalize(input.symbol, "");
  const side = normalize(input.side ?? input.signal, "HOLD");
  const instrumentType = normalize(input.instrumentType, "CASH_EQUITY");
  const allowedSymbols = new Set((options.allowedSymbols ?? []).map((value) => normalize(value, "")));
  const localHour = resolveLocalHour(input.now);
  const startHour = number(options.startHour, 9);
  const endHour = number(options.endHour, 15);
  const blockers = [];

  const quantity = Math.max(0, Math.floor(number(input.quantity, 0)));
  const price = number(input.price ?? input.limitPrice, 0);
  const orderValue = quantity * price;
  const currentSymbolExposure = number(input.currentSymbolExposure, 0);
  const totalExposure = number(input.totalExposure, 0);
  const dailyLoss = number(input.dailyLoss, 0);
  const consecutiveLosses = number(input.consecutiveLosses, 0);
  const maxDrawdown = number(input.maxDrawdown, 0);
  const ordersToday = number(input.ordersToday, 0);

  const maxSymbolExposure = number(options.maxSymbolExposure, 50000);
  const maxTotalExposure = number(options.maxTotalExposure, 200000);
  const maxDailyLoss = number(options.maxDailyLoss, 5000);
  const maxConsecutiveLosses = number(options.maxConsecutiveLosses, 3);
  const maxDrawdownLimit = number(options.maxDrawdown, 10);
  const maxOrdersPerDay = number(options.maxOrdersPerDay, 3);

  if (!symbol) blockers.push("SYMBOL_MISSING");
  if (!["BUY", "SELL"].includes(side)) blockers.push("SIDE_NOT_DIRECTIONAL");
  if (instrumentType !== "CASH_EQUITY") blockers.push("CASH_EQUITY_ONLY");
  if (allowedSymbols.size && !allowedSymbols.has(symbol)) blockers.push("SYMBOL_NOT_ALLOWLISTED");
  if (!(quantity > 0) || !(price > 0)) blockers.push("ORDER_VALUE_INVALID");
  if (currentSymbolExposure + orderValue > maxSymbolExposure) blockers.push("SYMBOL_EXPOSURE_LIMIT");
  if (totalExposure + orderValue > maxTotalExposure) blockers.push("TOTAL_EXPOSURE_LIMIT");
  if (dailyLoss >= maxDailyLoss) blockers.push("DAILY_LOSS_LIMIT");
  if (consecutiveLosses >= maxConsecutiveLosses) blockers.push("CONSECUTIVE_LOSS_LIMIT");
  if (maxDrawdown >= maxDrawdownLimit) blockers.push("MAX_DRAWDOWN_LIMIT");
  if (ordersToday >= maxOrdersPerDay) blockers.push("DAILY_ORDER_COUNT_LIMIT");
  if (localHour === null) blockers.push("INVALID_TIME");
  else if (localHour < startHour || localHour >= endHour) blockers.push("OUTSIDE_TRADING_WINDOW");

  return {
    version: RISK_GOVERNOR_VERSION,
    status: blockers.length ? "BLOCKED" : "DRY_RUN_ALLOWED",
    blockers,
    metrics: {
      symbol,
      side,
      instrumentType,
      quantity,
      price,
      orderValue,
      currentSymbolExposure,
      totalExposure,
      dailyLoss,
      consecutiveLosses,
      maxDrawdown,
      ordersToday,
      localHour,
    },
    limits: {
      maxSymbolExposure,
      maxTotalExposure,
      maxDailyLoss,
      maxConsecutiveLosses,
      maxDrawdown: maxDrawdownLimit,
      maxOrdersPerDay,
      startHour,
      endHour,
    },
    safety: {
      mode: "DRY_RUN_ONLY",
      brokerWriteAllowed: false,
      liveTradingAllowed: false,
      leverageAllowed: false,
      shortSellingAllowed: false,
      marginTradingAllowed: false,
      humanApprovalRequired: true,
    },
  };
}

export default evaluateRiskGovernor;
