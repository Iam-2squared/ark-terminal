// No12 observed chart -> local private READ ONLY receipt; no live attestations or orders.
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {inspectNo12RssChartSnapshot} from '../runtime/msii_rss_chart_observation.mjs';
import {normalizeNo12HistoricalChart} from '../runtime/rss_5m_history_bootstrap.mjs';
const fail=s=>{throw Error(s)};
const hash=v=>createHash('sha256').update(v).digest('hex');
function rootOf(root){
 if(typeof root!=='string'||!path.isAbsolute(root))fail('PRIVATE_ROOT_ABSOLUTE_REQUIRED');
 const s=fs.lstatSync(root);
 if(!s.isDirectory()||s.isSymbolicLink())fail('PRIVATE_ROOT_UNSAFE');
 return path.resolve(root);
}
function regular(file){
 const s=fs.lstatSync(file);
 if(!s.isFile()||s.isSymbolicLink())fail('PRIVATE_MARKET_FILE_UNSAFE');
}
function atomic(file,body){
 const temp=file+'.tmp-'+process.pid+'-'+randomUUID();let fd;
 try{
  fd=fs.openSync(temp,'wx',0o600);
  fs.writeFileSync(fd,body);fs.fsyncSync(fd);fs.closeSync(fd);fd=undefined;
  fs.renameSync(temp,file);
 }finally{
  if(fd!==undefined)fs.closeSync(fd);
  if(fs.existsSync(temp))fs.unlinkSync(temp);
 }
}
export function publishNo12ObservedChart({privateRoot,candidatePath,now=new Date()}={}){
 const root=rootOf(privateRoot),candidate=path.resolve(candidatePath??'');
 if(path.dirname(candidate)!==root||
   !/^chart-candidate-[a-f0-9]{32}\.json$/.test(path.basename(candidate)))
   fail('PRIVATE_CHART_CANDIDATE_PATH_INVALID');
 regular(candidate);
 const fileBytes=fs.readFileSync(candidate);
 if(fileBytes.length>250000)fail('PRIVATE_CHART_INPUT_TOO_LARGE');
 const snap=JSON.parse(fileBytes.toString('utf8').replace(/^\uFEFF/,''));
 const history=normalizeNo12HistoricalChart({snapshot:snap,now});
 const audit=inspectNo12RssChartSnapshot({snapshot:snap,decisionAt:now.toISOString(),now});
 if(audit.status!=='LOCAL_CHART_5M_BAR_OBSERVED_READONLY_NOT_LIVE_CERTIFIED')
  return Object.freeze({status:'NO_CURRENT_SESSION_COMPLETE_BAR',bars:0,productionReady:false});
 const value={schemaId:'ARK_NO12_PRIVATE_MARKET_OBSERVATION_V1',
  capturedAt:snap.capturedAt,symbol:snap.symbol,period:'5M',
  historyStatus:history.status,previousSessionsFound:history.observedSessions,
  historyRequiredSessions:history.requiredPreviousSessions,
  historySelectedSessionIds:history.selectedSessionIds,historyRows:history.historyRows,
  historySha256:history.historySha256,historicalArrivalCertified:false,
  bars:audit.closedBars,sourceRecord:audit.sourceRecord,
  sourcePayloadSha256:audit.sourcePayloadSha256,
  brokerArrivalCertified:false,nativeDecisionCertified:false,
  productionReady:false,orderTransmission:false};
 const data=Buffer.from(JSON.stringify(value)+'\n');
 const destination=path.join(root,'market-readonly-observed.json');
 const receiptFile=path.join(root,'market-readonly-receipt.json');
 if(fs.existsSync(destination))regular(destination);
 if(fs.existsSync(receiptFile))regular(receiptFile);
 atomic(destination,data);
 const receipt={schemaId:'ARK_NO12_PRIVATE_MARKET_RECEIPT_V1',
  marketSha256:hash(data),bars:value.bars.length,
  previousSessionsFound:history.observedSessions,
  historyStatus:history.status,historySha256:history.historySha256,
  brokerArrivalCertified:false,productionReady:false,orderTransmission:false};
 atomic(receiptFile,Buffer.from(JSON.stringify(receipt)+'\n'));
 return Object.freeze({status:'LOCAL_MARKET_OBSERVATION_RECORDED_NOT_CERTIFIED',
  bars:value.bars.length,previousSessionsFound:history.observedSessions,
  historyStatus:history.status,productionReady:false,orderTransmission:false});
}
export function verifyNo12ObservedChart({privateRoot,now=new Date()}={}){
 const root=rootOf(privateRoot),filename=path.join(root,'market-readonly-observed.json');
 const receiptFile=path.join(root,'market-readonly-receipt.json');
 regular(filename);regular(receiptFile);
 const raw=fs.readFileSync(filename),receipt=JSON.parse(fs.readFileSync(receiptFile,'utf8'));
 if(receipt.schemaId!=='ARK_NO12_PRIVATE_MARKET_RECEIPT_V1'||
  receipt.marketSha256!==hash(raw)||receipt.productionReady!==false||
  receipt.orderTransmission!==false)fail('LOCAL_MARKET_RECEIPT_MISMATCH');
 const obj=JSON.parse(raw.toString('utf8'));
 if(obj.schemaId!=='ARK_NO12_PRIVATE_MARKET_OBSERVATION_V1'||
   !Array.isArray(obj.bars)||obj.bars.length!==receipt.bars||
   obj.brokerArrivalCertified!==false||obj.productionReady!==false||
   obj.orderTransmission!==false||obj.historicalArrivalCertified!==false||
   !Array.isArray(obj.historyRows)||
   obj.historySha256!==hash(Buffer.from(JSON.stringify(obj.historyRows)))||
   obj.historyStatus!==receipt.historyStatus||
   obj.historySha256!==receipt.historySha256||
   obj.previousSessionsFound!==receipt.previousSessionsFound)
   fail('LOCAL_MARKET_RECEIPT_MISMATCH');
 // Hash-valid historical files are not valid as CURRENT market observations.
 const capturedAt=Date.parse(obj.capturedAt??'');
 const nowMs=now instanceof Date?now.getTime():Date.parse(now);
 if(!Number.isFinite(capturedAt)||!Number.isFinite(nowMs)||
    capturedAt>nowMs+1000||nowMs-capturedAt>30000)
   fail('NO12_LOCAL_MARKET_RECEIPT_STALE');
 return Object.freeze({status:'LOCAL_MARKET_RECEIPT_HASH_VALID',
  bars:receipt.bars,brokerArrivalCertified:false,
  productionReady:false,orderTransmission:false});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const args=process.argv.slice(2);
  if(args.length!==4||args[0]!=='--private-root'||args[2]!=='--candidate')
    fail('MARKET_PUBLISH_USAGE');
  const out=publishNo12ObservedChart({privateRoot:args[1],candidatePath:args[3]});
  if(out.status!=='LOCAL_MARKET_OBSERVATION_RECORDED_NOT_CERTIFIED')
    fail('NO12_CURRENT_SESSION_COMPLETED_BAR_REQUIRED');
  console.log('NO12_LOCAL_MARKET_RECEIPT='+out.status);
  console.log('NO12_LOCAL_MARKET_COMPLETE_BARS='+out.bars);
  console.log('NO12_5DAY_HISTORY_STATUS='+out.historyStatus);
  console.log('NO12_5DAY_HISTORY_PREVIOUS_SESSIONS='+out.previousSessionsFound);
  console.log('NO12_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch{
  console.error('NO12_LOCAL_MARKET_RECEIPT=BLOCKED');
  console.error('ORDER_TRANSMISSION=False');process.exitCode=2;
 }
}
