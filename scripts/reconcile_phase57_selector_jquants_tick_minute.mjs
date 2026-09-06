import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import {createHash} from 'node:crypto';
import {Readable} from 'node:stream';
import {createGunzip} from 'node:zlib';
import {fileURLToPath} from 'node:url';

const API_BASE='https://api.jquants.com/';
const TICK_ENDPOINT='/equities/trades';
const SCALE=1_000_000n;
const MAX_API_JSON_BYTES=2_000_000;
const MAX_TOTAL_COMPRESSED_BYTES=2_000_000_000;
const MAX_TICK_ROWS_FOR_TARGETS=2_000_000;
const REQUIRED_BOUNDARIES=Object.freeze(['09:00','11:30','12:30','15:30']);
const SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false});

// Permanently SOURCE_VALIDATION_ONLY. These dates are registered before any request.
export const RECONCILIATION_DATES=Object.freeze(['2025-01-14','2025-01-15']);
export const RECONCILIATION_CODES=Object.freeze(['72030','86970']);
export const RECONCILIATION_QUERIES=Object.freeze(RECONCILIATION_DATES.flatMap(date=>
  RECONCILIATION_CODES.map(code=>Object.freeze({date,code}))));

function sha256(value){return createHash('sha256').update(value).digest('hex');}
function requireKey(value){const key=String(value??'').trim();if(!key)throw new Error('AUTH_REQUIRED');return key;}
function pad2(value){return String(value).padStart(2,'0');}
function labelOf(totalMinutes){return `${pad2(Math.floor(totalMinutes/60))}:${pad2(totalMinutes%60)}`;}

function scaled6(value,label){
  const text=String(value??'').trim();
  const match=/^(\d+)(?:\.(\d{1,6}))?$/.exec(text);
  if(!match)throw new Error(`INVALID_${label}`);
  return BigInt(match[1])*SCALE+BigInt((match[2]??'').padEnd(6,'0'));
}

function positiveInteger(value,label){
  const text=String(value??'').trim();
  if(!/^\d+$/.test(text)||BigInt(text)<=0n)throw new Error(`INVALID_${label}`);
  return BigInt(text);
}

export function parseTickTime(value){
  const match=/^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)\.(\d{6})$/.exec(String(value??''));
  if(!match)throw new Error('INVALID_TICK_TIME');
  const hour=Number(match[1]),minute=Number(match[2]),second=Number(match[3]),micro=Number(match[4]);
  return Object.freeze({hour,minute,second,micro,totalMinute:hour*60+minute,
    microsWithinMinute:(second*1_000_000)+micro});
}

function parseCsvLine(line){
  const fields=[];let value='';let quoted=false;
  for(let index=0;index<line.length;index+=1){
    const char=line[index];
    if(char==='"'){
      if(quoted&&line[index+1]==='"'){value+='"';index+=1;}else quoted=!quoted;
    }else if(char===','&&!quoted){fields.push(value);value='';}else value+=char;
  }
  if(quoted)throw new Error('UNTERMINATED_CSV_QUOTE');
  fields.push(value);return fields;
}

function expectedSession(label){return label<='11:30'?'01':label>='12:30'?'02':null;}
function candidateLabels(tickTime){
  const start=tickTime.totalMinute;
  return Object.freeze({
    START_HALF_OPEN:labelOf(start),
    END_HALF_OPEN:labelOf(start+1),
    END_LEFT_OPEN_RIGHT_CLOSED:labelOf(tickTime.microsWithinMinute===0?start:start+1),
  });
}

function addTick(map,key,tick){
  let bin=map.get(key);
  if(!bin){bin={count:0,open:null,high:null,low:null,close:null,volume:0n,turnover:0n,
    firstKey:null,lastKey:null,sessions:new Set()};map.set(key,bin);}
  const orderKey=`${tick.time}|${tick.transactionId}`;
  bin.count+=1;bin.volume+=tick.volume;bin.turnover+=tick.price*tick.volume;
  bin.high=bin.high===null||tick.price>bin.high?tick.price:bin.high;
  bin.low=bin.low===null||tick.price<bin.low?tick.price:bin.low;
  if(bin.firstKey===null||orderKey<bin.firstKey){bin.firstKey=orderKey;bin.open=tick.price;}
  if(bin.lastKey===null||orderKey>bin.lastKey){bin.lastKey=orderKey;bin.close=tick.price;}
  bin.sessions.add(tick.session);
}

function minuteKey(date,code,label){return `${date}|${code}|${label}`;}
function minuteValue(raw){
  const date=String(raw?.Date??''),code=String(raw?.Code??''),label=String(raw?.Time??'');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!/^\d{5}$/.test(code)||!/^\d{2}:\d{2}$/.test(label))throw new Error('INVALID_MINUTE_ID');
  return Object.freeze({date,code,label,open:scaled6(raw.O,'MINUTE_O'),high:scaled6(raw.H,'MINUTE_H'),
    low:scaled6(raw.L,'MINUTE_L'),close:scaled6(raw.C,'MINUTE_C'),volume:positiveInteger(raw.Vo,'MINUTE_VOLUME'),
    turnover:scaled6(raw.Va,'MINUTE_TURNOVER')});
}

function exactMatch(minute,bin){
  return Boolean(bin&&bin.count>0&&bin.sessions.size===1&&bin.sessions.has(expectedSession(minute.label))
    &&minute.open===bin.open&&minute.high===bin.high&&minute.low===bin.low&&minute.close===bin.close
    &&minute.volume===bin.volume&&minute.turnover===bin.turnover);
}

export function reconcileTickMinute({ticks,minuteRows,queries=RECONCILIATION_QUERIES}={}){
  if(!Array.isArray(ticks)||!Array.isArray(minuteRows))throw new TypeError('ticks and minuteRows are required');
  const querySet=new Set(queries.map(q=>`${q.date}|${q.code}`));
  const maps={START_HALF_OPEN:new Map(),END_HALF_OPEN:new Map(),END_LEFT_OPEN_RIGHT_CLOSED:new Map()};
  const transactionIds=new Set();let duplicateTransactionIds=0,invalidTargetTicks=0;
  for(const raw of ticks){
    const date=String(raw?.Date??''),code=String(raw?.Code??'');
    if(!querySet.has(`${date}|${code}`))continue;
    try{
      const time=parseTickTime(raw.Time),session=String(raw.SessionDistinction??'');
      if(!['01','02'].includes(session))throw new Error('INVALID_SESSION');
      const transactionId=String(raw.TransactionId??'');
      if(!transactionId)throw new Error('INVALID_TRANSACTION_ID');
      const unique=`${date}|${code}|${transactionId}`;
      if(transactionIds.has(unique)){duplicateTransactionIds+=1;continue;}
      transactionIds.add(unique);
      const tick={date,code,time:String(raw.Time),session,transactionId,
        price:scaled6(raw.Price,'TICK_PRICE'),volume:positiveInteger(raw.TradingVolume,'TICK_VOLUME')};
      for(const [candidate,label] of Object.entries(candidateLabels(time))){
        addTick(maps[candidate],minuteKey(date,code,label),tick);
      }
    }catch{invalidTargetTicks+=1;}
  }
  const minutes=new Map();let invalidMinuteRows=0,duplicateMinuteRows=0;
  for(const raw of minuteRows){
    try{
      const minute=minuteValue(raw);if(!querySet.has(`${minute.date}|${minute.code}`))throw new Error('QUERY_MISMATCH');
      const key=minuteKey(minute.date,minute.code,minute.label);
      if(minutes.has(key)){duplicateMinuteRows+=1;continue;}minutes.set(key,minute);
    }catch{invalidMinuteRows+=1;}
  }
  const comparisons={};
  for(const candidate of Object.keys(maps))comparisons[candidate]={exactMatchCount:0,totalMinuteRows:minutes.size,orphanTickBinCount:0};
  for(const [key,minute] of minutes){
    for(const candidate of Object.keys(maps))if(exactMatch(minute,maps[candidate].get(key)))comparisons[candidate].exactMatchCount+=1;
  }
  for(const candidate of Object.keys(maps)){
    for(const key of maps[candidate].keys())if(!minutes.has(key))comparisons[candidate].orphanTickBinCount+=1;
  }
  const boundaries=[];
  for(const query of queries){for(const label of REQUIRED_BOUNDARIES){
    const key=minuteKey(query.date,query.code,label),minute=minutes.get(key);
    boundaries.push({date:query.date,code:query.code,label,minuteRowPresent:Boolean(minute),
      matches:Object.fromEntries(Object.keys(maps).map(candidate=>[candidate,Boolean(minute&&exactMatch(minute,maps[candidate].get(key)))]))});
  }}
  const start=comparisons.START_HALF_OPEN;
  const startComplete=minutes.size>0&&start.exactMatchCount===minutes.size&&start.orphanTickBinCount===0;
  const boundariesComplete=boundaries.every(row=>row.minuteRowPresent&&row.matches.START_HALF_OPEN);
  const alternativesNotEquivalent=['END_HALF_OPEN','END_LEFT_OPEN_RIGHT_CLOSED'].every(candidate=>
    comparisons[candidate].exactMatchCount<minutes.size||comparisons[candidate].orphanTickBinCount>0);
  const contractConfirmed=startComplete&&boundariesComplete&&alternativesNotEquivalent
    &&invalidTargetTicks===0&&duplicateTransactionIds===0&&invalidMinuteRows===0&&duplicateMinuteRows===0;
  return Object.freeze({contractConfirmed,
    contract:contractConfirmed?'BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES':'TIMESTAMP_CONTRACT_STILL_UNRESOLVED',
    targetTickCount:transactionIds.size,minuteRowCount:minutes.size,invalidTargetTicks,duplicateTransactionIds,
    invalidMinuteRows,duplicateMinuteRows,comparisons,boundaries});
}

async function boundedJson(response){
  const declared=Number(response.headers?.get('content-length')??0);
  if(declared>MAX_API_JSON_BYTES)throw new Error('API_JSON_TOO_LARGE');
  const text=await response.text();if(Buffer.byteLength(text)>MAX_API_JSON_BYTES)throw new Error('API_JSON_TOO_LARGE');
  return JSON.parse(text);
}

async function apiJson({apiKey,pathName,params,fetchImpl,report}){
  const url=new URL(pathName,API_BASE);for(const [key,value] of Object.entries(params))url.searchParams.set(key,String(value));
  report.apiRequestCount+=1;
  const response=await fetchImpl(url,{headers:{Accept:'application/json','x-api-key':apiKey},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(60_000)});
  if(response.status!==200)throw new Error(response.status===401?'AUTH_REJECTED':response.status===403?'BLOCKED_ENTITLEMENT':response.status===429?'RATE_LIMITED':`HTTP_${response.status}`);
  return boundedJson(response);
}

async function tickFiles({apiKey,fetchImpl,report,pace}){
  const files=new Map();
  for(const date of RECONCILIATION_DATES){
    if(report.apiRequestCount)await pace();
    const payload=await apiJson({apiKey,pathName:'v2/bulk/list',params:{endpoint:TICK_ENDPOINT,from:date,to:date},fetchImpl,report});
    if(!Array.isArray(payload?.data)||payload.data.length===0)throw new Error('TICK_BULK_LIST_EMPTY');
    for(const item of payload.data){
      const key=String(item?.Key??''),size=Number(item?.Size);
      const lastModified=String(item?.LastModified??'');
      if(!key||!Number.isSafeInteger(size)||size<=0||!Number.isFinite(Date.parse(lastModified)))throw new Error('TICK_BULK_METADATA_INVALID');
      files.set(key,{key,size,lastModified});
    }
  }
  const list=[...files.values()];
  const total=list.reduce((sum,item)=>sum+item.size,0);
  report.tickFileMetadata=list.map(item=>({keySha256:sha256(item.key),compressedBytes:item.size,
    lastModifiedValid:Number.isFinite(Date.parse(item.lastModified))}));
  report.totalCompressedBytes=total;
  if(total>MAX_TOTAL_COMPRESSED_BYTES)throw new Error('TICK_BULK_DOWNLOAD_BUDGET_EXCEEDED');
  return list;
}

async function streamTickCsv(response,onTargetRow){
  if(response.status!==200||!response.body)throw new Error(`TICK_DOWNLOAD_HTTP_${response.status}`);
  const downloaded=Readable.fromWeb(response.body),iterator=downloaded[Symbol.asyncIterator]();
  const first=await iterator.next();
  const replay=Readable.from((async function*(){if(!first.done)yield first.value;for await(const chunk of iterator)yield chunk;})());
  const gzip=Boolean(first.value?.length>=2&&first.value[0]===0x1f&&first.value[1]===0x8b);
  const input=gzip?replay.pipe(createGunzip()):replay;
  const lines=readline.createInterface({input,crlfDelay:Infinity});
  let header=null,totalRows=0,targetRows=0;
  for await(const rawLine of lines){
    const line=rawLine.replace(/^\uFEFF/,'');if(!line)continue;
    const fields=parseCsvLine(line);
    if(!header){header=fields;continue;}
    if(fields.length!==header.length)throw new Error('TICK_CSV_COLUMN_COUNT_INVALID');
    totalRows+=1;const row=Object.fromEntries(header.map((name,index)=>[name,fields[index]]));
    if(RECONCILIATION_DATES.includes(row.Date)&&RECONCILIATION_CODES.includes(row.Code)){
      targetRows+=1;if(targetRows>MAX_TICK_ROWS_FOR_TARGETS)throw new Error('TARGET_TICK_ROW_LIMIT_EXCEEDED');onTargetRow(row);
    }
  }
  const required=['Date','Code','Time','SessionDistinction','Price','TradingVolume','TransactionId'];
  if(!header||required.some(name=>!header.includes(name)))throw new Error('TICK_CSV_SCHEMA_INVALID');
  return {totalRows,targetRows};
}

async function downloadTicks({apiKey,files,fetchImpl,report,pace}){
  const ticks=[];
  for(const file of files){
    await pace();const payload=await apiJson({apiKey,pathName:'v2/bulk/get',params:{key:file.key},fetchImpl,report});
    const signedUrl=String(payload?.url??'');if(!/^https:\/\//.test(signedUrl))throw new Error('SIGNED_DOWNLOAD_URL_INVALID');
    const response=await fetchImpl(signedUrl,{headers:{Accept:'application/gzip'},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(1_200_000)});
    report.downloadCount+=1;const counts=await streamTickCsv(response,row=>ticks.push(row));
    report.tickCsvRowsScanned+=counts.totalRows;report.targetTickRowsRead+=counts.targetRows;
  }
  return ticks;
}

async function minuteRows({apiKey,fetchImpl,report,pace}){
  const rows=[];
  for(const query of RECONCILIATION_QUERIES){let paginationKey='';const seen=new Set();
    for(let page=0;page<10;page+=1){
      await pace();const params={date:query.date,code:query.code};if(paginationKey)params.pagination_key=paginationKey;
      const payload=await apiJson({apiKey,pathName:'v2/equities/bars/minute',params,fetchImpl,report});
      if(!Array.isArray(payload?.data))throw new Error('MINUTE_SCHEMA_INVALID');rows.push(...payload.data);
      const next=String(payload.pagination_key??payload.paginationKey??'');if(!next)break;
      if(seen.has(next)||page===9)throw new Error('MINUTE_PAGINATION_INVALID');seen.add(next);paginationKey=next;
    }
  }
  return rows;
}

export async function runTickMinuteReconciliation({apiKey,fetchImpl=globalThis.fetch,
  pace=()=>new Promise(resolve=>setTimeout(resolve,1100))}={}){
  const report={schemaVersion:1,phase:'57.jquants-tick-minute-reconciliation',
    status:'NOT_RUN',evidenceClass:'SOURCE_VALIDATION_ONLY',quarantinedSessions:[...RECONCILIATION_DATES],
    queries:RECONCILIATION_QUERIES,apiRequestCount:0,downloadCount:0,tickFileMetadata:[],
    totalCompressedBytes:0,tickCsvRowsScanned:0,targetTickRowsRead:0,
    rawPersisted:false,signedUrlPersisted:false,secretPersisted:false,responseBodiesPersisted:false,
    reconciliation:null,adapterChanged:false,fiveMinuteAggregationPerformed:false,
    sourceValidationPass:false,formalAcquisitionStarted:false,developmentReleased:false,
    validationReleased:false,untouchedOosReleased:false,safety:SAFETY};
  let key;
  try{key=requireKey(apiKey);}catch(error){report.status=error.message;return report;}
  try{
    const files=await tickFiles({apiKey:key,fetchImpl,report,pace});
    const ticks=await downloadTicks({apiKey:key,files,fetchImpl,report,pace});
    const minutes=await minuteRows({apiKey:key,fetchImpl,report,pace});
    report.reconciliation=reconcileTickMinute({ticks,minuteRows:minutes});
    report.status=report.reconciliation.contractConfirmed?'TIMESTAMP_CONTRACT_CONFIRMED':'TIMESTAMP_CONTRACT_STILL_UNRESOLVED';
  }catch(error){
    const safe=new Set(['AUTH_REJECTED','BLOCKED_ENTITLEMENT','RATE_LIMITED','TICK_BULK_LIST_EMPTY',
      'TICK_BULK_METADATA_INVALID','TICK_BULK_DOWNLOAD_BUDGET_EXCEEDED','SIGNED_DOWNLOAD_URL_INVALID',
      'TICK_CSV_COLUMN_COUNT_INVALID','TICK_CSV_SCHEMA_INVALID','TARGET_TICK_ROW_LIMIT_EXCEEDED',
      'MINUTE_SCHEMA_INVALID','MINUTE_PAGINATION_INVALID','API_JSON_TOO_LARGE']);
    report.status=safe.has(error.message)?error.message:'RECONCILIATION_TRANSPORT_OR_DATA_ERROR';
  }
  return report;
}

async function main(){
  const report=await runTickMinuteReconciliation({apiKey:process.env.JQUANTS_API_KEY});
  const content=JSON.stringify(report,null,2)+'\n';const directory='artifacts/phase57-jquants-tick-minute';
  fs.mkdirSync(directory,{recursive:true,mode:0o700});
  fs.writeFileSync(`${directory}/report.json`,content,{mode:0o600});
  fs.writeFileSync(`${directory}/report.sha256`,`${sha256(content)}  report.json\n`,{mode:0o600});
  console.log('JQUANTS_TICK_MINUTE_REPORT '+JSON.stringify(report));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(()=>{
  console.error('JQUANTS_TICK_MINUTE_INTERNAL_ERROR');process.exitCode=1;
});

export const Phase57TickMinuteInternals=Object.freeze({candidateLabels,scaled6,MAX_TOTAL_COMPRESSED_BYTES,REQUIRED_BOUNDARIES});
