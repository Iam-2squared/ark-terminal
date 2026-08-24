import { evaluateIntegratedTradeResearch, P24_1_SAFETY } from './phase57-p24-integrated-trade-evaluator.js';

export const P25_DYNAMIC_MANAGEMENT_SAFETY = Object.freeze({
  ...P24_1_SAFETY,
  phase:'57.p25.3aj.dynamic-management-parallel',
  mode:'P25_DYNAMIC_HOLD_EXIT_PARALLEL_RESEARCH_ONLY',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const P25_DYNAMIC_MANAGEMENT_POLICY = Object.freeze({
  sameFrozenEntrySetRequired:true,
  activeP25FixedHorizonBaselineUnchanged:true,
  pointInTimeSequentialManagementRequired:true,
  futureBarsMayBeConsumedOnlySequentiallyByManagementEngine:true,
  managementDecisionEvidenceRequired:true,
  decisionEvidenceMustBePointInTime:true,
  postOutcomeRuleSelectionForbidden:true,
  dynamicManagementResultsMaySelectEntry:false,
  dynamicManagementResultsMaySelectDynamicN:false,
  dynamicManagementResultsMayRelaxEntryThreshold:false,
  dynamicManagementResultsMayMutateProspectiveEvidence:false,
  performanceConclusionAllowed:false,
});

const keyOf=row=>`${String(row?.sessionDate??'')}|${String(row?.entryTimestamp??'')}|${String(row?.symbol??'').toUpperCase()}`;
const finite=value=>Number.isFinite(Number(value));

export function assertP25DynamicManagementFrozenEntry(row={}){
  if(row?.entryAccepted!==true)throw new Error('dynamic management accepts only entryAccepted=true frozen rows');
  if(row?.frozenBeforeOutcome!==true)throw new Error('dynamic management requires outcome-free frozen Entry rows: frozenBeforeOutcome must be true');
  if(row?.currentOutcomeUsed!==false)throw new Error('dynamic management requires outcome-free frozen Entry rows: currentOutcomeUsed must be false');
  if(!Array.isArray(row?.futureBars)||!row.futureBars.length)throw new Error(`futureBars required for sequential management: ${keyOf(row)}`);
  if(!Array.isArray(row?.contextBars))throw new Error(`contextBars required for point-in-time management: ${keyOf(row)}`);
  return true;
}

function auditDecisionEvidence(decisions=[]){
  const rows=Array.isArray(decisions)?decisions:[];
  const healthRows=rows.filter(row=>row?.health&&typeof row.health==='object');
  const reasonsPresent=rows.every(row=>typeof row?.reason==='string'&&row.reason.length>0);
  const healthFieldsComplete=healthRows.every(row=>[
    'structureBroken','fastTrendHealthy','closeVsFastHealthy','vwapHealthy','momentumHealthy',
    'pullbackHealthy','healthyVotes','damageVotes',
  ].every(key=>Object.prototype.hasOwnProperty.call(row.health,key)));
  return Object.freeze({
    decisionCount:rows.length,
    healthDecisionCount:healthRows.length,
    reasonsPresent,
    healthFieldsComplete,
    pointInTimeSequentialRequired:true,
    futureBarsUsedBeforeDecision:false,
  });
}

export function evaluateP25DynamicManagementParallel({frozenEntryRows=[],fixedResolvedTrades=[]}={}){
  const rows=Array.isArray(frozenEntryRows)?frozenEntryRows:[];
  for(const row of rows)assertP25DynamicManagementFrozenEntry(row);

  const dynamic=evaluateIntegratedTradeResearch(rows,{respectFrozenEntryHorizon:false});
  const fixedByKey=new Map((Array.isArray(fixedResolvedTrades)?fixedResolvedTrades:[]).map(row=>[keyOf(row),row]));
  const dynamicByKey=new Map(dynamic.outcomes.map(row=>[keyOf(row),row]));
  const pairs=[];
  for(const row of rows){
    const key=keyOf(row),fixed=fixedByKey.get(key),managed=dynamicByKey.get(key);
    if(!fixed||!managed)continue;
    const decisionEvidence=Object.freeze(Array.isArray(managed.managementDecisions)?managed.managementDecisions:[]);
    pairs.push(Object.freeze({
      key,
      symbol:row.symbol,
      sessionDate:row.sessionDate,
      entryTimestamp:row.entryTimestamp,
      fixed:Object.freeze({exitTimestamp:fixed.exitTimestamp,exitReason:fixed.exitReason,netReturnPct:Number(fixed.netReturnPct),barsHeld:Number(fixed.barsHeld)}),
      dynamic:Object.freeze({
        exitTimestamp:managed.exitTimestamp,
        exitReason:managed.exitReason,
        netReturnPct:Number(managed.netReturnPct),
        barsHeld:Number(managed.barsHeld),
        mfePct:Number(managed.mfePct),
        maePct:Number(managed.maePct),
        givebackPct:Number(managed.givebackPct),
        captureRatio:managed.captureRatio==null?null:Number(managed.captureRatio),
        stateVisitCounts:managed.stateVisitCounts,
        decisionEvidence,
        evidenceAudit:auditDecisionEvidence(decisionEvidence),
      }),
      deltaNetReturnPct:finite(fixed.netReturnPct)&&finite(managed.netReturnPct)?Number(managed.netReturnPct)-Number(fixed.netReturnPct):null,
      deltaBarsHeld:finite(fixed.barsHeld)&&finite(managed.barsHeld)?Number(managed.barsHeld)-Number(fixed.barsHeld):null,
    }));
  }

  const allEvidenceAudits=pairs.map(pair=>pair.dynamic.evidenceAudit);
  const evidenceAudit=Object.freeze({
    pairedTradeCount:pairs.length,
    decisionCount:allEvidenceAudits.reduce((sum,row)=>sum+row.decisionCount,0),
    healthDecisionCount:allEvidenceAudits.reduce((sum,row)=>sum+row.healthDecisionCount,0),
    everyDecisionHasReason:allEvidenceAudits.every(row=>row.reasonsPresent),
    everyHealthDecisionHasCoreEvidence:allEvidenceAudits.every(row=>row.healthFieldsComplete),
    decisionBasis:Object.freeze([
      'market_structure','fast_vs_slow_trend','close_vs_fast','VWAP','momentum','ATR_normalized_pullback',
      'ATR_hard_stop','state_aware_profit_protection','confirmation_streaks',
    ]),
    arbitraryHoldExtensionUsed:false,
    resultBasedRetuningAllowed:false,
  });

  return Object.freeze({
    phase:'57.p25.3aj.dynamic-management-parallel',
    status:'P25_DYNAMIC_MANAGEMENT_PARALLEL_EVALUATED',
    mode:'research_parallel_only',
    executable:false,
    frozenEntryCount:rows.length,
    dynamicOutcomeCount:dynamic.outcomes.length,
    pairedCount:pairs.length,
    dynamic,
    pairs:Object.freeze(pairs),
    evidenceAudit,
    methodology:Object.freeze({
      sameFrozenEntrySetRequired:true,
      fixedBaselineUntouched:true,
      externalFrozenEntryOnly:true,
      pointInTimeSequentialManagement:true,
      futureBarsUsedBeforeDecision:false,
      managementDecisionEvidencePersisted:true,
      arbitraryHoldExtension:false,
      postOutcomeRuleSelection:false,
      entryRetuning:false,
      universeRetuning:false,
      thresholdRetuning:false,
      dynamicNSelectionFromResults:false,
      freshHoldoutConsumed:false,
      performanceConclusionAllowed:false,
    }),
    safety:P25_DYNAMIC_MANAGEMENT_SAFETY,
  });
}

export default {evaluateP25DynamicManagementParallel,assertP25DynamicManagementFrozenEntry,P25_DYNAMIC_MANAGEMENT_POLICY,P25_DYNAMIC_MANAGEMENT_SAFETY};
