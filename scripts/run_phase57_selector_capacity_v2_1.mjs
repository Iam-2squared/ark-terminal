import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

import { runPhase57MinimalHybrid } from "../predict/daytrade/phase57-selector-minimal-hybrid.js";
import { buildPhase57MinimalHybridTargets } from "../predict/daytrade/phase57-selector-minimal-hybrid-targets.js";
import { extractPhase57CapacityV2Inputs } from "../predict/daytrade/phase57-selector-capacity-v2-contract.js";
import { Phase57FreshSessionInternals } from "./lib/phase57-selector-jquants-fresh-session.mjs";
import { Phase57CapacityV2Internals as V2 } from "./run_phase57_selector_capacity_v2.mjs";

const RESEARCH_ROOT = new URL("../predict/research/", import.meta.url);
const SPEC = readJson(
  new URL("phase57-selector-capacity-v2-1-precommit.json", RESEARCH_ROOT),
);
const HYBRID_MODEL = readJson(
  new URL(
    "phase57-selector-minimal-hybrid-development-model.json",
    RESEARCH_ROOT,
  ),
);
const PILOT_REGISTRY = readJson(
  new URL(
    "phase57-selector-source-validation-only-registry.json",
    RESEARCH_ROOT,
  ),
);
const API_BASE = "https://api.jquants.com/";
const CALENDAR_PATH = "v2/markets/calendar";
const FROM = "2025-04-15",
  TO = "2026-06-11";
const FEATURES = Object.freeze([
  ...SPEC.retainedModelContract.trainableFeatureWhitelist,
]);
const LAYERS = Object.freeze([
  { name: "RANK_6_10", min: 6, max: 10 },
  { name: "RANK_11_15", min: 11, max: 15 },
  { name: "RANK_16_20", min: 16, max: 20 },
]);
const LAMBDAS = Object.freeze([
  ...SPEC.retainedModelContract.ridgeLambdaCandidates,
]);
const QUANTILES = Object.freeze([
  ...SPEC.retainedModelContract.thresholdPredictionQuantiles,
]);
const ROUND_TRIP_COST_BPS = SPEC.retainedModelContract.roundTripCostBps;
const SAFETY = SPEC.safety;
const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const finite = (value) =>
  value !== null &&
  value !== undefined &&
  value !== "" &&
  Number.isFinite(Number(value));
const mean = (values) =>
  values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null;
const round = (value, digits = 8) =>
  finite(value) ? Number(Number(value).toFixed(digits)) : null;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
function writeJson(directory, name, value) {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const bytes = JSON.stringify(value, null, 2) + "\n";
  fs.writeFileSync(path.join(directory, name), bytes, { mode: 0o600 });
  fs.writeFileSync(
    path.join(directory, `${name}.sha256`),
    `${sha256(bytes)}  ${name}\n`,
    { mode: 0o600 },
  );
  return sha256(bytes);
}
function safeError(error) {
  return String(error?.message ?? error).replace(
    /[A-Za-z0-9_-]{24,}/g,
    "[REDACTED]",
  );
}
function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function assertSafety(safety) {
  for (const [key, value] of Object.entries(SAFETY))
    assert(
      value === false && safety?.[key] === false,
      `safety mismatch: ${key}`,
    );
}
function recursiveFiles(root, name) {
  const result = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const target = path.join(root, entry.name);
    if (entry.isDirectory()) result.push(...recursiveFiles(target, name));
    else if (entry.name === name) result.push(target);
  }
  return result.sort();
}
function assertBaseline() {
  assert(
    HYBRID_MODEL.modelDigest === SPEC.frozenBaseline.modelDigest,
    "Frozen Hybrid model digest mismatch",
  );
  assertSafety(SAFETY);
}

async function requestCalendar(apiKey, fetchImpl = globalThis.fetch) {
  assert(String(apiKey ?? "").trim(), "JQUANTS_API_KEY_REQUIRED");
  const url = new URL(CALENDAR_PATH, API_BASE);
  url.searchParams.set("from", FROM);
  url.searchParams.set("to", TO);
  const response = await fetchImpl(url, {
    headers: { Accept: "application/json", "x-api-key": apiKey },
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(60_000),
  });
  assert(response.status === 200, `JQUANTS_CALENDAR_HTTP_${response.status}`);
  const payload = JSON.parse(await response.text());
  assert(Array.isArray(payload?.data), "JQUANTS_CALENDAR_SCHEMA_INVALID");
  return payload.data;
}

function sourceDates(calendarRows) {
  const pilot = new Set(PILOT_REGISTRY.sessions.map((row) => row.sessionDate));
  return [
    ...new Set(
      calendarRows
        .filter((row) => String(row?.HolDiv) === "1")
        .map((row) => String(row.Date))
        .filter((date) => date >= FROM && date <= TO && !pilot.has(date)),
    ),
  ].sort();
}
function originalAllocatedDates(allocation) {
  return [
    ...allocation.development,
    ...allocation.purgeDevelopmentValidation,
    ...allocation.validation,
    ...allocation.purgeValidationOos,
    ...allocation.untouchedOos,
  ].sort();
}

export function buildV21Allocation(calendarRows, sourceAllocation) {
  assertBaseline();
  assert(
    sourceAllocation?.status === "CAPACITY_V2_FRESH_ALLOCATION_MATERIALIZED",
    "source allocation mismatch",
  );
  const dates = sourceDates(calendarRows);
  assert(
    dates.length === 282,
    `reserve calendar identity mismatch: ${dates.length}`,
  );
  assert(
    JSON.stringify(dates.slice(0, 120)) ===
      JSON.stringify(originalAllocatedDates(sourceAllocation)),
    "source first-120 allocation drift",
  );
  const freshValidation = dates.slice(120, 149),
    purge = dates.slice(149, 150),
    freshOos = dates.slice(150, 179),
    remaining = dates.slice(179);
  const result = {
    schemaVersion: 1,
    phase: "57.selector-capacity-v2-1.allocation",
    status: "CAPACITY_V2_1_FRESH_ALLOCATION_MATERIALIZED",
    datasetId: "PHASE57_JQUANTS_CAPACITY_V2_1_FRESH59_V1",
    sourceDatasetId: sourceAllocation.datasetId,
    sourceRunId: 34153192882,
    allocationMethod: SPEC.newFreshEvaluationAllocation.allocationMethod,
    queryWindow: { from: FROM, to: TO },
    developmentDates: [
      ...sourceAllocation.development,
      ...sourceAllocation.validation,
    ].sort(),
    freshValidation,
    purgeValidationOos: purge,
    freshUntouchedOos: freshOos,
    quarantinedOriginalOos: {
      first: sourceAllocation.untouchedOos[0],
      last: sourceAllocation.untouchedOos.at(-1),
      sessionCount: sourceAllocation.untouchedOos.length,
      released: false,
      reused: false,
    },
    remainingReserve: {
      first: remaining[0],
      last: remaining.at(-1),
      sessionCount: remaining.length,
      ordinals: [180, 282],
      released: false,
    },
    counts: {
      development: 89,
      freshValidation: 29,
      purge: 1,
      freshUntouchedOos: 29,
      freshAdmission: 59,
      reserveRemaining: 103,
    },
    guards: {
      chronological: true,
      sourceFirst120Exact: true,
      originalOosQuarantined: true,
      outcomesInspected: false,
      featuresCalculated: false,
      labelsGenerated: false,
      reserveBeyondOrdinal179Opened: false,
    },
    release: {
      development: true,
      freshValidation: false,
      freshUntouchedOos: false,
    },
    safety: SAFETY,
  };
  assert(
    result.developmentDates.length === 89 &&
      freshValidation.length === 29 &&
      purge.length === 1 &&
      freshOos.length === 29 &&
      remaining.length === 103,
    "v2.1 allocation count mismatch",
  );
  return result;
}

function freshAllocationRows(allocation) {
  return [
    ...allocation.freshValidation.map((sessionDate) => ({
      sessionDate,
      fold: "VALIDATION",
    })),
    ...allocation.purgeValidationOos.map((sessionDate) => ({
      sessionDate,
      fold: "PURGE",
    })),
    ...allocation.freshUntouchedOos.map((sessionDate) => ({
      sessionDate,
      fold: "UNTOUCHED_OOS",
    })),
  ].sort((a, b) => a.sessionDate.localeCompare(b.sessionDate));
}
function sanitizeAudit(audit) {
  const { symbolCoverage, ...safe } = audit;
  return { ...safe, symbolCoveragePersisted: false };
}
async function loadWithRetry(options) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    try {
      return await Phase57FreshSessionInternals.loadFreshSession({
        ...options,
        paceMs: 1300,
      });
    } catch (error) {
      if (
        !/RATE_LIMITED|HTTP_5\d\d/.test(String(error?.message ?? error)) ||
        attempt === 5
      )
        throw error;
      await sleep((attempt + 1) * 30_000);
    }
  }
  throw new Error("SESSION_RETRY_EXHAUSTED");
}

export async function runAdmissionShard({
  apiKey,
  allocation,
  shardIndex,
  shardCount,
  load = loadWithRetry,
}) {
  assertBaseline();
  assert(
    allocation.status === "CAPACITY_V2_1_FRESH_ALLOCATION_MATERIALIZED",
    "v2.1 allocation not materialized",
  );
  const assigned = freshAllocationRows(allocation).filter(
      (_, index) => index % shardCount === shardIndex,
    ),
    audits = [];
  for (const [index, item] of assigned.entries()) {
    console.error(
      `CAPACITY_V2_1_ADMISSION shard=${shardIndex} session=${index + 1}/${assigned.length} date=${item.sessionDate}`,
    );
    const { structuralAudit } = await load({
      apiKey,
      date: item.sessionDate,
      fold: "PURGE",
    });
    assert(
      structuralAudit.status === "SESSION_STRUCTURAL_AUDIT_PASS" &&
        !structuralAudit.featureCalculationPerformed &&
        !structuralAudit.labelGenerationPerformed,
      `structural admission failed ${item.sessionDate}`,
    );
    audits.push({ ...sanitizeAudit(structuralAudit), fold: item.fold });
  }
  return {
    schemaVersion: 1,
    status: "CAPACITY_V2_1_ADMISSION_SHARD_PASS",
    datasetId: allocation.datasetId,
    shardIndex,
    shardCount,
    audits,
    rawPersisted: false,
    secretPersisted: false,
    safety: SAFETY,
  };
}

export function summarizeAdmission({ allocation, inputRoot }) {
  const reports = recursiveFiles(inputRoot, "admission-shard.json").map(
      readJson,
    ),
    audits = reports.flatMap((report) => report.audits ?? []),
    expected = freshAllocationRows(allocation);
  assert(
    reports.length === 6 && audits.length === 59,
    `v2.1 admission incomplete reports=${reports.length} audits=${audits.length}`,
  );
  const byDate = new Map(audits.map((audit) => [audit.sessionDate, audit]));
  assert(byDate.size === 59, "duplicate v2.1 admission session");
  for (const row of expected) {
    const audit = byDate.get(row.sessionDate);
    assert(
      audit &&
        audit.fold === row.fold &&
        audit.status === "SESSION_STRUCTURAL_AUDIT_PASS",
      `admission identity mismatch ${row.sessionDate}`,
    );
    for (const key of [
      "exactDuplicateRows",
      "timestampConflicts",
      "lunchViolations",
      "futureAvailabilityViolations",
      "masterInvalidRows",
      "masterDuplicateCodes",
    ])
      assert(audit[key] === 0, `admission violation ${key} ${row.sessionDate}`);
  }
  const sorted = audits.sort((a, b) =>
    a.sessionDate.localeCompare(b.sessionDate),
  );
  const core = {
    schemaVersion: 1,
    phase: "57.selector-capacity-v2-1.dataset-admission",
    status: "CAPACITY_V2_1_DATASET_ADMISSION_PASS",
    datasetId: allocation.datasetId,
    sessionCount: 59,
    counts: allocation.counts,
    period: { first: sorted[0].sessionDate, last: sorted.at(-1).sessionDate },
    auditBySession: sorted.map((a) => ({
      sessionDate: a.sessionDate,
      fold: a.fold,
      minuteSha256: a.minuteSha256,
      fiveMinuteSha256: a.fiveMinuteSha256,
      memberSetSha256: a.memberSetSha256,
      eligibleJpxSymbolCount: a.eligibleJpxSymbolCount,
      normalizedMinuteRows: a.normalizedMinuteRows,
      fiveMinuteBars: a.fiveMinuteBars,
    })),
    guards: {
      pitUniverse: true,
      timestampCausality: true,
      availableAtCausal: true,
      ohlcvValid: true,
      duplicateConflicts: 0,
      timestampConflicts: 0,
      lunchViolations: 0,
      futureLeakage: 0,
      reserveContamination: 0,
      rawPersisted: false,
    },
    release: { freshValidation: true, freshUntouchedOos: false },
    safety: SAFETY,
  };
  return { ...core, admissionSha256: sha256(JSON.stringify(core)) };
}

function verifyStructural(expected, actual) {
  assert(expected, `missing admitted session ${actual?.sessionDate}`);
  for (const key of ["minuteSha256", "fiveMinuteSha256", "memberSetSha256"])
    assert(
      expected[key] === actual[key],
      `source drift ${expected.sessionDate} ${key}`,
    );
}
function targetUtility(row) {
  const target = row.targetsByHorizon?.[6];
  return target?.status === "TARGET_READY"
    ? target.twoSidedOpportunity * 10000 - ROUND_TRIP_COST_BPS
    : null;
}

export async function buildDecisionSamples({
  apiKey,
  dates,
  fold,
  admission,
  load = loadWithRetry,
}) {
  assertBaseline();
  const expected = new Map(
      admission.auditBySession.map((row) => [row.sessionDate, row]),
    ),
    samples = [];
  for (const [dateIndex, date] of dates.entries()) {
    console.error(
      `CAPACITY_V2_1_${fold} session=${dateIndex + 1}/${dates.length} date=${date}`,
    );
    const { structuralAudit, bySymbol } = await load({ apiKey, date, fold });
    verifyStructural(expected.get(date), structuralAudit);
    const entries = [...bySymbol.values()].map((row) => ({
      symbol: row.symbol,
      sector: row.sector,
      market: row.market,
      bars: row.bars,
    }));
    for (const time of Phase57FreshSessionInternals.DECISION_TIMES) {
      const featureCutoff = Phase57FreshSessionInternals.cutoffIso(date, time),
        cutoffMs = Date.parse(featureCutoff),
        segment = time < "12:00" ? "AM" : "PM";
      const hybrid = runPhase57MinimalHybrid({
        featureCutoff,
        entries,
        model: HYBRID_MODEL,
      });
      const input = extractPhase57CapacityV2Inputs({
        hybridResult: hybrid,
        decisionTime: featureCutoff,
      });
      const utilities = [];
      for (const row of hybrid.ranked.slice(0, 20)) {
        const item = bySymbol.get(row.symbol),
          causal =
            item?.bars.filter(
              (bar) => Date.parse(bar.availableAt) <= cutoffMs,
            ) ?? [];
        if (!causal.length) {
          utilities.push(null);
          continue;
        }
        const future = item.bars.filter(
          (bar) =>
            Date.parse(bar.availableAt) > cutoffMs &&
            bar.sessionSegment === segment,
        );
        utilities.push(
          targetUtility({
            targetsByHorizon: buildPhase57MinimalHybridTargets({
              featureCutoff,
              anchorPrice: causal.at(-1).close,
              sessionDate: date,
              futureBars: future,
            }).horizons,
          }),
        );
      }
      const bandTarget = (min, max) => {
        const values = utilities
          .slice(min - 1, max)
          .filter(finite)
          .map(Number);
        return values.length ? mean(values) : null;
      };
      const utilityAt = (capacity) => {
        const values = utilities
          .slice(0, Math.min(capacity, hybrid.ranked.length))
          .filter(finite)
          .map(Number);
        return values.length ? mean(values) : null;
      };
      const frozenValues = hybrid.selected
        .map((row) => utilities[row.hybridRank - 1])
        .filter(finite)
        .map(Number);
      samples.push({
        sessionDate: date,
        featureCutoff,
        features: input.features,
        availability: input.featureAvailability,
        targets: Object.fromEntries(
          LAYERS.map((layer) => [layer.name, bandTarget(layer.min, layer.max)]),
        ),
        utilityByCapacity: Object.fromEntries(
          Array.from({ length: 20 }, (_, i) => i + 1).map((k) => [
            k,
            utilityAt(k),
          ]),
        ),
        frozenSelectedCount: hybrid.selected.length,
        frozenSelectedUtility: frozenValues.length ? mean(frozenValues) : null,
        rankedCount: hybrid.ranked.length,
        prefixIdentity: true,
        modelDigest: hybrid.modelDigest,
      });
    }
  }
  return samples;
}

function featureScale(rows) {
  const usable = rows.filter((row) =>
    FEATURES.every((name) => finite(row.features[name])),
  );
  const centers = FEATURES.map((name) =>
    mean(usable.map((row) => Number(row.features[name]))),
  );
  const scales = FEATURES.map(
    (name, index) =>
      Math.sqrt(
        mean(
          usable.map(
            (row) => (Number(row.features[name]) - centers[index]) ** 2,
          ),
        ),
      ) || 1,
  );
  return { centers, scales };
}
function foldDefinitions(rows) {
  const sessions = [...new Set(rows.map((row) => row.sessionDate))].sort();
  assert(sessions.length === 89, "v2.1 development requires 89 sessions");
  return SPEC.outOfFoldContract.folds.map((item) => ({
    train: new Set(
      sessions.slice(
        item.trainSessionOrdinalsWithinDevelopment[0] - 1,
        item.trainSessionOrdinalsWithinDevelopment[1],
      ),
    ),
    test: new Set(
      sessions.slice(
        item.testSessionOrdinalsWithinDevelopment[0] - 1,
        item.testSessionOrdinalsWithinDevelopment[1],
      ),
    ),
  }));
}
function chooseLambda(rows, layer, folds) {
  let best = null;
  for (const lambda of LAMBDAS) {
    const errors = [];
    for (const fold of folds) {
      const train = rows.filter((row) => fold.train.has(row.sessionDate)),
        test = rows.filter((row) => fold.test.has(row.sessionDate)),
        scale = featureScale(train),
        model = {
          ...V2.fitRidge(train, layer, lambda, scale.centers, scale.scales),
          ...scale,
        };
      for (const row of test) {
        const actual = row.targets[layer],
          prediction = V2.predict(model, row.features);
        if (finite(actual) && finite(prediction))
          errors.push(Math.abs(Number(actual) - prediction));
      }
    }
    const candidate = { lambda, mae: mean(errors), n: errors.length };
    if (
      !best ||
      candidate.mae < best.mae ||
      (candidate.mae === best.mae && lambda < best.lambda)
    )
      best = candidate;
  }
  return best;
}
function capacityFromPredictions(row, predictions, thresholds) {
  if (row.frozenSelectedCount === 0) return 0;
  let capacity = Math.min(5, row.rankedCount);
  for (const layer of LAYERS) {
    const value = predictions[layer.name];
    if (!finite(value) || value < thresholds[layer.name]) break;
    capacity = Math.min(layer.max, row.rankedCount);
  }
  return capacity;
}
function sessionEqualUtility(rows, capacityOf) {
  const values = [];
  for (const date of [...new Set(rows.map((row) => row.sessionDate))].sort()) {
    const session = rows
      .filter((row) => row.sessionDate === date)
      .map((row) => {
        const capacity = capacityOf(row),
          value = capacity ? row.utilityByCapacity[capacity] : null;
        return finite(value) ? Number(value) : null;
      })
      .filter(finite);
    if (session.length) values.push(mean(session));
  }
  return mean(values);
}
function mappingMetrics(rows, thresholds) {
  const sorted = [...rows].sort((a, b) =>
      a.featureCutoff.localeCompare(b.featureCutoff),
    ),
    capacities = sorted.map((row) =>
      capacityFromPredictions(row, row.oofPredictions, thresholds),
    ),
    baselineCounts = sorted.map((row) => row.frozenSelectedCount),
    utility = sessionEqualUtility(sorted, (row) =>
      capacityFromPredictions(row, row.oofPredictions, thresholds),
    ),
    baselineUtility = sessionEqualUtility(
      sorted,
      (row) => row.frozenSelectedCount,
    ),
    v2Mean = mean(capacities),
    baselineMean = mean(baselineCounts);
  return {
    utility,
    baselineUtility,
    utilityDifference: utility - baselineUtility,
    meanCount: v2Mean,
    baselineCount: baselineMean,
    countRatio: v2Mean / baselineMean,
    absoluteIncrease: v2Mean - baselineMean,
    jump: V2.jumpRate(capacities),
  };
}
function compareThresholdTuple(a, b) {
  for (const layer of LAYERS) {
    const difference = a.thresholds[layer.name] - b.thresholds[layer.name];
    if (difference) return difference;
  }
  return 0;
}

export function trainV21(rows, sourceAdmission, freshAdmission, allocation) {
  assertBaseline();
  assert(rows.length === 1780, "v2.1 development decision count must be 1780");
  const folds = foldDefinitions(rows),
    choices = Object.fromEntries(
      LAYERS.map((layer) => [
        layer.name,
        chooseLambda(rows, layer.name, folds),
      ]),
    ),
    oofRows = [];
  for (const [foldIndex, fold] of folds.entries()) {
    const train = rows.filter((row) => fold.train.has(row.sessionDate)),
      test = rows.filter((row) => fold.test.has(row.sessionDate)),
      scale = featureScale(train),
      models = Object.fromEntries(
        LAYERS.map((layer) => [
          layer.name,
          {
            ...V2.fitRidge(
              train,
              layer.name,
              choices[layer.name].lambda,
              scale.centers,
              scale.scales,
            ),
            ...scale,
          },
        ]),
      );
    for (const row of test)
      oofRows.push({
        ...row,
        oofFold: foldIndex + 1,
        oofPredictions: Object.fromEntries(
          LAYERS.map((layer) => [
            layer.name,
            V2.predict(models[layer.name], row.features),
          ]),
        ),
      });
  }
  assert(oofRows.length === 880, "v2.1 OOF decision count must be 880");
  const quantile = (values, q) => values[Math.floor((values.length - 1) * q)],
    grids = Object.fromEntries(
      LAYERS.map((layer) => {
        const values = oofRows
          .map((row) => row.oofPredictions[layer.name])
          .filter(finite)
          .sort((a, b) => a - b);
        return [
          layer.name,
          QUANTILES.map((q) =>
            round(Math.max(0, q ? quantile(values, q) : 0), 6),
          ),
        ];
      }),
    );
  let best = null;
  for (const a of grids.RANK_6_10)
    for (const b of grids.RANK_11_15)
      for (const c of grids.RANK_16_20) {
        const thresholds = { RANK_6_10: a, RANK_11_15: b, RANK_16_20: c },
          global = mappingMetrics(oofRows, thresholds),
          foldMetrics = folds.map((_, index) =>
            mappingMetrics(
              oofRows.filter((row) => row.oofFold === index + 1),
              thresholds,
            ),
          ),
          worstFoldUtilityDifference = Math.min(
            ...foldMetrics.map((item) => item.utilityDifference),
          ),
          g = SPEC.mappingSelectionContract.eligibleGlobalGates,
          eligible =
            global.utilityDifference >= g.utilityDifferenceMinimumBps &&
            global.countRatio >= g.meanCandidateCountMinimumRelativeIncrease &&
            global.absoluteIncrease >=
              g.meanCandidateCountMinimumAbsoluteIncrease &&
            global.jump <= g.maximumAdjacentDecisionJumpGreaterThanFiveRate &&
            worstFoldUtilityDifference >=
              SPEC.mappingSelectionContract.eligibleFoldGate
                .minimumUtilityDifferenceBpsInEveryHeldOutFold,
          candidate = {
            thresholds,
            global,
            foldMetrics,
            worstFoldUtilityDifference,
            eligible,
          };
        if (
          eligible &&
          (!best ||
            candidate.worstFoldUtilityDifference >
              best.worstFoldUtilityDifference ||
            (candidate.worstFoldUtilityDifference ===
              best.worstFoldUtilityDifference &&
              candidate.global.utilityDifference >
                best.global.utilityDifference) ||
            (candidate.worstFoldUtilityDifference ===
              best.worstFoldUtilityDifference &&
              candidate.global.utilityDifference ===
                best.global.utilityDifference &&
              candidate.global.meanCount < best.global.meanCount) ||
            (candidate.worstFoldUtilityDifference ===
              best.worstFoldUtilityDifference &&
              candidate.global.utilityDifference ===
                best.global.utilityDifference &&
              candidate.global.meanCount === best.global.meanCount &&
              compareThresholdTuple(candidate, best) < 0))
        )
          best = candidate;
      }
  assert(best, "V2_1_DEVELOPMENT_NO_ROBUST_MAPPING_MEETS_PRECOMMITTED_GATES");
  const fullScale = featureScale(rows),
    layers = {};
  for (const layer of LAYERS)
    layers[layer.name] = {
      ...V2.fitRidge(
        rows,
        layer.name,
        choices[layer.name].lambda,
        fullScale.centers,
        fullScale.scales,
      ),
      lambda: choices[layer.name].lambda,
      oofMaeBps: round(choices[layer.name].mae, 6),
      centers: fullScale.centers,
      scales: fullScale.scales,
    };
  const core = {
    schemaVersion: 1,
    phase: "57.selector-capacity-v2-1.model",
    status: "CAPACITY_V2_1_DEVELOPMENT_MODEL_READY",
    modelFamily: SPEC.retainedModelContract.modelFamily,
    sourceHybridModelDigest: HYBRID_MODEL.modelDigest,
    featureNames: FEATURES,
    layers,
    decisionMapping: {
      type: "SEQUENTIAL_MARGINAL_GATES",
      thresholdsBps: best.thresholds,
      actionSpace: SPEC.scope.decisionSpace,
      preserveFrozenAbstain: true,
    },
    developmentSelection: { ...best, oofDecisionCount: oofRows.length },
    guards: {
      reranking: false,
      prefixOnly: true,
      thresholdSelectionUsesOnlyHeldOutPredictions: true,
      validationUsed: false,
      oosUsed: false,
      originalOosReused: false,
      reserveBeyondOrdinal179Opened: false,
    },
    safety: SAFETY,
  };
  const model = { ...core, modelDigest: sha256(JSON.stringify(core)) };
  const freezeCore = {
    schemaVersion: 1,
    phase: "57.selector-capacity-v2-1.development-freeze",
    status: "CAPACITY_V2_1_FROZEN_BEFORE_FRESH_VALIDATION",
    datasetId: allocation.datasetId,
    sourceAdmissionSha256: sourceAdmission.admissionSha256,
    freshAdmissionSha256: freshAdmission.admissionSha256,
    sourceHybridModelDigest: HYBRID_MODEL.modelDigest,
    capacityModelDigest: model.modelDigest,
    precommitSha256:
      "21ee356efe783242d0fed2ffb638b1880a75953577e2b8fe1e5f87a8b8cb0012",
    decisionMapping: model.decisionMapping,
    validationReleased: false,
    untouchedOosReleased: false,
    safety: SAFETY,
  };
  const freeze = {
    ...freezeCore,
    freezeSha256: sha256(JSON.stringify(freezeCore)),
  };
  return {
    model,
    freeze,
    summary: {
      schemaVersion: 1,
      status: "CAPACITY_V2_1_DEVELOPMENT_COMPLETE",
      sessionCount: 89,
      decisionTimestampCount: rows.length,
      oofDecisionTimestampCount: oofRows.length,
      lambdaSelection: choices,
      developmentSelection: best,
      performanceClaimAllowed: false,
      derivedDecisionRowsPersisted: true,
      rawMarketRowsPersisted: false,
      safety: SAFETY,
    },
  };
}

function verifyModelFreeze(model, freeze) {
  assert(
    model.modelDigest === freeze.capacityModelDigest &&
      freeze.sourceHybridModelDigest === HYBRID_MODEL.modelDigest,
    "v2.1 model/freeze mismatch",
  );
  assert(
    model.modelDigest ===
      sha256(
        JSON.stringify(
          Object.fromEntries(
            Object.entries(model).filter(([key]) => key !== "modelDigest"),
          ),
        ),
      ),
    "v2.1 model digest mismatch",
  );
  assert(
    freeze.freezeSha256 ===
      sha256(
        JSON.stringify(
          Object.fromEntries(
            Object.entries(freeze).filter(([key]) => key !== "freezeSha256"),
          ),
        ),
      ),
    "v2.1 freeze digest mismatch",
  );
  assertSafety(model.safety);
  assertSafety(freeze.safety);
}
function summarizeEvaluation(rows, model, freeze, fold) {
  verifyModelFreeze(model, freeze);
  const base = V2.evaluateRows(rows, model, fold),
    pass = base.pass;
  return {
    ...base,
    schemaVersion: 1,
    phase: `57.selector-capacity-v2-1.${fold.toLowerCase()}`,
    status: `CAPACITY_V2_1_${fold}_${pass ? "GO" : "NO_GO"}`,
    capacityModelDigest: model.modelDigest,
    freezeSha256: freeze.freezeSha256,
    originalOosReused: false,
    safety: SAFETY,
  };
}
function readRows(inputRoot) {
  return recursiveFiles(inputRoot, "decision-samples.json")
    .flatMap((file) => readJson(file).rows ?? [])
    .sort((a, b) => a.featureCutoff.localeCompare(b.featureCutoff));
}

async function modeAllocate() {
  const source = readJson(process.env.SOURCE_ALLOCATION_PATH),
    allocation = buildV21Allocation(
      await requestCalendar(process.env.JQUANTS_API_KEY),
      source,
    );
  writeJson(
    "artifacts/phase57-capacity-v2-1-allocation",
    "allocation.json",
    allocation,
  );
  console.log(
    JSON.stringify({ status: allocation.status, counts: allocation.counts }),
  );
}
async function modeAdmissionShard() {
  const allocation = readJson(process.env.ALLOCATION_PATH),
    report = await runAdmissionShard({
      apiKey: process.env.JQUANTS_API_KEY,
      allocation,
      shardIndex: Number(process.env.SHARD_INDEX),
      shardCount: Number(process.env.SHARD_COUNT),
    });
  writeJson(
    `artifacts/phase57-capacity-v2-1-admission-${report.shardIndex}`,
    "admission-shard.json",
    report,
  );
  console.log(
    JSON.stringify({
      status: report.status,
      shard: report.shardIndex,
      sessions: report.audits.length,
    }),
  );
}
function modeAdmissionSummary() {
  const allocation = readJson(process.env.ALLOCATION_PATH),
    report = summarizeAdmission({
      allocation,
      inputRoot: process.env.INPUT_ROOT,
    });
  writeJson(
    "artifacts/phase57-capacity-v2-1-admission-summary",
    "admission.json",
    report,
  );
  console.log(
    JSON.stringify({
      status: report.status,
      admissionSha256: report.admissionSha256,
    }),
  );
}
async function modeDevelopmentShard() {
  const allocation = readJson(process.env.ALLOCATION_PATH),
    admission = readJson(process.env.SOURCE_ADMISSION_PATH),
    shardIndex = Number(process.env.SHARD_INDEX),
    shardCount = Number(process.env.SHARD_COUNT),
    dates = allocation.developmentDates.filter(
      (_, index) => index % shardCount === shardIndex,
    ),
    rows = await buildDecisionSamples({
      apiKey: process.env.JQUANTS_API_KEY,
      dates,
      fold: "DEVELOPMENT",
      admission,
    }),
    report = {
      schemaVersion: 1,
      status: "CAPACITY_V2_1_DEVELOPMENT_SHARD_COMPLETE",
      datasetId: allocation.datasetId,
      shardIndex,
      shardCount,
      sessionCount: dates.length,
      decisionCount: rows.length,
      rows,
      derivedDecisionRowsPersisted: true,
      rawMarketRowsPersisted: false,
      safety: SAFETY,
    };
  writeJson(
    `artifacts/phase57-capacity-v2-1-development-${shardIndex}`,
    "decision-samples.json",
    report,
  );
  console.log(
    JSON.stringify({
      status: report.status,
      shard: shardIndex,
      sessions: dates.length,
      decisions: rows.length,
    }),
  );
}
function modeDevelopment() {
  const allocation = readJson(process.env.ALLOCATION_PATH),
    sourceAdmission = readJson(process.env.SOURCE_ADMISSION_PATH),
    freshAdmission = readJson(process.env.FRESH_ADMISSION_PATH),
    rows = readRows(process.env.INPUT_ROOT),
    result = trainV21(rows, sourceAdmission, freshAdmission, allocation),
    dir = "artifacts/phase57-capacity-v2-1-development";
  writeJson(dir, "model.json", result.model);
  writeJson(dir, "freeze.json", result.freeze);
  writeJson(dir, "development-summary.json", result.summary);
  console.log(
    JSON.stringify({
      status: result.summary.status,
      modelDigest: result.model.modelDigest,
      freezeSha256: result.freeze.freezeSha256,
    }),
  );
}
async function modeEvaluationShard(fold) {
  const allocation = readJson(process.env.ALLOCATION_PATH),
    admission = readJson(process.env.ADMISSION_PATH),
    model = readJson(process.env.MODEL_PATH),
    freeze = readJson(process.env.FREEZE_PATH);
  verifyModelFreeze(model, freeze);
  const sourceDatesForFold =
      fold === "VALIDATION"
        ? allocation.freshValidation
        : allocation.freshUntouchedOos,
    shardIndex = Number(process.env.SHARD_INDEX),
    shardCount = Number(process.env.SHARD_COUNT),
    dates = sourceDatesForFold.filter(
      (_, index) => index % shardCount === shardIndex,
    ),
    rows = await buildDecisionSamples({
      apiKey: process.env.JQUANTS_API_KEY,
      dates,
      fold,
      admission,
    }),
    report = {
      schemaVersion: 1,
      status: `CAPACITY_V2_1_${fold}_SHARD_COMPLETE`,
      datasetId: allocation.datasetId,
      capacityModelDigest: model.modelDigest,
      freezeSha256: freeze.freezeSha256,
      shardIndex,
      shardCount,
      sessionCount: dates.length,
      decisionCount: rows.length,
      rows,
      derivedDecisionRowsPersisted: true,
      rawMarketRowsPersisted: false,
      safety: SAFETY,
    };
  writeJson(
    `artifacts/phase57-capacity-v2-1-${fold.toLowerCase()}-${shardIndex}`,
    "decision-samples.json",
    report,
  );
  console.log(
    JSON.stringify({
      status: report.status,
      shard: shardIndex,
      sessions: dates.length,
      decisions: rows.length,
    }),
  );
}
function modeEvaluationSummary(fold) {
  const allocation = readJson(process.env.ALLOCATION_PATH),
    model = readJson(process.env.MODEL_PATH),
    freeze = readJson(process.env.FREEZE_PATH),
    rows = readRows(process.env.INPUT_ROOT),
    expected =
      (fold === "VALIDATION"
        ? allocation.counts.freshValidation
        : allocation.counts.freshUntouchedOos) *
      Phase57FreshSessionInternals.DECISION_TIMES.length;
  assert(
    rows.length === expected,
    `${fold} decision count ${rows.length} != ${expected}`,
  );
  const report = summarizeEvaluation(rows, model, freeze, fold),
    dir = `artifacts/phase57-capacity-v2-1-${fold.toLowerCase()}-summary`,
    name = `${fold.toLowerCase()}-summary.json`;
  writeJson(dir, name, report);
  console.log(
    JSON.stringify({
      status: report.status,
      pass: report.pass,
      metrics: report.metrics,
    }),
  );
  if (fold === "VALIDATION" && !report.pass) process.exitCode = 20;
}
function modeFinal() {
  const validation = readJson(process.env.VALIDATION_PATH),
    oos = readJson(process.env.OOS_PATH),
    model = readJson(process.env.MODEL_PATH),
    freeze = readJson(process.env.FREEZE_PATH);
  verifyModelFreeze(model, freeze);
  assert(
    validation.pass === true,
    "v2.1 final requires passing fresh Validation",
  );
  const ratio =
      oos.metrics.capacityV2Selected.mean /
      validation.metrics.capacityV2Selected.mean,
    gates = {
      ...oos.gates,
      validationPassed: true,
      validationToOosMeanCapacityRatio: ratio >= 0.75 && ratio <= 1.25,
    },
    pass = Object.values(gates).every(Boolean),
    report = {
      schemaVersion: 1,
      phase: "57.selector-capacity-v2-1.final",
      status: pass ? "CAPACITY_V2_1_FINAL_GO" : "CAPACITY_V2_1_FINAL_NO_GO",
      validation,
      oos,
      validationToOosMeanCapacityRatio: round(ratio, 6),
      gates,
      capacityModelDigest: model.modelDigest,
      freezeSha256: freeze.freezeSha256,
      originalOosReused: false,
      reserveRemaining: 103,
      automaticPromotion: false,
      safety: SAFETY,
    };
  writeJson(
    "artifacts/phase57-capacity-v2-1-final",
    "final-summary.json",
    report,
  );
  console.log(
    JSON.stringify({
      status: report.status,
      freezeSha256: report.freezeSha256,
      reserveRemaining: 103,
    }),
  );
}
function modeValidationNoGoFinal() {
  const validation = readJson(process.env.VALIDATION_PATH),
    model = readJson(process.env.MODEL_PATH),
    freeze = readJson(process.env.FREEZE_PATH);
  verifyModelFreeze(model, freeze);
  assert(
    validation.fold === "VALIDATION" && validation.pass === false,
    "v2.1 Validation NO-GO final requires pass=false",
  );
  const report = {
    schemaVersion: 1,
    phase: "57.selector-capacity-v2-1.final",
    status: "CAPACITY_V2_1_FINAL_NO_GO",
    reason: "FRESH_VALIDATION_GATE_FAILED",
    validation,
    oos: null,
    untouchedOosReleased: false,
    capacityModelDigest: model.modelDigest,
    freezeSha256: freeze.freezeSha256,
    originalOosReused: false,
    reserveRemaining: 103,
    automaticPromotion: false,
    safety: SAFETY,
  };
  writeJson(
    "artifacts/phase57-capacity-v2-1-final",
    "final-summary.json",
    report,
  );
  console.log(
    JSON.stringify({
      status: report.status,
      reason: report.reason,
      untouchedOosReleased: false,
      freezeSha256: report.freezeSha256,
    }),
  );
}

async function main() {
  const mode = process.argv[2];
  if (mode === "allocate") return modeAllocate();
  if (mode === "admission-shard") return modeAdmissionShard();
  if (mode === "admission-summary") return modeAdmissionSummary();
  if (mode === "development-shard") return modeDevelopmentShard();
  if (mode === "development") return modeDevelopment();
  if (mode === "validation-shard") return modeEvaluationShard("VALIDATION");
  if (mode === "validation-summary") return modeEvaluationSummary("VALIDATION");
  if (mode === "oos-shard") return modeEvaluationShard("UNTOUCHED_OOS");
  if (mode === "oos-summary") return modeEvaluationSummary("UNTOUCHED_OOS");
  if (mode === "final") return modeFinal();
  if (mode === "validation-no-go-final") return modeValidationNoGoFinal();
  throw new Error("unsupported Capacity v2.1 mode");
}
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
)
  main().catch((error) => {
    console.error(`CAPACITY_V2_1_FAIL ${safeError(error)}`);
    process.exitCode = 1;
  });

export const Phase57CapacityV21Internals = Object.freeze({
  buildV21Allocation,
  freshAllocationRows,
  summarizeAdmission,
  buildDecisionSamples,
  trainV21,
  mappingMetrics,
  summarizeEvaluation,
});
