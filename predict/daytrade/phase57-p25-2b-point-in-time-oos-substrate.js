import {createHash} from 'node:crypto';
import {selectJpxOpportunityUniverse} from './phase57-p25-jpx-opportunity-universe.js';
import {EXPANDED_UNIVERSE} from './phase57-expanded-universe.js';

export const PHASE57_P25_2B_SAFETY=Object.freeze({
  phase:'57.p25.2b.point-in-time-oos-substrate',
  mode:'READ_ONLY_POINT_IN_TIME_OOS_UNIVERSE_SUBSTRATE',
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

export const PHASE57_P25_2B_POLICY=Object.freeze({
  dynamicVariants:Object.freeze([30,40,50]),
  fixed5:Object.freeze(['7203.T','6758.T','9984.T','8306.T','8035.T']),
  oldFixed30:Object.freeze([...EXPANDED_UNIVERSE]),
  minimumEligibleCrossSection:3000,
  maxPerSector:4,
  pointInTimeOnly:true,
  laterSnapshotBackfillAllowed:false,
  duplicateSymbolRowsAllowed:false,
  outerOosUniverseSizeSelectionAllowed:false,
  entryThresholdRelaxationAllowed:false,
  postHocWinnerFilteringAllowed:false,
  preserveBlockedDecisions:true,
});

const SAFE_FINGERPRINT_FIELDS=Object.freeze([
  'symbol','sector','market','currentPrice','volume','volumeRatio','dailyChangePercent',
  'atrPercent','discoveryScore','technicalScore','confidence','qualityScore','scannedAt','status',
]);

function parseTimestamp(value,label){
  const ms=Date.parse(String(value??''));
  if(!Number.isFinite(ms))throw new TypeError(`${label} must be a valid timestamp`);
  return ms;
}

function snapshotGeneratedAt(snapshot){
  return snapshot?.generatedAt??snapshot?.meta?.generatedAt??null;
}

function normalizeSymbol(value){return String(value??'').trim().toUpperCase();}

function canonicalSnapshotEntries(snapshot){
  const entries=Array.isArray(snapshot?.entries)?snapshot.entries:[];
  const bySymbol=new Map();
  const duplicates=[];
  for(const row of entries){
    const symbol=normalizeSymbol(row?.symbol);
    if(!symbol)continue;
    if(bySymbol.has(symbol)){duplicates.push(symbol);continue;}
    bySymbol.set(symbol,{...row,symbol});
  }
  return {
    entries:[...bySymbol.values()].sort((a,b)=>a.symbol.localeCompare(b.symbol)),
    duplicateSymbols:[...new Set(duplicates)].sort(),
  };
}

function safeFingerprint(entries){
  const payload=entries.map(row=>Object.fromEntries(SAFE_FINGERPRINT_FIELDS.map(key=>[key,row?.[key]??null])));
  return createHash('sha256').update(JSON.stringify(payload)).digest('hex');
}

function blocked({sessionDate,decisionTimestamp,reason,sourceSnapshotGeneratedAt=null,sourceSnapshotFingerprint=null,inputCount=0,eligibleCount=0,detail=null}){
  return Object.freeze({
    phase:'57.p25.2b.point-in-time-oos-substrate',
    status:'BLOCKED_POINT_IN_TIME_UNIVERSE',
    ready:false,
    sessionDate:String(sessionDate??''),
    decisionTimestamp:String(decisionTimestamp??''),
    reason,
    detail,
    sourceSnapshotGeneratedAt,
    sourceSnapshotFingerprint,
    inputCount,
    eligibleCount,
    variants:null,
    methodology:Object.freeze({
      pointInTimeOnly:true,
      laterSnapshotBackfill:false,
      usesFutureOutcome:false,
      usesTradeResult:false,
      usesOuterOosPerformance:false,
      universeSizeSelectedFromOuterOos:false,
      entryThresholdRelaxed:false,
      blockedDecisionPreserved:true,
    }),
    safety:PHASE57_P25_2B_SAFETY,
  });
}

function chooseSnapshotAtOrBefore(snapshots,decisionMs){
  const candidates=[];
  for(const snapshot of Array.isArray(snapshots)?snapshots:[]){
    const generatedAt=snapshotGeneratedAt(snapshot);
    const ms=Date.parse(String(generatedAt??''));
    if(Number.isFinite(ms)&&ms<=decisionMs)candidates.push({snapshot,generatedAt:String(generatedAt),ms});
  }
  candidates.sort((a,b)=>b.ms-a.ms);
  if(!candidates.length)return {selected:null,conflict:false};
  const latestMs=candidates[0].ms;
  const latest=candidates.filter(x=>x.ms===latestMs);
  if(latest.length>1){
    const fingerprints=new Set(latest.map(x=>safeFingerprint(canonicalSnapshotEntries(x.snapshot).entries)));
    if(fingerprints.size>1)return {selected:null,conflict:true,generatedAt:latest[0].generatedAt};
  }
  return {selected:latest[0],conflict:false};
}

function nestedPrefix(shorter,longer){
  return shorter.every((row,index)=>longer[index]?.symbol===row.symbol);
}

export function buildP252PointInTimeUniverseAtDecision({
  sessionDate,
  decisionTimestamp,
  snapshots=[],
  minimumEligibleCrossSection=PHASE57_P25_2B_POLICY.minimumEligibleCrossSection,
  maxPerSector=PHASE57_P25_2B_POLICY.maxPerSector,
  maxSnapshotAgeMs=null,
  maxRowAgeMs=null,
}={}){
  const decisionMs=parseTimestamp(decisionTimestamp,'decisionTimestamp');
  if(!Number.isInteger(Number(minimumEligibleCrossSection))||Number(minimumEligibleCrossSection)<50)throw new TypeError('minimumEligibleCrossSection must be an integer >= 50');
  if(!Number.isInteger(Number(maxPerSector))||Number(maxPerSector)<1)throw new TypeError('maxPerSector must be a positive integer');
  if(maxSnapshotAgeMs!==null&&(!Number.isFinite(Number(maxSnapshotAgeMs))||Number(maxSnapshotAgeMs)<0))throw new TypeError('maxSnapshotAgeMs must be null or non-negative');
  if(maxRowAgeMs!==null&&(!Number.isFinite(Number(maxRowAgeMs))||Number(maxRowAgeMs)<0))throw new TypeError('maxRowAgeMs must be null or non-negative');

  const choice=chooseSnapshotAtOrBefore(snapshots,decisionMs);
  if(choice.conflict)return blocked({sessionDate,decisionTimestamp,reason:'CONFLICTING_SNAPSHOTS_AT_SAME_TIMESTAMP',sourceSnapshotGeneratedAt:choice.generatedAt});
  if(!choice.selected)return blocked({sessionDate,decisionTimestamp,reason:'NO_SNAPSHOT_AT_OR_BEFORE_DECISION'});

  const {snapshot,generatedAt,ms:snapshotMs}=choice.selected;
  const canonical=canonicalSnapshotEntries(snapshot);
  const fingerprint=safeFingerprint(canonical.entries);
  if(canonical.duplicateSymbols.length){
    return blocked({sessionDate,decisionTimestamp,reason:'DUPLICATE_SYMBOL_ROWS',sourceSnapshotGeneratedAt:generatedAt,sourceSnapshotFingerprint:fingerprint,inputCount:canonical.entries.length,detail:{duplicateSymbols:canonical.duplicateSymbols}});
  }
  if(maxSnapshotAgeMs!==null&&decisionMs-snapshotMs>Number(maxSnapshotAgeMs)){
    return blocked({sessionDate,decisionTimestamp,reason:'SNAPSHOT_TOO_OLD',sourceSnapshotGeneratedAt:generatedAt,sourceSnapshotFingerprint:fingerprint,inputCount:canonical.entries.length,detail:{snapshotAgeMs:decisionMs-snapshotMs,maxSnapshotAgeMs:Number(maxSnapshotAgeMs)}});
  }

  const selected=selectJpxOpportunityUniverse({
    entries:canonical.entries,
    dayCount:50,
    swingCount:1,
    maxCombinedCount:50,
    maxPerSector:Number(maxPerSector),
    asOf:String(decisionTimestamp),
    maxAgeMs:maxRowAgeMs===null?null:Number(maxRowAgeMs),
  });

  if(selected.eligibleCount<Number(minimumEligibleCrossSection)){
    return blocked({sessionDate,decisionTimestamp,reason:'INSUFFICIENT_POINT_IN_TIME_CROSS_SECTION',sourceSnapshotGeneratedAt:generatedAt,sourceSnapshotFingerprint:fingerprint,inputCount:canonical.entries.length,eligibleCount:selected.eligibleCount,detail:{minimumEligibleCrossSection:Number(minimumEligibleCrossSection)}});
  }
  if(selected.day.length<50){
    return blocked({sessionDate,decisionTimestamp,reason:'INSUFFICIENT_DIVERSIFIED_DAY_CANDIDATES',sourceSnapshotGeneratedAt:generatedAt,sourceSnapshotFingerprint:fingerprint,inputCount:canonical.entries.length,eligibleCount:selected.eligibleCount,detail:{selectedDayCount:selected.day.length,maxPerSector:Number(maxPerSector)}});
  }

  const d30=selected.day.slice(0,30),d40=selected.day.slice(0,40),d50=selected.day.slice(0,50);
  if(!nestedPrefix(d30,d40)||!nestedPrefix(d40,d50))throw new Error('dynamic universe variants must be nested prefixes of one frozen rank');

  const mapRows=rows=>Object.freeze(rows.map(row=>row.symbol));
  return Object.freeze({
    phase:'57.p25.2b.point-in-time-oos-substrate',
    status:'POINT_IN_TIME_UNIVERSE_READY',
    ready:true,
    sessionDate:String(sessionDate??''),
    decisionTimestamp:String(decisionTimestamp),
    sourceSnapshotGeneratedAt:generatedAt,
    sourceSnapshotFingerprint:fingerprint,
    inputCount:canonical.entries.length,
    eligibleCount:selected.eligibleCount,
    variants:Object.freeze({
      FIXED_5:PHASE57_P25_2B_POLICY.fixed5,
      OLD_FIXED_30:PHASE57_P25_2B_POLICY.oldFixed30,
      DYNAMIC_30:mapRows(d30),
      DYNAMIC_40:mapRows(d40),
      DYNAMIC_50:mapRows(d50),
    }),
    rankAudit:Object.freeze({
      maxPerSector:Number(maxPerSector),
      day50:Object.freeze(d50.map(row=>Object.freeze({symbol:row.symbol,sector:row.sector,opportunityScore:row.opportunityScore,sourceScannedAt:row.sourceScannedAt}))),
      dynamic30PrefixOf40:true,
      dynamic40PrefixOf50:true,
    }),
    methodology:Object.freeze({
      pointInTimeOnly:true,
      laterSnapshotBackfill:false,
      snapshotGeneratedAfterDecision:false,
      usesFutureOutcome:false,
      usesTradeResult:false,
      usesOuterOosPerformance:false,
      universeSizeSelectedFromOuterOos:false,
      entryThresholdRelaxed:false,
      oneFrozenRankForDynamic30_40_50:true,
      blockedDecisionPreserved:true,
    }),
    safety:PHASE57_P25_2B_SAFETY,
  });
}

export function buildP252PointInTimeUniverseTimeline({decisionPoints=[],snapshots=[],...options}={}){
  const points=(Array.isArray(decisionPoints)?decisionPoints:[]).map((point,index)=>({
    sessionDate:String(point?.sessionDate??''),
    decisionTimestamp:String(point?.decisionTimestamp??point?.entryTimestamp??''),
    index,
  }));
  const seen=new Set();
  for(const point of points){
    parseTimestamp(point.decisionTimestamp,'decisionTimestamp');
    if(seen.has(point.decisionTimestamp))throw new TypeError(`duplicate decisionTimestamp: ${point.decisionTimestamp}`);
    seen.add(point.decisionTimestamp);
  }
  points.sort((a,b)=>a.decisionTimestamp.localeCompare(b.decisionTimestamp)||a.index-b.index);
  const timeline=points.map(point=>buildP252PointInTimeUniverseAtDecision({...point,snapshots,...options}));
  return Object.freeze({
    phase:'57.p25.2b.point-in-time-oos-substrate',
    status:'POINT_IN_TIME_UNIVERSE_TIMELINE_BUILT',
    decisionCount:timeline.length,
    readyCount:timeline.filter(x=>x.ready).length,
    blockedCount:timeline.filter(x=>!x.ready).length,
    timeline:Object.freeze(timeline),
    methodology:Object.freeze({
      decisionsEvaluatedChronologically:true,
      laterSnapshotBackfill:false,
      blockedDecisionsPreserved:true,
      dynamicUniverseSizesPrecommitted:Object.freeze([30,40,50]),
    }),
    safety:PHASE57_P25_2B_SAFETY,
  });
}

export default {
  buildP252PointInTimeUniverseAtDecision,
  buildP252PointInTimeUniverseTimeline,
  PHASE57_P25_2B_POLICY,
  PHASE57_P25_2B_SAFETY,
};
