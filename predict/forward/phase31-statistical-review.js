const REVIEW_SAFETY = Object.freeze({
  mode: "STATISTICAL_REVIEW_ONLY",
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  humanApprovalRequired: true,
});

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function mean(values) {
  return values.length ? values.reduce((s, v) => s + v, 0) / values.length : 0;
}

function quantile(values, q) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  return sorted[base + 1] !== undefined
    ? sorted[base] + rest * (sorted[base + 1] - sorted[base])
    : sorted[base];
}

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

export function bootstrapCandidateAdvantage(run, options = {}) {
  const pairs = Array.isArray(run?.pairs) ? run.pairs : [];
  const iterations = Math.max(100, Math.trunc(finite(options.iterations, 2000)));
  const seed = Math.trunc(finite(options.seed, 31));
  const rng = seededRandom(seed);
  if (!pairs.length) {
    return { status: "BLOCKED", blockers: ["NO_PAIRED_SAMPLES"], safety: { ...REVIEW_SAFETY } };
  }
  const observed = mean(pairs.map((p) => finite(p.candidate?.netReturn) - finite(p.champion?.netReturn)));
  const samples = [];
  for (let i = 0; i < iterations; i += 1) {
    let total = 0;
    for (let j = 0; j < pairs.length; j += 1) {
      const pair = pairs[Math.floor(rng() * pairs.length)];
      total += finite(pair.candidate?.netReturn) - finite(pair.champion?.netReturn);
    }
    samples.push(total / pairs.length);
  }
  const probabilityPositive = samples.filter((v) => v > 0).length / samples.length;
  return {
    status: "READY",
    iterations,
    observedAverageAdvantage: observed,
    confidenceInterval95: [quantile(samples, 0.025), quantile(samples, 0.975)],
    probabilityCandidateBetter: probabilityPositive,
    statisticallyPositive: probabilityPositive >= finite(options.minProbability, 0.95),
    safety: { ...REVIEW_SAFETY },
  };
}

export function evaluateRegimeStability(run, options = {}) {
  const pairs = Array.isArray(run?.pairs) ? run.pairs : [];
  const minSamplesPerRegime = Math.max(1, Math.trunc(finite(options.minSamplesPerRegime, 10)));
  const groups = new Map();
  for (const pair of pairs) {
    const regime = String(pair.candidate?.regime ?? pair.champion?.regime ?? "UNKNOWN").toUpperCase();
    if (!groups.has(regime)) groups.set(regime, []);
    groups.get(regime).push(pair);
  }
  const regimes = [...groups.entries()].map(([regime, rows]) => {
    const advantages = rows.map((p) => finite(p.candidate?.netReturn) - finite(p.champion?.netReturn));
    return {
      regime,
      sampleCount: rows.length,
      averageAdvantage: mean(advantages),
      candidateBetterRate: advantages.filter((v) => v > 0).length / rows.length,
      sufficient: rows.length >= minSamplesPerRegime,
    };
  });
  const covered = regimes.filter((r) => r.regime !== "UNKNOWN");
  const blockers = [];
  if (!covered.length) blockers.push("NO_REGIME_LABELS");
  if (covered.some((r) => !r.sufficient)) blockers.push("INSUFFICIENT_REGIME_SAMPLES");
  if (covered.some((r) => r.averageAdvantage < 0)) blockers.push("NEGATIVE_REGIME_ADVANTAGE");
  return {
    status: blockers.length ? "CONTINUE_FORWARD_TEST" : "READY_FOR_REVIEW",
    regimes,
    blockers,
    stableAcrossRegimes: blockers.length === 0,
    safety: { ...REVIEW_SAFETY },
  };
}

export function buildCandidateReviewDashboard({ run, comparison, bootstrap, regimeStability } = {}) {
  const blockers = [
    ...(comparison?.blockers ?? []),
    ...(bootstrap?.status === "BLOCKED" ? bootstrap.blockers ?? [] : []),
    ...(regimeStability?.blockers ?? []),
  ];
  if (bootstrap?.statisticallyPositive !== true) blockers.push("BOOTSTRAP_NOT_POSITIVE");
  return {
    status: blockers.length ? "CONTINUE_FORWARD_TEST" : "READY_FOR_HUMAN_REVIEW",
    runId: run?.runId ?? null,
    pairedSamples: comparison?.pairedSamples ?? run?.pairs?.length ?? 0,
    champion: comparison?.champion ?? null,
    candidate: comparison?.candidate ?? null,
    deltas: comparison?.deltas ?? null,
    bootstrap: bootstrap ?? null,
    regimeStability: regimeStability ?? null,
    blockers: [...new Set(blockers)],
    promotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
    safety: { ...REVIEW_SAFETY },
  };
}

export function runPhase31StatisticalReview({ run, comparison, options = {} } = {}) {
  const bootstrap = bootstrapCandidateAdvantage(run, options.bootstrap ?? {});
  const regimeStability = evaluateRegimeStability(run, options.regime ?? {});
  const dashboard = buildCandidateReviewDashboard({ run, comparison, bootstrap, regimeStability });
  return {
    status: dashboard.status,
    bootstrap,
    regimeStability,
    dashboard,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...REVIEW_SAFETY },
  };
}

export { REVIEW_SAFETY };
