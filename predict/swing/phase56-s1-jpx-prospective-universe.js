import {createHash} from 'node:crypto';
import {selectJpxOpportunityUniverse} from '../daytrade/phase57-p25-jpx-opportunity-universe.js';
import {EXPANDED_UNIVERSE} from '../daytrade/phase57-expanded-universe.js';

export const PHASE56_SWING_S1_SAFETY=Object.freeze({
  phase:'56.swing.s1.jpx-prospective-universe',
  mode:'READ_ONLY_POINT_IN_TIME_SWING_UNIVERSE_RESEARCH',
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

export const PHASE56_SWING_S1_POLICY=Object.freeze({
  sourceScope:'JPX_DOMESTIC_PRIME_STANDARD_GROWTH',
  preOpenCutoffHmJst:'08:50',
  dynamicVariants:Object.freeze([30,40,50]),
  fixed5:Object.freeze(['7203.T','6758.T','9984.T','8306.T','8035.T']),
  oldFixed30:Object.freeze([...EXPANDED_UNIVERSE]),
  minimumEligibleCrossSection:3000,
  maxPerSector:4,
  maximumRowAgeMs:12*60*60*1000,
  completedScreenerCycleRequired:true,
  pointInTimeOnly:true,
  directionAgnosticOpportunityStrength:true,
  outcomeDrivenWinnerFilteringAllowed:false,
  currentOuterOosUniverseSizeSelectionAllowed:false,
  currentOuterOosHorizonSelectionAllowed:false,
  thresholdSearchAllowed:false,
  postHocSymbolFilteringAllowed:false,
  dailyMarketSpeedRequired:false,
  boardOrTickUsed:false,
  microstructureUsed:false,
});

const SAFE_FINGERPRINT_FIELDS=Object.freeze([
  'symbol','sector','market','currentPrice','volume','volumeRatio','dailyChangePercent',
  'atrPercent','discoveryScore','technicalScore','confidence','qualityScore','scannedAt','status',
]);
const JST=new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',
});

function normalizeSymbol(value){return String(value??'').trim().toUpperCase();}
function snapshotGeneratedAt(snapshot){return snapshot?.meta?.generatedAt??snapshot?.generatedAt??null;}
function jstParts(timestamp){
  const ms=Date.parse(String(timestamp??''));
  if(!Number.isFinite(ms))throw new TypeError('Swing S1 snapshot generatedAt must be a valid timestamp');
  const parts=Object.fromEntries(JST.formatToParts(new Date(ms)).map(x=>[x.type,x.value]));
  return {sessionDate:`${parts.year}-${parts.month}-${parts.day}`,hm:`${parts.hour}:${parts.minute}`};
}
function canonicalEntries(snapshot){
  const rows=Array.isArray(snapshot?.entries)?snapshot.entries:[];
  const bySymbol=new Map(),duplicates=[];
  for(const raw of rows){
    const symbol=normalizeSymbol(raw?.symbol);
    if(!symbol)continue;
    if(bySymbol.has(symbol)){duplicates.push(symbol);continue;}
    bySymbol.set(symbol,{...raw,symbol});
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
function nestedPrefix(shorter,longer){return shorter.every((row,index)=>longer[index]?.symbol===row.symbol);}
function blocked({snapshot,reason,detail=null,fingerprint=null,inputCount=0,eligibleCount=0}){
  const generatedAt=snapshotGeneratedAt(snapshot);
  let sessionDate=null,hm=null;
  try{({sessionDate,hm}=jstParts(generatedAt));}catch{}
  return Object.freeze({
    phase:'56.swing.s1.jpx-prospective-universe',
    status:'BLOCKED_SWING_PROSPECTIVE_UNIVERSE',
    ready:false,
    reason,
    detail,
    sessionDate,
    captureHmJst:hm,
    sourceSnapshotGeneratedAt:generatedAt,
    sourceSnapshotFingerprint:fingerprint,
    inputCount,
    eligibleCount,
    variants:null,
    methodology:Object.freeze({
      prospectiveOnly:true,
      historicalBackfill:false,
      pointInTimeOnly:true,
      usesFutureOutcome:false,
      usesTradeResult:false,
      usesOuterOosPerformance:false,
      currentOuterOosDoesNotSelectUniverseSize:true,
      currentOuterOosDoesNotSelectHorizon:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE56_SWING_S1_SAFETY,
  });
}

/**
 * Freeze a direction-agnostic Swing candidate rank from a completed overnight JPX
 * screener snapshot before the session opens. Dynamic30/40/50 are sensitivity
 * prefixes of the same pre-outcome rank; current outer OOS is never used to choose N.
 */
export function buildSwingS1ProspectiveUniverseRecord({snapshot}={}){
  const generatedAt=snapshotGeneratedAt(snapshot);
  const {sessionDate,hm}=jstParts(generatedAt);
  if(hm>=PHASE56_SWING_S1_POLICY.preOpenCutoffHmJst){
    return blocked({snapshot,reason:'CAPTURE_AFTER_PREOPEN_CUTOFF',detail:{cutoffHmJst:PHASE56_SWING_S1_POLICY.preOpenCutoffHmJst}});
  }
  if(snapshot?.meta?.refreshProgress?.cycleComplete!==true){
    return blocked({snapshot,reason:'SCREENER_CYCLE_INCOMPLETE',detail:{refreshProgress:snapshot?.meta?.refreshProgress??null}});
  }

  const canonical=canonicalEntries(snapshot);
  const fingerprint=safeFingerprint(canonical.entries);
  if(canonical.duplicateSymbols.length){
    return blocked({snapshot,reason:'DUPLICATE_SYMBOL_ROWS',detail:{duplicateSymbols:canonical.duplicateSymbols},fingerprint,inputCount:canonical.entries.length});
  }

  const selected=selectJpxOpportunityUniverse({
    entries:canonical.entries,
    dayCount:1,
    swingCount:50,
    maxCombinedCount:50,
    maxPerSector:PHASE56_SWING_S1_POLICY.maxPerSector,
    asOf:generatedAt,
    maxAgeMs:PHASE56_SWING_S1_POLICY.maximumRowAgeMs,
  });
  if(selected.eligibleCount<PHASE56_SWING_S1_POLICY.minimumEligibleCrossSection){
    return blocked({
      snapshot,reason:'INSUFFICIENT_POINT_IN_TIME_CROSS_SECTION',fingerprint,
      inputCount:canonical.entries.length,eligibleCount:selected.eligibleCount,
      detail:{minimumEligibleCrossSection:PHASE56_SWING_S1_POLICY.minimumEligibleCrossSection},
    });
  }
  if(selected.swing.length<50){
    return blocked({
      snapshot,reason:'INSUFFICIENT_DIVERSIFIED_SWING_CANDIDATES',fingerprint,
      inputCount:canonical.entries.length,eligibleCount:selected.eligibleCount,
      detail:{selectedSwingCount:selected.swing.length,maxPerSector:PHASE56_SWING_S1_POLICY.maxPerSector},
    });
  }

  const s30=selected.swing.slice(0,30),s40=selected.swing.slice(0,40),s50=selected.swing.slice(0,50);
  if(!nestedPrefix(s30,s40)||!nestedPrefix(s40,s50))throw new Error('Swing S1 dynamic variants must be nested prefixes of one frozen rank');
  const symbols=rows=>Object.freeze(rows.map(row=>row.symbol));

  return Object.freeze({
    phase:'56.swing.s1.jpx-prospective-universe',
    status:'SWING_PROSPECTIVE_UNIVERSE_FROZEN',
    ready:true,
    sessionDate,
    captureHmJst:hm,
    sourceSnapshotGeneratedAt:generatedAt,
    sourceSnapshotFingerprint:fingerprint,
    inputCount:canonical.entries.length,
    eligibleCount:selected.eligibleCount,
    variants:Object.freeze({
      SWING_FIXED_5:PHASE56_SWING_S1_POLICY.fixed5,
      SWING_OLD_FIXED_30:PHASE56_SWING_S1_POLICY.oldFixed30,
      SWING_DYNAMIC_30:symbols(s30),
      SWING_DYNAMIC_40:symbols(s40),
      SWING_DYNAMIC_50:symbols(s50),
    }),
    rankAudit:Object.freeze({
      maxPerSector:PHASE56_SWING_S1_POLICY.maxPerSector,
      swing50:Object.freeze(s50.map(row=>Object.freeze({
        symbol:row.symbol,
        sector:row.sector,
        opportunityScore:row.opportunityScore,
        sourceScannedAt:row.sourceScannedAt,
      }))),
      dynamic30PrefixOf40:true,
      dynamic40PrefixOf50:true,
    }),
    methodology:Object.freeze({
      prospectiveOnly:true,
      historicalBackfill:false,
      completedScreenerCycleRequired:true,
      pointInTimeOnly:true,
      directionAgnosticOpportunityStrength:true,
      usesFutureOutcome:false,
      usesTradeResult:false,
      usesOuterOosPerformance:false,
      oneFrozenRankForDynamic30_40_50:true,
      currentOuterOosDoesNotSelectUniverseSize:true,
      currentOuterOosDoesNotSelectHorizon:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE56_SWING_S1_SAFETY,
  });
}

export default {buildSwingS1ProspectiveUniverseRecord,PHASE56_SWING_S1_POLICY,PHASE56_SWING_S1_SAFETY};
