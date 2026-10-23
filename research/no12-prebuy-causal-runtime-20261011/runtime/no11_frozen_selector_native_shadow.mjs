/**
 * ORIGINAL frozen Phase57 No.1.1 Selector native READ-ONLY runtime.
 * Uses actual frozen Phase57 Ridge parameters and causal feature code.
 * No retrain, fallback score, model refit, RSS order, or broker calls.
 *
 * This is an engineering bridge: an explicit 348-symbol prefilter changes the
 * reference population and is NOT certified to preserve the original
 * all-market selector's economics.  Exact 1M Va, dated master and reference
 * metadata are mandatory; unknown input BLOCKS rather than silently becomes 0.
 */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {isJpxCashTradingDay,previousJpxCashTradingDays} from './jpx_cash_calendar_2026_2027.mjs';
import {OBSERVED_PASS_GATE_ID,checkObservedPassBeforeBuy}
  from './no11_observed_pass_watch_gate.mjs';
import {normalizeAndAggregateMinuteRows}
  from '../../../predict/long-only/phase57-long-only-integrated-dataset.js';
import {normalizeMinuteProvenance}
  from '../../../predict/long-only/phase57-long-only-northstar-semantics.js';
import {measureCorrectedRow}
  from '../../../predict/long-only/phase57-long-only-corrected-measurement.js';
import {
  L1_DECISION_TIMES_JST,buildCausalL1Features,
  addCausalBreadthContext,assignCausalLiquidityBuckets
} from '../../../predict/long-only/phase57-long-only-l1-labels-features.js';
import {scoreL2Candidate}
  from '../../../predict/long-only/phase57-long-only-l2-selector-v1.js';

const FREEZE_FILE=new URL('../../../predict/research/phase57-long-only-frozen-selector-v1.json',import.meta.url);
const FROZEN_JSON_BLOB='6c707566eb074ce89656be1626bd5aed63d044a8';
const INTENT='ARK_NO11_NATIVE_FROZEN_SELECTOR_OBSERVED_PREFILTER_SHADOW_V1';
const SYM=/^[0-9A-Z]{4}\.T$/;
const TIME=/^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$/;
const failure=msg=>{throw Error('NO11_NATIVE_SELECTOR_'+msg);};
const assert=(ok,msg)=>{if(!ok)failure(msg);};
const signature=bytes=>createHash('sha1')
  .update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
const minuteOf=time=>Number(time.slice(0,2))*60+Number(time.slice(3,5));

export function inspectFrozenSelectorAsset(){
  // Windows Git may materialize CRLF. Verify the exact original Git blob
  // after in-memory LF normalization; never rewrite or change Frozen bytes.
  const raw=fs.readFileSync(FREEZE_FILE);
  const bytes=Buffer.from(raw.toString('utf8').replace(/\r\n/g,'\n'));
  assert(signature(bytes)===FROZEN_JSON_BLOB,'FROZEN_JSON_BLOB_MISMATCH');
  const obj=JSON.parse(bytes.toString('utf8')).freezePayload;
  const spec=obj.selectorSpecification;
  assert(spec.model.configuration.artifactSha256===
    '994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb',
    'MODEL_SHA_CHANGED');
  assert(spec.model.configuration.candidateId==='RIDGE_Y30'&&
    spec.model.configuration.heads?.[0]?.featureNames?.length===15,
    'MODEL_NOT_ORIGINAL_RIDGE');
  assert(spec.ranking.topN===5&&
    JSON.stringify(spec.ranking.decisionTimesJst)===JSON.stringify(L1_DECISION_TIMES_JST),
    'DECISION_CLOCKS_CHANGED');
  return {spec,originalFrozenWeightsVerified:true,originalFrozenCodeUsed:true};
}
function checkClock(session,time){
  assert(isJpxCashTradingDay(session),'NOT_CASH_SESSION');
  assert(L1_DECISION_TIMES_JST.includes(time),'NOT_ORIGINAL_DECISION_TIME');
  return session+'T'+time+':00+09:00';
}
function checkReceipt(r,decisionAt){
  assert(r?.schemaId==='ARK_NO11_NATIVE_MINUTE_VA_INPUT_RECEIPT_V1',
    'SOURCE_RECEIPT_REQUIRED');
  assert(r.readOnly===true&&r.orderTransmission===false&&
    r.priceBasis==='RAW_COMPARABLE_FOR_DAILY_REFERENCE'&&
    r.minuteVaUnit==='JPY_EXACT'&&
    r.minuteVaMethod==='SUM_EXECUTED_PRICE_TIMES_QUANTITY'&&
    r.minuteVaSourceCertified===true&&
    r.completeFilteredUniverseCoverage===true&&
    r.datedMasterCertified===true&&
    r.corporateActionsCertified===true&&
    r.observedAtJst&&TIME.test(r.observedAtJst)&&
    r.observedAtJst<=decisionAt,'SOURCE_INCOMPLETE_OR_UNVERIFIED');
  // Caller certification is not broker delivery proof. Do not expose green readiness.
}
function maskCheck(mask,session){
  const prior=previousJpxCashTradingDays(session,1)[0];
  assert(mask?.schemaId===OBSERVED_PASS_GATE_ID&&
    mask.asOfSession===prior&&mask.shadowOnly===true&&
    mask.productionReady===false&&mask.orderTransmission===false&&
    mask.strictNoUnknownFallback===true,'DAYPASS_MASK_STALE_OR_UNSAFE');
  assert(Array.isArray(mask.observedPassSymbols)&&
    mask.observedPassCount===mask.observedPassSymbols.length&&
    mask.observedPassSymbols.length>0&&
    mask.observedPassSymbols.length<=500&&
    new Set(mask.observedPassSymbols).size===mask.observedPassSymbols.length&&
    mask.observedPassSymbols.every(x=>SYM.test(x)),'DAYPASS_MASK_INVALID');
  return new Set(mask.observedPassSymbols);
}
function validateMaster(master,codes,session){
  assert(Array.isArray(master),'DATED_MASTER_REQUIRED');
  const by=new Map();
  for(const row of master){
    assert(row&&SYM.test(row.symbol)&&!by.has(row.symbol) &&
      row.asOfSession===session,'DATED_MASTER_ROW_INVALID');
    const ok=['PRIME','STANDARD','GROWTH'].includes(row.segment)&&
      typeof row.sector==='string'&&row.sector.length>0&&
      typeof row.rawPreviousClose==='number'&&
      Number.isFinite(row.rawPreviousClose)&&row.rawPreviousClose>0&&
      row.corporateActionsCleared===true&&row.priceBasisVerified===true&&
      row.commonEquity===true;
    if(codes.has(row.symbol))assert(ok,'DATED_MASTER_INCOMPLETE_FOR_PASS');
    by.set(row.symbol,row);
  }
  for(const code of codes)assert(by.has(code),'PASS_SYMBOL_MISSING_FROM_MASTER');
  return by;
}
function validateRawMinuteRows(raw,codes,session,decisionAt){
  assert(Array.isArray(raw),'RAW_MINUTE_SOURCE_REQUIRED');
  const unique=new Set();
  let used=0;
  for(const row of raw){
    assert(row&&SYM.test(row.Code)&&codes.has(row.Code)&&row.Date===session &&
      typeof row.Time==='string'&&/^\d\d:\d\d(?::\d\d)?$/.test(row.Time),
      'MINUTE_IDENTITY_INVALID');
    const t=minuteOf(row.Time),start=session+'T'+row.Time.slice(0,5)+':00+09:00';
    const end=session+'T'+String(Math.floor((t+1)/60)).padStart(2,'0')+':'+
      String((t+1)%60).padStart(2,'0')+':00+09:00';
    const maxAllowed=Number(decisionAt.slice(11,13))*60+
      Number(decisionAt.slice(14,16));
    assert(t+1<=maxAllowed && TIME.test(row.knownAtJst)&&
      row.knownAtJst>=end&&row.knownAtJst<=decisionAt,
      'MINUTE_NOT_CAUSAL_OR_NOT_OBSERVED');
    for(const field of ['O','H','L','C','Vo','Va']){
      assert(typeof row[field]==='number'&&Number.isFinite(row[field]),
        'NATIVE_MINUTE_NUMERIC_REQUIRED');
    }
    assert(row.O>0&&row.H>=Math.max(row.O,row.C)&&
      row.L>0&&row.L<=Math.min(row.O,row.C)&&row.Vo>=0&&row.Va>=0&&
      (row.Vo===0 ? row.Va===0:row.Va>0),
      'MINUTE_OHLCV_VA_INVALID');
    const key=row.Code+'|'+row.Time.slice(0,5);
    assert(!unique.has(key),'MINUTE_DUPLICATE');
    unique.add(key);used++;
  }
  return used;
}
function validatePreviousWatches(previous,session,maskSet,decisionAt){
  assert(Array.isArray(previous),'WATCH_STATE_REQUIRED');
  const seen=new Set();
  for(const w of previous){
    assert(w.sessionDate===session&&
      maskSet.has(w.symbol)&&SYM.test(w.symbol)&&
      typeof w.firstSelectedAtJst==='string'&&
      typeof w.lastSelectedAtJst==='string'&&
      TIME.test(w.firstSelectedAtJst)&&TIME.test(w.lastSelectedAtJst)&&
      w.firstSelectedAtJst<=w.lastSelectedAtJst&&
      w.lastSelectedAtJst<=decisionAt&&
      !seen.has(w.symbol),'WATCH_STATE_INVALID');
    seen.add(w.symbol);
  }
  return new Map(previous.map(w=>[w.symbol,w]));
}
export function runOriginalFrozenSelectorShadow({
  sessionDate,decisionTimeJst,mask,sourceReceipt,datedMaster,
  nativeMinuteRows,previousWatches=[]
}={}){
  const decisionAt=checkClock(sessionDate,decisionTimeJst);
  const asset=inspectFrozenSelectorAsset();
  const codes=maskCheck(mask,sessionDate);
  checkReceipt(sourceReceipt,decisionAt);
  const by=validateMaster(datedMaster,codes,sessionDate);
  const used=validateRawMinuteRows(nativeMinuteRows,codes,sessionDate,decisionAt);
  const previous=validatePreviousWatches(previousWatches,sessionDate,codes,decisionAt);
  const agg=normalizeAndAggregateMinuteRows(nativeMinuteRows);
  const minutes=normalizeMinuteProvenance(nativeMinuteRows);
  assert(agg.audit.rejectedRows===0,'NORMALIZER_DROPPED_MINUTES');
  const grouped=new Map(),rawFeatures=[],rejectReasons={};
  for(const symbol of mask.observedPassSymbols){
    const bars=agg.bars.filter(x=>x.symbol===symbol&&x.sessionDate===sessionDate);
    const frame=minutes.get(sessionDate+'|'+symbol)??[];
    if(!bars.length||!frame.length){
      rejectReasons[symbol]='NO_CAUSAL_MINUTE_BARS';continue;
    }
    const detail=by.get(symbol);
    const feature=buildCausalL1Features({
      sessionDate,symbol,decisionTimeJst,bars5m:bars,
      previousAdjustedClose:detail.rawPreviousClose,
      segment:detail.segment,corporateActionFlag:false
    });
    if(!feature){rejectReasons[symbol]='NO_CAUSAL_FEATURE';continue;}
    const prefix=frame.filter(x=>x.availableMinute<=minuteOf(decisionTimeJst));
    const oldest=bars.filter(x=>x.availableAtJst<=decisionAt);
    const measured=measureCorrectedRow({
      feature,bars:oldest,minutes:prefix
    });
    if(measured.decisionPriceValid!==1||
       !(measured.decisionPrice>75)||
       measured.referenceAgeMin<0||measured.referenceAgeMin>5){
      rejectReasons[symbol]='PRICE_OR_FRESHNESS_INELIGIBLE';continue;
    }
    rawFeatures.push(feature);
    grouped.set(symbol,{measured,feature});
  }
  // Apply EXACT existing native cross-sectional transformations before scoring.
  // Filtered universe is a user-directed overlay and NOT equal to original L1.
  const sectors=Object.fromEntries([...by.entries()].map(([sym,row])=>
    [sessionDate+'|'+sym,row.sector]));
  const breadth=addCausalBreadthContext(rawFeatures,{sectorBySymbol:sectors});
  const features=assignCausalLiquidityBuckets(breadth);
  const eligible=[];
  const requiredNumeric=[
    'currentReturnPct','momentum30Pct','vwapDistancePct',
    'vwapSlope15Pct','cumulativeTurnover','volumeAccelerationRatio',
    'trendEfficiency','rangeExpansionPct','marketBreadthPositivePct',
    'sectorBreadthPositivePct'
  ];
  for(const f of features){
    if(requiredNumeric.some(key=>typeof f[key]!=='number'||
        !Number.isFinite(f[key]))){
      rejectReasons[f.symbol]='ORIGINAL_REQUIRED_FEATURE_NOT_OBSERVED';continue;
    }
    let score;
    try {score=scoreL2Candidate(f,asset.spec.model.configuration);}
    catch(e){rejectReasons[f.symbol]='ORIGINAL_FEATURE_INPUT_MISSING';continue;}
    if(!Number.isFinite(score)){
      rejectReasons[f.symbol]='SCORE_NONFINITE';continue;
    }
    const measured=grouped.get(f.symbol).measured;
    eligible.push({
      sessionDate,symbol:f.symbol,decisionTimestamp:decisionAt,
      decisionTimeJst,decisionPrice:measured.decisionPrice,
      referenceAgeMin:measured.referenceAgeMin,savedV1Score:score,
      selectorEventId:sessionDate+'|'+decisionAt+'|'+f.symbol
    });
  }
  eligible.sort((a,b)=>b.savedV1Score-a.savedV1Score||
    a.symbol.localeCompare(b.symbol));
  const selected=eligible.slice(0,asset.spec.ranking.topN).map((x,i)=>({
    ...x,newEligibleRank:i+1
  }));
  const watches=[...previous.values()].map(v=>({...v}));
  const events=[];
  for(const s of selected){
    const old=previous.get(s.symbol);
    const eventType=old?'WATCH_REFRESH':'WATCH_FIRST_SELECTION';
    const current={
      sessionDate,symbol:s.symbol,
      firstSelectedAtJst:old?.firstSelectedAtJst??decisionAt,
      lastSelectedAtJst:decisionAt,
      refreshCount:old?.refreshCount?old.refreshCount+1:0
    };
    if(old?.lastSelectedAtJst===decisionAt)continue; // same-clock retry is idempotent
    if(old)watches[watches.findIndex(w=>w.symbol===s.symbol)]=current;
    else watches.push(current);
    events.push({...s,watchEventType:eventType,
      firstWatchIdentity:sessionDate+'|'+s.symbol});
  }
  // Explicitly NO native runtime or economic parity certification:
  // cross-section narrowed from original full market and Va not yet supplied
  // in real-time by RSS.
  return {
    schemaId:INTENT,sessionDate,decisionTimestamp:decisionAt,
    sourceScope:'FILTERED_G1_348_USER_DIRECTED_STRATEGY_OVERLAY',
    frozenRidgeParametersUnchanged:true,
    frozenDecisionClocksUnchanged:true,
    frozenModelArtifactSha256:asset.spec.model.configuration.artifactSha256,
    originalCrossSectionReferenceUnchanged:false,
    fullMarketEquivalent:false,
    nativeMinuteRowsInspected:used,
    observedCandidatePool:mask.observedPassCount,
    rawFeatureCandidates:rawFeatures.length,
    rankableCandidates:eligible.length,
    skippedCandidates:rejectReasons,
    selected,watchEvents:events,nextWatches:watches,
    watchRefreshIdentityPreserved:true,
    firstEntryP1Executed:false,state9Executed:false,
    h235Executed:false,capitalExecuted:false,exitExecuted:false,
    brokerOrderPrepared:false,liveSourceCertified:false,
    forwardEconomicValidationComplete:false,
    shadowOnly:true,productionReady:false,orderTransmission:false
  };
}
