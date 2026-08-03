function numberOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function nonNegative(value) {
  const number = numberOrNull(value);

  return number === null
    ? 0
    : Math.max(0, number);
}

function clamp(value, minimum = 0, maximum = 100) {
  const number = numberOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(minimum, number),
  );
}

function ratio(numerator, denominator) {
  const top = numberOrNull(numerator);
  const bottom = numberOrNull(denominator);

  if (
    top === null ||
    bottom === null ||
    bottom === 0
  ) {
    return null;
  }

  return top / bottom;
}

function exponentialMovingAverage(values, period) {
  if (!values.length) {
    return null;
  }

  const multiplier = 2 / (period + 1);
  let current = values[0];

  for (let index = 1; index < values.length; index += 1) {
    current =
      values[index] * multiplier +
      current * (1 - multiplier);
  }

  return current;
}

export function calculateAdvanceDecline(snapshot = {}) {
  const advancing = nonNegative(
    snapshot.advancing ??
    snapshot.advancers,
  );

  const declining = nonNegative(
    snapshot.declining ??
    snapshot.decliners,
  );

  const unchanged = nonNegative(snapshot.unchanged);

  const total =
    advancing +
    declining +
    unchanged;

  return {
    advancing,
    declining,
    unchanged,
    total,
    netAdvances:
      advancing - declining,
    advanceDeclineRatio:
      ratio(advancing, declining),
    advancePercent:
      total > 0
        ? (advancing / total) * 100
        : null,
  };
}

export function calculateVolumeBreadth(snapshot = {}) {
  const upVolume = nonNegative(snapshot.upVolume);
  const downVolume = nonNegative(snapshot.downVolume);

  const directionalVolume =
    upVolume +
    downVolume;

  return {
    upVolume,
    downVolume,
    directionalVolume,
    netVolume:
      upVolume - downVolume,
    upDownVolumeRatio:
      ratio(upVolume, downVolume),
    upVolumePercent:
      directionalVolume > 0
        ? (upVolume / directionalVolume) * 100
        : null,
  };
}

export function calculateHighLowBreadth(snapshot = {}) {
  const newHighs = nonNegative(snapshot.newHighs);
  const newLows = nonNegative(snapshot.newLows);

  const total =
    newHighs +
    newLows;

  return {
    newHighs,
    newLows,
    netNewHighs:
      newHighs - newLows,
    highLowRatio:
      ratio(newHighs, newLows),
    highPercent:
      total > 0
        ? (newHighs / total) * 100
        : null,
  };
}

export function calculateBreadthThrust(snapshot = {}) {
  const {
    advancing,
    declining,
  } = calculateAdvanceDecline(snapshot);

  const directionalIssues =
    advancing +
    declining;

  const value =
    directionalIssues > 0
      ? (advancing / directionalIssues) * 100
      : null;

  let signal = "neutral";

  if (value !== null && value >= 61.5) {
    signal = "bullish-thrust";
  } else if (value !== null && value <= 38.5) {
    signal = "bearish-thrust";
  }

  return {
    value,
    signal,
  };
}

export function calculateMcClellanOscillator(history = []) {
  const netAdvances = history
    .map(
      (snapshot) =>
        calculateAdvanceDecline(snapshot).netAdvances,
    )
    .filter(Number.isFinite);

  if (!netAdvances.length) {
    return {
      oscillator: null,
      ema19: null,
      ema39: null,
      sampleSize: 0,
      ready: false,
    };
  }

  const ema19 =
    exponentialMovingAverage(netAdvances, 19);

  const ema39 =
    exponentialMovingAverage(netAdvances, 39);

  return {
    oscillator:
      ema19 - ema39,
    ema19,
    ema39,
    sampleSize:
      netAdvances.length,
    ready:
      netAdvances.length >= 39,
  };
}

export function calculatePercentAboveMovingAverages(
  snapshot = {},
) {
  const ma20 = clamp(
    snapshot.percentAbove20 ??
    snapshot.percentAboveMa20,
  );

  const ma50 = clamp(
    snapshot.percentAbove50 ??
    snapshot.percentAboveMa50,
  );

  const ma200 = clamp(
    snapshot.percentAbove200 ??
    snapshot.percentAboveMa200,
  );

  const available = [
    ma20,
    ma50,
    ma200,
  ].filter((value) => value !== null);

  return {
    ma20,
    ma50,
    ma200,
    average:
      available.length > 0
        ? available.reduce(
            (sum, value) => sum + value,
            0,
          ) / available.length
        : null,
    availableCount:
      available.length,
  };
}

function averageAvailable(values) {
  const available =
    values.filter(
      (value) =>
        value !== null &&
        Number.isFinite(value),
    );

  if (!available.length) {
    return null;
  }

  return available.reduce(
    (sum, value) => sum + value,
    0,
  ) / available.length;
}

export function buildMarketBreadthV2({
  snapshot = {},
  history = [],
} = {}) {
  const advanceDecline =
    calculateAdvanceDecline(snapshot);

  const volumeBreadth =
    calculateVolumeBreadth(snapshot);

  const highLowBreadth =
    calculateHighLowBreadth(snapshot);

  const breadthThrust =
    calculateBreadthThrust(snapshot);

  const percentAbove =
    calculatePercentAboveMovingAverages(snapshot);

  const mcclellan =
    calculateMcClellanOscillator([
      ...history,
      snapshot,
    ]);

  const score = averageAvailable([
    advanceDecline.advancePercent,
    volumeBreadth.upVolumePercent,
    highLowBreadth.highPercent,
    breadthThrust.value,
    percentAbove.average,
  ]);

  let regime = "neutral";

  if (score !== null && score >= 65) {
    regime = "broad-strength";
  } else if (score !== null && score <= 35) {
    regime = "broad-weakness";
  }

  return {
    version:
      "market-breadth-v2",
    score:
      score === null
        ? null
        : Math.round(score * 100) / 100,
    regime,
    advanceDecline,
    volumeBreadth,
    highLowBreadth,
    breadthThrust,
    percentAbove,
    mcclellan,
    quality: {
      hasIssueBreadth:
        advanceDecline.total > 0,
      hasVolumeBreadth:
        volumeBreadth.directionalVolume > 0,
      hasHighLowBreadth:
        (
          highLowBreadth.newHighs +
          highLowBreadth.newLows
        ) > 0,
      hasMovingAverageBreadth:
        percentAbove.availableCount > 0,
      mcclellanReady:
        mcclellan.ready,
    },
  };
}