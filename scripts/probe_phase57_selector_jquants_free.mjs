import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const API_BASE='https://api.jquants.com/v2/';
const PILOT_QUERIES=Object.freeze([
  Object.freeze({code:'72030',date:'2025-01-06'}),
  Object.freeze({code:'72030',date:'2025-01-07'}),
  Object.freeze({code:'67580',date:'2025-01-06'}),
  Object.freeze({code:'67580',date:'2025-01-07'}),
]);
const SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

function outputArg(argv){const index=argv.indexOf('--output');return index>=0?argv[index+1]:null;}
function entitlementOnlyArg(argv){return argv.includes('--entitlement-only');}
function finite(value){return value!==null&&value!==''&&Number.isFinite(Number(value));}

async function requestJson({apiKey,endpoint,query={},fetchImpl}){
  const url=new URL(endpoint,API_BASE);
  for(const [key,value] of Object.entries(query))url.searchParams.set(key,value);
  let response;
  try{
    response=await fetchImpl(url,{cache:'no-store',headers:{Accept:'application/json','x-api-key':apiKey}});
  }catch(error){
    return {endpoint:`/v2/${endpoint}`,httpStatus:null,transportStatus:'NETWORK_ERROR',data:null};
  }
  let payload=null;
  try{payload=await response.json();}catch{}
  return {
    endpoint:`/v2/${endpoint}`,
    httpStatus:response.status,
    transportStatus:response.ok?'HTTP_OK':'HTTP_ERROR',
    data:Array.isArray(payload?.data)?payload.data:null,
    paginationPresent:Boolean(payload?.pagination_key??payload?.paginationKey),
  };
}

function inspectMinuteRows(rows){
  const observations={rowCount:rows.length,fieldContractPass:true,ohlcOrderPass:true,nonNegativeVolumeTurnoverPass:true};
  for(const row of rows){
    if(!['Date','Time','Code','O','H','L','C','Vo','Va'].every(key=>key in row))observations.fieldContractPass=false;
    if(!['O','H','L','C','Vo','Va'].every(key=>finite(row[key])))observations.fieldContractPass=false;
    if(finite(row.H)&&finite(row.L)&&finite(row.O)&&finite(row.C)&&
      (Number(row.H)<Math.max(Number(row.O),Number(row.C),Number(row.L))||Number(row.L)>Math.min(Number(row.O),Number(row.C),Number(row.H))))observations.ohlcOrderPass=false;
    if((finite(row.Vo)&&Number(row.Vo)<0)||(finite(row.Va)&&Number(row.Va)<0))observations.nonNegativeVolumeTurnoverPass=false;
  }
  return observations;
}

export async function probeJquantsFree({apiKey,fetchImpl=globalThis.fetch,entitlementOnly=false}={}){
  const key=String(apiKey??'').trim();
  if(!key)throw new Error('JQUANTS_API_KEY_MISSING');
  if(typeof fetchImpl!=='function')throw new TypeError('fetch is required');
  const report={
    schemaVersion:1,phase:'57.selector-minimal-hybrid.jquants-free-entitlement-pilot',
    evidenceClass:'SOURCE_VALIDATION_ONLY',secretValueObserved:false,secretPersisted:false,
    authentication:{status:'NOT_RUN',endpoint:'/v2/equities/master',httpStatus:null},
    minuteEntitlement:{status:'NOT_RUN',endpoint:'/v2/equities/bars/minute',httpStatus:null},
    freeFallback:{status:'NOT_RUN',endpoint:'/v2/equities/bars/daily',httpStatus:null,interval:'1d',canConstructFiveMinute:false},
    pilot:{status:'NOT_RUN',symbols:[],sessions:[],requestCount:0,rowCount:0,payloadPersisted:false},
    historicalDepth:{requiredSessions:120,status:'NOT_PROVEN'},
    fiveMinutePath:{status:'NOT_AVAILABLE',oneMinuteRequired:false},
    admission:{status:'DATASET_NOT_READY',developmentReleased:false,validationReleased:false,untouchedOosReleased:false},
    safety:SAFETY,
  };

  const auth=await requestJson({apiKey:key,endpoint:'equities/master',query:{code:'86970'},fetchImpl});
  report.authentication.httpStatus=auth.httpStatus;
  report.authentication.status=auth.httpStatus===200&&auth.data?'AUTHENTICATED':'AUTH_FAILED';
  report.authentication.responseBodyPersisted=false;
  if(report.authentication.status!=='AUTHENTICATED')return report;

  const first=PILOT_QUERIES[0];
  const minute=await requestJson({apiKey:key,endpoint:'equities/bars/minute',query:first,fetchImpl});
  report.minuteEntitlement.httpStatus=minute.httpStatus;
  report.minuteEntitlement.responseBodyPersisted=false;
  if(minute.httpStatus!==200||!minute.data){
    report.minuteEntitlement.status=minute.httpStatus===401?'AUTH_REJECTED':minute.httpStatus===403?'BLOCKED_ENTITLEMENT':'ENDPOINT_UNAVAILABLE_OR_ERROR';
    report.fiveMinutePath.status='FREE_PLAN_CANNOT_CONSTRUCT_INTRADAY_5M';
    const daily=await requestJson({apiKey:key,endpoint:'equities/bars/daily',query:{code:'72030',date:'2025-01-06'},fetchImpl});
    report.freeFallback.httpStatus=daily.httpStatus;
    report.freeFallback.status=daily.httpStatus===200&&daily.data?.length>0?'HISTORICAL_DAILY_AVAILABLE_BUT_NOT_INTRADAY':'HISTORICAL_DAILY_NOT_PROVEN';
    report.freeFallback.rowCount=daily.data?.length??0;
    report.freeFallback.responseBodyPersisted=false;
    report.admission.status=report.minuteEntitlement.status==='BLOCKED_ENTITLEMENT'?'BLOCKED_ENTITLEMENT':'DATASET_NOT_READY';
    return report;
  }

  report.minuteEntitlement.status='AVAILABLE';
  if(entitlementOnly){
    report.pilot.status='NOT_RUN_ENTITLEMENT_ONLY';
    report.fiveMinutePath.status='MINUTE_ENDPOINT_AVAILABLE_PILOT_NOT_STARTED';
    report.admission.status='DATASET_NOT_READY_AWAITING_SOURCE_VALIDATION_PILOT';
    return report;
  }
  const responses=[minute];
  for(const query of PILOT_QUERIES.slice(1))responses.push(await requestJson({apiKey:key,endpoint:'equities/bars/minute',query,fetchImpl}));
  report.pilot.requestCount=responses.length;
  report.pilot.symbols=[...new Set(PILOT_QUERIES.map(value=>value.code))];
  report.pilot.sessions=[...new Set(PILOT_QUERIES.map(value=>value.date))];
  const successful=responses.filter(value=>value.httpStatus===200&&value.data);
  const observations=successful.map(value=>inspectMinuteRows(value.data));
  report.pilot.rowCount=observations.reduce((sum,value)=>sum+value.rowCount,0);
  report.pilot.paginationObserved=responses.some(value=>value.paginationPresent);
  report.pilot.timestampTimezoneStatus='JST_TIME_FIELDS_OBSERVED_CONTRACT_EDGE_MEANING_REQUIRES_CONFIRMATION';
  report.pilot.noTradeSemantics='ABSENT_MINUTES_REMAIN_MISSING_NEVER_ZERO_OR_FABRICATED';
  report.pilot.corporateActionSemantics='NOT_PROVEN_BY_TWO_SESSION_PILOT';
  report.pilot.fieldContractPass=observations.every(value=>value.fieldContractPass);
  report.pilot.ohlcOrderPass=observations.every(value=>value.ohlcOrderPass);
  report.pilot.nonNegativeVolumeTurnoverPass=observations.every(value=>value.nonNegativeVolumeTurnoverPass);
  report.pilot.status=successful.length===responses.length&&report.pilot.rowCount>0&&report.pilot.fieldContractPass&&report.pilot.ohlcOrderPass&&report.pilot.nonNegativeVolumeTurnoverPass?'PILOT_DATA_OBSERVED_SEMANTICS_NOT_FULLY_PROVEN':'PILOT_FAILED';
  report.historicalDepth.status=report.pilot.rowCount>0?'OLDEST_PILOT_DATE_AVAILABLE_120_SESSION_FULL_COVERAGE_NOT_YET_AUDITED':'NOT_PROVEN';
  report.fiveMinutePath.status=report.pilot.rowCount>0?'CAUSAL_ONE_MINUTE_TO_FIVE_MINUTE_AGGREGATION_TECHNICALLY_AVAILABLE':'NOT_AVAILABLE';
  return report;
}

async function main(){
  const report=await probeJquantsFree({apiKey:process.env.JQUANTS_API_KEY,entitlementOnly:entitlementOnlyArg(process.argv)});
  const output=outputArg(process.argv);
  if(output){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{mode:0o600});}
  console.log(JSON.stringify(report));
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]))main().catch(error=>{
  const code=error?.message==='JQUANTS_API_KEY_MISSING'?'JQUANTS_API_KEY_MISSING':'PROBE_INTERNAL_ERROR';
  console.error(JSON.stringify({status:code,secretValueObserved:false,secretPersisted:false}));
  process.exitCode=1;
});

export const Phase57JquantsFreeProbeInternals=Object.freeze({PILOT_QUERIES,SAFETY});
