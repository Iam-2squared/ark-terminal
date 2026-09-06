import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const PROFILE_DATE='2025-01-17'; // already permanently SOURCE_VALIDATION_ONLY
const MAX_PAGES=2500;
const MAX_BYTES_PER_PAGE=25_000_000;
const SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false});

async function boundedPayload(response){
  if(response.status!==200)throw new Error(response.status===401?'AUTH_REJECTED':response.status===403?'BLOCKED_ENTITLEMENT':response.status===429?'RATE_LIMITED':`HTTP_${response.status}`);
  const body=await response.text();
  if(Buffer.byteLength(body)>MAX_BYTES_PER_PAGE)throw new Error('PAGE_TOO_LARGE');
  return {payload:JSON.parse(body),bytes:Buffer.byteLength(body)};
}

export async function profileDateWideCapacity({apiKey,fetchImpl=globalThis.fetch,
  pace=()=>new Promise(resolve=>setTimeout(resolve,1100))}={}){
  const key=String(apiKey??'').trim();
  const report={schemaVersion:1,phase:'57.jquants-date-wide-capacity-profile',status:key?'NOT_RUN':'AUTH_REQUIRED',
    evidenceClass:'SOURCE_VALIDATION_ONLY',quarantinedSession:PROFILE_DATE,pageCount:0,rowCount:0,
    responseBytes:0,maxRowsPerPage:0,uniqueSymbolCount:0,duplicateMinuteKeys:0,invalidRows:0,
    firstTime:null,lastTime:null,symbolSetSha256:null,paginationComplete:false,
    rawPersisted:false,secretPersisted:false,responseBodiesPersisted:false,
    developmentReleased:false,validationReleased:false,untouchedOosReleased:false,safety:SAFETY};
  if(!key)return report;
  const symbols=new Set(),minuteKeys=new Set(),paginationKeys=new Set();
  let paginationKey='';
  try{
    for(let page=0;page<MAX_PAGES;page+=1){
      if(page)await pace();
      const url=new URL('https://api.jquants.com/v2/equities/bars/minute');url.searchParams.set('date',PROFILE_DATE);
      if(paginationKey)url.searchParams.set('pagination_key',paginationKey);
      const response=await fetchImpl(url,{headers:{Accept:'application/json','x-api-key':key},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(60_000)});
      const {payload,bytes}=await boundedPayload(response);
      if(!Array.isArray(payload?.data))throw new Error('INVALID_SCHEMA');
      report.pageCount+=1;report.responseBytes+=bytes;report.rowCount+=payload.data.length;
      report.maxRowsPerPage=Math.max(report.maxRowsPerPage,payload.data.length);
      for(const row of payload.data){
        const date=String(row?.Date??''),code=String(row?.Code??''),time=String(row?.Time??'');
        if(date!==PROFILE_DATE||!/^\d{5}$/.test(code)||!/^\d{2}:\d{2}$/.test(time)
          ||!['O','H','L','C','Vo','Va'].every(name=>Number.isFinite(Number(row?.[name])))){report.invalidRows+=1;continue;}
        symbols.add(code);const minuteKey=`${code}|${time}`;
        if(minuteKeys.has(minuteKey))report.duplicateMinuteKeys+=1;else minuteKeys.add(minuteKey);
        report.firstTime=report.firstTime===null||time<report.firstTime?time:report.firstTime;
        report.lastTime=report.lastTime===null||time>report.lastTime?time:report.lastTime;
      }
      const next=String(payload.pagination_key??payload.paginationKey??'');
      if(!next){report.paginationComplete=true;break;}
      if(paginationKeys.has(next)||page===MAX_PAGES-1)throw new Error('INVALID_PAGINATION');
      paginationKeys.add(next);paginationKey=next;
    }
    report.uniqueSymbolCount=symbols.size;
    report.symbolSetSha256=createHash('sha256').update([...symbols].sort().join('\n')).digest('hex');
    report.status=report.paginationComplete&&report.rowCount>0&&report.uniqueSymbolCount>0
      &&report.invalidRows===0&&report.duplicateMinuteKeys===0?'DATE_WIDE_CAPACITY_PROFILE_PASS':'DATE_WIDE_CAPACITY_PROFILE_FAIL';
  }catch(error){
    const safe=new Set(['AUTH_REJECTED','BLOCKED_ENTITLEMENT','RATE_LIMITED','PAGE_TOO_LARGE','INVALID_SCHEMA','INVALID_PAGINATION']);
    report.status=safe.has(error.message)?error.message:'CAPACITY_PROFILE_TRANSPORT_OR_DATA_ERROR';
  }
  return report;
}

async function main(){
  const report=await profileDateWideCapacity({apiKey:process.env.JQUANTS_API_KEY});
  const content=JSON.stringify(report,null,2)+'\n',directory='artifacts/phase57-jquants-date-capacity';
  fs.mkdirSync(directory,{recursive:true,mode:0o700});fs.writeFileSync(`${directory}/report.json`,content,{mode:0o600});
  fs.writeFileSync(`${directory}/report.sha256`,`${createHash('sha256').update(content).digest('hex')}  report.json\n`,{mode:0o600});
  console.log('JQUANTS_DATE_CAPACITY_REPORT '+JSON.stringify(report));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(()=>{
  console.error('JQUANTS_DATE_CAPACITY_INTERNAL_ERROR');process.exitCode=1;
});

export const Phase57DateCapacityInternals=Object.freeze({PROFILE_DATE,MAX_PAGES,MAX_BYTES_PER_PAGE});
