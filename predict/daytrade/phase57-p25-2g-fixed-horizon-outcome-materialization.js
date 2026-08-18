import {evaluateP252PrecommittedProspectiveComparison} from './phase57-p25-2d-precommitted-prospective-comparison.js';

export const PHASE57_P25_2G_SAFETY=Object.freeze({
  phase:'57.p25.2g.fixed-horizon-outcome-materialization',
  mode:'READ_ONLY_FROZEN_FIXED_HORIZON_OUTCOME_JOIN',
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

export const PHASE57_P25_2G_POLICY=Object.freeze({
  frozenDefault:'FIXED_HORIZON_BASELINE',
  roundTripCostPct:0.05,
  directionalHitUsesGrossAlignedReturn:true,
  tradeWinUsesAfterCostNetReturn:true,
  sessionEndTruncationMatchesP24FixedOutcome:true,
  dynamicRiskOverlayUsed:false,
  entryThresholdRelaxationAllowed:false,
  outcomeMayChangeFrozenEntry:false,
  postHocWinnerFilteringAllowed:false,
});

const JST_TIME=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function normalizeSymbol(value){return String(value??'').trim().toUpperCase();}
function finite(value){return value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));}
function timeBucket(timestamp){
  const hm=JST_TIME.format(new Date(timestamp));
  if(hm<'10:00')return'09:00-09:59';
  if(hm<'11:30')return'10:00-11:29';
  if(hm<'14:00')return'11:30-13:59';
  return'14:00-15:30';
}
function normalizeBars(rows,symbol){
  const bars=(Array.isArray(rows)?rows:[]).map((bar,index)=>{
    const timestamp=String(bar?.timestamp??bar?.time??'').trim();
    if(!Number.isFinite(Date.parse(timestamp)))throw new Error(`invalid outcome bar timestamp for ${symbol} at index ${index}`);
    for(const key of ['open','high','low','close'])if(!finite(bar?.[key])||Number(bar[key])<=0)throw new Error(`invalid outcome ${key} for ${symbol} at ${timestamp}`);
    if(!finite(bar?.volume)||Number(bar.volume)<0)throw new Error(`invalid outcome volume for ${symbol} at ${timestamp}`);
    return Object.freeze({timestamp:new Date(Date.parse(timestamp)).toISOString(),open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),volume:Number(bar.volume)});
  }).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(new Set(bars.map(x=>x.timestamp)).size!==bars.length)throw new Error(`duplicate outcome bar timestamps for ${symbol}`);
  return bars;
}

export function materializeP252FixedHorizonOutcomes({
  frozenTrades=[],
  sessionBarsBySymbol={},
  regimeBySession={},
  roundTripCostPct=PHASE57_P25_2G_POLICY.roundTripCostPct,
}={}){
  if(Number(roundTripCostPct)!==PHASE57_P25_2G_POLICY.roundTripCostPct)throw new Error('P25.2G round-trip cost must remain frozen at 0.05%');
  const source=sessionBarsBySymbol instanceof Map?sessionBarsBySymbol:new Map(Object.entries(sessionBarsBySymbol??{}));
  const cache=new Map(),resolved=[],unresolved=[];
  const seen=new Set();
  for(const trade of Array.isArray(frozenTrades)?frozenTrades:[]){
    if(trade?.entryAccepted!==true||trade?.frozenBeforeOutcome!==true||trade?.currentOutcomeUsed!==false)throw new Error('P25.2G accepts only frozen outcome-free Entry rows');
    const symbol=normalizeSymbol(trade.symbol),sessionDate=String(trade.sessionDate??''),entryTimestamp=new Date(Date.parse(trade.entryTimestamp??trade.featureCutoff??'')).toISOString();
    const horizonBars=Number(trade.baseHorizonBars),direction=Number(trade.signalDirection);
    if(!symbol||!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)||!Number.isInteger(horizonBars)||horizonBars<1||![-1,1].includes(direction))throw new Error(`invalid frozen trade identity for ${symbol||'UNKNOWN'}`);
    const key=`${sessionDate}|${entryTimestamp}|${symbol}`;
    if(seen.has(key))throw new Error(`duplicate frozen trade during outcome materialization: ${key}`);
    seen.add(key);
    if(!cache.has(symbol))cache.set(symbol,normalizeBars(source.get(symbol)??source.get(symbol.replace(/\.T$/,'')),symbol));
    const bars=cache.get(symbol),index=bars.findIndex(bar=>bar.timestamp===entryTimestamp);
    if(index<0){unresolved.push(Object.freeze({...trade,outcomeStatus:'UNRESOLVED_ENTRY_BAR_MISSING'}));continue;}
    const future=bars.slice(index+1);
    if(!future.length){unresolved.push(Object.freeze({...trade,outcomeStatus:'UNRESOLVED_NO_FUTURE_BAR'}));continue;}
    const barsHeld=Math.min(horizonBars,future.length),exit=future[barsHeld-1],entryPrice=bars[index].close;
    const grossAlignedReturnPct=(exit.close/entryPrice-1)*100*direction;
    const netReturnPct=grossAlignedReturnPct-Number(roundTripCostPct);
    resolved.push(Object.freeze({
      ...trade,
      entryPrice,
      barsHeld,
      exitTimestamp:exit.timestamp,
      exitPrice:exit.close,
      exitReason:'FROZEN_HORIZON',
      horizonTruncatedAtSessionEnd:barsHeld<horizonBars,
      grossReturnPct:grossAlignedReturnPct,
      alignedReturnPct:grossAlignedReturnPct,
      netReturnPct,
      hit:grossAlignedReturnPct>0,
      timeBucket:trade.timeBucket??timeBucket(entryTimestamp),
      regime:trade.regime??regimeBySession?.[sessionDate]??'UNKNOWN',
      outcomePending:false,
      outcomeStatus:'FROZEN_FIXED_HORIZON_RESOLVED',
    }));
  }
  return Object.freeze({
    phase:'57.p25.2g.fixed-horizon-outcome-materialization',
    status:unresolved.length?'FIXED_HORIZON_OUTCOMES_PARTIAL':'FIXED_HORIZON_OUTCOMES_READY',
    inputFrozenTrades:Array.isArray(frozenTrades)?frozenTrades.length:0,
    resolvedCount:resolved.length,
    unresolvedCount:unresolved.length,
    resolvedTrades:Object.freeze(resolved),
    unresolvedTrades:Object.freeze(unresolved),
    methodology:Object.freeze({
      frozenEntryNeverChanged:true,
      fixedHorizonDefault:true,
      dynamicRiskOverlayUsed:false,
      roundTripCostPct:Number(roundTripCostPct),
      directionalHitBeforeCost:true,
      tradeWinAfterCost:true,
      sessionEndTruncationMatchesP24FixedOutcome:true,
      postHocWinnerFiltering:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2G_SAFETY,
  });
}

export function evaluateP252ResolvedSession({
  universeRecord,
  ledger,
  sessionBarsBySymbol,
  regimeBySession={},
}={}){
  const outcomes=materializeP252FixedHorizonOutcomes({frozenTrades:ledger?.frozenTrades??[],sessionBarsBySymbol,regimeBySession});
  const comparison=evaluateP252PrecommittedProspectiveComparison({
    universeRecords:[universeRecord],
    frozenTrades:outcomes.resolvedTrades,
    eligibleDecisionCountsByVariant:ledger?.eligibleDecisionCountsByVariant??{},
  });
  return Object.freeze({
    phase:'57.p25.2g.fixed-horizon-outcome-materialization',
    status:'P25_2_SESSION_FIXED_HORIZON_COMPARISON_READY',
    sessionDate:universeRecord?.sessionDate??null,
    outcomes,
    comparison,
    methodology:Object.freeze({allFiveVariantsEvaluatedTogether:true,currentSessionDoesNotSelectDynamicN:true}),
    safety:PHASE57_P25_2G_SAFETY,
  });
}

export default {materializeP252FixedHorizonOutcomes,evaluateP252ResolvedSession,PHASE57_P25_2G_POLICY,PHASE57_P25_2G_SAFETY};
