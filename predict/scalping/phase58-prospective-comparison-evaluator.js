import crypto from 'node:crypto';
import {buildFrozenPhase57MicrostructureDecision} from './phase58-phase57-frozen-overlay.js';
import {estimateScalpingCostBps} from './phase58-integration-benchmark.js';
import {validateFrozenPhase57Snapshot} from './phase58-phase57-snapshot-contract.js';

export const PHASE58_P26_SAFETY=Object.freeze({
  phase:'58.p26.prospective-comparison-evaluator',
  mode:'READ_ONLY_PHASE57_VS_MICROSTRUCTURE_PROSPECTIVE_EVALUATION',
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

export const PHASE58_P26_EVIDENCE_POLICY=Object.freeze({
  minFormalNonOverlappingEvents:30,
  minDistinctSessions:3,
  barMinutes:5,
  microstructureHistoryRows:20,
  maxSnapshotAgeMs:300000,
  thresholdSearchAllowed:false,
  postHocOptimizationAllowed:false,
  promotionEvidence:false,
});

const UNSAFE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);
const finite=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
const pct=x=>finite(x)?Number(x)*100:null;
const parseMs=x=>{const ms=Date.parse(x??'');return Number.isFinite(ms)?ms:null;};
const sha256Text=text=>crypto.createHash('sha256').update(text).digest('hex');

function snapshotKey(row){
  const s=row?.phase57Snapshot??{};
  return [row?.symbol??'',s.modelId??'',s.artifactSha256??'',s.asOf??'',s.direction??''].join('|');
}

function midFromRow(row){
  const bid=Number(row?.market?.bestBid),ask=Number(row?.market?.bestAsk);
  return Number.isFinite(bid)&&Number.isFinite(ask)&&bid>0&&ask>=bid?(bid+ask)/2:null;
}

function spreadBpsFromRow(row){
  if(finite(row?.market?.spreadBps))return Math.max(0,Number(row.market.spreadBps));
  const bid=Number(row?.market?.bestBid),ask=Number(row?.market?.bestAsk),mid=midFromRow(row);
  return Number.isFinite(bid)&&Number.isFinite(ask)&&finite(mid)&&mid>0?Math.max(0,(ask-bid)/mid*10000):null;
}

function jstDate(capturedAt){
  const ms=parseMs(capturedAt);
  if(ms===null)return null;
  return new Date(ms+9*60*60*1000).toISOString().slice(0,10);
}

function datedTickTimestamp(value,capturedAt){
  if(typeof value!=='string'||!value.trim())return null;
  const raw=value.trim();
  if(/\d{4}-\d{2}-\d{2}/.test(raw)&&parseMs(raw)!==null)return raw;
  if(!/^\d{1,2}:\d{2}:\d{2}(?:\.\d+)?$/.test(raw))return null;
  const date=jstDate(capturedAt);
  return date?`${date}T${raw}+09:00`:null;
}

function quoteSnapshot(row){
  const market=row?.market??{},book=row?.orderBook??{};
  const out={
    timestamp:row?.capturedAt??null,
    bestAsk:market.bestAsk??null,
    bestBid:market.bestBid??null,
    askSize:market.bestAskSize??market.askSize1??null,
    bidSize:market.bestBidSize??market.bidSize1??null,
  };
  for(const level of Array.isArray(book.asks)?book.asks:[]){
    const rank=Number(level?.level??level?.rank);
    if(Number.isInteger(rank)&&rank>=1&&rank<=10){out[`askPrice${rank}`]=level?.price??null;out[`askSize${rank}`]=level?.size??null;}
  }
  for(const level of Array.isArray(book.bids)?book.bids:[]){
    const rank=Number(level?.level??level?.rank);
    if(Number.isInteger(rank)&&rank>=1&&rank<=10){out[`bidPrice${rank}`]=level?.price??null;out[`bidSize${rank}`]=level?.size??null;}
  }
  return out;
}

function causalTicks(row){
  let ticks=(Array.isArray(row?.ticks)?row.ticks:[]).map(t=>({
    timestamp:datedTickTimestamp(t?.timestamp??t?.time,row?.capturedAt),
    price:t?.price??t?.executionPrice??null,
    size:t?.size??t?.volume??null,
  })).filter(t=>t.timestamp&&finite(t.price)&&Number(t.price)>0);
  if(row?.tickOrder==='DESC')ticks=[...ticks].reverse();
  return ticks;
}

function sameSymbolIndices(rows,index,limit=PHASE58_P26_EVIDENCE_POLICY.microstructureHistoryRows){
  const symbol=rows[index]?.symbol;
  const out=[];
  for(let i=index;i>=0&&out.length<limit;i-=1)if(rows[i]?.symbol===symbol)out.push(i);
  return out.reverse();
}

function microInput(rows,index){
  const quoteSnapshots=sameSymbolIndices(rows,index).map(i=>quoteSnapshot(rows[i]));
  const row=rows[index];
  return {snapshot:quoteSnapshot(row),quoteSnapshots,ticks:causalTicks(row),asOf:row?.capturedAt??null};
}

function defaultOverlayAction(rows,index,direction){
  const indices=sameSymbolIndices(rows,index);
  const inputSeries=indices.map(i=>microInput(rows,i));
  const decision=buildFrozenPhase57MicrostructureDecision({
    phase57Context:{direction,frozenByPhase57:true,sourceTimestamp:rows[index]?.phase57Snapshot?.asOf??null},
    inputSeries,
  });
  return {action:decision.action,decision};
}

function validateRows(rows){
  const blockers=[];
  let previousMs=null;
  for(let i=0;i<rows.length;i+=1){
    const row=rows[i],n=i+1;
    if(row?.schemaVersion!==2)blockers.push(`ROW_${n}_SCHEMA_VERSION_NOT_2`);
    if(row?.phase!=='58.p9.sync-capture')blockers.push(`ROW_${n}_WRONG_PHASE`);
    if(row?.sourceMode!=='MARKETSPEED_II_RSS_READ_ONLY')blockers.push(`ROW_${n}_WRONG_SOURCE_MODE`);
    const capturedMs=parseMs(row?.capturedAt);
    if(capturedMs===null)blockers.push(`ROW_${n}_INVALID_CAPTURE_TIMESTAMP`);
    if(previousMs!==null&&capturedMs!==null&&capturedMs<previousMs)blockers.push(`ROW_${n}_NON_MONOTONIC_CAPTURE_TIME`);
    if(capturedMs!==null)previousMs=capturedMs;
    for(const key of UNSAFE_KEYS)if(row?.safety?.[key]!==false)blockers.push(`ROW_${n}_UNSAFE_${key}`);
    if(row?.methodology?.phase58MayReverseDirection!==false)blockers.push(`ROW_${n}_DIRECTION_REVERSAL_GUARD_MISSING`);
    if(row?.methodology?.historicalDecisionReconstructionAllowed!==false)blockers.push(`ROW_${n}_HISTORICAL_RECONSTRUCTION_GUARD_MISSING`);
    if(row?.methodology?.futureOutcomeUsed!==false)blockers.push(`ROW_${n}_FUTURE_OUTCOME_GUARD_MISSING`);
    const v=validateFrozenPhase57Snapshot(row?.phase57Snapshot,{captureAsOf:row?.capturedAt,maxAgeMs:PHASE58_P26_EVIDENCE_POLICY.maxSnapshotAgeMs});
    if(!v.complete)for(const blocker of v.blockers)blockers.push(`ROW_${n}_${blocker}`);
    if(midFromRow(row)===null)blockers.push(`ROW_${n}_INVALID_TOP_OF_BOOK`);
    if(row?.tickOrder!=='DESC'&&row?.tickOrder!=='ASC')blockers.push(`ROW_${n}_UNKNOWN_TICK_ORDER`);
  }
  return [...new Set(blockers)];
}

function outcomeRowIndex(rows,startIndex,targetMs,symbol){
  for(let i=startIndex+1;i<rows.length;i+=1){
    const ms=parseMs(rows[i]?.capturedAt);
    if(rows[i]?.symbol===symbol&&ms!==null&&ms>=targetMs&&midFromRow(rows[i])!==null)return i;
  }
  return null;
}

function tradeResult({entryRow,exitRow,direction}){
  const entryMid=midFromRow(entryRow),exitMid=midFromRow(exitRow),spreadBps=spreadBpsFromRow(entryRow);
  const cost=estimateScalpingCostBps({spreadBps});
  if(!finite(entryMid)||!finite(exitMid)||entryMid<=0||!cost.ready)return null;
  const grossReturn=direction*(exitMid/entryMid-1),costReturn=cost.totalRoundTripBps/10000,netReturn=grossReturn-costReturn;
  return Object.freeze({
    entryAt:entryRow.capturedAt,exitAt:exitRow.capturedAt,direction,entryMid,exitMid,
    grossReturn,costReturn,netReturn,
    grossReturnPct:pct(grossReturn),costPct:pct(costReturn),netReturnPct:pct(netReturn),
    spreadBps,costRoundTripBps:cost.totalRoundTripBps,directionalHit:grossReturn>0,netWin:netReturn>0,
  });
}

function metrics(trades){
  const valid=trades.filter(Boolean),returns=valid.map(x=>x.netReturn);
  const wins=returns.filter(x=>x>0),losses=returns.filter(x=>x<0);
  const grossWin=wins.reduce((s,x)=>s+x,0),grossLoss=-losses.reduce((s,x)=>s+x,0);
  let equity=1,peak=1,maxDrawdown=0;
  for(const r of returns){equity*=Math.max(0,1+r);peak=Math.max(peak,equity);if(peak>0)maxDrawdown=Math.max(maxDrawdown,(peak-equity)/peak);}
  return Object.freeze({
    entryCount:valid.length,
    hitRate:valid.length?valid.filter(x=>x.directionalHit).length/valid.length:null,
    hitRatePct:valid.length?100*valid.filter(x=>x.directionalHit).length/valid.length:null,
    winRate:valid.length?wins.length/valid.length:null,
    winRatePct:valid.length?100*wins.length/valid.length:null,
    profitFactor:grossLoss>0?grossWin/grossLoss:null,
    netReturn:valid.length?equity-1:null,
    netReturnPct:valid.length?100*(equity-1):null,
    meanNetReturnPct:valid.length?100*returns.reduce((s,x)=>s+x,0)/valid.length:null,
    maxDrawdown:valid.length?maxDrawdown:null,
    maxDrawdownPct:valid.length?100*maxDrawdown:null,
  });
}

function groupedSnapshotIndices(rows){
  const map=new Map();
  for(let i=0;i<rows.length;i+=1){
    const key=snapshotKey(rows[i]);
    if(!map.has(key))map.set(key,[]);
    map.get(key).push(i);
  }
  return [...map.entries()].map(([key,indices])=>({key,indices}));
}

function buildEvents(rows,overlayActionForIndex){
  const events=[];
  let waitDecisionCount=0;
  for(const group of groupedSnapshotIndices(rows)){
    const firstIndex=group.indices[0],firstRow=rows[firstIndex],snapshot=firstRow.phase57Snapshot??{};
    const direction=Number(snapshot.direction);
    if(direction!==1&&direction!==-1){waitDecisionCount+=1;continue;}
    const horizonBars=Number(snapshot?.context?.selectedHorizonBars);
    if(!Number.isInteger(horizonBars)||horizonBars<1){events.push({status:'BLOCKED_MISSING_HORIZON',key:group.key});continue;}
    const horizonMs=horizonBars*PHASE58_P26_EVIDENCE_POLICY.barMinutes*60*1000;
    const baselineEntryIndex=firstIndex,baselineTargetMs=parseMs(firstRow.capturedAt)+horizonMs;
    const baselineExitIndex=outcomeRowIndex(rows,baselineEntryIndex,baselineTargetMs,firstRow.symbol);
    let overlayEntryIndex=null,overlayAction='DEFER_TO_PHASE57',liquidityShockSeen=false;
    for(const index of group.indices){
      const result=overlayActionForIndex(rows,index,direction);
      const action=result?.action??'DEFER_TO_PHASE57';
      if(action==='ABSTAIN_LIQUIDITY_SHOCK'){liquidityShockSeen=true;overlayAction='ABSTAIN_LIQUIDITY_SHOCK';break;}
      if(action==='CONFIRM_PHASE57_ENTRY'){overlayEntryIndex=index;overlayAction='CONFIRM_PHASE57_ENTRY';break;}
    }
    let overlayExitIndex=null;
    if(overlayEntryIndex!==null){
      const target=parseMs(rows[overlayEntryIndex].capturedAt)+horizonMs;
      overlayExitIndex=outcomeRowIndex(rows,overlayEntryIndex,target,firstRow.symbol);
    }
    const baseline=baselineExitIndex===null?null:tradeResult({entryRow:firstRow,exitRow:rows[baselineExitIndex],direction});
    const overlay=overlayEntryIndex===null||overlayExitIndex===null?null:tradeResult({entryRow:rows[overlayEntryIndex],exitRow:rows[overlayExitIndex],direction});
    const pending=baselineExitIndex===null||(overlayEntryIndex!==null&&overlayExitIndex===null);
    const boundaries=[baselineExitIndex,overlayExitIndex].filter(x=>x!==null).map(x=>parseMs(rows[x].capturedAt)).filter(x=>x!==null);
    events.push(Object.freeze({
      status:pending?'PENDING_OUTCOME':'MATURED',key:group.key,symbol:firstRow.symbol,direction,
      modelId:snapshot.modelId,artifactSha256:snapshot.artifactSha256,phase57AsOf:snapshot.asOf,
      sessionDate:jstDate(firstRow.capturedAt),horizonBars,horizonMinutes:horizonBars*PHASE58_P26_EVIDENCE_POLICY.barMinutes,
      baselineEntryIndex,baselineExitIndex,overlayEntryIndex,overlayExitIndex,overlayAction,liquidityShockSeen,
      baseline,overlay,overlayFiltered:overlayEntryIndex===null,
      outcomeBoundaryMs:boundaries.length?Math.max(...boundaries):0,
    }));
  }
  return {events,waitDecisionCount};
}

function nonOverlapping(events){
  const selected=[];
  let nextAllowedMs=-Infinity;
  for(const event of events.filter(x=>x.status==='MATURED'&&x.baseline).sort((a,b)=>parseMs(a.baseline.entryAt)-parseMs(b.baseline.entryAt))){
    const entryMs=parseMs(event.baseline.entryAt);
    if(entryMs<nextAllowedMs)continue;
    selected.push(event);
    nextAllowedMs=event.outcomeBoundaryMs||parseMs(event.baseline.exitAt);
  }
  return selected;
}

function comparison(events){
  const comparable=events.filter(x=>x.status==='MATURED'&&x.baseline);
  const baselineTrades=comparable.map(x=>x.baseline),overlayTrades=comparable.map(x=>x.overlay).filter(Boolean);
  const baselineLosers=comparable.filter(x=>x.baseline.netReturn<=0),baselineWinners=comparable.filter(x=>x.baseline.netReturn>0);
  const filtered=comparable.filter(x=>x.overlayFiltered),filteredLosers=baselineLosers.filter(x=>x.overlayFiltered),filteredWinners=baselineWinners.filter(x=>x.overlayFiltered);
  const base=metrics(baselineTrades),overlay=metrics(overlayTrades);
  return Object.freeze({
    comparableEventCount:comparable.length,
    baseline:base,
    phase57PlusPhase58:overlay,
    overlayCoverage:comparable.length?overlayTrades.length/comparable.length:null,
    overlayCoveragePct:comparable.length?100*overlayTrades.length/comparable.length:null,
    filteredEventCount:filtered.length,
    falseEntryReduction:baselineLosers.length?filteredLosers.length/baselineLosers.length:null,
    falseEntryReductionPct:baselineLosers.length?100*filteredLosers.length/baselineLosers.length:null,
    opportunityLoss:baselineWinners.length?filteredWinners.length/baselineWinners.length:null,
    opportunityLossPct:baselineWinners.length?100*filteredWinners.length/baselineWinners.length:null,
    deltas:Object.freeze({
      hitRatePct:finite(base.hitRatePct)&&finite(overlay.hitRatePct)?overlay.hitRatePct-base.hitRatePct:null,
      winRatePct:finite(base.winRatePct)&&finite(overlay.winRatePct)?overlay.winRatePct-base.winRatePct:null,
      netReturnPct:finite(base.netReturnPct)&&finite(overlay.netReturnPct)?overlay.netReturnPct-base.netReturnPct:null,
      profitFactor:finite(base.profitFactor)&&finite(overlay.profitFactor)?overlay.profitFactor-base.profitFactor:null,
      maxDrawdownPct:finite(base.maxDrawdownPct)&&finite(overlay.maxDrawdownPct)?overlay.maxDrawdownPct-base.maxDrawdownPct:null,
    }),
  });
}

function countBy(events,keyFn){
  const counts=new Map();
  for(const event of events){const key=String(keyFn(event)??'UNKNOWN');counts.set(key,(counts.get(key)??0)+1);}
  return Object.fromEntries([...counts].sort(([a],[b])=>a.localeCompare(b)));
}

function maxConcentration(counts,total){
  const values=Object.values(counts);
  return total&&values.length?Math.max(...values)/total:null;
}

function stability(events){
  const total=events.length;
  const eventsPerSession=countBy(events,x=>x.sessionDate),eventsPerSymbol=countBy(events,x=>x.symbol),eventsPerModel=countBy(events,x=>x.modelId);
  const distinctSessions=Object.keys(eventsPerSession).length;
  const sessionConcentration=maxConcentration(eventsPerSession,total),symbolConcentration=maxConcentration(eventsPerSymbol,total),modelConcentration=maxConcentration(eventsPerModel,total);
  return Object.freeze({
    distinctSessions,distinctSymbols:Object.keys(eventsPerSymbol).length,distinctModels:Object.keys(eventsPerModel).length,
    eventsPerSession:Object.freeze(eventsPerSession),eventsPerSymbol:Object.freeze(eventsPerSymbol),eventsPerModel:Object.freeze(eventsPerModel),
    maxSessionConcentration:sessionConcentration,maxSessionConcentrationPct:pct(sessionConcentration),
    maxSymbolConcentration:symbolConcentration,maxSymbolConcentrationPct:pct(symbolConcentration),
    maxModelConcentration:modelConcentration,maxModelConcentrationPct:pct(modelConcentration),
    stabilityEvidenceReady:distinctSessions>=PHASE58_P26_EVIDENCE_POLICY.minDistinctSessions,
  });
}

/**
 * Frozen, prospective-only comparison. Phase57 supplies direction; Phase58 can only
 * confirm, defer or abstain. Outcomes are joined strictly to later synchronized
 * captures after the predeclared Phase57 horizon. No thresholds are searched here.
 */
export function evaluatePhase58ProspectiveComparison({rows=[],datasetSha256=null,overlayActionForIndex=defaultOverlayAction}={}){
  const input=Array.isArray(rows)?rows:[];
  const blockers=validateRows(input);
  if(!input.length)blockers.push('EMPTY_SYNCHRONIZED_DATASET');
  if(typeof datasetSha256!=='string'||!/^[a-f0-9]{64}$/i.test(datasetSha256))blockers.push('INVALID_DATASET_SHA256');
  if(blockers.length)return Object.freeze({
    phase:'58.p26.prospective-comparison-evaluator',status:'BLOCKED_DATASET_INTEGRITY',complete:false,
    datasetSha256,blockers:Object.freeze([...new Set(blockers)]),promotionEvidence:false,
    methodology:Object.freeze({phase57DirectionIsFrozenBase:true,phase58MayReverseDirection:false,prospectiveOnly:true,thresholdSearchAllowed:false,postHocOptimizationAllowed:false}),
    safety:PHASE58_P26_SAFETY,
  });
  const {events,waitDecisionCount}=buildEvents(input,overlayActionForIndex);
  const horizonBlockers=events.filter(x=>x.status==='BLOCKED_MISSING_HORIZON');
  if(horizonBlockers.length)return Object.freeze({
    phase:'58.p26.prospective-comparison-evaluator',status:'BLOCKED_MISSING_PHASE57_HORIZON',complete:false,
    datasetSha256,blockers:Object.freeze(horizonBlockers.map(x=>`MISSING_HORIZON:${x.key}`)),promotionEvidence:false,safety:PHASE58_P26_SAFETY,
  });
  const matured=events.filter(x=>x.status==='MATURED'),pending=events.filter(x=>x.status==='PENDING_OUTCOME');
  const formalEvents=nonOverlapping(events);
  const allComparison=comparison(matured),formalComparison=comparison(formalEvents),formalStability=stability(formalEvents);
  const evidenceReady=formalEvents.length>=PHASE58_P26_EVIDENCE_POLICY.minFormalNonOverlappingEvents&&formalStability.stabilityEvidenceReady;
  const resultMaterial={datasetSha256,eventKeys:events.map(x=>x.key),formalKeys:formalEvents.map(x=>x.key),allComparison,formalComparison};
  return Object.freeze({
    phase:'58.p26.prospective-comparison-evaluator',
    status:evidenceReady?'PHASE58_PROSPECTIVE_COMPARISON_EVIDENCE_READY':'PHASE58_PROSPECTIVE_COMPARISON_INSUFFICIENT_EVIDENCE',
    complete:true,datasetSha256,resultSha256:sha256Text(JSON.stringify(resultMaterial)),
    rowCount:input.length,decisionEventCount:events.length,waitDecisionCount,maturedEventCount:matured.length,pendingEventCount:pending.length,
    formalNonOverlappingEventCount:formalEvents.length,
    allOverlappingDescriptive:allComparison,formalNonOverlapping:formalComparison,stability:formalStability,
    evidence:Object.freeze({...PHASE58_P26_EVIDENCE_POLICY,ready:evidenceReady,promotionEvidence:false}),
    eventAudit:Object.freeze(events.map(x=>Object.freeze({
      status:x.status,key:x.key,symbol:x.symbol,direction:x.direction,sessionDate:x.sessionDate,horizonBars:x.horizonBars,
      overlayAction:x.overlayAction,overlayFiltered:x.overlayFiltered,baselineEntryAt:x.baseline?.entryAt??null,baselineExitAt:x.baseline?.exitAt??null,
      overlayEntryAt:x.overlay?.entryAt??null,overlayExitAt:x.overlay?.exitAt??null,
    }))),
    methodology:Object.freeze({
      phase57DirectionIsFrozenBase:true,phase58MayConfirmDeferOrAbstainOnly:true,phase58MayReverseDirection:false,
      waitMayBecomeEntry:false,prospectiveOnly:true,futureOutcomeJoinedOnlyAfterFrozenHorizon:true,
      sameSymbolMicrostructureHistoryOnly:true,overlappingResultsDescriptiveOnly:true,formalResultsNonOverlapping:true,
      tickOrderNormalizedCausally:true,thresholdSearchAllowed:false,postHocOptimizationAllowed:false,
      automaticPromotionAllowed:false,freshHoldoutConsumed:false,
    }),
    promotionEvidence:false,recommendationAllowed:false,safety:PHASE58_P26_SAFETY,
  });
}

export default {evaluatePhase58ProspectiveComparison,PHASE58_P26_EVIDENCE_POLICY,PHASE58_P26_SAFETY};
