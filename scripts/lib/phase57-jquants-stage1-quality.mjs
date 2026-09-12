const TIME = /^(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?$/;

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

export function parseCsvLine(line) {
  const fields = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (quoted && line[index + 1] === '"') { field += '"'; index += 1; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) {
      fields.push(field); field = "";
    } else field += char;
  }
  if (quoted) throw new Error("UNCLOSED_CSV_QUOTE");
  fields.push(field);
  return fields;
}

export function minuteLabelFromTickTime(value) {
  const match = TIME.exec(String(value ?? ""));
  if (!match) throw new Error("INVALID_TICK_TIME");
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  const second = Number(match[3] ?? 0);
  if (hour > 23 || minute > 59 || second > 59) throw new Error("INVALID_TICK_TIME");
  return `${match[1]}:${match[2]}`;
}

export function addMinute(label, delta) {
  const match = /^(\d{2}):(\d{2})$/.exec(String(label));
  if (!match) throw new Error("INVALID_MINUTE_LABEL");
  const total = Number(match[1]) * 60 + Number(match[2]) + delta;
  if (total < 0 || total >= 24 * 60) throw new Error("MINUTE_LABEL_OVERFLOW");
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

export function aggregateTicksByMinute(rows) {
  const bins = new Map();
  for (const row of rows) {
    const time = minuteLabelFromTickTime(row.Time);
    if (!finite(row.Price) || !finite(row.TradingVolume)) throw new Error("INVALID_TICK_VALUE");
    const price = Number(row.Price);
    const volume = Number(row.TradingVolume);
    if (price <= 0 || volume < 0) throw new Error("INVALID_TICK_VALUE");
    const current = bins.get(time);
    if (!current) bins.set(time, { time, open: price, high: price, low: price, close: price, volume });
    else {
      current.high = Math.max(current.high, price);
      current.low = Math.min(current.low, price);
      current.close = price;
      current.volume += volume;
    }
  }
  return bins;
}

function sameOhlcv(minute, tick) {
  if (!minute || !tick) return false;
  return Number(minute.O) === tick.open && Number(minute.H) === tick.high &&
    Number(minute.L) === tick.low && Number(minute.C) === tick.close && Number(minute.Vo) === tick.volume;
}

export function compareTimestampHypotheses(minuteRows, tickRows, labels) {
  const minute = new Map(minuteRows.map((row) => [String(row.Time), row]));
  const tick = aggregateTicksByMinute(tickRows);
  const probes = labels.map((label) => ({
    label,
    tickObserved: tick.has(label),
    sameLabelMatch: sameOhlcv(minute.get(label), tick.get(label)),
    nextLabelMatch: sameOhlcv(minute.get(addMinute(label, 1)), tick.get(label)),
  }));
  const observed = probes.filter((probe) => probe.tickObserved);
  const sameMatches = observed.filter((probe) => probe.sameLabelMatch).length;
  const nextMatches = observed.filter((probe) => probe.nextLabelMatch).length;
  let conclusion = "UNRESOLVED";
  if (observed.length >= 3 && sameMatches === observed.length && nextMatches < sameMatches) {
    conclusion = "BAR_START_HALF_OPEN";
  } else if (observed.length >= 3 && nextMatches === observed.length && sameMatches < nextMatches) {
    conclusion = "BAR_END_RIGHT_CLOSED";
  }
  return { observedProbeCount: observed.length, sameMatches, nextMatches, conclusion, probes };
}

export function classifyMinuteAbsence({ listedAtSession, dailyRowPresent, dailyHasTrade, tickObserved, minuteObserved }) {
  if (minuteObserved) return "OBSERVED";
  if (!listedAtSession) return "NOT_LISTED_OR_OUT_OF_UNIVERSE";
  if (tickObserved) return "MISSING_PROVIDER_MINUTE";
  if (dailyRowPresent && dailyHasTrade) return "NO_TRADE_OR_PROVIDER_MISSING_UNKNOWN";
  if (dailyRowPresent && !dailyHasTrade) return "NO_TRADE_SUSPENDED_OR_UNKNOWN";
  return "UNKNOWN";
}

export function tierFromQuality(audit) {
  const pitViolationFree = audit.pitViolations === 0;
  const causal = audit.timestamp === "PASS" && audit.fiveMinuteAggregation === "PASS";
  if (causal && pitViolationFree && audit.universe === "PASS" && audit.adjustment === "PASS" &&
      audit.missing === "PASS" && audit.hybridParity === "PASS" && audit.entryParity === "PASS" &&
      audit.historicalProviderAvailableAt === "PASS") return "TIER_1_FULL_GOLDEN_REPLAY";
  if (causal && pitViolationFree && audit.universe !== "FAIL" && audit.adjustment !== "FAIL" &&
      audit.hybridParity !== "FAIL" && audit.entryParity !== "FAIL") return "TIER_2_RECONSTRUCTED_REPLAY_CANDIDATE";
  return "TIER_3_DIAGNOSTIC_ONLY";
}

export function classifyTickBulkScope(rows, sessionDate) {
  const compact = String(sessionDate).replaceAll("-", "");
  if (!/^\d{8}$/.test(compact)) throw new Error("INVALID_SESSION_DATE");
  const normalized = rows.map((row) => ({ key: String(row?.Key ?? row?.key ?? ""), size: Number(row?.Size ?? row?.size ?? 0) }));
  const daily = normalized.find((row) => row.key.includes(compact));
  if (daily) return { scope: "DAY", file: daily };
  const monthly = normalized.find((row) => row.key.includes(compact.slice(0, 6)));
  if (monthly) return { scope: "MONTH", file: monthly };
  return { scope: "UNKNOWN", file: null };
}
