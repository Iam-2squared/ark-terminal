/**
 * One-ticker 1M RssChart local-private source receipt, READ ONLY.
 * Never a Selector/First Entry/State9/ML decision or order writer.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {inspectNo12OneMinuteObservation} from '../runtime/rss_1m_history_observation.mjs';
const fail=s=>{throw Error(s)};
const hash=b=>createHash('sha256').update(b).digest('hex');
function regular(file){
 const s=fs.lstatSync(file);
 if(!s.isFile()||s.isSymbolicLink())fail('NO12_1M_PRIVATE_FILE_UNSAFE');
}
function rootOf(root){
 if(typeof root!=='string'||!path.isAbsolute(root))fail('NO12_1M_PRIVATE_ROOT_ABSOLUTE_REQUIRED');
 const s=fs.lstatSync(root);
 if(!s.isDirectory()||s.isSymbolicLink())fail('NO12_1M_PRIVATE_ROOT_UNSAFE');
 return path.resolve(root);
}
function atomic(file,body){
 const temp=file+'.tmp-'+process.pid+'-'+randomUUID();
 let fd;
 try{
  fd=fs.openSync(temp,'wx',0o600);
  fs.writeFileSync(fd,body);fs.fsyncSync(fd);
  fs.closeSync(fd);fd=undefined;fs.renameSync(temp,file);
 }finally{
  if(fd!==undefined)fs.closeSync(fd);
  if(fs.existsSync(temp))fs.unlinkSync(temp);
 }
}
const col=(row,k)=>{
 const n=row[k];
 if(typeof n!=='number'||!Number.isFinite(n))fail('NO12_1M_PRIVATE_OHLCV_INVALID');
 return n;
};
export function publishNo12PrivateOneMinute({
 privateRoot,candidatePath,now=new Date()
}={}){
 const root=rootOf(privateRoot),candidate=path.resolve(candidatePath??'');
 if(path.dirname(candidate)!==root||
   !/^one-minute-candidate-[a-f0-9]{32}\.json$/.test(path.basename(candidate)))
   fail('NO12_1M_PRIVATE_CANDIDATE_INVALID');
 regular(candidate);
 const raw=fs.readFileSync(candidate);
 if(raw.length>1100000)fail('NO12_1M_PRIVATE_CANDIDATE_TOO_LARGE');
 const snapshot=JSON.parse(raw.toString('utf8').replace(/^\uFEFF/,''));
 const audit=inspectNo12OneMinuteObservation({snapshot,now});
 if(audit.status!=='ONE_MINUTE_CLOSED_BAR_LOCAL_OBSERVATION_ONLY'||
    audit.currentBar===null||audit.productionReady!==false)
   fail('NO12_1M_NO_COMPLETED_CURRENT_BAR');
 // Only whitelisted market fields are persisted. Account/private extra keys are discarded.
 const rows=snapshot.rows.map(r=>({
  day:String(r['日付']),clock:String(r['時刻']),
  open:col(r,'始値'),high:col(r,'高値'),low:col(r,'安値'),
  close:col(r,'終値'),volume:col(r,'出来高')
 }));
 const evidence={
  schemaId:'ARK_NO12_PRIVATE_ONE_MINUTE_MARKET_V1',
  symbol:snapshot.symbol,period:'1M',capturedAt:snapshot.capturedAt,
  historyStatus:audit.historyStatus,
  previousSessionsRequired:audit.requiredPreviousSessions,
  historyBars:audit.historyBars,historySha256:audit.historySha256,
  latestClosedBar:audit.currentBar,rows,
  originalState9Certified:false,brokerActualArrivalCertified:false,
  historicalBrokerArrivalCertified:false,
  productionReady:false,orderTransmission:false
 };
 const data=Buffer.from(JSON.stringify(evidence)+'\n');
 const receipt={
  schemaId:'ARK_NO12_PRIVATE_ONE_MINUTE_RECEIPT_V1',
  sourceSha256:hash(data),historySha256:audit.historySha256,
  historyStatus:audit.historyStatus,barCount:rows.length,
  capturedAt:snapshot.capturedAt,
  brokerActualArrivalCertified:false,
  productionReady:false,orderTransmission:false
 };
 const out=path.join(root,'market-1m-readonly-observed.json');
 const rec=path.join(root,'market-1m-readonly-receipt.json');
 if(fs.existsSync(out))regular(out);
 if(fs.existsSync(rec))regular(rec);
 atomic(out,data);
 atomic(rec,Buffer.from(JSON.stringify(receipt)+'\n'));
 return Object.freeze({
  status:'LOCAL_1M_MARKET_RECEIPT_NOT_LIVE_CERTIFIED',
  historyStatus:audit.historyStatus,historyBars:audit.historyBars,
  rows:rows.length,brokerActualArrivalCertified:false,
  productionReady:false,orderTransmission:false
 });
}
export function verifyNo12PrivateOneMinute({privateRoot,now=new Date()}={}){
 const root=rootOf(privateRoot);
 const out=path.join(root,'market-1m-readonly-observed.json');
 const rec=path.join(root,'market-1m-readonly-receipt.json');
 regular(out);regular(rec);
 const data=fs.readFileSync(out),receipt=JSON.parse(fs.readFileSync(rec,'utf8'));
 const evidence=JSON.parse(data.toString('utf8'));
 if(receipt.schemaId!=='ARK_NO12_PRIVATE_ONE_MINUTE_RECEIPT_V1'||
    receipt.sourceSha256!==hash(data)||
    evidence.schemaId!=='ARK_NO12_PRIVATE_ONE_MINUTE_MARKET_V1'||
    evidence.period!=='1M'||evidence.historySha256!==receipt.historySha256||
    evidence.historyStatus!==receipt.historyStatus||
    !Array.isArray(evidence.rows)||evidence.rows.length!==receipt.barCount||
    evidence.brokerActualArrivalCertified!==false||
    receipt.brokerActualArrivalCertified!==false||
    evidence.productionReady!==false||receipt.productionReady!==false||
    evidence.orderTransmission!==false||receipt.orderTransmission!==false)
    fail('NO12_1M_PRIVATE_RECEIPT_TAMPERED');
 const capture=Date.parse(evidence.capturedAt);
 const clock=now instanceof Date?now.getTime():Date.parse(now);
 if(!Number.isFinite(capture)||!Number.isFinite(clock)||
    capture>clock+1000||clock-capture>30000)
    fail('NO12_1M_PRIVATE_RECEIPT_STALE');
 return Object.freeze({status:'LOCAL_1M_RECEIPT_HASH_VALID_NOT_LIVE',
  rows:receipt.barCount,productionReady:false,orderTransmission:false});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const a=process.argv.slice(2);
  if(a.length!==4||a[0]!=='--private-root'||a[2]!=='--candidate')
    fail('NO12_1M_PRIVATE_CLI_USAGE');
  const r=publishNo12PrivateOneMinute({privateRoot:a[1],candidatePath:a[3]});
  console.log('NO12_1M_RECEIPT='+r.status);
  console.log('NO12_1M_HISTORY_STATUS='+r.historyStatus);
  console.log('NO12_1M_HISTORY_BARS='+r.historyBars);
  console.log('NO12_1M_OBSERVED_ROWS='+r.rows);
  console.log('NO12_1M_NATIVE_STATE9_READY=False');
  console.log('NO12_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch{
  console.error('NO12_1M_RECEIPT=BLOCKED');
  console.error('NO12_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
