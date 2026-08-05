export const DRIFT_DETECTION_V1_VERSION = "drift-detection-v1";

function finite(values = []) {
  return values.map(Number).filter(Number.isFinite);
}
function mean(values) { return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null; }
function std(values, m = mean(values)) { return values.length && m !== null ? Math.sqrt(values.reduce((s, v) => s + (v - m) ** 2, 0) / values.length) : null; }
function numericFeatureNames(records = []) {
  const names = new Set();
  for (const record of records) {
    for (const [key, value] of Object.entries(record.features ?? record.technical ?? {})) {
      if (Number.isFinite(Number(value))) names.add(key);
    }
  }
  return Array.from(names);
}
function values(records, feature) {
  return finite(records.map((r) => (r.features ?? r.technical ?? {})[feature]));
}

export function detectDrift({ baseline = [], current = [], zThreshold = 1, minSample = 10 } = {}) {
  const names = new Set([...numericFeatureNames(baseline), ...numericFeatureNames(current)]);
  const features = Array.from(names).map((feature) => {
    const base = values(baseline, feature);
    const now = values(current, feature);
    const baseMean = mean(base);
    const currentMean = mean(now);
    const baseStd = std(base, baseMean);
    const meanShiftZ = baseMean === null || currentMean === null || !baseStd
      ? null
      : Math.abs(currentMean - baseMean) / baseStd;
    const insufficient = base.length < minSample || now.length < minSample;
    return {
      feature,
      baselineCount: base.length,
      currentCount: now.length,
      baselineMean: baseMean,
      currentMean,
      baselineStd: baseStd,
      meanShiftZ,
      insufficient,
      drifted: !insufficient && meanShiftZ !== null && meanShiftZ >= zThreshold,
    };
  });

  const regimeCounts = (records) => {
    const result = {};
    for (const record of records) {
      const key = String(record.marketRegime ?? record.regime ?? "UNKNOWN").toUpperCase();
      result[key] = (result[key] ?? 0) + 1;
    }
    return result;
  };
  const baselineRegimes = regimeCounts(baseline);
  const currentRegimes = regimeCounts(current);
  const baselineTop = Object.entries(baselineRegimes).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
  const currentTop = Object.entries(currentRegimes).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
  const driftedFeatures = features.filter((f) => f.drifted).map((f) => f.feature);

  return {
    version: DRIFT_DETECTION_V1_VERSION,
    generatedAt: new Date().toISOString(),
    features,
    driftedFeatures,
    regime: {
      baseline: baselineTop,
      current: currentTop,
      changed: baselineTop !== null && currentTop !== null && baselineTop !== currentTop,
      baselineCounts: baselineRegimes,
      currentCounts: currentRegimes,
    },
    driftDetected: driftedFeatures.length > 0 || (baselineTop !== null && currentTop !== null && baselineTop !== currentTop),
    action: driftedFeatures.length > 0 ? "REVIEW_CANDIDATE_AND_RECALIBRATE" : "NO_AUTOMATIC_PRODUCTION_CHANGE",
    productionUpdateAllowed: false,
  };
}

export default detectDrift;
