export const INTRADAY_MARKET_VERSION =
  "intraday-market-data-v2";

export const INTRADAY_INTERVAL_SECONDS = 15 * 60;

export const DEFAULT_INTRADAY_POLICY = Object.freeze({
  minimumSessionBars: 4,
  minimumHistoryBars: 21,

  volumeLookback: 20,
  volumeLookbackSessions: 10,
  minimumVolumeBaselineSamples: 3,

  breakoutLookback: 20,
  atrPeriod: 14,

  volumeSurgeRatio: 1.8,
  breakoutBufferPercent: 0.05,
  vwapTolerancePercent: 0.3,

  maximumBarAgeSeconds: 20 * 60,
});

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function positive(value) {
  return finite(value) && Number(value) > 0;
}

function clamp(value, minimum, maximum) {
  return Math.min(
    maximum,
    Math.max(minimum, Number(value)),
  );
}

function average(values) {
  const usable = values
    .filter(finite)
    .map(Number);

  return usable.length
    ? usable.reduce(
        (sum, value) => sum + value,
        0,
      ) / usable.length
    : null;
}

export function normalizeIntradaySymbol(value) {
  const symbol = String(value || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");

  if (/^(?:\d{4}|\d{3}[A-Z])$/.test(symbol)) {
    return `${symbol}.T`;
  }

  return symbol;
}

export function intradaySessionDate(
  time,
  timeZone = "UTC",
) {
  if (!finite(time)) {
    return null;
  }

  const date = new Date(Number(time) * 1000);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  try {
    const parts = new Intl.DateTimeFormat(
      "en-US",
      {
        timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      },
    ).formatToParts(date);

    const values = Object.fromEntries(
      parts
        .filter((part) =>
          ["year", "month", "day"].includes(
            part.type,
          ),
        )
        .map((part) => [
          part.type,
          part.value,
        ]),
    );

    if (
      values.year &&
      values.month &&
      values.day
    ) {
      return `${values.year}-${values.month}-${values.day}`;
    }
  } catch {
    // 不明なタイムゾーンではUTCへフォールバックする。
  }

  return date.toISOString().slice(0, 10);
}

export function buildIntradayCandles(
  result = {},
  {
    nowSeconds = Math.floor(Date.now() / 1000),
  } = {},
) {
  const timestamps = result.timestamp || [];
  const quote =
    result.indicators?.quote?.[0] || {};
  const timeZone =
    result.meta?.exchangeTimezoneName ||
    result.meta?.timezone ||
    "UTC";

  const rows = timestamps.map(
    (time, index) => {
      const open = Number(quote.open?.[index]);
      const high = Number(quote.high?.[index]);
      const low = Number(quote.low?.[index]);
      const close = Number(quote.close?.[index]);
      const rawVolume =
        quote.volume?.[index];
      const volume = finite(rawVolume)
        ? Number(rawVolume)
        : null;

      if (
        !finite(time) ||
        !positive(open) ||
        !positive(high) ||
        !positive(low) ||
        !positive(close) ||
        high < low
      ) {
        return null;
      }

      return {
        time: Number(time),
        open,
        high,
        low,
        close,
        volume:
          finite(volume) && volume >= 0
            ? volume
            : null,
        sessionDate: intradaySessionDate(
          time,
          timeZone,
        ),
        isClosed:
          Number(time) +
            INTRADAY_INTERVAL_SECONDS <=
          Number(nowSeconds),
      };
    },
  );

  const candles = rows.filter(Boolean);

  return {
    candles,
    sourceRowCount: rows.length,
    droppedRowCount:
      rows.length - candles.length,
    closedRowCount: candles.filter(
      (candle) => candle.isClosed,
    ).length,
    volumeRowCount: candles.filter(
      (candle) => finite(candle.volume),
    ).length,
    timeZone,
  };
}

export function normalizeIntradayCandles(
  candles = [],
) {
  const byTime = new Map();

  candles.forEach((candle) => {
    const time = Number(candle?.time);
    const open = Number(candle?.open);
    const high = Number(candle?.high);
    const low = Number(candle?.low);
    const close = Number(candle?.close);
    const volume = finite(candle?.volume)
      ? Number(candle.volume)
      : null;

    if (
      !finite(time) ||
      !positive(open) ||
      !positive(high) ||
      !positive(low) ||
      !positive(close) ||
      high < low
    ) {
      return;
    }

    byTime.set(time, {
      ...candle,
      time,
      open,
      high,
      low,
      close,
      volume:
        finite(volume) && volume >= 0
          ? volume
          : null,
      sessionDate:
        candle.sessionDate ||
        intradaySessionDate(time),
      isClosed: candle.isClosed !== false,
    });
  });

  return Array.from(byTime.values()).sort(
    (first, second) =>
      first.time - second.time,
  );
}

export function selectLatestClosedSession(
  candles = [],
) {
  const normalized =
    normalizeIntradayCandles(candles);

  const closed = normalized.filter(
    (candle) => candle.isClosed,
  );

  if (!closed.length) {
    return [];
  }

  const latestSession =
    closed.at(-1).sessionDate;

  return closed.filter(
    (candle) =>
      candle.sessionDate === latestSession,
  );
}

export function calculateIntradayVwapSeries(
  candles = [],
) {
  let cumulativePriceVolume = 0;
  let cumulativeVolume = 0;

  return candles.map((candle) => {
    const typicalPrice =
      (Number(candle.high) +
        Number(candle.low) +
        Number(candle.close)) /
      3;

    if (
      finite(candle.volume) &&
      Number(candle.volume) > 0
    ) {
      cumulativePriceVolume +=
        typicalPrice *
        Number(candle.volume);

      cumulativeVolume +=
        Number(candle.volume);
    }

    return {
      ...candle,
      vwap:
        cumulativeVolume > 0
          ? cumulativePriceVolume /
            cumulativeVolume
          : null,
    };
  });
}

export function calculateIntradayAtr(
  candles = [],
  period = 14,
) {
  if (candles.length < 2) {
    return null;
  }

  const ranges = [];

  for (
    let index = 1;
    index < candles.length;
    index += 1
  ) {
    const current = candles[index];
    const previous = candles[index - 1];

    const trueRange = Math.max(
      Number(current.high) -
        Number(current.low),
      Math.abs(
        Number(current.high) -
          Number(previous.close),
      ),
      Math.abs(
        Number(current.low) -
          Number(previous.close),
      ),
    );

    if (finite(trueRange)) {
      ranges.push(trueRange);
    }
  }

  return average(
    ranges.slice(
      -Math.max(1, Number(period) || 14),
    ),
  );
}

export function calculateIntradayVolumeRatio(
  candles = [],
  lookback = 20,
) {
  if (candles.length < 2) {
    return null;
  }

  const latest = candles.at(-1);

  if (!finite(latest.volume)) {
    return null;
  }

  const previousVolumes = candles
    .slice(
      -Math.max(
        2,
        Number(lookback) + 1,
      ),
      -1,
    )
    .map((candle) => candle.volume)
    .filter(
      (value) =>
        finite(value) &&
        Number(value) > 0,
    );

  const baseline = average(previousVolumes);

  if (!positive(baseline)) {
    return null;
  }

  return (
    Number(latest.volume) /
    Number(baseline)
  );
}

export function calculateSessionAwareVolumeRatio(
  candles = [],
  {
    lookbackSessions = 10,
    minimumSamples = 3,
    fallbackLookback = 20,
  } = {},
) {
  const normalized =
    normalizeIntradayCandles(
      candles,
    ).filter(
      (candle) =>
        candle.isClosed !== false,
    );

  if (normalized.length < 2) {
    return {
      ratio: null,
      baseline: null,
      sampleCount: 0,
      source: "unavailable",
      sessionSlotIndex: null,
    };
  }

  const latest =
    normalized.at(-1);

  if (
    !finite(latest.volume) ||
    Number(latest.volume) < 0
  ) {
    return {
      ratio: null,
      baseline: null,
      sampleCount: 0,
      source: "unavailable",
      sessionSlotIndex: null,
    };
  }

  const rowsBySession =
    new Map();

  normalized.forEach((candle) => {
    const key =
      candle.sessionDate ||
      "unknown";

    if (!rowsBySession.has(key)) {
      rowsBySession.set(key, []);
    }

    rowsBySession
      .get(key)
      .push(candle);
  });

  const latestSessionRows =
    rowsBySession.get(
      latest.sessionDate,
    ) || [];

  const sessionSlotIndex =
    latestSessionRows.findIndex(
      (candle) =>
        Number(candle.time) ===
        Number(latest.time),
    );

  const priorSessionDates =
    Array.from(
      rowsBySession.keys(),
    )
      .filter(
        (date) =>
          date !==
          latest.sessionDate,
      )
      .slice(
        -Math.max(
          1,
          Number(
            lookbackSessions,
          ) || 10,
        ),
      );

  const sameSlotVolumes =
    sessionSlotIndex >= 0
      ? priorSessionDates
          .map((date) => {
            const row =
              rowsBySession
                .get(date)
                ?.[sessionSlotIndex];

            return row?.volume;
          })
          .filter(
            (value) =>
              finite(value) &&
              Number(value) > 0,
          )
      : [];

  const requiredSamples =
    Math.max(
      1,
      Number(minimumSamples) || 3,
    );

  let baselineValues =
    sameSlotVolumes;

  let source =
    "same_session_slot";

  if (
    baselineValues.length <
    requiredSamples
  ) {
    baselineValues =
      normalized
        .slice(
          -Math.max(
            2,
            Number(
              fallbackLookback,
            ) + 1,
          ),
          -1,
        )
        .map(
          (candle) =>
            candle.volume,
        )
        .filter(
          (value) =>
            finite(value) &&
            Number(value) > 0,
        );

    source =
      "recent_closed_bars";
  }

  const baseline =
    average(baselineValues);

  if (!positive(baseline)) {
    return {
      ratio: null,
      baseline: null,
      sampleCount:
        baselineValues.length,
      source: "unavailable",
      sessionSlotIndex,
    };
  }

  return {
    ratio:
      Number(latest.volume) /
      Number(baseline),

    baseline:
      Number(baseline),

    sampleCount:
      baselineValues.length,

    source,
    sessionSlotIndex,
  };
}

function calculateDataQuality({
  sourceCandles,
  normalizedCandles,
  sessionCandles,
  stale,
}) {
  const sourceCount = Math.max(
    1,
    sourceCandles.length,
  );

  const validRatio =
    normalizedCandles.length / sourceCount;

  const volumeCoverage =
    sessionCandles.length > 0
      ? sessionCandles.filter(
          (candle) =>
            finite(candle.volume),
        ).length /
        sessionCandles.length
      : 0;

  const freshnessScore = stale ? 0 : 10;

  return Math.round(
    clamp(
      validRatio * 60 +
        volumeCoverage * 30 +
        freshnessScore,
      0,
      100,
    ),
  );
}

function calculateSetupStrength({
  breakout,
  volumeSurge,
  vwapAligned,
  reclaim,
  pullback,
  stale,
}) {
  let score = 35;

  if (breakout) {
    score += 25;
  }

  if (volumeSurge) {
    score += 15;
  }

  if (vwapAligned) {
    score += 10;
  }

  if (reclaim) {
    score += 10;
  }

  if (pullback) {
    score += 10;
  }

  if (stale) {
    score -= 50;
  }

  return Math.round(clamp(score, 0, 95));
}

export function analyzeIntradayMarket(
  candles = [],
  {
    nowSeconds = Math.floor(
      Date.now() / 1000,
    ),
    policy = {},
  } = {},
) {
  const resolvedPolicy = {
    ...DEFAULT_INTRADAY_POLICY,
    ...(policy || {}),
  };

  const normalized =
    normalizeIntradayCandles(candles);

  const closedCandles =
    normalized.filter(
      (candle) =>
        candle.isClosed !== false,
    );

  const sessionCandles =
    selectLatestClosedSession(
      closedCandles,
    );

  const minimumSessionBars =
    Math.max(
      2,
      Number(
        resolvedPolicy
          .minimumSessionBars,
      ) || 4,
    );

  const requiredHistoryBars =
    Math.max(
      minimumSessionBars,

      Math.max(
        2,
        Number(
          resolvedPolicy
            .minimumHistoryBars,
        ) || 21,
      ),

      Math.max(
        2,
        Number(
          resolvedPolicy
            .volumeLookback,
        ) || 20,
      ) + 1,

      Math.max(
        2,
        Number(
          resolvedPolicy
            .breakoutLookback,
        ) || 20,
      ) + 1,

      Math.max(
        2,
        Number(
          resolvedPolicy
            .atrPeriod,
        ) || 14,
      ) + 1,
    );

  const historyReady =
    closedCandles.length >=
    requiredHistoryBars;

  const sessionReady =
    sessionCandles.length >=
    minimumSessionBars;

  if (
    !historyReady ||
    !sessionReady
  ) {
    const readinessReasons = [];

    if (!historyReady) {
      readinessReasons.push(
        `指標計算用の確定済み15分足が${requiredHistoryBars}本未満です。`,
      );
    }

    if (!sessionReady) {
      readinessReasons.push(
        `当日の確定済み15分足が${minimumSessionBars}本未満です。`,
      );
    }

    return {
      version:
        INTRADAY_MARKET_VERSION,

      ready: false,
      marketBlocked: true,
      setup: "insufficient_data",
      direction: "中立",
      entryCondition: "データ待ち",

      reasons:
        readinessReasons,

      sessionBarCount:
        sessionCandles.length,

      historyBarCount:
        closedCandles.length,

      minimumSessionBars,
      requiredHistoryBars,

      dataQualityScore:
        calculateDataQuality({
          sourceCandles:
            candles,

          normalizedCandles:
            normalized,

          sessionCandles,
          stale: false,
        }),
    };
  }

  const latest = sessionCandles.at(-1);
  const previous =
    sessionCandles.at(-2);

  const completedAt =
    Number(latest.time) +
    INTRADAY_INTERVAL_SECONDS;

  const dataAgeSeconds = Math.max(
    0,
    Number(nowSeconds) - completedAt,
  );

  const stale =
    dataAgeSeconds >
    Number(
      resolvedPolicy.maximumBarAgeSeconds,
    );

  const vwapSeries =
    calculateIntradayVwapSeries(
      sessionCandles,
    );

  const currentVwap =
    vwapSeries.at(-1)?.vwap ?? null;

  const previousVwap =
    vwapSeries.at(-2)?.vwap ?? null;

  const volumeContext =
    calculateSessionAwareVolumeRatio(
      closedCandles,
      {
        lookbackSessions:
          resolvedPolicy
            .volumeLookbackSessions,

        minimumSamples:
          resolvedPolicy
            .minimumVolumeBaselineSamples,

        fallbackLookback:
          resolvedPolicy
            .volumeLookback,
      },
    );

  const volumeRatio =
    volumeContext.ratio;

  const volumeSurge =
    finite(volumeRatio) &&
    Number(volumeRatio) >=
      Number(
        resolvedPolicy.volumeSurgeRatio,
      );

  const lookbackWindow =
    closedCandles.slice(
      -Math.max(
        2,
        Number(
          resolvedPolicy.breakoutLookback,
        ) + 1,
      ),
      -1,
    );

  const priorHigh = lookbackWindow.length
    ? Math.max(
        ...lookbackWindow.map(
          (candle) => Number(candle.high),
        ),
      )
    : null;

  const priorLow = lookbackWindow.length
    ? Math.min(
        ...lookbackWindow.map(
          (candle) => Number(candle.low),
        ),
      )
    : null;

  const breakoutBuffer =
    Number(
      resolvedPolicy.breakoutBufferPercent,
    ) / 100;

  const breakoutLong =
    positive(priorHigh) &&
    Number(latest.close) >
      Number(priorHigh) *
        (1 + breakoutBuffer);

  const breakoutShort =
    positive(priorLow) &&
    Number(latest.close) <
      Number(priorLow) *
        (1 - breakoutBuffer);

  const aboveVwap =
    positive(currentVwap) &&
    Number(latest.close) >
      Number(currentVwap);

  const belowVwap =
    positive(currentVwap) &&
    Number(latest.close) <
      Number(currentVwap);

  const reclaimLong =
    positive(previousVwap) &&
    Number(previous.close) <=
      Number(previousVwap) &&
    aboveVwap &&
    Number(latest.close) >
      Number(latest.open);

  const reclaimShort =
    positive(previousVwap) &&
    Number(previous.close) >=
      Number(previousVwap) &&
    belowVwap &&
    Number(latest.close) <
      Number(latest.open);

  const tolerance =
    Number(
      resolvedPolicy.vwapTolerancePercent,
    ) / 100;

  const sessionExpansionWindow =
    sessionCandles.slice(
      -Math.max(
        2,
        Number(
          resolvedPolicy
            .breakoutLookback,
        ) + 1,
      ),
      -1,
    );

  const sessionPriorHigh =
    sessionExpansionWindow.length
      ? Math.max(
          ...sessionExpansionWindow.map(
            (candle) =>
              Number(candle.high),
          ),
        )
      : null;

  const sessionPriorLow =
    sessionExpansionWindow.length
      ? Math.min(
          ...sessionExpansionWindow.map(
            (candle) =>
              Number(candle.low),
          ),
        )
      : null;

  const hadLongExpansion =
    positive(currentVwap) &&
    positive(sessionPriorHigh) &&
    Number(sessionPriorHigh) >=
      Number(currentVwap) * 1.004;

  const hadShortExpansion =
    positive(currentVwap) &&
    positive(sessionPriorLow) &&
    Number(sessionPriorLow) <=
      Number(currentVwap) * 0.996;

  const pullbackLong =
    hadLongExpansion &&
    Number(latest.low) <=
      Number(currentVwap) *
        (1 + tolerance) &&
    aboveVwap &&
    Number(latest.close) >=
      Number(latest.open);

  const pullbackShort =
    hadShortExpansion &&
    Number(latest.high) >=
      Number(currentVwap) *
        (1 - tolerance) &&
    belowVwap &&
    Number(latest.close) <=
      Number(latest.open);

  let setup = "wait";
  let direction = "中立";
  let entryCondition =
    "短期セットアップ未成立";
  const reasons = [];

  if (stale) {
    setup = "stale_data";
    reasons.push(
      "15分足データが古いため取引判断を停止します。",
    );
  } else if (
    breakoutLong &&
    volumeSurge &&
    aboveVwap
  ) {
    setup = "breakout_long";
    direction = "強気";
    entryCondition =
      "VWAP上で直近高値を出来高急増とともに突破";
  } else if (
    breakoutShort &&
    volumeSurge &&
    belowVwap
  ) {
    setup = "breakout_short";
    direction = "弱気";
    entryCondition =
      "VWAP下で直近安値を出来高急増とともに下抜け";
  } else if (
    reclaimLong &&
    finite(volumeRatio) &&
    Number(volumeRatio) >= 1.2
  ) {
    setup = "vwap_reclaim_long";
    direction = "強気";
    entryCondition =
      "VWAPを上方向へ回復";
  } else if (
    reclaimShort &&
    finite(volumeRatio) &&
    Number(volumeRatio) >= 1.2
  ) {
    setup = "vwap_reclaim_short";
    direction = "弱気";
    entryCondition =
      "VWAPを下方向へ割り込み";
  } else if (pullbackLong) {
    setup = "pullback_long";
    direction = "強気";
    entryCondition =
      "上昇後にVWAP付近まで押して反発";
  } else if (pullbackShort) {
    setup = "pullback_short";
    direction = "弱気";
    entryCondition =
      "下落後にVWAP付近まで戻して反落";
  } else {
    if (
      breakoutLong &&
      !volumeSurge
    ) {
      reasons.push(
        "高値を突破しましたが、出来高の裏付けが不足しています。",
      );
    }

    if (
      breakoutShort &&
      !volumeSurge
    ) {
      reasons.push(
        "安値を下抜けましたが、出来高の裏付けが不足しています。",
      );
    }

    if (!reasons.length) {
      reasons.push(
        "ブレイク・VWAP回復・押し目反発の条件が未成立です。",
      );
    }
  }

  const atr = calculateIntradayAtr(
    closedCandles,
    resolvedPolicy.atrPeriod,
  );

  const setupStrengthScore =
    calculateSetupStrength({
      breakout:
        breakoutLong || breakoutShort,
      volumeSurge,
      vwapAligned:
        (direction === "強気" &&
          aboveVwap) ||
        (direction === "弱気" &&
          belowVwap),
      reclaim:
        reclaimLong || reclaimShort,
      pullback:
        pullbackLong || pullbackShort,
      stale,
    });

  const dataQualityScore =
    calculateDataQuality({
      sourceCandles: candles,
      normalizedCandles: normalized,
      sessionCandles,
      stale,
    });

  return {
    version: INTRADAY_MARKET_VERSION,
    ready: !stale,
    marketBlocked: stale,

    setup,
    direction,
    entryCondition,
    reasons,

    sessionDate:
      latest.sessionDate,
    sessionBarCount:
      sessionCandles.length,

    historyBarCount:
      closedCandles.length,

    minimumSessionBars,
    requiredHistoryBars,

    currentPrice:
      Number(latest.close),
    latestBarTime:
      Number(latest.time),
    dataAgeSeconds,

    vwap: currentVwap,
    atr,
    volumeRatio,
    volumeSurge,

    volumeBaseline: {
      source:
        volumeContext.source,

      sampleCount:
        volumeContext.sampleCount,

      averageVolume:
        volumeContext.baseline,

      sessionSlotIndex:
        volumeContext
          .sessionSlotIndex,
    },

    priorHigh,
    priorLow,

    breakoutLong,
    breakoutShort,
    reclaimLong,
    reclaimShort,
    pullbackLong,
    pullbackShort,
    aboveVwap,
    belowVwap,

    setupStrengthScore,
    dataQualityScore,

    scoreCalibration:
      "rules-v2-session-aware-uncalibrated",

    tradeSignal: {
      direction,
      currentPrice:
        Number(latest.close),
      atr,
      confidenceScore:
        setupStrengthScore,
      dataQualityScore,
      spreadPercent: null,
      dataAgeSeconds,
      setup,
      entryCondition,
      marketBlocked: stale,
      marketBlockReason: stale
        ? "15分足データが古いため停止"
        : null,
    },
  };
}

export const IntradayMarketInternals = {
  finite,
  positive,
  clamp,
  average,
  calculateDataQuality,
  calculateSetupStrength,
};