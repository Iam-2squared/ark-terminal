import {
  summarizeP252TradeFrequencyVariant,
  PHASE57_P25_2_VARIANTS,
} from './phase57-p25-2-trade-frequency-evaluator.js';

export const PHASE57_P25_2D_SAFETY=Object.freeze({
  phase:'57.p25.2d.precommitted-prospective-comparison',
  mode:'READ_ONLY_FROZEN_MEMBERSHIP_OUTCOME_JOIN',
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

export const PHASE57_P25_2D_POLICY=Object.freeze({
  variants:Object.freeze(PHASE57_P25_2_VARIANTS.map(x=>x.id)),
  commonReadySessionsOnly:true,
  blockedSessionsPreserved:true,
  membershipFrozenBeforeOutcome:true,
  outerOosUniverseSizeSelectionAllowed:false,
  entryThresholdRelaxationAllowed:false,
  postHocWinnerFilteringAllowed:false,
  preserveAllVariantResults:true,
});

function normalizeSymbol(value){return String(value??'').trim().toUpperCase();}

function validateReadyRecord(record){
  if(record?.ready!==true||!record?.variants)return false;
  const expected={FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50};
  for(const [variant,count] of Object.entries(expected)){
    const symbols=record.variants?.[variant];
    if(!Array.isArray(symbols)||symbols.length!==count)throw new Error(`invalid ${variant} membership for ${record.sessionDate??'UNKNOWN'}: expected ${count}`);
    if(new Set(symbols.map(normalizeSymbol)).size!==count)throw new Error(`duplicate ${variant} membership for ${record.sessionDate??'UNKNOWN'}`);
  }
  const d30=record.variants.DYNAMIC_30.map(normalizeSymbol),d40=record.variants.DYNAMIC_40.map(normalizeSymbol),d50=record.variants.DYNAMIC_50.map(normalizeSymbol);
  if(!d30.every((s,i)=>d40[i]===s)||!d40.every((s,i)=>d50[i]===s))throw new Error(`dynamic memberships are not nested for ${record.sessionDate??'UNKNOWN'}`);
  return true;
}

function readySessionMap(records){
  const ready=new Map(),blocked=[];
  for(const record of Array.isArray(records)?records:[]){
    const sessionDate=String(record?.sessionDate??'').trim();
    if(!sessionDate){blocked.push({sessionDate:null,status:record?.status??null,reason:'MISSING_SESSION_DATE'});continue;}
    if(validateReadyRecord(record)){
      if(ready.has(sessionDate))throw new Error(`multiple frozen ready universe records for session ${sessionDate}`);
      ready.set(sessionDate,record);
    }else{
      blocked.push({
        sessionDate,
        status:record?.status??'BLOCKED',
        reason:record?.reason??'UNIVERSE_NOT_READY',
        sourceSnapshotGeneratedAt:record?.sourceSnapshotGeneratedAt??null,
      });
    }
  }
  return {ready,blocked};
}

function tradeKey(row){return `${row.sessionDate??''}|${row.entryTimestamp??row.featureCutoff??''}|${normalizeSymbol(row.symbol)}`;}

function sectorLookup(record){
  const map=new Map();
  for(const row of record?.rankAudit?.day50??[]){
    const symbol=normalizeSymbol(row?.symbol);
    if(symbol)map.set(symbol,String(row?.sector??'UNKNOWN'));
  }
  return map;
}

export function evaluateP252PrecommittedProspectiveComparison({
  universeRecords=[],
  frozenTrades=[],
  eligibleDecisionCountsByVariant={},
}={}){
  const {ready,blocked}=readySessionMap(universeRecords);
  const commonSessions=[...ready.keys()].sort();
  const commonSet=new Set(commonSessions);
  const seenTrades=new Set();
  const normalizedTrades=[];
  for(const row of Array.isArray(frozenTrades)?frozenTrades:[]){
    const sessionDate=String(row?.sessionDate??'').trim(),symbol=normalizeSymbol(row?.symbol);
    if(!commonSet.has(sessionDate)||!symbol)continue;
    const key=tradeKey({...row,sessionDate,symbol});
    if(seenTrades.has(key))throw new Error(`duplicate frozen trade row: ${key}`);
    seenTrades.add(key);
    normalizedTrades.push({...row,sessionDate,symbol});
  }

  const joinedCounts={},results={};
  for(const spec of PHASE57_P25_2_VARIANTS){
    const trades=[];
    for(const row of normalizedTrades){
      const record=ready.get(row.sessionDate);
      const membership=new Set(record.variants[spec.id].map(normalizeSymbol));
      if(!membership.has(row.symbol))continue;
      const sector=String(row.sector??sectorLookup(record).get(row.symbol)??'UNKNOWN');
      trades.push({...row,sector});
    }
    joinedCounts[spec.id]=trades.length;
    const denominator=eligibleDecisionCountsByVariant?.[spec.id]??null;
    results[spec.id]=summarizeP252TradeFrequencyVariant({
      variant:spec.id,
      trades,
      evaluatedSessions:commonSessions,
      eligibleDecisionCount:denominator,
    });
  }

  return Object.freeze({
    phase:'57.p25.2d.precommitted-prospective-comparison',
    status:'PRECOMMITTED_FIVE_VARIANT_COMPARISON_MEASURED',
    commonReadySessionCount:commonSessions.length,
    commonReadySessions:Object.freeze(commonSessions),
    blockedUniverseSessions:Object.freeze(blocked.map(x=>Object.freeze(x))),
    inputFrozenTrades:Array.isArray(frozenTrades)?frozenTrades.length:0,
    commonWindowFrozenTrades:normalizedTrades.length,
    joinedTradeCounts:Object.freeze(joinedCounts),
    results:Object.freeze(results),
    methodology:Object.freeze({
      commonTemporalWindow:true,
      membershipFrozenBeforeOutcome:true,
      blockedSessionsPreserved:true,
      allFiveVariantsRetained:true,
      universeSizeSelectedFromOuterOos:false,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      currentComparisonDoesNotPromoteVariant:true,
    }),
    safety:PHASE57_P25_2D_SAFETY,
  });
}

export default {evaluateP252PrecommittedProspectiveComparison,PHASE57_P25_2D_POLICY,PHASE57_P25_2D_SAFETY};
