import {replayP252FrozenDaySession} from './phase57-p25-2f-postsession-point-in-time-replay.js';
import {buildP252FrozenDaySessionLedger} from './phase57-p25-2e-frozen-day-session-ledger.js';

export const PHASE57_P25_3O_SAFETY=Object.freeze({
  phase:'57.p25.3o.sharded-prefix-replay',
  mode:'READ_ONLY_DETERMINISTIC_PREFIX_REPLAY_SHARDING',
  researchOnly:true,
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

export const PHASE57_P25_3O_POLICY=Object.freeze({
  variants:Object.freeze(['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50']),
  preserveFullTargetUnionCutoffGrid:true,
  shardOnlyExpensiveScorerCalls:true,
  recombineBeforeOutcomeMaterialization:true,
  currentOuterOosDoesNotSelectShardMembership:true,
  entryThresholdRelaxationAllowed:false,
  modelChangeAllowed:false,
  universeChangeAllowed:false,
  freshHoldoutConsumed:false,
});

const EXPECTED=Object.freeze({FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50});
const normalizeSymbol=value=>String(value??'').trim().toUpperCase();
const sameArray=(a,b)=>JSON.stringify(a??[])===JSON.stringify(b??[]);

function validateUniverse(record){
  if(record?.ready!==true||!record?.variants)throw new Error('P25.3O requires a ready frozen universe record');
  const sessionDate=String(record.sessionDate??'').trim();
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('P25.3O universe sessionDate must be YYYY-MM-DD');
  const normalized={};
  for(const [variant,count] of Object.entries(EXPECTED)){
    const values=record.variants?.[variant];
    if(!Array.isArray(values)||values.length!==count)throw new Error(`P25.3O ${variant} must contain exactly ${count} symbols`);
    const symbols=values.map(normalizeSymbol);
    if(symbols.some(x=>!x)||new Set(symbols).size!==count)throw new Error(`P25.3O ${variant} contains blank or duplicate symbols`);
    normalized[variant]=symbols;
  }
  if(!normalized.DYNAMIC_30.every((x,i)=>normalized.DYNAMIC_40[i]===x)||!normalized.DYNAMIC_40.every((x,i)=>normalized.DYNAMIC_50[i]===x)){
    throw new Error('P25.3O Dynamic30/40/50 must remain nested prefixes');
  }
  const targetUnion=[...new Set(Object.values(normalized).flat())].sort();
  return Object.freeze({sessionDate,targetUnion:Object.freeze(targetUnion)});
}

function placeholderWait({symbol,featureCutoff,sessionDate}){
  return Object.freeze({
    complete:true,
    status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
    policyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
    currentSymbol:symbol,
    snapshot:Object.freeze({asOf:featureCutoff,context:Object.freeze({sourceBarCloseAt:null})}),
    phase57:Object.freeze({
      status:'PROSPECTIVE_PHASE57_FROZEN_WAIT_READY',
      modelId:'P25_3O_SHARD_PLACEHOLDER_WAIT',
      artifactSha256:null,
      decision:Object.freeze({
        direction:0,
        confidence:null,
        setup:null,
        asOf:featureCutoff,
        frozenByPhase57:true,
        pointInTimeOnly:true,
        futureOutcomeUsed:false,
        thresholdSearchAfterCapture:false,
        entryRetunedAfterCapture:false,
        context:Object.freeze({
          probability:null,
          signalEligible:false,
          selectedHorizonBars:null,
          selectedFeatureFamily:null,
          selectedModelType:null,
          selectedConfigId:null,
          selectedThreshold:null,
        }),
      }),
    }),
    provenance:Object.freeze({currentSymbol:symbol,currentFeatureCutoff:featureCutoff,currentSessionDate:sessionDate}),
  });
}

function attemptToPhase57Result(row){
  return Object.freeze({
    complete:true,
    status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
    policyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
    currentSymbol:row.symbol,
    snapshot:Object.freeze({asOf:row.featureCutoff,context:Object.freeze({sourceBarCloseAt:row.sourceBarCloseAt??null})}),
    phase57:Object.freeze({
      status:row.status,
      modelId:row.modelId??null,
      artifactSha256:row.artifactSha256??null,
      decision:Object.freeze({
        direction:Number(row.direction),
        confidence:row.confidence??null,
        setup:row.selectedFeatureFamily??null,
        asOf:row.featureCutoff,
        frozenByPhase57:true,
        pointInTimeOnly:true,
        futureOutcomeUsed:false,
        thresholdSearchAfterCapture:false,
        entryRetunedAfterCapture:false,
        context:Object.freeze({
          probability:row.probability??null,
          signalEligible:row.signalEligible===true,
          selectedHorizonBars:row.selectedHorizonBars??null,
          selectedFeatureFamily:row.selectedFeatureFamily??null,
          selectedModelType:row.selectedModelType??null,
          selectedConfigId:row.selectedConfigId??null,
          selectedThreshold:row.selectedThreshold??null,
        }),
      }),
    }),
    provenance:Object.freeze({currentSymbol:row.symbol,currentFeatureCutoff:row.featureCutoff,currentSessionDate:row.sessionDate}),
  });
}

/**
 * Run the existing P25.2F replay controller so the fair cutoff grid is still
 * computed from the entire precommitted five-variant target union. Only symbols
 * assigned to this shard invoke the expensive frozen Phase57 scorer; all other
 * symbols receive a deterministic WAIT placeholder that is discarded from the
 * shard artifact. This changes compute placement only, not feature cutoffs,
 * scorer inputs, model, Entry rules, or universe membership.
 */
export function replayP253PrefixShard({
  universeRecord,
  historicalSessions=[],
  sessionBarsBySymbol={},
  scoreSymbols=[],
  scorePrefix,
}={}){
  if(typeof scorePrefix!=='function')throw new TypeError('P25.3O scorePrefix must be a function');
  const universe=validateUniverse(universeRecord);
  const selected=[...new Set((Array.isArray(scoreSymbols)?scoreSymbols:[]).map(normalizeSymbol).filter(Boolean))].sort();
  if(!selected.length)throw new Error('P25.3O shard requires at least one score symbol');
  const targetSet=new Set(universe.targetUnion);
  if(selected.some(symbol=>!targetSet.has(symbol)))throw new Error('P25.3O shard contains symbol outside frozen target union');
  const selectedSet=new Set(selected);
  const replay=replayP252FrozenDaySession({
    universeRecord,
    historicalSessions,
    sessionBarsBySymbol,
    scorePrefix:args=>selectedSet.has(normalizeSymbol(args.symbol))?scorePrefix(args):placeholderWait(args),
  });
  const decisionAttempts=(replay?.ledger?.decisionAttempts??[]).filter(row=>selectedSet.has(normalizeSymbol(row.symbol)));
  const blockedDecisions=(replay?.blockedDecisions??[]).filter(row=>selectedSet.has(normalizeSymbol(row.symbol)));
  return Object.freeze({
    phase:'57.p25.3o.sharded-prefix-replay',
    status:'P25_3O_PREFIX_SHARD_COMPLETE',
    sessionDate:universe.sessionDate,
    fullTargetSymbolCount:universe.targetUnion.length,
    fullTargetSymbols:universe.targetUnion,
    shardSymbolCount:selected.length,
    shardSymbols:Object.freeze(selected),
    commonFairCutoffCount:Number(replay.commonFairCutoffCount??0),
    commonFairCutoffs:Object.freeze([...(replay.commonFairCutoffs??[])]),
    successfulDecisionCount:decisionAttempts.length,
    blockedDecisionCount:blockedDecisions.length,
    decisionAttempts:Object.freeze(decisionAttempts.map(row=>Object.freeze({...row}))),
    blockedDecisions:Object.freeze(blockedDecisions.map(row=>Object.freeze({...row}))),
    methodology:Object.freeze({
      fullTargetUnionUsedForFairCutoffGrid:true,
      nonShardSymbolsUseDiscardedPlaceholderWait:true,
      placeholderWaitMayEnterRecombinedEvidence:false,
      shardMembershipSelectedFromOuterOos:false,
      entryThresholdRelaxed:false,
      modelChanged:false,
      universeChanged:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_3O_SAFETY,
  });
}

/** Recombine disjoint shard checkpoints into the exact P25.2E ledger surface. */
export function recombineP253PrefixShards({universeRecord,shards=[]}={}){
  const universe=validateUniverse(universeRecord);
  if(!Array.isArray(shards)||!shards.length)throw new Error('P25.3O recombine requires shard artifacts');
  let commonFairCutoffs=null;
  const covered=new Set(),attempts=[],blocked=[];
  for(const shard of shards){
    if(shard?.phase!=='57.p25.3o.sharded-prefix-replay'||shard?.status!=='P25_3O_PREFIX_SHARD_COMPLETE')throw new Error('P25.3O invalid shard artifact');
    if(String(shard.sessionDate)!==universe.sessionDate)throw new Error('P25.3O shard session mismatch');
    if(!sameArray(shard.fullTargetSymbols,universe.targetUnion))throw new Error('P25.3O shard target union mismatch');
    const shardCutoffs=[...(shard.commonFairCutoffs??[])];
    if(commonFairCutoffs===null)commonFairCutoffs=shardCutoffs;
    else if(!sameArray(commonFairCutoffs,shardCutoffs))throw new Error('P25.3O shard fair cutoff grids differ');
    for(const symbol of shard.shardSymbols??[]){
      const normalized=normalizeSymbol(symbol);
      if(covered.has(normalized))throw new Error(`P25.3O duplicate shard symbol ${normalized}`);
      covered.add(normalized);
    }
    attempts.push(...(shard.decisionAttempts??[]));
    blocked.push(...(shard.blockedDecisions??[]));
  }
  const missing=universe.targetUnion.filter(symbol=>!covered.has(symbol));
  const extra=[...covered].filter(symbol=>!universe.targetUnion.includes(symbol));
  if(missing.length||extra.length)throw new Error(`P25.3O shard coverage mismatch missing=${missing.join(',')} extra=${extra.join(',')}`);
  const phase57Results=attempts.map(attemptToPhase57Result);
  const ledger=buildP252FrozenDaySessionLedger({universeRecord,phase57Results});
  return Object.freeze({
    phase:'57.p25.3o.sharded-prefix-replay-recombined',
    status:'P25_3O_PREFIX_SHARDS_RECOMBINED',
    sessionDate:universe.sessionDate,
    targetSymbolCount:universe.targetUnion.length,
    commonFairCutoffCount:(commonFairCutoffs??[]).length,
    commonFairCutoffs:Object.freeze([...(commonFairCutoffs??[])]),
    scorerCallCount:attempts.length+blocked.length,
    scoredDecisionCount:attempts.length,
    blockedDecisionCount:blocked.length,
    blockedDecisions:Object.freeze(blocked.map(row=>Object.freeze({...row}))),
    ledger,
    methodology:Object.freeze({
      deterministicRecombine:true,
      fullTargetUnionUsedForFairCutoffGrid:true,
      placeholderWaitDiscardedBeforeRecombine:true,
      recombinedBeforeOutcomeMaterialization:true,
      entryThresholdRelaxed:false,
      modelChanged:false,
      universeChanged:false,
      currentOuterOosDoesNotSelectShardMembership:true,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_3O_SAFETY,
  });
}

export default {replayP253PrefixShard,recombineP253PrefixShards,PHASE57_P25_3O_POLICY,PHASE57_P25_3O_SAFETY};
