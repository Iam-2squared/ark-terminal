import { buildProspectiveP21HistoricalRows } from '../daytrade/phase57-p21-prospective-history.js';
import { buildProspectiveP21FeatureFeed } from '../daytrade/phase57-p21-prospective-feature-feed.js';
import { buildProspectiveP21FrozenDecision } from '../daytrade/phase57-p21-prospective-frozen-base.js';
import { buildFrozenPhase57SnapshotFromRuntimeDecision } from './phase58-phase57-runtime-adapter.js';

export const PHASE58_P13_SAFETY=Object.freeze({
  phase:'58.p13.phase57-prospective-pipeline',
  mode:'READ_ONLY_PROSPECTIVE_PHASE57_SNAPSHOT_PIPELINE',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE58_P13_FROZEN_POLICY=Object.freeze({
  policyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
  horizonsBars:Object.freeze([1,3,6,12,24]),
  selectionOptions:Object.freeze({
    innerTrainFraction:0.6,
    innerTestFraction:0.15,
    innerMinTrainRows:200,
    thresholds:Object.freeze([0.55,0.60,0.65]),
    minInnerSignals:50,
    minimumInnerNetReturnPct:0,
    roundTripCostPct:0.05,
  }),
});

function blocked(status,extra={}){
  return Object.freeze({
    phase:'58.p13.phase57-prospective-pipeline',status,complete:false,
    ...extra,
    safety:PHASE58_P13_SAFETY,
  });
}

function sameArray(a,b){
  return Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((value,index)=>Number(value)===Number(b[index]));
}

function isFrozenPolicy(policy){
  if(!policy||policy.policyId!==PHASE58_P13_FROZEN_POLICY.policyId)return false;
  if(!sameArray(policy.horizonsBars,PHASE58_P13_FROZEN_POLICY.horizonsBars))return false;
  const actual=policy.selectionOptions??{};
  const frozen=PHASE58_P13_FROZEN_POLICY.selectionOptions;
  if(!sameArray(actual.thresholds,frozen.thresholds))return false;
  for(const key of ['innerTrainFraction','innerTestFraction','innerMinTrainRows','minInnerSignals','minimumInnerNetReturnPct','roundTripCostPct']){
    if(Number(actual[key])!==Number(frozen[key]))return false;
  }
  for(const overrideKey of ['featureFamilies','modelConfigs','fitPredictor']){
    if(Object.prototype.hasOwnProperty.call(actual,overrideKey))return false;
  }
  return true;
}

/**
 * End-to-end READ ONLY composition used before Phase58 synchronized capture.
 * Historical outcomes may exist only in the historical materialization. The live
 * 5m prefix is outcome-free and the P21 scorer independently filters history to
 * rows whose outcomeAt is fully realized by the live feature cutoff.
 */
export function buildPhase57ProspectiveSnapshotPipeline({
  historicalSessions=[],
  currentPrefix={},
  policy=PHASE58_P13_FROZEN_POLICY,
}={}){
  const policyFrozen=isFrozenPolicy(policy);
  const horizons=Array.isArray(policy?.horizonsBars)?policy.horizonsBars:PHASE58_P13_FROZEN_POLICY.horizonsBars;
  const selectionOptions=policy?.selectionOptions??PHASE58_P13_FROZEN_POLICY.selectionOptions;

  if(currentPrefix?.latestBarClosed!==true)return blocked('BLOCKED_CURRENT_PREFIX_NOT_COMPLETED_BAR_SAFE');
  if(!Array.isArray(currentPrefix?.bars5m)||!currentPrefix.bars5m.length)return blocked('BLOCKED_CURRENT_PREFIX_BARS_MISSING');
  if(typeof currentPrefix?.symbol!=='string'||!currentPrefix.symbol.trim())return blocked('BLOCKED_CURRENT_PREFIX_SYMBOL_MISSING');
  if(typeof currentPrefix?.sessionDate!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(currentPrefix.sessionDate))return blocked('BLOCKED_CURRENT_PREFIX_SESSION_INVALID');

  const history=buildProspectiveP21HistoricalRows({sessions:historicalSessions,horizons});
  if(!history.complete)return blocked('BLOCKED_P21_HISTORY_MATERIALIZATION',{history});

  const feed=buildProspectiveP21FeatureFeed({
    symbol:currentPrefix.symbol,
    sessionDate:currentPrefix.sessionDate,
    bars5m:currentPrefix.bars5m,
    horizons,
    latestBarClosed:true,
  });
  if(!feed.complete)return blocked('BLOCKED_P21_CURRENT_FEATURE_FEED',{historySummary:{rowCounts:history.rowCounts,sessionCount:history.sessionCount},feed});

  const base=buildProspectiveP21FrozenDecision({
    historicalHorizonRowsByBars:history.historicalHorizonRowsByBars,
    currentRowsByHorizon:feed.currentRowsByHorizon,
    options:selectionOptions,
  });
  if(!base.complete)return blocked('BLOCKED_P21_PROSPECTIVE_BASE',{historySummary:{rowCounts:history.rowCounts,sessionCount:history.sessionCount},feedSummary:{featureCutoff:feed.featureCutoff},base});
  if(!base.decision||typeof base.modelId!=='string'||!/^[a-f0-9]{64}$/i.test(String(base.artifactSha256??''))){
    return blocked('BLOCKED_P21_PROVENANCE_NOT_READY',{
      historySummary:{rowCounts:history.rowCounts,sessionCount:history.sessionCount},
      feedSummary:{featureCutoff:feed.featureCutoff},
      base,
    });
  }

  const built=buildFrozenPhase57SnapshotFromRuntimeDecision({
    decision:base.decision,
    modelId:base.modelId,
    artifactSha256:base.artifactSha256,
  });
  if(!built.complete)return blocked('BLOCKED_PHASE57_RUNTIME_ADAPTER',{
    historySummary:{rowCounts:history.rowCounts,sessionCount:history.sessionCount},
    feedSummary:{featureCutoff:feed.featureCutoff},
    baseStatus:base.status,
    snapshotBuild:built,
  });

  return Object.freeze({
    phase:'58.p13.phase57-prospective-pipeline',
    status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
    complete:true,
    policyId:policy?.policyId??null,
    policyFrozen,
    promotionEvidence:false,
    snapshot:built.snapshot,
    phase57:Object.freeze({
      status:base.status,
      decision:base.decision,
      modelId:base.modelId,
      artifactSha256:base.artifactSha256,
      selectedHorizonBars:base.decision?.context?.selectedHorizonBars??null,
      selectedFeatureFamily:base.decision?.context?.selectedFeatureFamily??null,
      selectedModelType:base.decision?.context?.selectedModelType??null,
      selectedThreshold:base.decision?.context?.selectedThreshold??null,
    }),
    provenance:Object.freeze({
      historicalSessionCount:history.sessionCount,
      historicalRowCounts:history.rowCounts,
      currentFeatureCutoff:feed.featureCutoff,
      currentSourceBarCount:feed.sourceBarCount,
      currentPrefixStatus:currentPrefix?.status??null,
    }),
    methodology:Object.freeze({
      historicalFeatureParityTarget:'PHASE57_P24_HISTORICAL_INTEGRATED_FEATURE_ROWS',
      historicalOutcomesAllowedOnlyForFullyRealizedPriorRows:true,
      currentOutcomeFieldsForbidden:true,
      currentPrefixCompletedBarSafe:true,
      selectionRefitAndScoreArePriorOnly:true,
      phase57DirectionFrozenBeforePhase58:true,
      phase58MayReverseDirection:false,
      thresholdSearchAfterCapture:false,
      entryRetunedAfterCapture:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE58_P13_SAFETY,
  });
}

export default {buildPhase57ProspectiveSnapshotPipeline,PHASE58_P13_FROZEN_POLICY,PHASE58_P13_SAFETY};
