import {
  calculateAccuracyMetrics,
} from "./accuracy-metrics.js";

function parseTimestamp(row) {
  const candidates = [
    row?.timestamp,
    row?.date,
    row?.createdAt,
    row?.evaluatedAt,
    row?.executedAt,
    row?.result?.timestamp,
  ];

  for (const candidate of candidates) {
    if (candidate instanceof Date) {
      if (!Number.isNaN(candidate.getTime())) {
        return candidate;
      }
    }

    if (
      typeof candidate === "string" ||
      typeof candidate === "number"
    ) {
      const date = new Date(candidate);

      if (!Number.isNaN(date.getTime())) {
        return date;
      }
    }
  }

  return null;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function dayKey(date) {
  return [
    date.getUTCFullYear(),
    pad(date.getUTCMonth() + 1),
    pad(date.getUTCDate()),
  ].join("-");
}

function monthKey(date) {
  return [
    date.getUTCFullYear(),
    pad(date.getUTCMonth() + 1),
  ].join("-");
}

function weekKey(date) {
  const working = new Date(
    Date.UTC(
      date.getUTCFullYear(),
      date.getUTCMonth(),
      date.getUTCDate(),
    ),
  );

  const day = working.getUTCDay() || 7;
  working.setUTCDate(working.getUTCDate() + 4 - day);

  const yearStart = new Date(
    Date.UTC(working.getUTCFullYear(), 0, 1),
  );

  const week = Math.ceil(
    ((working - yearStart) / 86400000 + 1) / 7,
  );

  return `${working.getUTCFullYear()}-W${pad(week)}`;
}

function readSymbol(row) {
  return String(
    row?.symbol ??
      row?.ticker ??
      row?.code ??
      row?.instrument ??
      "UNKNOWN",
  ).trim() || "UNKNOWN";
}

function readSignal(row) {
  return String(
    row?.signal ??
      row?.prediction ??
      row?.action ??
      row?.decision ??
      "UNKNOWN",
  ).toUpperCase();
}

function readConfidence(row) {
  const number = Number(
    row?.confidence ??
      row?.confidenceScore ??
      row?.probability,
  );

  if (!Number.isFinite(number)) {
    return 0;
  }

  return Math.max(
    0,
    Math.min(1, number > 1 ? number / 100 : number),
  );
}

function confidenceKey(row) {
  const confidence = readConfidence(row);

  if (confidence < 0.4) {
    return "0.00-0.39";
  }

  if (confidence < 0.6) {
    return "0.40-0.59";
  }

  if (confidence < 0.8) {
    return "0.60-0.79";
  }

  return "0.80-1.00";
}

function readWalkForwardWindow(row) {
  return String(
    row?.walkForwardWindow ??
      row?.window ??
      row?.windowId ??
      row?.fold ??
      row?.features?.walkForwardWindow ??
      "UNKNOWN",
  );
}

function groupRows(rows, keySelector) {
  const groups = new Map();

  for (const row of rows) {
    const key = keySelector(row);

    if (!groups.has(key)) {
      groups.set(key, []);
    }

    groups.get(key).push(row);
  }

  return Object.fromEntries(
    [...groups.entries()]
      .sort(([left], [right]) =>
        String(left).localeCompare(String(right)),
      )
      .map(([key, values]) => [
        key,
        calculateAccuracyMetrics(values),
      ]),
  );
}

export function aggregatePeriodPerformance(rows = []) {
  if (!Array.isArray(rows)) {
    throw new TypeError("rows must be an array");
  }

  const datedRows = rows
    .map((row) => ({
      row,
      date: parseTimestamp(row),
    }))
    .filter((entry) => entry.date);

  return {
    overall: calculateAccuracyMetrics(rows),

    daily: groupRows(
      datedRows.map((entry) => entry.row),
      (row) => dayKey(parseTimestamp(row)),
    ),

    weekly: groupRows(
      datedRows.map((entry) => entry.row),
      (row) => weekKey(parseTimestamp(row)),
    ),

    monthly: groupRows(
      datedRows.map((entry) => entry.row),
      (row) => monthKey(parseTimestamp(row)),
    ),

    bySymbol: groupRows(rows, readSymbol),
    bySignal: groupRows(rows, readSignal),
    byConfidence: groupRows(rows, confidenceKey),
    byWalkForwardWindow: groupRows(
      rows,
      readWalkForwardWindow,
    ),

    metadata: {
      totalRows: rows.length,
      datedRows: datedRows.length,
      undatedRows: rows.length - datedRows.length,
    },
  };
}

export default aggregatePeriodPerformance;
