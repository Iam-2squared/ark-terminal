import { enrichHistoricalIntradayBars } from './phase57-intraday-multifactor.js';
import { buildMultiHorizonMagnitudeRows } from './phase57-adaptive-horizon-magnitude.js';
import { buildIntradayHorizonDatasets } from './phase57-nested-adaptive-horizon.js';

export const PHASE57_P21_PROSPECTIVE_HISTORY_SAFETY = Object.freeze({
  phase:'57.p21.prospective-history',
  mode:'PHASE57_P21_HISTORICAL_ROWS_RESEARCH_ONLY',
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

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));

function normalizeBar(bar){
  const timestamp=bar?.timestamp??bar?.time??bar?.datetime;
  if(!timestamp||!finite(bar?.open)||!finite(bar?.high)||!finite(bar?.low)||!finite(bar?.close))return null;
  const parsed=Date.parse(timestamp);
  if(!Number.isFinite(parsed))return null;
  const out={
    timestamp:new Date(parsed).toISOString(),
    open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),
    volume:finite(bar?.volume)?Number(bar.volume):0,
  };
  return out.open>0&&out.close>0&&out.high>=out.low&&out.high>=Math.max(out.open,out.close)&&out.low<=Math.min(out.open,out.close)?out:null;
}

function normalizeSession(session){
  const symbol=String(session?.symbol??'').trim();
  const sessionDate=String(session?.sessionDate??'').trim();
  if(!symbol||!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))return null;
  const bars=(Array.isArray(session?.bars5m)?session.bars5m:[]).map(normalizeBar).filter(Boolean)
    .sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(!bars.length)return null;
  const timestamps=bars.map(bar=>bar.timestamp);
  if(new Set(timestamps).size!==timestamps.length)return null;
  return {symbol,sessionDate,bars};
}

function rowKey(row){return `${row?.symbol??''}|${row?.sessionDate??''}|${row?.featureCutoff??''}`;}

function featureRowsForSession(symbol,sessionDate,bars,baseRows){
  const enriched=enrichHistoricalIntradayBars(bars);
  const byTimestamp=new Map(enriched.map(row=>[new Date(row.timestamp).toISOString(),row]));
  const indexByTimestamp=new Map(bars.map((bar,index)=>[new Date(bar.timestamp).toISOString(),index]));
  const open0=Number(bars[0]?.open||0);
  return baseRows.flatMap(base=>{
    const timestamp=new Date(base.featureCutoff).toISOString();
    const index=indexByTimestamp.get(timestamp);
    const current=index===undefined?null:bars[index];
    const enrichedCurrent=byTimestamp.get(timestamp);
    if(index===undefined||!current||!enrichedCurrent)return[];
    const previous=index>0?bars[index-1]:current;
    const priorVolumes=bars.slice(Math.max(0,index-5),index).map(bar=>Number(bar.volume||0));
    const averagePriorVolume=priorVolumes.length?priorVolumes.reduce((sum,value)=>sum+value,0)/priorVolumes.length:0;
    return [{
      symbol,
      sessionDate,
      featureCutoff:timestamp,
      features:{
        returnFromOpen:open0?(Number(current.close)/open0-1)*100:0,
        rangePosition:Number(current.high)>Number(current.low)?(Number(current.close)-Number(current.low))/(Number(current.high)-Number(current.low)):0.5,
        shortMomentum:Number(previous.close)?(Number(current.close)/Number(previous.close)-1)*100:0,
        relativeVolume:averagePriorVolume>0?Number(current.volume||0)/averagePriorVolume:1,
        ...(enrichedCurrent.multiFactor??{}),
      },
    }];
  });
}

/**
 * Re-materializes the fully realized historical P21 horizon rows from local 5m
 * sessions using the same feature definitions as the P24 historical integrated
 * baseline. No current/live row is accepted here.
 */
export function buildProspectiveP21HistoricalRows({sessions=[],horizons=[1,3,6,12,24]}={}){
  const hs=[...new Set((Array.isArray(horizons)?horizons:[]).map(Number).filter(value=>Number.isInteger(value)&&value>0))].sort((a,b)=>a-b);
  if(!hs.length)return Object.freeze({
    phase:'57.p21.prospective-history',status:'BLOCKED_NO_VALID_HORIZONS',complete:false,
    blockers:Object.freeze(['NO_VALID_HORIZONS']),safety:PHASE57_P21_PROSPECTIVE_HISTORY_SAFETY,
  });
  const normalized=(Array.isArray(sessions)?sessions:[]).map(normalizeSession).filter(Boolean);
  if(!normalized.length)return Object.freeze({
    phase:'57.p21.prospective-history',status:'BLOCKED_NO_VALID_HISTORICAL_SESSIONS',complete:false,
    blockers:Object.freeze(['NO_VALID_HISTORICAL_SESSIONS']),safety:PHASE57_P21_PROSPECTIVE_HISTORY_SAFETY,
  });

  const seenSessions=new Set();
  const horizonRows=Object.fromEntries(hs.map(h=>[h,[]]));
  let sourceBarCount=0;
  let baseRowCount=0;
  for(const session of normalized){
    const sessionKey=`${session.symbol}|${session.sessionDate}`;
    if(seenSessions.has(sessionKey))return Object.freeze({
      phase:'57.p21.prospective-history',status:'BLOCKED_DUPLICATE_SYMBOL_SESSION',complete:false,
      blockers:Object.freeze([`DUPLICATE_SYMBOL_SESSION:${sessionKey}`]),safety:PHASE57_P21_PROSPECTIVE_HISTORY_SAFETY,
    });
    seenSessions.add(sessionKey);
    sourceBarCount+=session.bars.length;
    const base=buildMultiHorizonMagnitudeRows({symbol:session.symbol,sessionDate:session.sessionDate,bars:session.bars,horizons:hs});
    baseRowCount+=base.length;
    const featureRows=featureRowsForSession(session.symbol,session.sessionDate,session.bars,base);
    const datasets=buildIntradayHorizonDatasets(base,{horizons:hs,featureRows});
    for(const h of hs)horizonRows[h].push(...(datasets[h]??[]));
  }

  for(const h of hs){
    horizonRows[h].sort((a,b)=>{
      const byTime=String(a.featureCutoff).localeCompare(String(b.featureCutoff));
      return byTime||String(a.symbol).localeCompare(String(b.symbol));
    });
    const keys=horizonRows[h].map(rowKey);
    if(new Set(keys).size!==keys.length)return Object.freeze({
      phase:'57.p21.prospective-history',status:'BLOCKED_DUPLICATE_HISTORICAL_ROW_KEY',complete:false,
      blockers:Object.freeze([`DUPLICATE_HISTORICAL_ROW_KEY:H${h}`]),safety:PHASE57_P21_PROSPECTIVE_HISTORY_SAFETY,
    });
  }

  const frozenRows=Object.freeze(Object.fromEntries(hs.map(h=>[h,Object.freeze(horizonRows[h])] )));
  const rowCounts=Object.freeze(Object.fromEntries(hs.map(h=>[h,horizonRows[h].length])));
  return Object.freeze({
    phase:'57.p21.prospective-history',
    status:'PROSPECTIVE_P21_HISTORICAL_ROWS_READY',
    complete:true,
    sessionCount:normalized.length,
    sourceBarCount,
    baseRowCount,
    horizonsBars:Object.freeze(hs),
    rowCounts,
    historicalHorizonRowsByBars:frozenRows,
    integrity:Object.freeze({
      featureParityTarget:'PHASE57_P24_HISTORICAL_INTEGRATED_FEATURE_ROWS',
      historicalOutcomesMaterialized:true,
      currentLiveRowIncluded:false,
      laterProspectiveScorerMustRequireOutcomeAtOnOrBeforeCurrentCutoff:true,
      sameSessionRowsBuiltIndependently:true,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P21_PROSPECTIVE_HISTORY_SAFETY,
  });
}

export default {buildProspectiveP21HistoricalRows,PHASE57_P21_PROSPECTIVE_HISTORY_SAFETY};
