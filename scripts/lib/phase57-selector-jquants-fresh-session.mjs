import {createHash} from 'node:crypto';

import {buildIntradayDynamicUniverseTimeline} from '../../predict/daytrade/phase57-p25-intraday-dynamic-universe.js';
import {extractPhase57MinimalHybridFeatures,runPhase57MinimalHybrid} from '../../predict/daytrade/phase57-selector-minimal-hybrid.js';
import {buildPhase57MinimalHybridTargets} from '../../predict/daytrade/phase57-selector-minimal-hybrid-targets.js';
import {selectPhase57SelectorV3} from '../../predict/daytrade/phase57-selector-v3.js';
import {
  aggregateJquantsMinutesToFiveMinuteBars,
  normalizeJquantsMinuteRows,
  Phase57SelectorJquantsMinuteInternals,
} from './phase57-selector-jquants-minute.mjs';

const API_BASE='https://api.jquants.com/';
const MINUTE_PATH='v2/equities/bars/minute';
const MASTER_PATH='v2/equities/master';
const TIMESTAMP_CONTRACT='BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES';
const ALLOWED_MARKETS=new Set(['0111','0112','0113']);
const DOMESTIC_STOCK_PRODUCT='011';
const DECISION_TIMES=Object.freeze([
  '10:00','10:05','10:10','10:15','10:20','10:25','10:30',
  '13:30','13:35','13:40','13:45','13:50','13:55','14:00','14:05','14:10','14:15','14:20','14:25','14:30',
]);
const SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false});
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const sha256=value=>createHash('sha256').update(value).digest('hex');

function cutoffIso(date,time){return new Date(`${date}T${time}:00+09:00`).toISOString();}

async function requestJson({apiKey,path,query,fetchImpl=globalThis.fetch,attempts=4}){
  const url=new URL(path,API_BASE);
  for(const [name,value] of Object.entries(query))if(value!==null&&value!==undefined&&String(value)!=='')url.searchParams.set(name,String(value));
  for(let attempt=0;attempt<attempts;attempt+=1){
    const response=await fetchImpl(url,{headers:{Accept:'application/json','x-api-key':apiKey},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(90_000)});
    if(response.status===200){
      const body=await response.text();
      if(Buffer.byteLength(body)>30_000_000)throw new Error('JQUANTS_PAGE_TOO_LARGE');
      return JSON.parse(body);
    }
    if((response.status===429||response.status>=500)&&attempt+1<attempts){await sleep((attempt+1)*5000);continue;}
    if(response.status===401)throw new Error('AUTH_REJECTED');
    if(response.status===403)throw new Error('BLOCKED_ENTITLEMENT');
    if(response.status===429)throw new Error('RATE_LIMITED');
    throw new Error(`JQUANTS_HTTP_${response.status}`);
  }
  throw new Error('JQUANTS_REQUEST_EXHAUSTED');
}

async function fetchMinuteDate({apiKey,date,fetchImpl=globalThis.fetch,paceMs=1100}){
  const raw=[];const seenPagination=new Set();let paginationKey='';let pageCount=0;
  for(let page=0;page<2500;page+=1){
    if(page)await sleep(paceMs);
    const payload=await requestJson({apiKey,path:MINUTE_PATH,query:{date,pagination_key:paginationKey},fetchImpl});
    if(!Array.isArray(payload?.data))throw new Error('JQUANTS_MINUTE_SCHEMA_INVALID');
    raw.push(...payload.data);pageCount+=1;
    const next=String(payload.pagination_key??payload.paginationKey??'');
    if(!next)break;
    if(seenPagination.has(next)||page===2499)throw new Error('JQUANTS_MINUTE_PAGINATION_INVALID');
    seenPagination.add(next);paginationKey=next;
  }
  return {raw,pageCount,paginationComplete:true};
}

async function fetchMasterDate({apiKey,date,fetchImpl=globalThis.fetch}){
  const payload=await requestJson({apiKey,path:MASTER_PATH,query:{date},fetchImpl});
  if(!Array.isArray(payload?.data))throw new Error('JQUANTS_MASTER_SCHEMA_INVALID');
  return payload.data;
}

function normalizeMaster(rows,date){
  const byCode=new Map();let invalidRows=0,duplicateCodes=0;
  for(const row of rows){
    const code=String(row?.Code??'').trim().toUpperCase();
    const rowDate=String(row?.Date??'');
    if(rowDate!==date||!Phase57SelectorJquantsMinuteInternals.ISSUE_CODE.test(code)){invalidRows+=1;continue;}
    if(byCode.has(code)){duplicateCodes+=1;continue;}
    byCode.set(code,Object.freeze({
      sourceCode:code,symbol:Phase57SelectorJquantsMinuteInternals.sourceCodeToSymbol(code),
      sector:String(row?.S33Nm??row?.S33??'UNKNOWN').trim()||'UNKNOWN',
      marketCode:String(row?.Mkt??''),market:String(row?.MktNm??row?.Mkt??'UNKNOWN').trim()||'UNKNOWN',
      productCategory:String(row?.ProdCat??''),
    }));
  }
  return {byCode,invalidRows,duplicateCodes};
}

function canonicalMinute(row){
  return JSON.stringify([row.date,row.time,row.code,row.open,row.high,row.low,row.close,row.volume,row.turnover]);
}

function canonicalBar(bar){
  return JSON.stringify([bar.sessionDate,bar.sourceCode,bar.timestamp,bar.availableAt,bar.open,bar.high,bar.low,bar.close,bar.volume,bar.turnover,bar.observedMinuteCount]);
}

function groupBars(bars,master){
  const bySymbol=new Map();
  for(const bar of bars){
    const meta=master.byCode.get(bar.sourceCode);
    const commonIssue=bar.sourceCode.length===4||bar.sourceCode.endsWith('0');
    if(!meta||!ALLOWED_MARKETS.has(meta.marketCode)||meta.productCategory!==DOMESTIC_STOCK_PRODUCT||!commonIssue)continue;
    if(!bySymbol.has(bar.symbol))bySymbol.set(bar.symbol,{...meta,bars:[]});
    bySymbol.get(bar.symbol).bars.push(bar);
  }
  return bySymbol;
}

function developmentSamples({date,bySymbol}){
  const samples=[];const diagnostics={decisionCutoffCount:0,v1CandidateRows:0,featureRows:0,targetRows:0,skippedTargetRows:0};
  const entries=[...bySymbol.values()].map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars}));
  for(const time of DECISION_TIMES){
    const featureCutoff=cutoffIso(date,time),cutoffMs=Date.parse(featureCutoff);
    const decisionSegment=time<'12:00'?'AM':'PM';
    const snapshots=[];
    for(const entry of entries){
      const causal=entry.bars.filter(bar=>Date.parse(bar.availableAt)<=cutoffMs);
      if(!causal.length)continue;
      const current=causal.at(-1),first=causal[0];
      snapshots.push({symbol:entry.symbol,sector:entry.sector,market:entry.market,status:'analyzed',scannedAt:featureCutoff,
        currentPrice:current.close,volume:causal.reduce((sum,bar)=>sum+bar.volume,0),dailyChangePercent:(current.close/first.open-1)*100});
    }
    const v1=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf:featureCutoff,entries:snapshots}]}).points[0]?.rawUniverse??[];
    const candidateSet=new Set(v1.map(row=>row.symbol));
    const featureResult=extractPhase57MinimalHybridFeatures({featureCutoff,entries:entries.filter(entry=>candidateSet.has(entry.symbol))});
    const featureBySymbol=new Map(featureResult.rankedFeatures.map(row=>[row.symbol,row]));
    diagnostics.decisionCutoffCount+=1;diagnostics.v1CandidateRows+=v1.length;diagnostics.featureRows+=featureResult.rankedFeatures.length;
    for(const [v1Index,candidate] of v1.entries()){
      const feature=featureBySymbol.get(candidate.symbol),entry=bySymbol.get(candidate.symbol);
      if(!feature||!entry){diagnostics.skippedTargetRows+=1;continue;}
      const futureBars=entry.bars.filter(bar=>Date.parse(bar.availableAt)>cutoffMs&&bar.sessionSegment===decisionSegment);
      const targetSuite=buildPhase57MinimalHybridTargets({featureCutoff,anchorPrice:feature.currentPrice,sessionDate:date,futureBars});
      if(targetSuite.horizons[12]?.status!=='TARGET_READY'){diagnostics.skippedTargetRows+=1;continue;}
      samples.push({sessionDate:date,featureCutoff,symbol:candidate.symbol,v1Rank:v1Index+1,v1BaseScore:Number(candidate.opportunityScore),
        features:feature.features,targetsByHorizon:targetSuite.horizons});
      diagnostics.targetRows+=1;
    }
  }
  return {samples,diagnostics};
}

function sessionEntries(bySymbol){return [...bySymbol.values()].map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars}));}

function v1AtCutoff({date,time,entries}){
  const featureCutoff=cutoffIso(date,time),cutoffMs=Date.parse(featureCutoff),snapshots=[];
  for(const entry of entries){
    const causal=entry.bars.filter(bar=>Date.parse(bar.availableAt)<=cutoffMs);
    if(!causal.length)continue;
    const current=causal.at(-1),first=causal[0];
    snapshots.push({symbol:entry.symbol,sector:entry.sector,market:entry.market,status:'analyzed',scannedAt:featureCutoff,
      currentPrice:current.close,volume:causal.reduce((sum,bar)=>sum+bar.volume,0),dailyChangePercent:(current.close/first.open-1)*100});
  }
  return {featureCutoff,rows:buildIntradayDynamicUniverseTimeline({snapshots:[{asOf:featureCutoff,entries:snapshots}]}).points[0]?.rawUniverse??[]};
}

async function loadFreshSession({apiKey,date,fold,fetchImpl=globalThis.fetch,paceMs=1100}={}){
  if(!String(apiKey??'').trim())throw new Error('JQUANTS_API_KEY_REQUIRED');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(date??'')))throw new Error('SESSION_DATE_REQUIRED');
  if(!['DEVELOPMENT','PURGE','VALIDATION','UNTOUCHED_OOS'].includes(fold))throw new Error('FOLD_REQUIRED');
  const [{raw,pageCount,paginationComplete},masterRows]=await Promise.all([
    fetchMinuteDate({apiKey,date,fetchImpl,paceMs}),fetchMasterDate({apiKey,date,fetchImpl}),
  ]);
  const normalized=normalizeJquantsMinuteRows(raw);
  const exactDuplicateRows=raw.length-normalized.length;
  if(exactDuplicateRows)throw new Error('EXACT_DUPLICATE_MINUTES_PRESENT');
  const master=normalizeMaster(masterRows,date);
  if(master.invalidRows||master.duplicateCodes)throw new Error('PIT_MASTER_INVALID');
  const bars=aggregateJquantsMinutesToFiveMinuteBars(raw,{sourceMinuteTimestampMeaning:TIMESTAMP_CONTRACT});
  const bySymbol=groupBars(bars,master);
  if(!bySymbol.size)throw new Error('NO_ELIGIBLE_JPX_SYMBOLS');
  const regularRows=normalized.filter(row=>row.sourceMinuteKind==='REGULAR_CONTINUOUS_MINUTE').length;
  const terminalRows=normalized.length-regularRows;
  const minuteDigest=sha256(normalized.map(canonicalMinute).join('\n'));
  const fiveMinuteDigest=sha256(bars.map(canonicalBar).join('\n'));
  const memberDigest=sha256([...bySymbol.keys()].sort().join('\n'));
  const symbolCoverage=[...bySymbol.values()].map(item=>({symbol:item.symbol,fiveMinuteBars:item.bars.length})).sort((a,b)=>a.symbol.localeCompare(b.symbol));
  const structuralAudit={schemaVersion:1,status:'SESSION_STRUCTURAL_AUDIT_PASS',sessionDate:date,fold,
    pageCount,paginationComplete,rawMinuteRows:raw.length,normalizedMinuteRows:normalized.length,
    regularMinuteRows:regularRows,terminalAuctionRows:terminalRows,fiveMinuteBars:bars.length,
    eligibleJpxSymbolCount:bySymbol.size,exactDuplicateRows:0,timestampConflicts:0,invalidMinuteRows:0,
    lunchViolations:0,futureAvailabilityViolations:0,masterRows:masterRows.length,masterInvalidRows:0,masterDuplicateCodes:0,
    minuteSha256:minuteDigest,fiveMinuteSha256:fiveMinuteDigest,memberSetSha256:memberDigest,
    symbolCoverage,
    timestampContract:TIMESTAMP_CONTRACT,noTradeMinutePolicy:'MISSING_NEVER_FABRICATE',
    corporateActionHandling:'RAW_UNADJUSTED_INTRADAY_SAME_SESSION_FEATURES_AND_TARGETS',
    pointInTimeUniverse:true,rawPersisted:false,secretPersisted:false,
    featureCalculationPerformed:fold==='DEVELOPMENT',labelGenerationPerformed:fold==='DEVELOPMENT',
    outcomeInspectionPerformed:false,researchPayloadReleased:fold==='DEVELOPMENT',
    validationReleased:false,untouchedOosReleased:false,safety:SAFETY};
  return {structuralAudit,bySymbol};
}

export async function acquireFreshSession(options={}){
  const {fold}=options;
  const {structuralAudit,bySymbol}=await loadFreshSession(options);
  const development=fold==='DEVELOPMENT'?developmentSamples({date:structuralAudit.sessionDate,bySymbol}):{samples:[],diagnostics:null};
  return Object.freeze({structuralAudit:Object.freeze(structuralAudit),developmentSamples:Object.freeze(development.samples),
    developmentDiagnostics:development.diagnostics?Object.freeze(development.diagnostics):null});
}

export async function evaluateFreshValidationSession({apiKey,date,expectedAudit,model,fetchImpl=globalThis.fetch,paceMs=1100}={}){
  if(expectedAudit?.fold!=='VALIDATION'||expectedAudit?.sessionDate!==date)throw new Error('frozen Validation structural audit is required');
  const {structuralAudit,bySymbol}=await loadFreshSession({apiKey,date,fold:'VALIDATION',fetchImpl,paceMs});
  for(const name of ['minuteSha256','fiveMinuteSha256','memberSetSha256'])if(structuralAudit[name]!==expectedAudit[name])throw new Error(`Validation source drift: ${name}`);
  const entries=sessionEntries(bySymbol),records=[],points=[];
  for(const time of DECISION_TIMES){
    const {featureCutoff,rows:v1Rows}=v1AtCutoff({date,time,entries});
    const v3=selectPhase57SelectorV3({featureCutoff,entries,threshold:0.7});
    const hybrid=runPhase57MinimalHybrid({featureCutoff,entries,model,baselineDiagnostics:{v3SelectedSymbols:v3.selected.map(row=>row.symbol)}});
    const arms={V1:v1Rows.map((row,index)=>({symbol:row.symbol,rank:index+1,score:Number(row.opportunityScore),remainingOpportunityScore:null})),
      V3:v3.selected.map(row=>({symbol:row.symbol,rank:row.rank,score:row.utilityScore,remainingOpportunityScore:null})),
      HYBRID:hybrid.selected.map(row=>({symbol:row.symbol,rank:row.hybridRank,score:row.hybridScore,remainingOpportunityScore:row.stage2.remainingOpportunityScore,v1Rank:row.v1Rank,softAdjustment:row.softAdjustment}))};
    points.push({sessionDate:date,featureCutoff,selectedCounts:Object.fromEntries(Object.entries(arms).map(([name,rows])=>[name,rows.length])),hybridStatus:hybrid.status});
    const decisionSegment=time<'12:00'?'AM':'PM',cutoffMs=Date.parse(featureCutoff);
    for(const [selector,selected] of Object.entries(arms))for(const row of selected){
      const item=bySymbol.get(row.symbol);if(!item)continue;
      const causal=item.bars.filter(bar=>Date.parse(bar.availableAt)<=cutoffMs);
      if(!causal.length)continue;
      const current=causal.at(-1),futureBars=item.bars.filter(bar=>Date.parse(bar.availableAt)>cutoffMs&&bar.sessionSegment===decisionSegment);
      const targets=buildPhase57MinimalHybridTargets({featureCutoff,anchorPrice:current.close,sessionDate:date,futureBars});
      records.push({sessionDate:date,featureCutoff,symbol:row.symbol,selector,rank:row.rank,score:row.score,
        v1Rank:row.v1Rank??(selector==='V1'?row.rank:null),softAdjustment:row.softAdjustment??null,remainingOpportunityScore:row.remainingOpportunityScore,
        preSelectionMove:Math.abs(current.close/causal[0].open-1),targetsByHorizon:targets.horizons});
    }
  }
  return Object.freeze({status:'VALIDATION_SESSION_EVALUATED_FROZEN_HYBRID',sessionDate:date,records:Object.freeze(records),points:Object.freeze(points),
    structuralHashesVerified:true,validationReleased:true,untouchedOosReleased:false,hybridModelDigest:model.modelDigest,v3Threshold:0.7,safety:SAFETY});
}

export const Phase57FreshSessionInternals=Object.freeze({DECISION_TIMES,TIMESTAMP_CONTRACT,ALLOWED_MARKETS,DOMESTIC_STOCK_PRODUCT,normalizeMaster,cutoffIso,loadFreshSession,developmentSamples,v1AtCutoff});
export default {acquireFreshSession,evaluateFreshValidationSession,Phase57FreshSessionInternals};
