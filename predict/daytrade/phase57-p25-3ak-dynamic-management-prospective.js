import {replayP252FrozenDaySession} from './phase57-p25-2f-postsession-point-in-time-replay.js';
import {materializeP252FixedHorizonOutcomes} from './phase57-p25-2g-fixed-horizon-outcome-materialization.js';
import {evaluateP25DynamicManagementParallel,P25_DYNAMIC_MANAGEMENT_SAFETY} from './phase57-p25-dynamic-management-parallel.js';

export const PHASE57_P25_3AK_SAFETY=Object.freeze({
  ...P25_DYNAMIC_MANAGEMENT_SAFETY,
  phase:'57.p25.3ak.dynamic-management-prospective',
  mode:'P25_DYNAMIC_HOLD_EXIT_LINEAGE_PARALLEL_RESEARCH_ONLY',
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

export const PHASE57_P25_3AK_POLICY=Object.freeze({
  sameFrozenUniverseAndEntryAsFixedBaseline:true,
  fixedBaselineMutationAllowed:false,
  scorerReceivesPrefixOnly:true,
  futureBarsUsedForEntryDecision:false,
  managementConsumesFutureBarsSequentiallyOnly:true,
  dynamicManagementMaySelectDynamicN:false,
  dynamicManagementMayRetuneEntry:false,
  dynamicManagementMayRetuneModel:false,
  dynamicManagementMayRetuneUniverse:false,
  dynamicManagementMayRetuneThreshold:false,
  postOutcomeRuleSelectionAllowed:false,
  freshHoldoutConsumed:false,
});

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const normalizeSymbol=value=>String(value??'').trim().toUpperCase();
const keyOf=row=>`${String(row?.sessionDate??'')}|${String(row?.entryTimestamp??'')}|${normalizeSymbol(row?.symbol)}`;

function normalizeBars(rows=[],symbol='UNKNOWN'){
  const bars=(Array.isArray(rows)?rows:[]).map((bar,index)=>{
    const timestamp=String(bar?.timestamp??bar?.time??'').trim();
    if(!Number.isFinite(Date.parse(timestamp)))throw new Error(`P25.3AK invalid bar timestamp for ${symbol} at ${index}`);
    for(const key of ['open','high','low','close'])if(!finite(bar?.[key])||Number(bar[key])<=0)throw new Error(`P25.3AK invalid ${key} for ${symbol} at ${timestamp}`);
    if(!finite(bar?.volume)||Number(bar.volume)<0)throw new Error(`P25.3AK invalid volume for ${symbol} at ${timestamp}`);
    return Object.freeze({timestamp:new Date(Date.parse(timestamp)).toISOString(),open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),volume:Number(bar.volume)});
  }).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(new Set(bars.map(x=>x.timestamp)).size!==bars.length)throw new Error(`P25.3AK duplicate bar timestamp for ${symbol}`);
  return Object.freeze(bars);
}

/** Build management rows only after Entry has already been frozen by P25.2F/2E.
 * The entry bar close is the same reference price used by the Fixed-Horizon materializer.
 * Context ends at the frozen Entry timestamp; future bars begin strictly after it and are
 * consumed sequentially inside the management state machine.
 */
export function buildP253AKManagementRows({frozenTrades=[],sessionBarsBySymbol={}}={}){
  const source=sessionBarsBySymbol instanceof Map?sessionBarsBySymbol:new Map(Object.entries(sessionBarsBySymbol??{}));
  const cache=new Map(),rows=[],blocked=[];
  for(const trade of Array.isArray(frozenTrades)?frozenTrades:[]){
    if(trade?.entryAccepted!==true||trade?.frozenBeforeOutcome!==true||trade?.currentOutcomeUsed!==false)throw new Error('P25.3AK accepts only frozen outcome-free Entry rows');
    const symbol=normalizeSymbol(trade.symbol),entryTimestamp=new Date(Date.parse(trade.entryTimestamp??trade.featureCutoff??'')).toISOString();
    if(!cache.has(symbol))cache.set(symbol,normalizeBars(source.get(symbol)??source.get(symbol.replace(/\.T$/,'')),symbol));
    const bars=cache.get(symbol),index=bars.findIndex(bar=>bar.timestamp===entryTimestamp);
    if(index<0){blocked.push(Object.freeze({key:keyOf(trade),symbol,status:'BLOCKED_ENTRY_BAR_MISSING'}));continue;}
    const futureBars=bars.slice(index+1);
    if(!futureBars.length){blocked.push(Object.freeze({key:keyOf(trade),symbol,status:'BLOCKED_NO_MANAGED_FUTURE_BAR'}));continue;}
    rows.push(Object.freeze({
      ...trade,
      entryTimestamp,
      entryPrice:bars[index].close,
      contextBars:Object.freeze(bars.slice(0,index+1)),
      futureBars:Object.freeze(futureBars),
      outcomePending:true,
      frozenBeforeOutcome:true,
      currentOutcomeUsed:false,
    }));
  }
  return Object.freeze({rows:Object.freeze(rows),blocked:Object.freeze(blocked)});
}

export function runP253AKDynamicManagementSession({
  universeRecord,
  historicalSessions=[],
  sessionBarsBySymbol={},
  scorePrefix,
}={}){
  const replay=replayP252FrozenDaySession({
    universeRecord,
    historicalSessions,
    sessionBarsBySymbol,
    ...(typeof scorePrefix==='function'?{scorePrefix}:{}),
  });
  const ledger=replay?.ledger;
  if(!ledger||String(ledger?.sessionDate??'')!==String(universeRecord?.sessionDate??''))throw new Error('P25.3AK frozen ledger not ready');
  const fixed=materializeP252FixedHorizonOutcomes({frozenTrades:ledger.frozenTrades??[],sessionBarsBySymbol});
  const adapted=buildP253AKManagementRows({frozenTrades:ledger.frozenTrades??[],sessionBarsBySymbol});
  const dynamic=evaluateP25DynamicManagementParallel({
    frozenEntryRows:adapted.rows,
    fixedResolvedTrades:fixed.resolvedTrades,
  });
  const fixedKeys=new Set(fixed.resolvedTrades.map(keyOf));
  const dynamicKeys=new Set(dynamic.pairs.map(pair=>pair.key));
  const missingDynamicPairs=[...fixedKeys].filter(key=>!dynamicKeys.has(key));
  return Object.freeze({
    phase:'57.p25.3ak.dynamic-management-prospective',
    status:'P25_3AK_DYNAMIC_MANAGEMENT_SESSION_EVALUATED',
    sessionDate:ledger.sessionDate,
    replay,
    fixedOutcomes:fixed,
    dynamicParallel:dynamic,
    adapterAudit:Object.freeze({
      frozenTradeCount:Number(ledger.frozenTrades?.length??0),
      fixedResolvedCount:fixed.resolvedCount,
      fixedUnresolvedCount:fixed.unresolvedCount,
      managementReadyCount:adapted.rows.length,
      managementBlockedCount:adapted.blocked.length,
      pairedCount:dynamic.pairedCount,
      missingDynamicPairCount:missingDynamicPairs.length,
      blocked:Object.freeze(adapted.blocked),
      missingDynamicPairs:Object.freeze(missingDynamicPairs),
    }),
    methodology:Object.freeze({
      sameFrozenLedgerAsFixed:true,
      fixedEntryReferencePriceReused:true,
      fixedBaselineUntouched:true,
      currentEntryOutcomeFree:true,
      scorerReceivesPrefixOnly:true,
      futureBarsUsedForEntryDecision:false,
      managementFutureBarsSequentialOnly:true,
      postOutcomeRuleSelection:false,
      entryRetuning:false,
      modelRetuning:false,
      universeRetuning:false,
      thresholdRetuning:false,
      dynamicNSelectionFromResults:false,
      freshHoldoutConsumed:false,
      performanceConclusionAllowed:false,
    }),
    safety:PHASE57_P25_3AK_SAFETY,
  });
}

export default {runP253AKDynamicManagementSession,buildP253AKManagementRows,PHASE57_P25_3AK_POLICY,PHASE57_P25_3AK_SAFETY};
