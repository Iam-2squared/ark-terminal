import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

// Fixed source-only dates; never replace these with Development, Validation or OOS.
export const EDGE_QUERIES=Object.freeze(['2025-01-08','2025-01-09'].flatMap(date=>
  ['72030','86970'].map(code=>Object.freeze({date,code}))));
const EDGE_TIMES=['09:00','09:01','11:29','11:30','12:30','12:31','15:24','15:25','15:29','15:30'];
const SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false});
const isNumber=value=>typeof value==='number'&&Number.isFinite(value);

export function minuteBoundaryMembership(time){
  if(!/^\d{2}:\d{2}$/.test(String(time)))return {barStart:false,barEnd:false,auctionBoundary:false};
  const [h,m]=time.split(':').map(Number);
  if(h>23||m>59)return {barStart:false,barEnd:false,auctionBoundary:false};
  const t=h*60+m;
  return {
    barStart:(t>=540&&t<690)||(t>=750&&t<930),
    barEnd:(t>540&&t<=690)||(t>750&&t<=930),
    auctionBoundary:t===690||t===930,
  };
}

export function inspectEdgeRows(rows,query){
  const report={...query,rowCount:rows.length,queryMismatchCount:0,invalidTimestampCount:0,
    invalidOhlcCount:0,invalidVolumeTurnoverCount:0,duplicateCount:0,conflictingDuplicateCount:0,
    interiorLunchRows:0,barStartIncompatibleRows:0,barEndIncompatibleRows:0,
    edges:Object.fromEntries(EDGE_TIMES.map(t=>[t,{count:0,nonFlatCount:0,positiveVolumeCount:0}])),
    haltVsNoTrade:'UNKNOWN_NO_CAUSE_FIELD',timezoneProof:'UNKNOWN_TIME_FIELD_HAS_NO_OFFSET',
    corporateActionBasis:'UNKNOWN_NOT_ESTABLISHED_BY_FIELD_NAMES',
    sourceTimestampRetainedInMemory:true,sourceTimestampShiftApplied:false};
  const seen=new Map();
  for(const row of rows){
    if(row?.Date!==query.date||row?.Code!==query.code)report.queryMismatchCount++;
    const validTime=typeof row?.Time==='string'&&/^([01]\d|2[0-3]):[0-5]\d$/.test(row.Time);
    if(!validTime)report.invalidTimestampCount++;
    const numbers=['O','H','L','C'].every(k=>isNumber(row?.[k])&&row[k]>0);
    const ohlc=numbers&&row.H>=Math.max(row.O,row.C,row.L)&&row.L<=Math.min(row.O,row.C,row.H);
    if(!ohlc)report.invalidOhlcCount++;
    if(!['Vo','Va'].every(k=>isNumber(row?.[k])&&row[k]>=0))report.invalidVolumeTurnoverCount++;
    const key=JSON.stringify([row?.Date,row?.Code,row?.Time]);
    const value=JSON.stringify(['O','H','L','C','Vo','Va'].map(k=>row?.[k]));
    if(seen.has(key)){
      report.duplicateCount++;
      if(seen.get(key)!==value)report.conflictingDuplicateCount++;
    }else seen.set(key,value);
    const boundary=minuteBoundaryMembership(row?.Time);
    if(!boundary.barStart)report.barStartIncompatibleRows++;
    if(!boundary.barEnd)report.barEndIncompatibleRows++;
    if(validTime&&row.Time>'11:30'&&row.Time<'12:30')report.interiorLunchRows++;
    const edge=report.edges[row?.Time];
    if(edge){
      edge.count++;
      if(ohlc&&row.H!==row.L)edge.nonFlatCount++;
      if(isNumber(row?.Vo)&&row.Vo>0)edge.positiveVolumeCount++;
    }
  }
  // Boundary observations may falsify a hypothesis, but must not certify one.
  report.uniformBarEndFalsified=report.edges['09:00'].nonFlatCount>0||report.edges['12:30'].nonFlatCount>0;
  report.strictBarStartSessionRangeFalsified=report.edges['11:30'].count>0||report.edges['15:30'].count>0;
  report.hypothesis=report.uniformBarEndFalsified&&report.strictBarStartSessionRangeFalsified
    ?'BAR_START_WITH_TERMINAL_AUCTION_CANDIDATE_NOT_CONFIRMED':'UNKNOWN';
  return report;
}

async function readBoundedJson(response){
  const limit=2_000_000;
  if(Number(response.headers?.get('content-length'))>limit)throw new Error('RESPONSE_SIZE_LIMIT');
  if(!response.body?.getReader)return response.json(); // Unit-test transport only.
  const reader=response.body.getReader();const chunks=[];let size=0;
  try{
    for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;
      if(size>limit)throw new Error('RESPONSE_SIZE_LIMIT');chunks.push(value);}
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  }finally{await reader.cancel().catch(()=>{});}
}

export async function runJquantsEdgeProbe({apiKey,fetchImpl=globalThis.fetch,
  pace=()=>new Promise(resolve=>setTimeout(resolve,1250))}={}){
  const key=String(apiKey??'').trim();
  const report={schemaVersion:1,phase:'57.jquants-timestamp-edge-probe',
    status:key?'BLOCKED_TIMESTAMP_CONTRACT_UNRESOLVED':'AUTH_REQUIRED',
    evidenceClass:'SOURCE_VALIDATION_ONLY',quarantinedSessions:['2025-01-06','2025-01-07','2025-01-08','2025-01-09'],
    requests:[],groups:[],requestCount:0,maximumRequests:8,
    rawPersisted:false,secretPersisted:false,responseErrorsPersisted:false,
    aggregationPerformed:false,featuresCalculated:false,labelsGenerated:false,
    sourceValidationPass:false,formalAcquisitionStarted:false,developmentReleased:false,
    validationReleased:false,untouchedOosReleased:false,providerAvailableAt:'UNKNOWN_EXACT_PUBLICATION_TIME',
    documentedProviderUpdate:'DAILY_AROUND_16_30_JST_NOT_INTRADAY',
    marketBarCloseIsProviderAvailableAt:false,safety:SAFETY};
  if(!key)return report;
  for(const query of EDGE_QUERIES){
    const rows=[];const seenPages=new Set();let next=null;let complete=false;
    for(let page=0;page<2;page++){
      if(report.requestCount>0)await pace();
      const url=new URL('https://api.jquants.com/v2/equities/bars/minute');
      for(const [k,v] of Object.entries(query))url.searchParams.set(k,v);
      if(next)url.searchParams.set('pagination_key',next);
      const request={...query,page:page+1,httpStatus:null,status:'NOT_SENT'};
      report.requests.push(request);report.requestCount++;
      let payload;
      try{
        const response=await fetchImpl(url,{headers:{Accept:'application/json','x-api-key':key},
          redirect:'error',signal:AbortSignal.timeout(30_000),cache:'no-store'});
        request.httpStatus=response.status;
        if(response.status!==200){
          request.status=response.status===401?'AUTH_REJECTED':response.status===403?'BLOCKED_ENTITLEMENT':
            response.status===429?'RATE_LIMITED':'HTTP_ERROR';
          report.status=request.status;return report;
        }
        payload=await readBoundedJson(response);
      }catch{request.status='TRANSPORT_OR_PAYLOAD_ERROR';report.status=request.status;return report;}
      if(!Array.isArray(payload?.data)){request.status='INVALID_SCHEMA';report.status=request.status;return report;}
      request.status=payload.data.length?'NON_EMPTY':'EMPTY';request.rowCount=payload.data.length;
      rows.push(...payload.data);
      next=payload.pagination_key??payload.paginationKey??null;
      if(next===null||next===''){complete=true;break;}
      if(typeof next!=='string'||seenPages.has(next)){request.status='INVALID_PAGINATION';break;}
      seenPages.add(next);
    }
    const group=inspectEdgeRows(rows,query);group.paginationComplete=complete;
    report.groups.push(group);
    const invalid=['queryMismatchCount','invalidTimestampCount','invalidOhlcCount',
      'invalidVolumeTurnoverCount','duplicateCount','conflictingDuplicateCount','interiorLunchRows']
      .some(field=>group[field]>0);
    if(!complete||rows.length===0||invalid){report.status='PILOT_FAILED_DATA_INTEGRITY';return report;}
  }
  return report;
}

async function main(){
  const report=await runJquantsEdgeProbe({apiKey:process.env.JQUANTS_API_KEY});
  const content=JSON.stringify(report,null,2)+'\n';
  const directory='artifacts/phase57-jquants-edge';
  fs.mkdirSync(directory,{recursive:true});
  fs.writeFileSync(`${directory}/report.json`,content,{mode:0o600});
  fs.writeFileSync(`${directory}/report.sha256`,`${createHash('sha256').update(content).digest('hex')}  report.json\n`,{mode:0o600});
  console.log('JQUANTS_EDGE_REPORT '+JSON.stringify(report));
  // Success here means the audit completed; sourceValidationPass remains false.
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(()=>{
  console.error('JQUANTS_EDGE_AUDIT_INTERNAL_ERROR');process.exitCode=1;
});
