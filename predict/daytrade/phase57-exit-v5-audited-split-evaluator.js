import {
  PHASE57_EXIT_V5_PAIRED_SAFETY,
  assertExitV5PairedSafety,
  runExitV5FourWayPairedEvaluation,
} from './phase57-exit-v5-paired-evaluator.js';

const EVALUATION_SPLITS = Object.freeze(['validation', 'oos', 'prospective']);
const SAFETY_FALSE_KEYS = Object.freeze([
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
]);

export const PHASE57_EXIT_V5_AUDITED_SPLIT_POLICY = Object.freeze({
  phase: '57.exit-v5.audited-split-paired.v1',
  evaluationSplits: EVALUATION_SPLITS,
  splitSourceRequired: 'buildPurgedExitV5Split',
  boundaryPurgingRequired: true,
  wholeBoundarySessionPurgingRequired: true,
  fullTradeTrajectoryMustRemainInsideSplit: true,
  fittedDevelopmentBoundaryMustMatchSplit: true,
  evaluationLabelsUsedByDecision: false,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
  automaticPromotionAllowed: false,
});

export const PHASE57_EXIT_V5_AUDITED_SPLIT_SAFETY = Object.freeze({
  ...PHASE57_EXIT_V5_PAIRED_SAFETY,
  researchOnly: true,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

function isoMillis(value, name) {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) throw new Error(`${name} must be an ISO timestamp`);
  return parsed;
}

function assertAuditedSplit(purgedSplit) {
  if (purgedSplit?.splitPolicy?.chronological !== true
    || purgedSplit?.splitPolicy?.labelBoundaryPurged !== true
    || purgedSplit?.splitPolicy?.sessionAware !== true) {
    throw new Error('audited chronological label- and session-purged split is required');
  }
  if (purgedSplit.splitPolicy.boundarySessionTreatment !== 'PURGE_ENTIRE_SESSION') {
    throw new Error('boundary sessions must be purged in full');
  }

  const developmentEndMs = isoMillis(purgedSplit?.boundaries?.developmentEnd, 'developmentEnd');
  const validationEndMs = isoMillis(purgedSplit?.boundaries?.validationEnd, 'validationEnd');
  const oosEndMs = isoMillis(purgedSplit?.boundaries?.oosEnd, 'oosEnd');
  if (!(developmentEndMs < validationEndMs && validationEndMs < oosEndMs)) {
    throw new Error('audited split boundaries must be strictly increasing');
  }

  return Object.freeze({
    developmentEnd: new Date(developmentEndMs).toISOString(),
    validationEnd: new Date(validationEndMs).toISOString(),
    oosEnd: new Date(oosEndMs).toISOString(),
    developmentEndMs,
    validationEndMs,
    oosEndMs,
    purgedSessionKeys: Object.freeze([...(purgedSplit.splitPolicy.purgedSessionKeys ?? [])].map(String).sort()),
  });
}

function splitWindow(boundaries, splitName) {
  if (!EVALUATION_SPLITS.includes(splitName)) {
    throw new Error(`splitName must be one of ${EVALUATION_SPLITS.join(', ')}`);
  }
  if (splitName === 'validation') {
    return Object.freeze({ lowerExclusive: boundaries.developmentEndMs, upperInclusive: boundaries.validationEndMs });
  }
  if (splitName === 'oos') {
    return Object.freeze({ lowerExclusive: boundaries.validationEndMs, upperInclusive: boundaries.oosEndMs });
  }
  return Object.freeze({ lowerExclusive: boundaries.oosEndMs, upperInclusive: null });
}

export function assertExitV5AuditedSplitSafety() {
  assertExitV5PairedSafety();
  for (const key of SAFETY_FALSE_KEYS) {
    if (PHASE57_EXIT_V5_AUDITED_SPLIT_SAFETY[key] !== false) throw new Error(`unsafe audited EXIT v5 flag: ${key}`);
  }
  if (PHASE57_EXIT_V5_AUDITED_SPLIT_SAFETY.researchOnly !== true) throw new Error('audited EXIT v5 evaluator must remain researchOnly');
  return true;
}

/**
 * Guards the outer evaluation boundary at whole-trade granularity.
 * A trade belongs to one split only when its entry is after that split's lower
 * boundary and its entire supplied finalized-bar trajectory remains at or before
 * the split's upper boundary. Prospective has no upper boundary.
 *
 * This is intentionally stricter than merely checking entry > developmentEnd:
 * an OOS request cannot silently consume validation rows, and a validation/OOS
 * trade cannot leak its realized trajectory across the next outer boundary.
 */
export function assertExitV5AuditedEvaluationRows({ evaluationRows, purgedSplit, splitName } = {}) {
  assertExitV5AuditedSplitSafety();
  if (!Array.isArray(evaluationRows) || evaluationRows.length === 0) throw new Error('evaluationRows must be a non-empty array');
  const boundaries = assertAuditedSplit(purgedSplit);
  const window = splitWindow(boundaries, splitName);
  const purgedSessions = new Set(boundaries.purgedSessionKeys);
  let previousEntryMs = -Infinity;

  for (const [index, row] of evaluationRows.entries()) {
    const entryMs = isoMillis(row?.entryTimestamp, `evaluationRows[${index}].entryTimestamp`);
    if (entryMs < previousEntryMs) throw new Error('evaluationRows must be chronological');
    previousEntryMs = entryMs;

    if (!(entryMs > window.lowerExclusive)) {
      throw new Error(`${splitName} row must start strictly after its lower split boundary`);
    }
    if (window.upperInclusive !== null && entryMs > window.upperInclusive) {
      throw new Error(`${splitName} row starts after its upper split boundary`);
    }

    const sessionKey = String(row?.sessionDate ?? '').trim();
    if (!sessionKey) throw new Error(`evaluationRows[${index}].sessionDate is required`);
    if (purgedSessions.has(sessionKey)) {
      throw new Error(`${splitName} row belongs to a purged boundary session`);
    }

    if (!Array.isArray(row?.futureBars) || row.futureBars.length === 0) {
      throw new Error(`evaluationRows[${index}].futureBars must contain finalized bars`);
    }
    let trajectoryEndMs = -Infinity;
    for (const [barIndex, bar] of row.futureBars.entries()) {
      const barMs = isoMillis(bar?.timestamp ?? bar?.time, `evaluationRows[${index}].futureBars[${barIndex}].timestamp`);
      if (barMs <= entryMs) throw new Error('evaluation future bars must be strictly after entryTimestamp');
      trajectoryEndMs = Math.max(trajectoryEndMs, barMs);
    }
    if (window.upperInclusive !== null && trajectoryEndMs > window.upperInclusive) {
      throw new Error(`${splitName} trade trajectory crosses its upper split boundary`);
    }
  }

  return Object.freeze({
    status: 'EXIT_V5_AUDITED_SPLIT_ROWS_CONFIRMED',
    splitName,
    rowCount: evaluationRows.length,
    boundaries: Object.freeze({
      developmentEnd: boundaries.developmentEnd,
      validationEnd: boundaries.validationEnd,
      oosEnd: boundaries.oosEnd,
    }),
    fullTradeTrajectoryContained: true,
    purgedBoundarySessionsExcluded: true,
    evaluationLabelsUsedByDecision: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

/**
 * Strict outer-split entrypoint for the existing four-way paired evaluator.
 * The underlying v3/v4/v5 policies are unchanged; this wrapper only rejects
 * evaluation rows that do not belong to the requested audited split.
 */
export function runExitV5AuditedSplitPairedEvaluation({
  evaluationRows,
  purgedSplit,
  fittedModels,
  splitName,
  ...options
} = {}) {
  const splitAudit = assertExitV5AuditedEvaluationRows({ evaluationRows, purgedSplit, splitName });
  if (String(fittedModels?.developmentEnd ?? '') !== splitAudit.boundaries.developmentEnd) {
    throw new Error('fitted v5 development boundary does not match audited split');
  }

  const result = runExitV5FourWayPairedEvaluation({
    evaluationRows,
    fittedModels,
    splitName,
    ...options,
  });

  return Object.freeze({
    ...result,
    splitAudit,
    methodology: Object.freeze({
      ...result.methodology,
      exactOuterSplitMembershipEnforced: true,
      fullTradeTrajectoryContainedInSplit: true,
      purgedBoundarySessionsExcluded: true,
    }),
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

export default {
  PHASE57_EXIT_V5_AUDITED_SPLIT_POLICY,
  PHASE57_EXIT_V5_AUDITED_SPLIT_SAFETY,
  assertExitV5AuditedSplitSafety,
  assertExitV5AuditedEvaluationRows,
  runExitV5AuditedSplitPairedEvaluation,
};
