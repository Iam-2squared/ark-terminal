function finiteNumber(
  value,
  fallback = NaN,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function normalizeDate(value) {
  if (!value) {
    return null;
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return null;
  }

  return date
    .toISOString()
    .slice(0, 10);
}

export function normalizeMarketHistoryRow(
  row = {},
) {
  const close =
    finiteNumber(
      row.close ??
      row.Close ??
      row.price ??
      row.adjustedClose ??
      row.adjClose,
    );

  const open =
    finiteNumber(
      row.open ??
      row.Open,
      close,
    );

  const high =
    finiteNumber(
      row.high ??
      row.High,
      close,
    );

  const low =
    finiteNumber(
      row.low ??
      row.Low,
      close,
    );

  const volume =
    Math.max(
      0,
      finiteNumber(
        row.volume ??
        row.Volume,
        0,
      ),
    );

  return {
    date:
      normalizeDate(
        row.date ??
        row.Date ??
        row.timestamp ??
        row.datetime,
      ),

    symbol:
      row.symbol ??
      row.ticker ??
      null,

    open,

    high,

    low,

    close,

    volume,

    features:
      row.features ??
      {},
  };
}

export function adaptMarketHistory({
  rows = [],
  symbol = null,
} = {}) {
  const safeRows =
    Array.isArray(rows)
      ? rows
      : [];

  const normalized =
    safeRows
      .map(
        normalizeMarketHistoryRow,
      )
      .map(
        (row) => ({
          ...row,

          symbol:
            row.symbol ??
            symbol,
        }),
      )
      .filter(
        (row) =>
          row.date &&
          Number.isFinite(
            row.close,
          ) &&
          row.close > 0,
      )
      .sort(
        (
          first,
          second,
        ) =>
          new Date(
            first.date,
          ) -
          new Date(
            second.date,
          ),
      );

  const uniqueByDate =
    new Map();

  for (
    const row of normalized
  ) {
    uniqueByDate.set(
      row.date,
      row,
    );
  }

  return [
    ...uniqueByDate.values(),
  ];
}

export function validateMarketHistory({
  rows = [],
  minimumRows = 30,
} = {}) {
  const adapted =
    adaptMarketHistory({
      rows,
    });

  const errors = [];
  const warnings = [];

  if (
    adapted.length <
    minimumRows
  ) {
    errors.push(
      "insufficient_rows",
    );
  }

  for (
    let index = 1;
    index < adapted.length;
    index++
  ) {
    const previous =
      adapted[index - 1];

    const current =
      adapted[index];

    if (
      new Date(
        current.date,
      ) <=
      new Date(
        previous.date,
      )
    ) {
      errors.push(
        "dates_not_strictly_increasing",
      );

      break;
    }
  }

  const missingVolume =
    adapted.filter(
      (row) =>
        !row.volume,
    ).length;

  if (
    adapted.length > 0 &&
    missingVolume /
    adapted.length >
    0.5
  ) {
    warnings.push(
      "volume_data_sparse",
    );
  }

  return {
    valid:
      errors.length === 0,

    rowCount:
      adapted.length,

    firstDate:
      adapted[0]?.date ??
      null,

    lastDate:
      adapted.at(-1)
        ?.date ??
      null,

    errors:
      [...new Set(errors)],

    warnings:
      [...new Set(warnings)],

    rows:
      adapted,
  };
}

export function buildAuditRows({
  rows = [],
  symbol = null,
  featureBuilder,
} = {}) {
  const adapted =
    adaptMarketHistory({
      rows,
      symbol,
    });

  return adapted.map(
    (
      row,
      index,
    ) => {
      const visibleRows =
        adapted.slice(
          0,
          index + 1,
        );

      const features =
        typeof featureBuilder ===
        "function"
          ? featureBuilder({
              row,
              index,
              history:
                visibleRows,
            })
          : row.features;

      return {
        date:
          row.date,

        symbol:
          row.symbol,

        close:
          row.close,

        features:
          features ?? {},

        market: {
          open:
            row.open,

          high:
            row.high,

          low:
            row.low,

          volume:
            row.volume,
        },
      };
    },
  );
}

export const AccuracyAuditDataAdapterInternals = {
  finiteNumber,
  normalizeDate,
};