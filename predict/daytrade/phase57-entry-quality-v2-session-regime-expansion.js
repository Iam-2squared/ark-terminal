import { PHASE58_P13_FROZEN_POLICY } from '../scalping/phase58-phase57-prospective-pipeline.js';
import { PHASE57_ENTRY_QUALITY_V2_SAFETY } from './phase57-entry-quality-v2-research.js';

export const ENTRY_V2_SESSION_EXPANSION_POLICY = Object.freeze({
  phase: '57.entry-quality-v2.session-regime-expansion',
  currentFrozenBaselineEarliestReplaySession: '2026-08-13',
  currentFrozenHistoryEndSession: '2026-08-12',
  sourceClasses: Object.freeze({
    currentFrozen: 'CURRENT_FROZEN_P21_BASELINE',
    historicalMethodology: 'HISTORICALLY_RECONSTRUCTED_P21_METHODOLOGY',
  }),
  sessionCheckpoints: Object.freeze([30, 50, 100]),
  providerAdoptionRequirements: Object.freeze([
    'TIMESTAMP_SEMANTICS_EXPLAINED_AND_OVERLAP_TESTED',
    'OHLCV_SEMANTICS_EXPLAINED_AND_OVERLAP_TESTED',
    'SOURCE_LINEAGE_AND_RAW_SHA256_RETAINABLE',
    'CORPORATE_ACTION_SEMANTICS_EXPLAINED',
    'HISTORICAL_UNIVERSE_COVERAGE_AUDITABLE',
    'LICENSE_PERMITS_THE_INTENDED_PRIVATE_RESEARCH_AND_STORAGE',
  ]),
  untouchedOos: Object.freeze({
    currentPoolRole: 'DEVELOPMENT_VALIDATION_DIAGNOSTIC_ONLY',
    reservation: 'FIRST_THREE_ELIGIBLE_FUTURE_SESSIONS_AFTER_MODEL_AND_THRESHOLD_FREEZE',
    consumeBeforeFreeze: false,
  }),
  modelFittingAllowed: false,
  performanceSelectionAllowed: false,
});

export const ENTRY_V2_SESSION_EXPANSION_SAFETY = Object.freeze({
  ...PHASE57_ENTRY_QUALITY_V2_SAFETY,
  phase: ENTRY_V2_SESSION_EXPANSION_POLICY.phase,
  mode: 'READ_ONLY_OFFLINE_SOURCE_AND_CAUSALITY_AUDIT',
  researchOnly: true,
  prospective: false,
  formalOos: false,
  freshHoldoutConsumed: false,
});

const FALSE_KEYS = Object.freeze([
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed',
  'productionUpdateAllowed', 'transmitted',
]);

function assertSafe() {
  for (const key of FALSE_KEYS) {
    if (ENTRY_V2_SESSION_EXPANSION_SAFETY[key] !== false) {
      throw new Error(`ENTRY_V2_SESSION_EXPANSION_UNSAFE_${key}`);
    }
  }
}

export function describeFrozenP21PriorDependency() {
  assertSafe();
  const policy = PHASE58_P13_FROZEN_POLICY;
  return Object.freeze({
    policyId: policy.policyId,
    methodologyFrozenNotParameterVector: true,
    historicalUniverse: Object.freeze([...policy.historicalUniverse]),
    horizonsBars: Object.freeze([...policy.horizonsBars]),
    selectionOptions: Object.freeze({
      innerTrainFraction: policy.selectionOptions.innerTrainFraction,
      innerTestFraction: policy.selectionOptions.innerTestFraction,
      innerMinTrainRows: policy.selectionOptions.innerMinTrainRows,
      thresholds: Object.freeze([...policy.selectionOptions.thresholds]),
      minInnerSignals: policy.selectionOptions.minInnerSignals,
      minimumInnerNetReturnPct: policy.selectionOptions.minimumInnerNetReturnPct,
      roundTripCostPct: policy.selectionOptions.roundTripCostPct,
    }),
    requiredPriorRowSemantics: Object.freeze({
      commonRowKeyAcrossAllHorizons: true,
      featureCutoffStrictlyBeforeOutcomeAt: true,
      outcomeAtOnOrBeforeDecisionTimestamp: true,
      labelsAndActualReturnsRequired: true,
      currentDecisionRowOutcomeFree: true,
      currentCompletedPrefixMinimumBars: 6,
    }),
    selectedAtEveryDecisionFromPriorOnlyRows: Object.freeze([
      'HORIZON', 'FEATURE_FAMILY', 'MODEL_TYPE_AND_CONFIG', 'CONFIDENCE_THRESHOLD',
    ]),
    refitAtEveryDecisionFromPriorOnlyRows: true,
  });
}

export function classifyHistoricalP21Replay({
  decisionSessionDate,
  historyEndSessionDate,
  historyBuiltOnlyFromDataAvailableBeforeDecision = false,
  usesCurrentFrozenHistoryPack = false,
} = {}) {
  assertSafe();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(decisionSessionDate))) {
    throw new Error('ENTRY_V2_DECISION_SESSION_REQUIRED');
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(historyEndSessionDate))) {
    throw new Error('ENTRY_V2_HISTORY_END_SESSION_REQUIRED');
  }
  if (historyEndSessionDate >= decisionSessionDate) {
    return Object.freeze({
      eligible: false,
      status: 'BLOCKED_FUTURE_OR_SAME_SESSION_P21_HISTORY',
      pitViolationPrevented: true,
      researchClass: null,
    });
  }
  if (usesCurrentFrozenHistoryPack) {
    const expectedEnd = ENTRY_V2_SESSION_EXPANSION_POLICY.currentFrozenHistoryEndSession;
    if (historyEndSessionDate !== expectedEnd || decisionSessionDate < ENTRY_V2_SESSION_EXPANSION_POLICY.currentFrozenBaselineEarliestReplaySession) {
      return Object.freeze({
        eligible: false,
        status: 'BLOCKED_CURRENT_FROZEN_HISTORY_OUTSIDE_FORWARD_REPLAY_WINDOW',
        pitViolationPrevented: true,
        researchClass: null,
      });
    }
    return Object.freeze({
      eligible: true,
      status: 'CURRENT_FROZEN_P21_FORWARD_REPLAY_ELIGIBLE',
      pitViolationPrevented: false,
      researchClass: ENTRY_V2_SESSION_EXPANSION_POLICY.sourceClasses.currentFrozen,
    });
  }
  if (!historyBuiltOnlyFromDataAvailableBeforeDecision) {
    return Object.freeze({
      eligible: false,
      status: 'BLOCKED_HISTORICAL_P21_CAUSAL_LINEAGE_UNPROVEN',
      pitViolationPrevented: true,
      researchClass: null,
    });
  }
  return Object.freeze({
    eligible: true,
    status: 'HISTORICAL_P21_METHODOLOGY_CAUSALLY_RECONSTRUCTED',
    pitViolationPrevented: false,
    researchClass: ENTRY_V2_SESSION_EXPANSION_POLICY.sourceClasses.historicalMethodology,
    sameAsCurrentFrozenBaseline: false,
  });
}

export function assessHistoricalProvider(provider = {}) {
  assertSafe();
  const checks = Object.freeze({
    timestampSemantics: provider.timestampSemanticsDocumented === true && provider.timestampOverlapPilotPassed === true,
    ohlcvSemantics: provider.ohlcvSemanticsDocumented === true && provider.ohlcvOverlapPilotPassed === true,
    immutableLineage: provider.rawFingerprintRetainable === true && provider.sourceLineageRetainable === true,
    corporateActions: provider.corporateActionSemanticsDocumented === true,
    historicalUniverse: provider.historicalUniverseCoverageAuditable === true,
    intendedUseLicensed: provider.intendedUseLicensed === true,
  });
  const blockers = Object.entries(checks).filter(([, passed]) => !passed).map(([name]) => name);
  return Object.freeze({
    providerId: String(provider.providerId ?? ''),
    checks,
    adoptionReady: blockers.length === 0,
    blockers: Object.freeze(blockers),
    pilotRequired: provider.timestampOverlapPilotPassed !== true || provider.ohlcvOverlapPilotPassed !== true,
  });
}

export function buildSessionCheckpointProjection({
  currentSessions = 16,
  currentCandidates = 445,
  maximumAdditionalSessions = 0,
} = {}) {
  assertSafe();
  const sessionYield = currentSessions > 0 ? currentCandidates / currentSessions : null;
  const maximumSessions = currentSessions + Math.max(0, Number(maximumAdditionalSessions) || 0);
  return Object.freeze({
    currentSessions,
    currentCandidates,
    observedCandidatesPerSession: sessionYield,
    maximumSessions,
    checkpoints: Object.freeze(Object.fromEntries(ENTRY_V2_SESSION_EXPANSION_POLICY.sessionCheckpoints.map(checkpoint => [
      checkpoint,
      Object.freeze({
        reachableByProviderPeriod: maximumSessions >= checkpoint,
        additionalSessionsRequired: Math.max(0, checkpoint - currentSessions),
        mechanicalCandidatePlanningEstimate: sessionYield === null ? null : Math.round(checkpoint * sessionYield),
        performanceForecast: false,
      }),
    ]))),
  });
}

export function validateOverlapPilotManifest(manifest = {}) {
  assertSafe();
  const blockers = [];
  if (manifest.readOnly !== true) blockers.push('PILOT_NOT_EXPLICITLY_READ_ONLY');
  if (manifest.sourceClass !== 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED') blockers.push('INVALID_SOURCE_CLASS');
  if (manifest.classification !== 'DEVELOPMENT_ONLY_NON_PROSPECTIVE') blockers.push('INVALID_CLASSIFICATION');
  if (!Array.isArray(manifest.sessions) || manifest.sessions.length < 2) blockers.push('INSUFFICIENT_OVERLAP_SESSIONS');
  if (!Array.isArray(manifest.symbols) || manifest.symbols.length < 2) blockers.push('INSUFFICIENT_OVERLAP_SYMBOLS');
  for (const field of ['provider', 'interval', 'timezone', 'normalizerVersion', 'parserVersion']) {
    if (!String(manifest[field] ?? '').trim()) blockers.push(`MISSING_${field.toUpperCase()}`);
  }
  if (manifest.rawSha256Required !== true) blockers.push('RAW_SHA256_NOT_REQUIRED');
  if (manifest.timestampSemanticsClaimedBeforePilot === true) blockers.push('TIMESTAMP_SEMANTICS_PREJUDGED');
  if (manifest.noTradeBarsMayBeSynthesized !== false) blockers.push('NO_TRADE_BAR_POLICY_NOT_FAIL_CLOSED');
  return Object.freeze({ valid: blockers.length === 0, blockers: Object.freeze(blockers) });
}

export default {
  ENTRY_V2_SESSION_EXPANSION_POLICY,
  ENTRY_V2_SESSION_EXPANSION_SAFETY,
  describeFrozenP21PriorDependency,
  classifyHistoricalP21Replay,
  assessHistoricalProvider,
  buildSessionCheckpointProjection,
  validateOverlapPilotManifest,
};
