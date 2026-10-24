/**
 * ORIGINAL frozen Phase57 No.1.1 Selector native READ-ONLY runtime.
 * Fixed Ridge weights, feature math, ten scheduled cutoffs and Top5 unchanged.
 * Explicit RSS proxy receipts may be processed after a cutoff, within 90s.
 * Scheduled bar cutoff and actual PC receipt/evaluation time remain distinct.
 * No fitting, broker calls, orders or economic-parity certification.
 */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {isJpxCashTradingDay,previousJpxCashTradingDays} from './jpx_cash_calendar_2026_2027.mjs';
import {OBSERVED_PASS_GATE_ID,checkObservedPassBeforeBuy}
  from './no11_observed_pass_watch_gate.mjs';
import {validateNo11Chart50Plan}
  from './no11_rss_chart_50_prescreen.mjs';
import {RSS_VA_PROXY_RECEIPT}
  from './no11_rss_vendor_va_shadow_adapter.mjs';
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
const TIME=/^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?\+09:00$/;
const failure=msg=>{throw Error('NO11_NATIVE_SELECTOR_'+msg);};
const assert=(ok,msg)=>{if(!ok)failure(msg);};
const signature=bytes=>createHash('sha1')
  .update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
const minuteOf=time=>Number(time.slice(0,2))*60+Number(time.slice(3,5));
const instant=x=>typeof x==='string'&&TIME.test(x)?Date.parse(x):NaN;

export function inspectFrozenSelectorAsset(){
  // Canonicalize checkout CRLF only in memory; never rewrite Frozen bytes.
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
function checkReceipt(r,decisionAt,nativeMinuteRows,selectorSymbols,receivedBy){
  if(r?.schemaId===RSS_VA_PROXY_RECEIPT){
    const sourceHash=createHash('sha256')
      .update(JSON.stringify(nativeMinuteRows)).digest('hex');
    assert(r.readOnly===true&&r.shadowOnly===true&&
      r.productionReady===false&&r.orderTransmission===false&&
      r.modelInputDistributionChanged===true&&
      r.historicalOriginalVaParityNotRequired===true&&
      r.nativeExactMinuteVaCertified===false&&
      r.marketTurnoverFieldTimestampCertified===false&&
      r.inputKind==='RSS_MARKET_OBSERVED_60S_CUMULATIVE_DELTA_PROXY'&&
      r.decisionAtJst===receivedBy&&
      r.sessionDate===decisionAt.slice(0,10)&&
      r.validOneMinuteProxyRows===nativeMinuteRows.length&&
      r.hasAnyUsableRows===true&&
      r.derivedMinuteRowsSha256===sourceHash&&
      Array.isArray(r.selectedSymbols)&&
      JSON.stringify(r.selectedSymbols)===JSON.stringify(selectorSymbols)&&
      nativeMinuteRows.every(row=>row.vaProvenance===
        'RSS_MARKET_CUMULATIVE_60S_ESTIMATE_NOT_VENDOR_MINUTE_VA'),
      'RSS_APPROX_VA_SOURCE_UNUSABLE');
    return 'RSS_MARKET_APPROX_60S';
  }
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
    Number.isFinite(instant(r.observedAtJst))&&
    instant(r.observedAtJst)<=instant(receivedBy),
    'SOURCE_INCOMPLETE_OR_UNVERIFIED');
  return 'NATIVE_MINUTE_EXACT_RESEARCH_RECEIPT';
}
function maskCheck(mask,session){
  const prior=previousJpxCashTradingDays(session,1)[0];
  assert(mask?.schemaId===OBSERVED_PASS_GATE_ID&&
    mask.asOfSession===prior&&mask.shadowOnly===true&&
    mask.productionReady===false&&mask.orderTransmission===false&&
    mask.strictNoUnknownFallback===true,'DAYPASS_MASK_STALE_OR_UNSAFE');
  assert(Array.isArray(mask.observedPassSymbols)&&
    mask.observedPassCount===mask.observedPassSymbols.length&&
    mask.observedPassSymbols.length>0&&mask.observedPassSymbols.length<=500&&
    new Set(mask.observedPassSymbols).size===mask.observedPassSymbols.length&&
    mask.observedPassSymbols.every(x=>SYM.test(x)),'DAYPASS_MASK_INVALID');
  return new Set(mask.observedPassSymbols);
}
function validateMaster(master,codes,session){
  assert(Array.isArray(master),'DATED_MASTER_REQUIRED');
  const by=new Map();
  for(const row of master){
    assert(row&&SYM.test(row.symbol)&&!by.has(row.symbol)&&
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
function validateRawMinuteRows(raw,codes,session,decisionAt,receivedBy){
  assert(Array.isArray(raw),'RAW_MINUTE_SOURCE_REQUIRED');
  const unique=new Set();let used=0;
  for(const row of raw){
    assert(row&&SYM.test(row.Code)&&codes.has(row.Code)&&row.Date===session&&
      typeof row.Time==='string'&&/^(?:[01]\d|2[0-3]):[0-5]\d(?::00)?$/.test(row.Time),
      'MINUTE_IDENTITY_INVALID');
    const t=minuteOf(row.Time);
    const end=session+'T'+String(Math.floor((t+1)/60)).padStart(2,'0')+':'+
      String((t+1)%60).padStart(2,'0')+':00+09:00';
    const cutoff=Number(decisionAt.slice(11,13))*60+Number(decisionAt.slice(14,16));
    assert(t+1<=cutoff&&Number.isFinite(instant(row.knownAtJst))&&
      instant(row.knownAtJst)>=instant(end)&&
      instant(row.knownAtJst)<=instant(receivedBy),
      'MINUTE_NOT_CAUSAL_OR_NOT_OBSERVED');
    for(const field of ['O','H','L','C','Vo','Va']){
      assert(typeof row[field]==='number'&&Number.isFinite(row[field]),
        'NATIVE_MINUTE_NUMERIC_REQUIRED');
    }
    assert(row.O>0&&row.H>=Math.max(row.O,row.C)&&
      row.L>0&&row.L<=Math.min(row.O,row.C)&&row.Vo>=0&&row.Va>=0&&
      (row.Vo===0?row.Va===0:row.Va>0),'MINUTE_OHLCV_VA_INVALID');
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
    assert(w.sessionDate===session&&maskSet.has(w.symbol)&&SYM.test(w.symbol)&&
      Number.isFinite(instant(w.firstSelectedAtJst))&&
      Number.isFinite(instant(w.lastSelectedAtJst))&&
      instant(w.firstSelectedAtJst)<=instant(w.lastSelectedAtJst)&&
      instant(w.lastSelectedAtJst)<=instant(decisionAt)&&
      (w.refreshCount===undefined||Number.isInteger(w.refreshCount)&&w.refreshCount>=0)&&
      !seen.has(w.symbol),'WATCH_STATE_INVALID');
    seen.add(w.symbol);
  }
  return new Map(previous.map(w=>[w.symbol,w]));
}
export function runOriginalFrozenSelectorShadow({
  sessionDate,decisionTimeJst,mask,sourceReceipt,datedMaster,
  nativeMinuteRows,previousWatches=[],chartPlan=null,evaluatedAtJst=null
}={}){
  const decisionAt=checkClock(sessionDate,decisionTimeJst);
  const receivedBy=evaluatedAtJst??decisionAt;
  const lag=instant(receivedBy)-instant(decisionAt);
  assert(Number.isFinite(lag)&&receivedBy.slice(0,10)===sessionDate&&
    lag>=0&&lag<=90_000,'EVALUATION_CLOCK_INVALID');
  const asset=inspectFrozenSelectorAsset();
  const g1Codes=maskCheck(mask,sessionDate);
  const selectorSymbols=chartPlan===null?mask.observedPassSymbols:
    validateNo11Chart50Plan({chartPlan,mask,sessionDate});
  const codes=new Set(selectorSymbols);
  assert([...codes].every(s=>g1Codes.has(s)),'CHART50_SYMBOL_OUTSIDE_ORIGINAL_G1_PASS');
  if(chartPlan!==null){
    assert(previousWatches.every(w=>chartPlan.activeWatchSymbols.includes(w.symbol)&&
      chartPlan.protectedChartSymbols.includes(w.symbol)),
      'PERSISTENT_WATCH_NOT_PINNED_IN_CHART50');
  }
  const minuteVaMode=checkReceipt(sourceReceipt,decisionAt,
    nativeMinuteRows,selectorSymbols,receivedBy);
  const by=validateMaster(datedMaster,codes,sessionDate);
  const used=validateRawMinuteRows(nativeMinuteRows,codes,sessionDate,decisionAt,receivedBy);
  const previous=validatePreviousWatches(previousWatches,sessionDate,codes,decisionAt);
  const agg=normalizeAndAggregateMinuteRows(nativeMinuteRows);
  const minutes=normalizeMinuteProvenance(nativeMinuteRows);
  assert(agg.audit.rejectedRows===0,'NORMALIZER_DROPPED_MINUTES');
  const grouped=new Map(),rawFeatures=[],rejectReasons={};
  for(const symbol of selectorSymbols){
    const bars=agg.bars.filter(x=>x.symbol===symbol&&x.sessionDate===sessionDate);
    const frame=minutes.get(sessionDate+'|'+symbol)??[];
    if(!bars.length||!frame.length){rejectReasons[symbol]='NO_CAUSAL_MINUTE_BARS';continue;}
    const detail=by.get(symbol);
    const feature=buildCausalL1Features({sessionDate,symbol,decisionTimeJst,bars5m:bars,
      previousAdjustedClose:detail.rawPreviousClose,segment:detail.segment,corporateActionFlag:false});
    if(!feature){rejectReasons[symbol]='NO_CAUSAL_FEATURE';continue;}
    const prefix=frame.filter(x=>x.availableMinute<=minuteOf(decisionTimeJst));
    const oldest=bars.filter(x=>x.availableAtJst<=decisionAt);
    const measured=measureCorrectedRow({feature,bars:oldest,minutes:prefix});
    if(measured.decisionPriceValid!==1||!(measured.decisionPrice>75)||
      measured.referenceAgeMin<0||measured.referenceAgeMin>5){
      rejectReasons[symbol]='PRICE_OR_FRESHNESS_INELIGIBLE';continue;
    }
    rawFeatures.push(feature);grouped.set(symbol,{measured,feature});
  }
  const sectors=Object.fromEntries([...by.entries()].map(([sym,row])=>
    [sessionDate+'|'+sym,row.sector]));
  const breadth=addCausalBreadthContext(rawFeatures,{sectorBySymbol:sectors});
  const features=assignCausalLiquidityBuckets(breadth);
  const eligible=[];
  const requiredNumeric=['currentReturnPct','momentum30Pct','vwapDistancePct',
    'vwapSlope15Pct','cumulativeTurnover','volumeAccelerationRatio','trendEfficiency',
    'rangeExpansionPct','marketBreadthPositivePct','sectorBreadthPositivePct'];
  for(const f of features){
    if(requiredNumeric.some(key=>typeof f[key]!=='number'||!Number.isFinite(f[key]))){
      rejectReasons[f.symbol]='ORIGINAL_REQUIRED_FEATURE_NOT_OBSERVED';continue;
    }
    let score;
    try{score=scoreL2Candidate(f,asset.spec.model.configuration);}
    catch(e){rejectReasons[f.symbol]='ORIGINAL_FEATURE_INPUT_MISSING';continue;}
    if(!Number.isFinite(score)){rejectReasons[f.symbol]='SCORE_NONFINITE';continue;}
    const measured=grouped.get(f.symbol).measured;
    eligible.push({sessionDate,symbol:f.symbol,decisionTimestamp:decisionAt,
      decisionTimeJst,decisionPrice:measured.decisionPrice,
      referenceAgeMin:measured.referenceAgeMin,savedV1Score:score,
      selectorEventId:sessionDate+'|'+decisionAt+'|'+f.symbol});
  }
  eligible.sort((a,b)=>b.savedV1Score-a.savedV1Score||a.symbol.localeCompare(b.symbol));
  const selected=eligible.slice(0,asset.spec.ranking.topN).map((x,i)=>({...x,newEligibleRank:i+1}));
  const watches=[...previous.values()].map(v=>({...v}));
  const events=[];
  for(const s of selected){
    const old=previous.get(s.symbol);
    if(old?.lastSelectedAtJst===decisionAt)continue;
    const eventType=old?'WATCH_REFRESH':'WATCH_FIRST_SELECTION';
    const current={sessionDate,symbol:s.symbol,
      firstSelectedAtJst:old?.firstSelectedAtJst??decisionAt,
      lastSelectedAtJst:decisionAt,refreshCount:old?(old.refreshCount??0)+1:0};
    if(old)watches[watches.findIndex(w=>w.symbol===s.symbol)]=current;
    else watches.push(current);
    events.push({...s,watchEventType:eventType,firstWatchIdentity:sessionDate+'|'+s.symbol});
  }
  return {
    schemaId:INTENT,sessionDate,decisionTimestamp:decisionAt,
    sourceCutoffAtJst:decisionAt,evaluatedAtJst:receivedBy,
    sourceScope:chartPlan===null?'FILTERED_G1_PASS_USER_DIRECTED_STRATEGY_OVERLAY':
      'FILTERED_G1_PASS_PLUS_CHART50_USER_DIRECTED_STRATEGY_OVERLAY',
    frozenRidgeParametersUnchanged:true,frozenDecisionClocksUnchanged:true,
    frozenModelArtifactSha256:asset.spec.model.configuration.artifactSha256,
    originalCrossSectionReferenceUnchanged:false,fullMarketEquivalent:false,
    nativeMinuteRowsInspected:used,minuteVaMode,
    rssApproximateSourceAdopted:minuteVaMode==='RSS_MARKET_APPROX_60S',
    rssMinuteVaIsNotOriginalExact:minuteVaMode==='RSS_MARKET_APPROX_60S',
    frozenSourceFeatureDistributionUnchanged:minuteVaMode==='NATIVE_MINUTE_EXACT_RESEARCH_RECEIPT',
    observedCandidatePool:mask.observedPassCount,
    allocatedChartSelectorCandidates:selectorSymbols.length,
    chart50PrescreenApplied:chartPlan!==null,
    chartFunctionsReserved:chartPlan?.totalChartFunctionsBudgeted??null,
    nativeFull348ChartCoverageCertified:false,rawFeatureCandidates:rawFeatures.length,
    rankableCandidates:eligible.length,skippedCandidates:rejectReasons,
    selected,watchEvents:events,nextWatches:watches,watchRefreshIdentityPreserved:true,
    firstEntryP1Executed:false,state9Executed:false,h235Executed:false,
    capitalExecuted:false,exitExecuted:false,brokerOrderPrepared:false,
    liveSourceCertified:false,forwardEconomicValidationComplete:false,
    shadowOnly:true,productionReady:false,orderTransmission:false
  };
}
