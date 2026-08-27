import {createHash} from 'node:crypto';
import {selectJpxOpportunityUniverse,PHASE57_P25_SAFETY} from './phase57-p25-jpx-opportunity-universe.js';

export const PHASE57_INTRADAY_UNIVERSE_POLICY=Object.freeze({
  candidateId:'INTRADAY_DYNAMIC_5M_UNIVERSE_V1',
  cadenceMinutes:5,
  sourceScope:'JPX_DOMESTIC_PRIME_STANDARD_GROWTH',
  candidatePoolSize:120,
  finalUniverseSize:50,
  dayCount:30,
  swingCount:30,
  maxPerSector:4,
  semanticDeduplication:true,
  excludeHeldSymbolsAtAllocationGate:true,
  replaceFrozenDynamic50:false,
  formalOos:false,
  promotionEligible:false,
  winnerSelectionAllowed:false,
  allocationRuleTuningAllowed:false,
  thresholdRelaxationAllowed:false,
});

export const PHASE57_INTRADAY_UNIVERSE_SAFETY=Object.freeze({
  ...PHASE57_P25_SAFETY,
  phase:'57.p25.intraday-dynamic-universe',
  mode:'READ_ONLY_5M_DYNAMIC_UNIVERSE_RESEARCH_CANDIDATE',
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

const FORBIDDEN_KEYS=Object.freeze([
  'outcome','outcomeAt','actualReturnPct','futureReturnPct','netReturnPct','grossReturnPct','tradeWin','hit','label','target','outerOosProfitFactor',
]);
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const symbolOf=row=>String(row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.sector??'未分類').trim()||'未分類';
const numberOr=(v,fallback=0)=>finite(v)?Number(v):fallback;
const clamp=(v,min=0,max=1)=>Math.min(max,Math.max(min,v));

function assertSafeRow(row){
  if(!row||typeof row!=='object')throw new TypeError('intraday universe row must be an object');
  const poisoned=FORBIDDEN_KEYS.filter(k=>Object.prototype.hasOwnProperty.call(row,k));
  if(poisoned.length)throw new Error(`intraday universe row contains forbidden outcome fields: ${poisoned.join(',')}`);
}

function semanticRow(row){
  assertSafeRow(row);
  return {
    symbol:symbolOf(row),sector:sectorOf(row),market:row.market??null,status:row.status??null,
    currentPrice:numberOr(row.currentPrice,null),volume:numberOr(row.volume,null),volumeRatio:numberOr(row.volumeRatio,null),
    dailyChangePercent:numberOr(row.dailyChangePercent,null),atrPercent:numberOr(row.atrPercent,null),
    discoveryScore:numberOr(row.discoveryScore,null),technicalScore:numberOr(row.technicalScore,null),
    confidence:numberOr(row.confidence,null),qualityScore:numberOr(row.qualityScore,null),
  };
}

function semanticFingerprint(entries){
  const rows=entries.map(semanticRow).sort((a,b)=>a.symbol.localeCompare(b.symbol));
  return createHash('sha256').update(JSON.stringify(rows)).digest('hex');
}

function cheapOpportunityScore(row){
  const turnover=Math.max(0,numberOr(row.currentPrice)*numberOr(row.volume));
  const logTurnover=Math.log10(1+turnover);
  const volumeRatio=Math.max(0,numberOr(row.volumeRatio));
  const absChange=Math.abs(numberOr(row.dailyChangePercent));
  const atr=Math.max(0,numberOr(row.atrPercent));
  const discovery=Math.abs(numberOr(row.discoveryScore,50)-50)/50;
  const technical=Math.abs(numberOr(row.technicalScore,50)-50)/50;
  const confidence=numberOr(row.confidence); const conf01=confidence<=1?confidence:confidence/100;
  const quality=numberOr(row.qualityScore)/100;
  return (
    clamp(logTurnover/10)*0.28+
    clamp(volumeRatio/5)*0.20+
    clamp(absChange/8)*0.15+
    clamp(atr/8)*0.10+
    clamp(discovery)*0.10+
    clamp(technical)*0.07+
    clamp(conf01)*0.05+
    clamp(quality)*0.05
  );
}

function prescreen(entries,poolSize){
  const seen=new Set();
  const eligible=[];
  for(const row of entries){
    assertSafeRow(row);
    const symbol=symbolOf(row);
    if(!symbol||seen.has(symbol))continue;
    seen.add(symbol);
    if(row.status&&row.status!=='analyzed')continue;
    if(!finite(row.currentPrice)||Number(row.currentPrice)<=0||!finite(row.volume)||Number(row.volume)<=0)continue;
    eligible.push({row,score:cheapOpportunityScore(row)});
  }
  eligible.sort((a,b)=>b.score-a.score||numberOr(b.row.currentPrice)*numberOr(b.row.volume)-numberOr(a.row.currentPrice)*numberOr(a.row.volume)||symbolOf(a.row).localeCompare(symbolOf(b.row)));
  return eligible.slice(0,Math.min(poolSize,eligible.length)).map(x=>x.row);
}

function normalizeHeld(heldSymbols){
  return new Set((Array.isArray(heldSymbols)?heldSymbols:[]).map(x=>symbolOf({symbol:x})).filter(Boolean));
}

function cadenceBucket(timestamp,cadenceMinutes){
  const ms=Date.parse(timestamp);
  if(!Number.isFinite(ms))throw new TypeError('snapshot asOf must be a valid timestamp');
  const bucketMs=cadenceMinutes*60_000;
  return Math.floor(ms/bucketMs)*bucketMs;
}

export function buildIntradayDynamicUniverseTimeline({snapshots=[],heldSymbolsByCutoff={},policy={}}={}){
  if(!Array.isArray(snapshots))throw new TypeError('snapshots must be an array');
  const cfg={...PHASE57_INTRADAY_UNIVERSE_POLICY,...policy};
  for(const [name,value] of Object.entries({cadenceMinutes:cfg.cadenceMinutes,candidatePoolSize:cfg.candidatePoolSize,finalUniverseSize:cfg.finalUniverseSize,dayCount:cfg.dayCount,swingCount:cfg.swingCount,maxPerSector:cfg.maxPerSector})){
    if(!Number.isInteger(Number(value))||Number(value)<1)throw new TypeError(`${name} must be a positive integer`);
  }
  if(cfg.cadenceMinutes!==5)throw new Error('V1 cadence is frozen at 5 minutes');
  if(cfg.thresholdRelaxationAllowed!==false||cfg.replaceFrozenDynamic50!==false)throw new Error('intraday candidate cannot relax Entry or replace Frozen DYNAMIC_50');

  const ordered=[...snapshots].sort((a,b)=>Date.parse(a?.asOf??'')-Date.parse(b?.asOf??''));
  const seenBuckets=new Set();
  const semanticCache=new Map();
  const points=[];
  let selectorCalls=0,dedupHits=0,prescreenedRows=0,inputRows=0;

  for(const snapshot of ordered){
    if(!snapshot||typeof snapshot!=='object'||!Array.isArray(snapshot.entries))throw new TypeError('each snapshot requires entries[]');
    const asOf=String(snapshot.asOf??'');
    const bucket=cadenceBucket(asOf,Number(cfg.cadenceMinutes));
    if(seenBuckets.has(bucket))continue;
    seenBuckets.add(bucket);
    inputRows+=snapshot.entries.length;
    const fingerprint=semanticFingerprint(snapshot.entries);
    let base=semanticCache.get(fingerprint);
    let reused=false;
    if(!base){
      const pool=prescreen(snapshot.entries,Number(cfg.candidatePoolSize));
      prescreenedRows+=pool.length;
      base=selectJpxOpportunityUniverse({
        entries:pool,dayCount:Number(cfg.dayCount),swingCount:Number(cfg.swingCount),maxCombinedCount:Number(cfg.finalUniverseSize),maxPerSector:Number(cfg.maxPerSector),
        asOf,maxAgeMs:null,
      });
      semanticCache.set(fingerprint,base);
      selectorCalls+=1;
    }else{
      reused=true;dedupHits+=1;
    }
    const held=normalizeHeld(heldSymbolsByCutoff?.[asOf]??heldSymbolsByCutoff?.[new Date(bucket).toISOString()]??[]);
    const allocationEligible=base.combined.filter(row=>!held.has(row.symbol));
    points.push(Object.freeze({
      asOf:new Date(bucket).toISOString(),sourceAsOf:asOf,semanticFingerprint:fingerprint,reusedSelection:reused,
      rawUniverse:Object.freeze(base.combined),allocationEligibleUniverse:Object.freeze(allocationEligible),heldExcludedCount:base.combined.length-allocationEligible.length,
    }));
  }

  return Object.freeze({
    phase:'57.p25.intraday-dynamic-universe',
    status:'INTRADAY_DYNAMIC_5M_UNIVERSE_TIMELINE_READY',
    candidateId:cfg.candidateId,
    points:Object.freeze(points),
    diagnostics:Object.freeze({
      inputSnapshotCount:snapshots.length,uniqueCadencePointCount:points.length,inputRows,prescreenedRows,selectorCalls,dedupHits,
      selectorCallAvoidanceRate:points.length?dedupHits/points.length:0,
      averagePrescreenRowsPerSelectorCall:selectorCalls?prescreenedRows/selectorCalls:0,
    }),
    methodology:Object.freeze({
      marketWideRefreshEachFiveMinutes:true,
      twoStageLightweightPrescreen:true,
      semanticSnapshotDeduplication:true,
      duplicateSymbolSuppression:true,
      heldSymbolExclusionOccursOnlyAtAllocationGate:true,
      futureOutcomeUsed:false,
      entryThresholdRelaxed:false,
      frozenDynamic50Replaced:false,
      formalOos:false,
      promotionEligible:false,
    }),
    policy:Object.freeze(cfg),
    safety:PHASE57_INTRADAY_UNIVERSE_SAFETY,
  });
}

export default {buildIntradayDynamicUniverseTimeline,PHASE57_INTRADAY_UNIVERSE_POLICY,PHASE57_INTRADAY_UNIVERSE_SAFETY};
