function dateValue(value, endOfDay = false) {
  if (!value) return null;

  const suffix = endOfDay ? "T23:59:59.999Z" : "T00:00:00.000Z";
  const date = new Date(`${value}${suffix}`);

  return Number.isNaN(date.getTime()) ? null : date.getTime();
}

function recordDate(record) {
  const date = new Date(record.createdAt);

  return Number.isNaN(date.getTime()) ? null : date.getTime();
}

export function filterPredictionHistory(records, filters = {}) {
  const from = dateValue(filters.dateFrom);
  const to = dateValue(filters.dateTo, true);
  const symbol = String(filters.symbol || "").trim().toUpperCase();
  const result = filters.result || "all";
  const scope = filters.scope || "recent30";
  const ordered = [...records].sort(
    (first, second) => recordDate(second) - recordDate(first),
  );

  const filtered = ordered.filter((record) => {
    const createdAt = recordDate(record);
    const matchesSymbol =
      !symbol || String(record.symbol || "").toUpperCase() === symbol;
    const matchesResult =
      result === "all" ||
      (result === "success" &&
        record.status === "resolved" &&
        record.hit === true) ||
      (result === "failure" &&
        record.status === "resolved" &&
        record.hit === false);
    const matchesFrom = from === null || (createdAt !== null && createdAt >= from);
    const matchesTo = to === null || (createdAt !== null && createdAt <= to);

    return matchesSymbol && matchesResult && matchesFrom && matchesTo;
  });

  return scope === "recent30" ? filtered.slice(0, 30) : filtered;
}

export function paginatePredictionHistory(records, page = 1, pageSize = 50) {
  const safePageSize = Math.max(10, Math.min(200, Number(pageSize) || 50));
  const pageCount = Math.max(1, Math.ceil(records.length / safePageSize));
  const currentPage = Math.max(1, Math.min(pageCount, Number(page) || 1));
  const start = (currentPage - 1) * safePageSize;

  return {
    rows: records.slice(start, start + safePageSize),
    page: currentPage,
    pageSize: safePageSize,
    pageCount,
    total: records.length,
    start: records.length ? start + 1 : 0,
    end: Math.min(records.length, start + safePageSize),
  };
}

export function predictionSymbols(records) {
  return [...new Set(records.map((record) => record.symbol).filter(Boolean))]
    .sort((first, second) => String(first).localeCompare(String(second)));
}
