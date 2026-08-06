export const TRADING_CALENDAR_VERSION = "trading-calendar-v1";

function toDateKey(value) {
  const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  if (Number.isNaN(date.getTime())) throw new TypeError("invalid date");
  return date.toISOString().slice(0, 10);
}

function toUtcDate(value) {
  const key = toDateKey(value);
  return new Date(`${key}T00:00:00.000Z`);
}

export function buildTradingCalendar({ holidays = [], specialClosures = [], halfDays = [] } = {}) {
  const holidaySet = new Set(holidays.map(toDateKey));
  const closureSet = new Set(specialClosures.map(toDateKey));
  const halfDaySet = new Set(halfDays.map(toDateKey));

  function isTradingDay(value) {
    const date = toUtcDate(value);
    const day = date.getUTCDay();
    const key = toDateKey(date);
    if (day === 0 || day === 6) return false;
    if (holidaySet.has(key) || closureSet.has(key)) return false;
    return true;
  }

  function sessionType(value) {
    const key = toDateKey(value);
    if (!isTradingDay(key)) return "CLOSED";
    return halfDaySet.has(key) ? "HALF_DAY" : "FULL_DAY";
  }

  function nextTradingDay(value, step = 1) {
    const direction = step >= 0 ? 1 : -1;
    let remaining = Math.max(1, Math.abs(Number(step) || 1));
    const cursor = toUtcDate(value);
    while (remaining > 0) {
      cursor.setUTCDate(cursor.getUTCDate() + direction);
      if (isTradingDay(cursor)) remaining -= 1;
    }
    return toDateKey(cursor);
  }

  function tradingDaysBetween(start, end, { inclusive = false } = {}) {
    const left = toUtcDate(start);
    const right = toUtcDate(end);
    const direction = left <= right ? 1 : -1;
    const cursor = new Date(left.getTime());
    const days = [];

    if (inclusive && isTradingDay(cursor)) days.push(toDateKey(cursor));
    while ((direction > 0 && cursor < right) || (direction < 0 && cursor > right)) {
      cursor.setUTCDate(cursor.getUTCDate() + direction);
      if (cursor.getTime() === right.getTime() && !inclusive) break;
      if (isTradingDay(cursor)) days.push(toDateKey(cursor));
    }
    return direction > 0 ? days : days.reverse();
  }

  return Object.freeze({
    version: TRADING_CALENDAR_VERSION,
    isTradingDay,
    sessionType,
    nextTradingDay,
    tradingDaysBetween,
    metadata: Object.freeze({
      holidays: [...holidaySet].sort(),
      specialClosures: [...closureSet].sort(),
      halfDays: [...halfDaySet].sort(),
    }),
  });
}

export default buildTradingCalendar;
