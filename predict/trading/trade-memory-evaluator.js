function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function toTimestamp(value) {
  if (!finite(value)) {
    return null;
  }

  const numeric = Number(value);

  return numeric < 10_000_000_000
    ? numeric * 1000
    : numeric;
}

function normalizeBar(bar) {
  const time =
    toTimestamp(
      bar?.time ??
      bar?.timestamp ??
      bar?.date,
    );

  const open =
    finite(bar?.open)
      ? Number(bar.open)
      : null;

  const high =
    finite(bar?.high)
      ? Number(bar.high)
      : null;

  const low =
    finite(bar?.low)
      ? Number(bar.low)
      : null;

  const close =
    finite(bar?.close)
      ? Number(bar.close)
      : null;

  if (
    time === null ||
    open === null ||
    high === null ||
    low === null ||
    close === null
  ) {
    return null;
  }

  return {
    time,
    open,
    high,
    low,
    close,
  };
}

function percentChange(from, to) {
  if (
    !finite(from) ||
    !finite(to) ||
    Number(from) === 0
  ) {
    return null;
  }

  return (
    (
      Number(to) -
      Number(from)
    ) /
    Number(from)
  ) * 100;
}

function outcomeLabel(reason, returnPercent) {
  if (reason === "first_target") {
    return "第一利確到達";
  }

  if (reason === "second_target") {
    return "第二利確到達";
  }

  if (reason === "stop") {
    return "損切り到達";
  }

  if (finite(returnPercent)) {
    if (returnPercent > 0) {
      return "期間終了・利益";
    }

    if (returnPercent < 0) {
      return "期間終了・損失";
    }
  }

  return "期間終了・変化なし";
}

function resolveExitWithinBar({
  bar,
  stopPrice,
  firstTargetPrice,
  secondTargetPrice,
}) {
  const stopHit =
    finite(stopPrice) &&
    bar.low <= Number(stopPrice);

  const secondTargetHit =
    finite(secondTargetPrice) &&
    bar.high >= Number(secondTargetPrice);

  const firstTargetHit =
    finite(firstTargetPrice) &&
    bar.high >= Number(firstTargetPrice);

  /*
   * 日足・15分足だけでは同じ足の中の到達順を断定できない。
   * ストップと利確が同じ足で両方到達した場合は、
   * 過大評価を避けるため保守的にストップを優先する。
   */
  if (stopHit) {
    return {
      reason: "stop",
      exitPrice: Number(stopPrice),
      hit: false,
    };
  }

  if (secondTargetHit) {
    return {
      reason: "second_target",
      exitPrice: Number(secondTargetPrice),
      hit: true,
    };
  }

  if (firstTargetHit) {
    return {
      reason: "first_target",
      exitPrice: Number(firstTargetPrice),
      hit: true,
    };
  }

  return null;
}

export function evaluateTradeMemoryRecord(
  record,
  bars,
  options = {},
) {
  if (
    !record ||
    record.status !== "pending"
  ) {
    return {
      record,
      evaluated: false,
      reason: "not_pending",
    };
  }

  if (
    record.decision !== "approve"
  ) {
    return {
      record,
      evaluated: false,
      reason: "not_approved",
    };
  }

  const entryPrice =
    finite(record.entryPrice)
      ? Number(record.entryPrice)
      : finite(record.candidatePrice)
        ? Number(record.candidatePrice)
        : null;

  if (
    entryPrice === null ||
    entryPrice <= 0
  ) {
    return {
      record,
      evaluated: false,
      reason: "missing_entry_price",
    };
  }

  const signalTime =
    toTimestamp(
      record.signalTime ??
      record.createdAt,
    );

  const normalizedBars =
    (Array.isArray(bars) ? bars : [])
      .map(normalizeBar)
      .filter(Boolean)
      .filter(
        (bar) =>
          signalTime === null ||
          bar.time > signalTime,
      )
      .sort(
        (first, second) =>
          first.time - second.time,
      );

  const maximumBars =
    Number.isInteger(
      options.maximumBars,
    )
      ? Math.max(
          1,
          options.maximumBars,
        )
      : 20;

  const evaluationBars =
    normalizedBars.slice(
      0,
      maximumBars,
    );

  if (!evaluationBars.length) {
    return {
      record,
      evaluated: false,
      reason: "no_future_bars",
    };
  }

  let maximumHigh =
    entryPrice;

  let minimumLow =
    entryPrice;

  let exit = null;
  let exitBar = null;

  for (
    const bar of evaluationBars
  ) {
    maximumHigh =
      Math.max(
        maximumHigh,
        bar.high,
      );

    minimumLow =
      Math.min(
        minimumLow,
        bar.low,
      );

    const resolved =
      resolveExitWithinBar({
        bar,

        stopPrice:
          record.stopPrice,

        firstTargetPrice:
          record.firstTargetPrice,

        secondTargetPrice:
          record.secondTargetPrice,
      });

    if (resolved) {
      exit = resolved;
      exitBar = bar;
      break;
    }
  }

  const finalBar =
    exitBar ??
    evaluationBars[
      evaluationBars.length - 1
    ];

  const exitPrice =
    exit?.exitPrice ??
    finalBar.close;

  const actualReturnPercent =
    percentChange(
      entryPrice,
      exitPrice,
    );

  const maximumFavorableMovePercent =
    percentChange(
      entryPrice,
      maximumHigh,
    );

  const maximumAdverseMovePercent =
    percentChange(
      entryPrice,
      minimumLow,
    );

  const reason =
    exit?.reason ??
    "horizon_end";

  const hit =
    exit?.hit ??
    (
      finite(actualReturnPercent) &&
      actualReturnPercent > 0
    );

  const evaluatedAt =
    new Date(
      finalBar.time,
    ).toISOString();

  const resolvedRecord = {
    ...record,

    status: "resolved",

    outcome:
      outcomeLabel(
        reason,
        actualReturnPercent,
      ),

    evaluation: {
      evaluatedAt,

      exitTime:
        finalBar.time,

      exitReason:
        reason,

      barsEvaluated:
        evaluationBars.length,

      exitPrice,

      actualReturnPercent,

      maximumFavorableMovePercent,

      maximumAdverseMovePercent,

      hit,
    },
  };

  return {
    record: resolvedRecord,
    evaluated: true,
    reason,
  };
}

export function resolvePendingTradeMemory(
  records,
  barsBySymbol,
  options = {},
) {
  const safeRecords =
    Array.isArray(records)
      ? records
      : [];

  const resolved = [];
  const unchanged = [];

  const updatedRecords =
    safeRecords.map((record) => {
      const symbol =
        String(
          record?.symbol || "",
        ).toUpperCase();

      const bars =
        barsBySymbol instanceof Map
          ? barsBySymbol.get(symbol)
          : barsBySymbol?.[symbol];

      const result =
        evaluateTradeMemoryRecord(
          record,
          bars,
          options,
        );

      if (result.evaluated) {
        resolved.push(
          result.record,
        );

        return result.record;
      }

      unchanged.push({
        id: record?.id,
        symbol,
        reason: result.reason,
      });

      return record;
    });

  return {
    records:
      updatedRecords,

    resolved,

    unchanged,

    resolvedCount:
      resolved.length,

    pendingCount:
      updatedRecords.filter(
        (record) =>
          record?.status === "pending",
      ).length,
  };
}

export const TradeMemoryEvaluatorInternals = {
  finite,
  normalizeBar,
  outcomeLabel,
  percentChange,
  resolveExitWithinBar,
  toTimestamp,
};