/**
 * Common MSII order-boundary primitives. Pure validation, no transport.
 * ISO timestamps are compared at 100 ns precision (PowerShell DateTime "o").
 * Date.parse alone normalizes impossible dates and discards sub-ms fractions.
 */
const fail = code => { throw Error(code); };
export const MSII_MAX_ORDER_ID = 2147483647;
export const NS_PER_MS = 1000000n;
const NS_PER_SECOND = 1000000000n;

export function validMsiiOrderId(value) {
  return Number.isSafeInteger(value) && value >= 1 && value <= MSII_MAX_ORDER_ID;
}

/** Never coerces strings, rounds IDs or silently deduplicates a source list. */
export function validateMsiiOrderIds(values, code, maximum = 5000) {
  if (!Array.isArray(values) || values.length > maximum) fail(code);
  const seen = new Set();
  for (const value of values) {
    if (!validMsiiOrderId(value) || seen.has(value)) fail(code);
    seen.add(value);
  }
  return seen;
}

export function orderInstant(value, code, {jstOnly = false} = {}) {
  if (typeof value !== 'string') fail(code);
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,7}))?(Z|([+-])(\d{2}):(\d{2}))$/.exec(value);
  if (!match || (jstOnly && match[8] !== '+09:00')) fail(code);
  const [year, month, day, hour, minute, second] = match.slice(1, 7).map(Number);
  if (year < 2000 || year > 2099 || month < 1 || month > 12 ||
      day < 1 || hour > 23 || minute > 59 || second > 59) fail(code);
  const date = new Date(Date.UTC(year, month - 1, day, hour, minute, second));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 ||
      date.getUTCDate() !== day) fail(code);
  let offset = 0;
  if (match[8] !== 'Z') {
    const oh = Number(match[10]), om = Number(match[11]);
    // Supported real-world UTC offsets, with no invented 14:xx zone.
    if (oh > 14 || om > 59 || oh === 14 && om !== 0) fail(code);
    offset = (oh * 60 + om) * (match[9] === '+' ? 1 : -1);
  }
  const fraction = BigInt((match[7] || '').padEnd(9, '0'));
  const ns = BigInt(date.getTime() - offset * 60000) * NS_PER_MS + fraction;
  return {ns, epochMs: Number(ns / NS_PER_MS), localDay: value.slice(0, 10)};
}

export function currentOrderInstant(value, code) {
  if (value instanceof Date) {
    const ms = value.getTime();
    if (!Number.isSafeInteger(ms)) fail(code);
    return {ns: BigInt(ms) * NS_PER_MS, epochMs: ms};
  }
  return orderInstant(value, code);
}

/** Vendor time is seconds-only: permit floor(local origin), never an older second. */
export function vendorSecondAtOrAfterOrigin(vendor, origin) {
  return vendor.ns >= (origin.ns / NS_PER_SECOND) * NS_PER_SECOND;
}
