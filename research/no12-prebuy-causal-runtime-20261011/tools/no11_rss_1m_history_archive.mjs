/**
 * Immutable, READ-ONLY, single-symbol 1M RssChart archive.
 * Can run on JPX holidays; does not pretend this is marketwide training data.
 * No Excel COM, broker API, orders, or external network.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
import {isJpxCashTradingDay} from '../runtime/jpx_cash_calendar_2026_2027.mjs';
const fail=x=>{throw Error(x)};
const hash=b=>createHash('sha256').update(b).digest('hex');
const timestamp=(x,label)=>{
 if(typeof x!=='string'||!/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(x)||
    !Number.isFinite(Date.parse(x)))fail(label);
 return Date.parse(x);
};
const jst=x=>new Intl.DateTimeFormat('en-CA',{
 timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(x)).replaceAll('/','-');
const num=(x,zero=false)=>{
 if(typeof x!=='number'||!Number.isFinite(x)||(zero?x<0:x<=0))
   fail('NO11_1M_ARCHIVE_OHLCV_INVALID');
 return x;
};
function rootOf(root){
 if(typeof root!=='string'||!path.isAbsolute(root))
   fail('NO11_1M_ARCHIVE_ABSOLUTE_ROOT_REQUIRED');
 const st=fs.lstatSync(root);
 if(!st.isDirectory()||st.isSymbolicLink())
   fail('NO11_1M_ARCHIVE_ROOT_UNSAFE');
 return path.resolve(root);
}
function candidateBytes(file){
 const st=fs.lstatSync(file);
 if(!st.isFile()||st.isSymbolicLink()||st.size<20||st.size>2200000)
   fail('NO11_1M_ARCHIVE_FILE_UNSAFE');
 return fs.readFileSync(file);
}
export function inspectNo11Rss1mHistorical({snapshot,now=new Date()}={}){
 if(snapshot?.schemaId!=='ARK_NO12_MSII_RSS_CHART_1M_OBSERVATION_V1'||
    snapshot.sourceFunction!=='RssChart'||snapshot.period!=='1M'||
    snapshot.evidenceMode!=='OBSERVED_READ_ONLY'||snapshot.symbol!=='7203.T'||
    snapshot.privateAccountDataIncluded!==false||snapshot.excelOrderEnabled===true||
    !Array.isArray(snapshot.columns)||snapshot.columns.length!==RSS_CHART_COLUMNS.length||
    RSS_CHART_COLUMNS.some((c,i)=>snapshot.columns[i]!==c)||
    !Array.isArray(snapshot.rows)||snapshot.rows.length<1||snapshot.rows.length>3000)
   fail('NO11_1M_ARCHIVE_SOURCE_CONTRACT_INVALID');
 const captured=timestamp(snapshot.capturedAt,'NO11_1M_ARCHIVE_CAPTURE_INVALID');
 const current=now instanceof Date?now.getTime():timestamp(now,'NO11_1M_ARCHIVE_NOW_INVALID');
 if(!Number.isFinite(current)||captured>current+1000||current-captured>30000)
   fail('NO11_1M_ARCHIVE_CAPTURE_STALE_OR_FUTURE');
 const seen=new Set(),rows=[];
 for(const raw of snapshot.rows){
  if(!raw||typeof raw!=='object'||Array.isArray(raw)||raw['足種']!=='1M'||
     typeof raw['日付']!=='string'||!/^20\d\d\/\d\d\/\d\d$/.test(raw['日付'])||
     typeof raw['時刻']!=='string'||!/^\d\d:\d\d$/.test(raw['時刻']))
    fail('NO11_1M_ARCHIVE_ROW_FORMAT_INVALID');
  const day=raw['日付'].replaceAll('/','-'),clock=raw['時刻'];
  if(!isJpxCashTradingDay(day)||day>jst(captured))
    fail('NO11_1M_ARCHIVE_DAY_INVALID');
  const minute=Number(clock.slice(0,2))*60+Number(clock.slice(3));
  if(!((minute>=540&&minute<=690)||(minute>=750&&minute<=930)))
    fail('NO11_1M_ARCHIVE_MARKET_CLOCK_INVALID');
  const ms=Date.parse(day+'T'+clock+':00+09:00');
  if(!Number.isFinite(ms)||ms>captured)
    fail('NO11_1M_ARCHIVE_FUTURE_BAR_INVALID');
  const key=day+'|'+clock;
  if(seen.has(key))fail('NO11_1M_ARCHIVE_DUPLICATE_BAR');
  seen.add(key);
  const open=num(raw['始値']),high=num(raw['高値']),low=num(raw['安値']),
    close=num(raw['終値']),volume=num(raw['出来高'],true);
  if(!Number.isSafeInteger(volume)||low>Math.min(open,close)||
     high<Math.max(open,close)||high<low)
    fail('NO11_1M_ARCHIVE_OHLCV_INCONSISTENT');
  // Conservative; source START/END label semantics remain UNVERIFIED.
  if(ms+60000>captured)continue;
  rows.push({day,clock,open,high,low,close,volume});
 }
 rows.sort((a,b)=>(a.day+a.clock).localeCompare(b.day+b.clock));
 if(rows.length===0)fail('NO11_1M_ARCHIVE_NO_CLOSED_ROWS');
 const days=[...new Set(rows.map(x=>x.day))];
 return Object.freeze({
  schemaId:'ARK_NO11_RSS_1M_HISTORICAL_READONLY_V1',
  status:'LOCAL_HISTORICAL_1M_OBSERVED_NOT_TRAINING_CERTIFIED',
  symbol:'7203.T',sourceFunction:'RssChart',period:'1M',
  capturedAt:snapshot.capturedAt,requestedRows:snapshot.rows.length,
  acceptedClosedRows:rows.length,observedSessions:days.length,
  earliestDay:days[0],latestDay:days.at(-1),
  daily:days.map(day=>({day,bars:rows.filter(r=>r.day===day).length})),
  barTimeConvention:'UNVERIFIED',missingBars:'NOT_FILLED',
  marketwideSelectorCertified:false,firstEntryCertified:false,
  state9Certified:false,teacherLabelsCertified:false,
  brokerArrivalCertified:false,modelTrainingReady:false,
  productionReady:false,orderTransmission:false,rows
 });
}
export function archiveNo11Rss1mHistorical({
 privateRoot,candidatePath,now=new Date()
}={}){
 const root=rootOf(privateRoot),candidate=path.resolve(candidatePath??'');
 if(path.dirname(candidate)!==root||
    !/^one-minute-candidate-[a-f0-9]{32}\.json$/.test(path.basename(candidate)))
   fail('NO11_1M_ARCHIVE_CANDIDATE_INVALID');
 const raw=candidateBytes(candidate);
 const snapshot=JSON.parse(raw.toString('utf8').replace(/^\uFEFF/,''));
 const report=inspectNo11Rss1mHistorical({snapshot,now});
 const bytes=Buffer.from(JSON.stringify(report)+'\n'),digest=hash(bytes);
 const time=new Date(Date.parse(snapshot.capturedAt)).toISOString()
   .replace(/[-:]/g,'').replace(/\.\d+Z$/,'Z');
 const stem='rss-1m-7203T-'+time+'-'+digest.slice(0,12);
 const dataFile=path.join(root,stem+'.json');
 const receiptFile=path.join(root,stem+'.receipt.json');
 const receipt={
  schemaId:'ARK_NO11_RSS_1M_HISTORICAL_RECEIPT_V1',
  fileName:path.basename(dataFile),sha256:digest,
  capturedAt:snapshot.capturedAt,acceptedClosedRows:report.acceptedClosedRows,
  observedSessions:report.observedSessions,earliestDay:report.earliestDay,
  latestDay:report.latestDay,modelTrainingReady:false,
  productionReady:false,orderTransmission:false
 };
 // No overwrite: each source capture remains independently auditable.
 fs.writeFileSync(dataFile,bytes,{flag:'wx',mode:0o600});
 fs.writeFileSync(receiptFile,JSON.stringify(receipt)+'\n',
   {flag:'wx',mode:0o600});
 return Object.freeze({status:report.status,rows:report.acceptedClosedRows,
  sessions:report.observedSessions,earliestDay:report.earliestDay,
  latestDay:report.latestDay,productionReady:false,orderTransmission:false});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const a=process.argv.slice(2);
  if(a.length!==4||a[0]!=='--private-root'||a[2]!=='--candidate')
    fail('NO11_1M_ARCHIVE_CLI_USAGE');
  const r=archiveNo11Rss1mHistorical({
    privateRoot:a[1],candidatePath:a[3]});
  console.log('NO11_1M_ARCHIVE_STATUS='+r.status);
  console.log('NO11_1M_ARCHIVE_ROWS='+r.rows);
  console.log('NO11_1M_ARCHIVE_SESSIONS='+r.sessions);
  console.log('NO11_1M_ARCHIVE_EARLIEST_DAY='+r.earliestDay);
  console.log('NO11_1M_ARCHIVE_LATEST_DAY='+r.latestDay);
  console.log('NO11_MODEL_TRAINING_READY=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch{
  console.error('NO11_1M_ARCHIVE_STATUS=BLOCKED');
  console.error('NO11_MODEL_TRAINING_READY=False');
  console.error('NO11_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
