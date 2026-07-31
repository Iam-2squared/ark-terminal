const TRADING_DAY_SECONDS = 24 * 60 * 60;

export class DataQualityError extends Error {
  constructor(report) {
    const reasons = report.blockingIssues.map((issue) => issue.message);
    super(
      reasons.length
        ? `データ品質検証に失敗しました: ${reasons.join(" / ")}`
        : "データ品質検証に失敗しました。",
    );
    this.name = "DataQualityError";
    this.report = report;
  }
}

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function issue(code, message, severity = "warning", count = 1) {
  return {
    code,
    message,
    severity,
    count,
  };
}

function expectedCurrency(symbol) {
  if (String(symbol).endsWith(".T")) {
    return "JPY";
  }

  if (
    String(symbol).startsWith("^") ||
    String(symbol).endsWith("=X") ||
    String(symbol).includes("-")
  ) {
    return null;
  }

  return "USD";
}

function normalizeCandle(candle) {
  return {
    time: Number(candle?.time),
    open: Number(candle?.open),
    high: Number(candle?.high),
    low: Number(candle?.low),
    close: Number(candle?.close),
    volume:
      candle?.volume === null || candle?.volume === undefined
        ? null
        : Number(candle.volume),
    rawClose: finite(candle?.rawClose) ? Number(candle.rawClose) : null,
    adjustedClose: finite(candle?.adjustedClose)
      ? Number(candle.adjustedClose)
      : null,
    adjustedCloseProvided: candle?.adjustedCloseProvided === true,
    adjustmentFactor: finite(candle?.adjustmentFactor)
      ? Number(candle.adjustmentFactor)
      : null,
    volumeAdjustmentFactor: finite(candle?.volumeAdjustmentFactor)
      ? Number(candle.volumeAdjustmentFactor)
      : null,
  };
}

function isValidOhlc(candle) {
  return (
    finite(candle.open) &&
    finite(candle.high) &&
    finite(candle.low) &&
    finite(candle.close) &&
    candle.open > 0 &&
    candle.high > 0 &&
    candle.low > 0 &&
    candle.close > 0 &&
    candle.high >= Math.max(candle.open, candle.close, candle.low) &&
    candle.low <= Math.min(candle.open, candle.close, candle.high)
  );
}

function deduplicate(candles) {
  const byTime = new Map();

  candles.forEach((candle) => {
    byTime.set(candle.time, candle);
  });

  return [...byTime.values()].sort((first, second) => first.time - second.time);
}

function dailyReturnOutliers(candles, maximumReturn) {
  const outliers = [];

  for (let index = 1; index < candles.length; index += 1) {
    const previous = candles[index - 1].close;
    const current = candles[index].close;

    if (!finite(previous) || !finite(current) || previous <= 0) {
      continue;
    }

    const change = Math.abs(current / previous - 1);

    if (change > maximumReturn) {
      outliers.push({
        time: candles[index].time,
        changePercent: change * 100,
      });
    }
  }

  return outliers;
}

function longGaps(candles) {
  const gaps = [];

  for (let index = 1; index < candles.length; index += 1) {
    const difference = candles[index].time - candles[index - 1].time;

    if (difference > TRADING_DAY_SECONDS * 10) {
      gaps.push({
        from: candles[index - 1].time,
        to: candles[index].time,
        calendarDays: difference / TRADING_DAY_SECONDS,
      });
    }
  }

  return gaps;
}

export function validateHistoryData(
  history,
  {
    minimumHistory = 252,
    requireAdjustedClose = true,
    requireVolume = true,
    requireOhlcIntegrity = true,
    maximumMissingRate = 0.02,
    maximumAdjustedDailyReturn = 0.8,
  } = {},
) {
  const rawCandles = Array.isArray(history?.candles) ? history.candles : [];
  const normalized = rawCandles.map(normalizeCandle);
  const issues = [];

  const invalidTime = normalized.filter((candle) => !finite(candle.time));
  const validTime = normalized.filter((candle) => finite(candle.time));
  const invalidOhlc = requireOhlcIntegrity
    ? validTime.filter((candle) => !isValidOhlc(candle))
    : validTime.filter((candle) => !finite(candle.close) || candle.close <= 0);
  const validOhlc = requireOhlcIntegrity
    ? validTime.filter(isValidOhlc)
    : validTime.filter((candle) => finite(candle.close) && candle.close > 0);
  const duplicateCount =
    validOhlc.length - new Set(validOhlc.map((candle) => candle.time)).size;
  const candles = deduplicate(validOhlc);
  const missingVolume = candles.filter(
    (candle) => !finite(candle.volume) || candle.volume < 0,
  );
  const providedAdjustedCount = Number(
    history?.sourceQuality?.adjustedCloseCount,
  );
  const structurallyInvalidAdjustedClose = candles.filter(
    (candle) =>
      !finite(candle.adjustedClose) ||
      !finite(candle.adjustmentFactor) ||
      candle.adjustmentFactor <= 0,
  );
  const missingAdjustedCloseCount = Number.isFinite(providedAdjustedCount)
    ? Math.max(
        structurallyInvalidAdjustedClose.length,
        candles.length - providedAdjustedCount,
      )
    : Math.max(
        structurallyInvalidAdjustedClose.length,
        candles.filter((candle) => !candle.adjustedCloseProvided).length,
      );
  const sourceRows = Math.max(
    Number(history?.sourceQuality?.sourceRowCount) || rawCandles.length,
    rawCandles.length,
    1,
  );
  const droppedAtSource = Number(history?.sourceQuality?.droppedRowCount) || 0;
  const missingCount =
    droppedAtSource + invalidTime.length + invalidOhlc.length;
  const missingRate = missingCount / sourceRows;
  const outliers = dailyReturnOutliers(candles, maximumAdjustedDailyReturn);
  const gaps = longGaps(candles);
  const expected = expectedCurrency(history?.symbol);
  const actualCurrency = history?.meta?.currency || null;
  const priceUnit = history?.meta?.priceUnit || null;
  const volumeUnit = history?.meta?.volumeUnit || null;

  if (invalidTime.length) {
    issues.push(
      issue(
        "invalid-time",
        `日時が不正な行が${invalidTime.length}件あります。`,
        "blocking",
        invalidTime.length,
      ),
    );
  }

  if (invalidOhlc.length) {
    issues.push(
      issue(
        "invalid-ohlc",
        `価格の大小関係または正値条件を満たさない行が${invalidOhlc.length}件あります。`,
        "blocking",
        invalidOhlc.length,
      ),
    );
  }

  if (missingRate > maximumMissingRate) {
    issues.push(
      issue(
        "missing-rate",
        `欠損率${(missingRate * 100).toFixed(2)}%が許容値${(
          maximumMissingRate * 100
        ).toFixed(2)}%を超えています。`,
        "blocking",
        missingCount,
      ),
    );
  } else if (missingCount) {
    issues.push(
      issue(
        "repaired-missing",
        `${missingCount}件の欠損行を除外しました。`,
        "warning",
        missingCount,
      ),
    );
  }

  if (duplicateCount) {
    issues.push(
      issue(
        "duplicates",
        `${duplicateCount}件の重複日時を後勝ちで統合しました。`,
        "warning",
        duplicateCount,
      ),
    );
  }

  if (requireVolume && missingVolume.length) {
    issues.push(
      issue(
        "invalid-volume",
        `出来高の欠損または負値が${missingVolume.length}件あります。`,
        "blocking",
        missingVolume.length,
      ),
    );
  }

  if (requireAdjustedClose && missingAdjustedCloseCount) {
    issues.push(
      issue(
        "missing-adjusted-close",
        `調整後終値を確認できない行が${missingAdjustedCloseCount}件あります。`,
        "blocking",
        missingAdjustedCloseCount,
      ),
    );
  }

  if (candles.length < minimumHistory) {
    issues.push(
      issue(
        "insufficient-history",
        `${minimumHistory}営業日必要ですが${candles.length}営業日しかありません。`,
        "blocking",
      ),
    );
  }

  if (outliers.length) {
    issues.push(
      issue(
        "extreme-return",
        `調整後価格で1日${(maximumAdjustedDailyReturn * 100).toFixed(
          0,
        )}%超の変動が${outliers.length}件あります。分割調整または異常値を確認してください。`,
        "blocking",
        outliers.length,
      ),
    );
  }

  if (expected && actualCurrency && expected !== actualCurrency) {
    issues.push(
      issue(
        "currency-mismatch",
        `想定通貨${expected}に対して取得通貨は${actualCurrency}です。`,
        "blocking",
      ),
    );
  }

  if (!actualCurrency || !priceUnit) {
    issues.push(
      issue(
        "unknown-price-unit",
        "価格の通貨または単位を確認できません。",
        "blocking",
      ),
    );
  }

  if (actualCurrency && priceUnit && actualCurrency !== priceUnit) {
    issues.push(
      issue(
        "price-unit-mismatch",
        `価格通貨${actualCurrency}と価格単位${priceUnit}が一致しません。`,
        "blocking",
      ),
    );
  }

  if (requireVolume && volumeUnit !== "shares") {
    issues.push(
      issue(
        "unknown-volume-unit",
        `出来高単位がsharesではありません（${volumeUnit || "不明"}）。`,
        "blocking",
      ),
    );
  }

  if (gaps.length) {
    issues.push(
      issue(
        "long-gap",
        `10暦日を超える価格履歴の空白が${gaps.length}件あります。`,
        "warning",
        gaps.length,
      ),
    );
  }

  const blockingIssues = issues.filter((item) => item.severity === "blocking");
  const warningIssues = issues.filter((item) => item.severity === "warning");
  const qualityScore = Math.max(
    0,
    Math.round(
      100 -
        missingRate * 500 -
        warningIssues.reduce((sum, item) => sum + Math.min(item.count, 5), 0) *
          2 -
        blockingIssues.length * 30,
    ),
  );

  return {
    status: blockingIssues.length
      ? "failed"
      : warningIssues.length
        ? "warning"
        : "passed",
    canScore: blockingIssues.length === 0,
    qualityScore,
    symbol: history?.symbol || "",
    currency: actualCurrency,
    priceUnit: priceUnit || "unknown",
    volumeUnit: volumeUnit || "unknown",
    adjustmentMethod: history?.adjustmentMethod || "unknown",
    splitCount:
      Number(history?.sourceQuality?.splitCount) ||
      history?.corporateActions?.splits?.length ||
      0,
    sourceRowCount: sourceRows,
    validRowCount: candles.length,
    missingCount,
    missingRate: missingRate * 100,
    duplicateCount,
    outlierCount: outliers.length,
    longGapCount: gaps.length,
    issues,
    blockingIssues,
    warningIssues,
    audits: {
      adjustedCloseCoverage:
        candles.length > 0
          ? ((candles.length - missingAdjustedCloseCount) / candles.length) *
            100
          : 0,
      volumeCoverage:
        candles.length > 0
          ? ((candles.length - missingVolume.length) / candles.length) * 100
          : 0,
      firstTime: candles[0]?.time || null,
      lastTime: candles.at(-1)?.time || null,
    },
    candles,
  };
}

export function assertHistoryQuality(history, options) {
  const report = validateHistoryData(history, options);

  if (!report.canScore) {
    throw new DataQualityError(report);
  }

  return report;
}

function nearlyEqual(first, second, tolerance = 1e-8) {
  if (!finite(first) || !finite(second)) {
    return first === null && second === null;
  }

  return (
    Math.abs(Number(first) - Number(second)) <=
    tolerance * Math.max(1, Math.abs(Number(first)), Math.abs(Number(second)))
  );
}

function mean(values) {
  return values.reduce((sum, value) => sum + Number(value), 0) / values.length;
}

function expectedSma(candles, period) {
  return candles.length >= period
    ? mean(candles.slice(-period).map((candle) => candle.close))
    : null;
}

function expectedVwap(candles, period = 20) {
  const window = candles.slice(-period);
  const volume = window.reduce((sum, candle) => sum + Number(candle.volume), 0);

  if (!window.length || volume === 0) {
    return null;
  }

  return (
    window.reduce(
      (sum, candle) =>
        sum +
        ((Number(candle.high) + Number(candle.low) + Number(candle.close)) /
          3) *
          Number(candle.volume),
      0,
    ) / volume
  );
}

export function validateIndicatorCalculations(indicators, candles) {
  const ordered = [...candles].sort(
    (first, second) => first.time - second.time,
  );
  const year = ordered.slice(-252);
  const expected = {
    ma5: expectedSma(ordered, 5),
    ma25: expectedSma(ordered, 25),
    ma75: expectedSma(ordered, 75),
    ma200: expectedSma(ordered, 200),
    high52Week: year.length
      ? Math.max(...year.map((candle) => candle.high))
      : null,
    low52Week: year.length
      ? Math.min(...year.map((candle) => candle.low))
      : null,
    vwap: expectedVwap(ordered),
  };
  const actual = {
    ma5: indicators?.movingAverages?.ma5,
    ma25: indicators?.movingAverages?.ma25,
    ma75: indicators?.movingAverages?.ma75,
    ma200: indicators?.movingAverages?.ma200,
    high52Week: indicators?.high52Week,
    low52Week: indicators?.low52Week,
    vwap: indicators?.vwap,
  };
  const labels = {
    ma5: "5MA",
    ma25: "25MA",
    ma75: "75MA",
    ma200: "200MA",
    high52Week: "52週高値",
    low52Week: "52週安値",
    vwap: "VWAP",
  };
  const checks = Object.keys(expected).map((key) => ({
    key,
    label: labels[key],
    expected: expected[key],
    actual: actual[key],
    passed: nearlyEqual(expected[key], actual[key]),
  }));
  const failed = checks.filter((check) => !check.passed);

  return {
    status: failed.length ? "failed" : "passed",
    canScore: failed.length === 0,
    checks,
    blockingIssues: failed.map((check) =>
      issue(
        `calculation-${check.key}`,
        `${check.label}の再計算結果が一致しません。`,
        "blocking",
      ),
    ),
  };
}
