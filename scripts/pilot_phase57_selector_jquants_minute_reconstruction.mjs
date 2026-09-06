import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {
  aggregateJquantsMinutesToFiveMinuteBars,
  normalizeJquantsMinuteRows,
  partitionJquantsMinuteRowsForFiveMinuteBars,
} from './lib/phase57-selector-jquants-minute.mjs';

const CONTRACT='BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES';
const SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false});
export const PILOT_DATES=Object.freeze(['2025-01-16','2025-01-17']);
export const PILOT_CODES=Object.freeze(['72030','86970']);
export const PILOT_QUERIES=Object.freeze(PILOT_DATES.flatMap(date=>PILOT_CODES.map(code=>Object.freeze({date,code}))));

async function boundedJson(response){
  if(response.status!==200)throw new Error(response.status===401?'AUTH_REJECTED':response.status===403?'BLOCKED_ENTITLEMENT':response.status===429?'RATE_LIMITED':`HTTP_${response.status}`);
  const text=await response.text();if(Buffer.byteLength(text)>2_000_000)throw new Error('RESPONSE_TOO_LARGE');return JSON.parse(text);
}

async function fetchQuery({apiKey,query,fetchImpl,pace,report}){
  const rows=[];const keys=new Set();let paginationKey='';let complete=false;
  for(let page=0;page<10;page+=1){
    if(report.requestCount)await pace();
    const url=new URL('https://api.jquants.com/v2/equities/bars/minute');
    url.searchParams.set('date',query.date);url.searchParams.set('code',query.code);
    if(paginationKey)url.searchParams.set('pagination_key',paginationKey);
    report.requestCount+=1;
    const response=await fetchImpl(url,{headers:{Accept:'application/json','x-api-key':apiKey},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(60_000)});
    const payload=await boundedJson(response);if(!Array.isArray(payload?.data))throw new Error('INVALID_SCHEMA');rows.push(...payload.data);
    const next=String(payload.pagination_key??payload.paginationKey??'');
    if(!next){complete=true;break;}if(keys.has(next)||page===9)throw new Error('INVALID_PAGINATION');keys.add(next);paginationKey=next;
  }
  if(!complete||!rows.length)throw new Error('EMPTY_OR_INCOMPLETE');return rows;
}

function verifyBars(bars){
  for(const bar of bars){
    const timestamp=Date.parse(bar.timestamp),availableAt=Date.parse(bar.availableAt);
    if(!Number.isFinite(timestamp)||availableAt!==timestamp+5*60_000)return false;
    const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(timestamp));
    const [hour,minute]=parts.split(':').map(Number),total=hour*60+minute;
    if(minute%5!==0||!((total>=540&&total<690)||(total>=750&&total<930)))return false;
    if(!Number.isFinite(bar.volume)||bar.volume<=0||!Number.isFinite(bar.turnover)||bar.turnover<=0)return false;
    if(bar.observedMinuteCount<1||bar.observedMinuteCount>5||bar.missingNoTradeMinuteCount!==5-bar.observedMinuteCount||bar.fabricatedMinuteCount!==0)return false;
  }
  return true;
}

export function inspectReconstructionRows(rawRows,query){
  const normalized=normalizeJquantsMinuteRows(rawRows);
  if(normalized.some(row=>row.date!==query.date||row.code!==query.code))throw new Error('QUERY_MISMATCH');
  const partition=partitionJquantsMinuteRowsForFiveMinuteBars(rawRows);
  const first=aggregateJquantsMinutesToFiveMinuteBars(rawRows,{sourceMinuteTimestampMeaning:CONTRACT});
  const second=aggregateJquantsMinutesToFiveMinuteBars(rawRows,{sourceMinuteTimestampMeaning:CONTRACT});
  const terminalCounts=Object.fromEntries(['11:30','15:30'].map(label=>[label,
    partition.terminalAuctionRows.filter(row=>row.time===label).length]));
  const inputAccounting=first.reduce((sum,bar)=>sum+bar.observedMinuteCount,0)===partition.regularRows.length;
  const passed=first.length>0&&JSON.stringify(first)===JSON.stringify(second)&&verifyBars(first)&&inputAccounting
    &&terminalCounts['11:30']===1&&terminalCounts['15:30']===1;
  return Object.freeze({...query,status:passed?'PASS':'FAIL',sourceMinuteRows:normalized.length,
    regularContinuousMinuteRows:partition.regularRows.length,terminalAuctionMinuteRows:partition.terminalAuctionRows.length,
    terminalCounts,fiveMinuteBars:first.length,sameInputDeterministic:JSON.stringify(first)===JSON.stringify(second),
    causalAvailability:true,noFabricatedMinutes:first.every(bar=>bar.fabricatedMinuteCount===0),
    terminalAuctionsExcludedFromRegular5m:inputAccounting,passed});
}

export async function runMinuteReconstructionPilot({apiKey,fetchImpl=globalThis.fetch,
  pace=()=>new Promise(resolve=>setTimeout(resolve,1100))}={}){
  const key=String(apiKey??'').trim();
  const report={schemaVersion:1,phase:'57.jquants-minute-reconstruction-pilot',status:key?'NOT_RUN':'AUTH_REQUIRED',
    evidenceClass:'SOURCE_VALIDATION_ONLY',quarantinedSessions:[...PILOT_DATES],queries:PILOT_QUERIES,
    timestampContract:CONTRACT,aggregationPolicy:'REGULAR_CONTINUOUS_MINUTES_ONLY_TERMINAL_AUCTIONS_CLASSIFIED_SEPARATELY',
    requestCount:0,groups:[],rawPersisted:false,secretPersisted:false,responseBodiesPersisted:false,
    minutePriceBasis:'RAW_EXECUTION_PRICE_MATCHED_TICK_WITHIN_PRIOR_RECONCILIATION',
    volumeSemantics:'SUM_EXECUTION_VOLUME',turnoverSemantics:'SUM_PRICE_TIMES_EXECUTION_VOLUME',
    actualProviderPublication:'DAILY_AROUND_16_30_JST',sourceValidationPass:false,
    formalAcquisitionStarted:false,developmentReleased:false,validationReleased:false,untouchedOosReleased:false,safety:SAFETY};
  if(!key)return report;
  try{
    for(const query of PILOT_QUERIES){
      const rows=await fetchQuery({apiKey:key,query,fetchImpl,pace,report});
      report.groups.push(inspectReconstructionRows(rows,query));
    }
    report.sourceValidationPass=report.groups.length===PILOT_QUERIES.length&&report.groups.every(group=>group.passed);
    report.status=report.sourceValidationPass?'SOURCE_VALIDATION_ONLY_PASS':'SOURCE_VALIDATION_ONLY_FAIL';
  }catch(error){
    const safe=new Set(['AUTH_REJECTED','BLOCKED_ENTITLEMENT','RATE_LIMITED','RESPONSE_TOO_LARGE','INVALID_SCHEMA','INVALID_PAGINATION','EMPTY_OR_INCOMPLETE','QUERY_MISMATCH']);
    report.status=safe.has(error.message)?error.message:'PILOT_TRANSPORT_OR_DATA_ERROR';
  }
  return report;
}

async function main(){
  const report=await runMinuteReconstructionPilot({apiKey:process.env.JQUANTS_API_KEY});
  const content=JSON.stringify(report,null,2)+'\n';const directory='artifacts/phase57-jquants-minute-reconstruction';
  fs.mkdirSync(directory,{recursive:true,mode:0o700});fs.writeFileSync(`${directory}/report.json`,content,{mode:0o600});
  fs.writeFileSync(`${directory}/report.sha256`,`${createHash('sha256').update(content).digest('hex')}  report.json\n`,{mode:0o600});
  console.log('JQUANTS_MINUTE_RECONSTRUCTION_REPORT '+JSON.stringify(report));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(()=>{
  console.error('JQUANTS_MINUTE_RECONSTRUCTION_INTERNAL_ERROR');process.exitCode=1;
});
