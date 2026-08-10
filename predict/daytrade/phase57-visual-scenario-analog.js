import { findIntradayHistoricalAnalogs } from './phase57-intraday-historical-analog.js';
import { PHASE57_P23_12_SAFETY } from './phase57-visual-chart-reasoning.js';

export const P23_13_VISUAL_ANALOG_FEATURE_KEYS = Object.freeze([
  'structureCoherence',
  'directionalPressure',
  'wickControl',
  'participation',
  'extensionHealth',
  'spaceToObstacle',
  'volatilityTransition',
  'setupGeometryFit',
  'alignedSlope5m',
  'alignedSlope15m',
  'alignedSlope60m',
  'alignedSlope1d',
  'openSpaceFlag',
]);

export const P23_13_VISUAL_ANALOG_POLICY = Object.freeze({
  phase: '57.p23.13',
  id: 'VISUAL_SCENARIO_CAUSAL_ANALOG_V1',
  horizonBars: 12,
  horizonMinutes: 60,
  topK: 40,
  minimumAnalogs: 20,
  minimumFeatureFraction: 0.70,
  sameSetupOnly: true,
  sameSessionAnalogsAllowed: false,
  sameSymbolOnly: false,
  timeBucketPenalty: 0.25,
  roundTripFrictionPct: 0.05,
  outcomeTuned: false,
  predictionUsedAsEntryGate: false,
  externalVisionCallEnabled: false,
  recommendationAllowed: false,
  edgeClaimAllowed: false,
});

export const PHASE57_P23_13_SAFETY = Object.freeze({
  ...PHASE57_P23_12_SAFETY,
  mode: 'PHASE57_P23_13_VISUAL_SCENARIO_ANALOG_READ_ONLY_RESEARCH',
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

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const JST = new Intl.DateTimeFormat('en-CA', {
  timeZone:'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit',
  hour:'2-digit', minute:'2-digit', hourCycle:'h23',
});

function jstParts(timestamp) {
  const p = Object.fromEntries(JST.formatToParts(new Date(timestamp)).map(part => [part.type,part.value]));
  return { date:`${p.year}-${p.month}-${p.day}`, minutes:Number(p.hour) * 60 + Number(p.minute) };
}

function timeBucket(timestamp) {
  const { minutes } = jstParts(timestamp);
  if (minutes < 10 * 60) return 'OPEN';
  if (minutes < 11 * 60 + 30) return 'MID_AM';
  if (minutes < 13 * 60 + 30) return 'LUNCH_RETURN';
  if (minutes < 14 * 60 + 30) return 'MID_PM';
  return 'CLOSE';
}

function signFromRecord(record) {
  if (record?.direction === 'UP') return 1;
  if (record?.direction === 'DOWN') return -1;
  const setup = String(record?.setup ?? '');
  if (setup.endsWith('_UP')) return 1;
  if (setup.endsWith('_DOWN')) return -1;
  return 0;
}

export function visualRecordFeatures(record = {}) {
  const components = record?.visualComponents ?? {};
  const geometry = record?.visualGeometry ?? {};
  const sign = signFromRecord(record);
  return Object.freeze({
    structureCoherence: finite(components.structureCoherence) ? Number(components.structureCoherence) : null,
    directionalPressure: finite(components.directionalPressure) ? Number(components.directionalPressure) : null,
    wickControl: finite(components.wickControl) ? Number(components.wickControl) : null,
    participation: finite(components.participation) ? Number(components.participation) : null,
    extensionHealth: finite(components.extensionHealth) ? Number(components.extensionHealth) : null,
    spaceToObstacle: finite(components.spaceToObstacle) ? Number(components.spaceToObstacle) : null,
    volatilityTransition: finite(components.volatilityTransition) ? Number(components.volatilityTransition) : null,
    setupGeometryFit: finite(components.setupGeometryFit) ? Number(components.setupGeometryFit) : null,
    alignedSlope5m: finite(geometry.slope5mPctPerBar) ? Number(geometry.slope5mPctPerBar) * sign : null,
    alignedSlope15m: finite(geometry.slope15mPctPerBar) ? Number(geometry.slope15mPctPerBar) * sign : null,
    alignedSlope60m: finite(geometry.slope60mPctPerBar) ? Number(geometry.slope60mPctPerBar) * sign : null,
    alignedSlope1d: finite(geometry.slope1dPctPerBar) ? Number(geometry.slope1dPctPerBar) * sign : null,
    openSpaceFlag: geometry.openSpaceAhead === true ? 1 : 0,
  });
}

export function visualRecordToAnalogCandidate(record = {}) {
  const outcome = record?.outcome60m;
  if (!outcome || !finite(outcome.directionalReturnPct) || !record.featureCutoff || !record.sessionDate) return null;
  return Object.freeze({
    id:`${record.symbol}|${record.featureCutoff}|${record.setup}|60m`,
    symbol:String(record.symbol ?? ''),
    sessionDate:String(record.sessionDate),
    outcomeSessionDate:String(record.sessionDate),
    featureCutoff:new Date(record.featureCutoff).toISOString(),
    outcomeAt:new Date(outcome.outcomeAt).toISOString(),
    horizonBars:P23_13_VISUAL_ANALOG_POLICY.horizonBars,
    features:visualRecordFeatures(record),
    context:Object.freeze({ timeBucket:timeBucket(record.featureCutoff), regime:String(record.setup ?? '') }),
    actualReturnPct:Number(outcome.directionalReturnPct),
    absMovePct:Math.abs(Number(outcome.directionalReturnPct)),
    mfePct:finite(outcome.mfePct) ? Number(outcome.mfePct) : null,
    maePct:finite(outcome.maePct) ? Number(outcome.maePct) : null,
    pointInTimeValid:true,
    intradayOnly:true,
  });
}

export function visualRecordToAnalogQuery(record = {}) {
  if (!record.featureCutoff || !record.sessionDate) throw new TypeError('visual record requires featureCutoff and sessionDate');
  return Object.freeze({
    symbol:String(record.symbol ?? ''),
    sessionDate:String(record.sessionDate),
    asOf:new Date(record.featureCutoff).toISOString(),
    featureCutoff:new Date(record.featureCutoff).toISOString(),
    horizonBars:P23_13_VISUAL_ANALOG_POLICY.horizonBars,
    features:visualRecordFeatures(record),
    context:Object.freeze({ timeBucket:timeBucket(record.featureCutoff), regime:String(record.setup ?? '') }),
  });
}

export function findVisualScenarioAnalogs({ record, historyRecords = [] } = {}) {
  const setup = String(record?.setup ?? '');
  const candidates = (Array.isArray(historyRecords) ? historyRecords : [])
    .filter(row => !P23_13_VISUAL_ANALOG_POLICY.sameSetupOnly || String(row?.setup ?? '') === setup)
    .map(visualRecordToAnalogCandidate)
    .filter(Boolean);
  const result = findIntradayHistoricalAnalogs({
    query:visualRecordToAnalogQuery(record),
    candidates,
    featureKeys:P23_13_VISUAL_ANALOG_FEATURE_KEYS,
    topK:P23_13_VISUAL_ANALOG_POLICY.topK,
    minimumAnalogs:P23_13_VISUAL_ANALOG_POLICY.minimumAnalogs,
    minFeatureFraction:P23_13_VISUAL_ANALOG_POLICY.minimumFeatureFraction,
    excludeCurrentSession:true,
    sameSymbolOnly:false,
    contextPenalties:{ timeBucket:P23_13_VISUAL_ANALOG_POLICY.timeBucketPenalty, regime:1.0 },
    roundTripCostPct:P23_13_VISUAL_ANALOG_POLICY.roundTripFrictionPct,
  });
  const meanAligned = result?.summary?.weightedMeanReturnPct;
  const expectedAlignedNetAfterCost = finite(meanAligned)
    ? Number(meanAligned) - P23_13_VISUAL_ANALOG_POLICY.roundTripFrictionPct
    : null;
  return Object.freeze({
    phase:'57.p23.13-visual-scenario-analog',
    status:result.status,
    setup,
    queryCutoff:record.featureCutoff,
    analogCount:result?.summary?.sampleCount ?? 0,
    effectiveAnalogCount:result?.summary?.effectiveSampleSize ?? 0,
    expectedAlignedReturnPct:finite(meanAligned) ? Number(meanAligned) : null,
    expectedAlignedNetAfterCostPct:expectedAlignedNetAfterCost,
    expectedSetupSuccessProbability:finite(result?.summary?.weightedUpRate) ? Number(result.summary.weightedUpRate) : null,
    weightedMeanMfePct:finite(result?.summary?.weightedMeanMfePct) ? Number(result.summary.weightedMeanMfePct) : null,
    weightedMeanMaePct:finite(result?.summary?.weightedMeanMaePct) ? Number(result.summary.weightedMeanMaePct) : null,
    analogQualityScore:Number(result?.analogQualityScore ?? 0),
    candidateAudit:result.candidateAudit,
    selectedAnalogs:result.analogs,
    distanceUsesOutcomeLabels:false,
    outcomeDerivedFeaturesAllowed:false,
    sameSetupOnly:true,
    sameSessionAnalogsAllowed:false,
    predictionUsedAsEntryGate:false,
    pointInTime:true,
    futureOutcomeUsedForSimilarity:false,
    recommendationAllowed:false,
    edgeClaimAllowed:false,
    transmitted:false,
    ...PHASE57_P23_13_SAFETY,
    safety:PHASE57_P23_13_SAFETY,
  });
}

export default {
  P23_13_VISUAL_ANALOG_FEATURE_KEYS,
  P23_13_VISUAL_ANALOG_POLICY,
  PHASE57_P23_13_SAFETY,
  visualRecordFeatures,
  visualRecordToAnalogCandidate,
  visualRecordToAnalogQuery,
  findVisualScenarioAnalogs,
};
