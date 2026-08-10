import { PHASE57_P23_10G_SAFETY, simulateSetupSpecificManagedExit } from './phase57-setup-specific-trade-management.js';
import { simulateFrozenRatchetExit } from './phase57-frozen-ratchet-exit.js';

export const P23_10H_DIRECTION_SETUP_POLICY = Object.freeze({
  phase: '57.p23.10h',
  id: 'DIRECTION_ASYMMETRIC_SETUP_MANAGEMENT_V1',
  developmentEvidenceSource: 'P23.10G_DIRECTION_SPLIT_ONLY',
  longPolicy: 'SETUP_STRUCTURAL_INVALIDATION_OVER_FROZEN_RATCHET',
  shortPolicy: 'FROZEN_RATCHET_BASELINE_ONLY',
  rationale: 'P23.10G established direction asymmetry; P23.10H freezes architecture choice only and performs no numeric retuning.',
  q4ThresholdRetuningAllowed: false,
  setupRuleRetuningAllowed: false,
  numericExitParameterSearchAllowed: false,
  directionSpecificNumericParameterSearchAllowed: false,
  setupSpecificNumericParameterSearchAllowed: false,
  futureOutcomeSelectionAllowed: false,
  pairedEntrySetRequired: true,
  recommendationAllowed: false,
  edgeClaimAllowed: false,
});

export const PHASE57_P23_10H_SAFETY = Object.freeze({
  ...PHASE57_P23_10G_SAFETY,
  mode: 'PHASE57_P23_10H_DIRECTION_SETUP_MANAGEMENT_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
});

function sign(direction) {
  if (direction === 'UP' || direction === 'LONG' || direction === 1) return 1;
  if (direction === 'DOWN' || direction === 'SHORT' || direction === -1 || direction === 0) return -1;
  throw new TypeError('direction must be UP/DOWN, LONG/SHORT, or +/-1');
}

export function simulateDirectionSetupManagedExit({ setup, perception, entryPrice, direction, contextBars = [], futureBars = [], sessionDate = null } = {}) {
  const directionSign = sign(direction);
  if (directionSign === -1) {
    const baseline = simulateFrozenRatchetExit({
      entryPrice,
      signalDirection: 'SHORT',
      contextBars,
      futureBars,
      frozenEntry: true,
      sessionDate,
    });
    if (!baseline) return null;
    return Object.freeze({
      ...baseline,
      phase: '57.p23.10h-direction-setup-management',
      managerVariant: 'SHORT_FROZEN_RATCHET_BASELINE_ONLY',
      directionArchitecture: 'SHORT_BASELINE_ONLY',
      structuralInvalidationTriggeredBeforeBaseline: false,
      numericRetuningUsed: false,
      ...PHASE57_P23_10H_SAFETY,
      safety: PHASE57_P23_10H_SAFETY,
    });
  }

  const managed = simulateSetupSpecificManagedExit({
    setup,
    perception,
    entryPrice,
    direction: 'UP',
    contextBars,
    futureBars,
    sessionDate,
  });
  if (!managed) return null;
  return Object.freeze({
    ...managed,
    phase: '57.p23.10h-direction-setup-management',
    managerVariant: managed.structuralInvalidationTriggeredBeforeBaseline
      ? 'LONG_SETUP_STRUCTURAL_INVALIDATION_EARLIER_THAN_RATCHET'
      : 'LONG_FROZEN_RATCHET_SURVIVED',
    directionArchitecture: 'LONG_SETUP_STRUCTURAL_INVALIDATION',
    numericRetuningUsed: false,
    ...PHASE57_P23_10H_SAFETY,
    safety: PHASE57_P23_10H_SAFETY,
  });
}

export default {
  P23_10H_DIRECTION_SETUP_POLICY,
  PHASE57_P23_10H_SAFETY,
  simulateDirectionSetupManagedExit,
};
