import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const FROM='2024-10-01',TO='2026-06-11';
const USABLE=120,TOTAL=122;
const SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false});
const registry=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-source-validation-only-registry.json',import.meta.url),'utf8'));
const phaseA=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-phase-a.json',import.meta.url),'utf8'));
const excludedSourceSessions=new Set(registry.sessions.map(row=>row.sessionDate));

function splitDates(dates){
  if(dates.length!==TOTAL)throw new Error('allocation requires exactly 122 eligible dates');
  return Object.freeze({development:Object.freeze(dates.slice(0,72)),purgeDevelopmentValidation:Object.freeze(dates.slice(72,73)),
    validation:Object.freeze(dates.slice(73,97)),purgeValidationOos:Object.freeze(dates.slice(97,98)),
    untouchedOos:Object.freeze(dates.slice(98)),usableSessionCount:USABLE,purgeSessionCount:2,
    validationReleased:false,untouchedOosReleased:false});
}

function overlapsConsumed(date){return phaseA.consumedEvidence.datasets.some(item=>date>=item.firstSession&&date<=item.lastSession);}

export function buildFreshAllocation(calendarRows){
  if(!Array.isArray(calendarRows))throw new TypeError('calendar rows are required');
  const seen=new Set(),eligible=[];let invalidRows=0,halfDaysExcluded=0,sourceValidationExcluded=0,consumedExcluded=0;
  for(const row of calendarRows){
    const date=String(row?.Date??''),division=String(row?.HolDiv??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!['0','1','2','3'].includes(division)){invalidRows+=1;continue;}
    if(seen.has(date))throw new Error('calendar contains duplicate dates');seen.add(date);
    if(division!=='1'){if(division==='2')halfDaysExcluded+=1;continue;}
    if(excludedSourceSessions.has(date)){sourceValidationExcluded+=1;continue;}
    if(overlapsConsumed(date)){consumedExcluded+=1;continue;}
    if(date>=FROM&&date<=TO)eligible.push(date);
  }
  eligible.sort();
  if(invalidRows||eligible.length<TOTAL)return Object.freeze({status:'ALLOCATION_NOT_READY',invalidRows,eligibleSessionCount:eligible.length,
    halfDaysExcluded,sourceValidationExcluded,consumedExcluded,safety:SAFETY});
  const allocated=eligible.slice(0,TOTAL),split=splitDates(allocated),reserve=eligible.slice(TOTAL);
  return Object.freeze({schemaVersion:1,phase:'57.selector-minimal-hybrid.fresh-session-allocation',status:'FRESH_120_ALLOCATION_CANDIDATE',
    datasetId:'PHASE57_JQUANTS_OHLCMIN_FRESH120_V1',source:'JQUANTS_OHLCMIN_ADDON',queryWindow:{from:FROM,to:TO},
    allocationPolicy:'FRESH_120_PLUS_TWO_ONE_SESSION_PURGES',calendarRowsObserved:calendarRows.length,
    invalidRows,halfDaysExcluded,sourceValidationExcluded,consumedExcluded,
    eligibleSessionCount:eligible.length,allocatedSessionCount:TOTAL,allocatedUsableSessionCount:USABLE,
    firstAllocatedSession:allocated[0],lastAllocatedSession:allocated.at(-1),split,
    reserve:{classification:'ARK_WIDE_SEALED_RESERVE',sessionCount:reserve.length,firstSession:reserve[0]??null,lastSession:reserve.at(-1)??null,
      rawAcquisitionAllowed:true,featureCalculationAllowed:false,labelGenerationAllowed:false,diagnosticAllowed:false,manualInspectionAllowed:false},
    guards:{sourceValidationSessionsExcluded:true,consumedPeriodExcluded:true,resultsInspectedBeforeAllocation:false,
      sameTimestampCrossSectionAtomic:true,splitMutableAfterFreeze:false,oosPayloadRequested:false},
    secretPersisted:false,rawMarketDataPersisted:false,validationReleased:false,untouchedOosReleased:false,safety:SAFETY});
}

async function run({apiKey,fetchImpl=globalThis.fetch}={}){
  const key=String(apiKey??'').trim();if(!key)return {status:'AUTH_REQUIRED',safety:SAFETY};
  const url=new URL('https://api.jquants.com/v2/markets/calendar');url.searchParams.set('from',FROM);url.searchParams.set('to',TO);
  const response=await fetchImpl(url,{headers:{Accept:'application/json','x-api-key':key},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(60_000)});
  if(response.status!==200)return {status:response.status===401?'AUTH_REJECTED':response.status===403?'BLOCKED_ENTITLEMENT':response.status===429?'RATE_LIMITED':`HTTP_${response.status}`,safety:SAFETY};
  const text=await response.text();if(Buffer.byteLength(text)>2_000_000)return {status:'CALENDAR_RESPONSE_TOO_LARGE',safety:SAFETY};
  const payload=JSON.parse(text);if(!Array.isArray(payload?.data))return {status:'INVALID_CALENDAR_SCHEMA',safety:SAFETY};
  return buildFreshAllocation(payload.data);
}

async function main(){
  const report=await run({apiKey:process.env.JQUANTS_API_KEY});const content=JSON.stringify(report,null,2)+'\n';
  const directory='artifacts/phase57-jquants-fresh-allocation';fs.mkdirSync(directory,{recursive:true,mode:0o700});
  fs.writeFileSync(`${directory}/report.json`,content,{mode:0o600});fs.writeFileSync(`${directory}/report.sha256`,`${createHash('sha256').update(content).digest('hex')}  report.json\n`,{mode:0o600});
  console.log('JQUANTS_FRESH_ALLOCATION_REPORT '+JSON.stringify(report));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(()=>{
  console.error('JQUANTS_FRESH_ALLOCATION_INTERNAL_ERROR');process.exitCode=1;
});

export const Phase57AllocationInternals=Object.freeze({FROM,TO,USABLE,TOTAL,splitDates});
