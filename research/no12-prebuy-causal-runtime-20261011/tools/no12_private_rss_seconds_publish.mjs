/**
 * RssMarket 1-ticker seconds sample receipt. Local-private READ ONLY only.
 * PC sampledAt is an upper bound on first-seen time, NOT broker delivery time.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const fail=s=>{throw Error(s)};
const sha=x=>createHash('sha256').update(x).digest('hex');
const iso=(s,label)=>{
 if(typeof s!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(s)||!Number.isFinite(Date.parse(s)))
   fail(label);
 return Date.parse(s);
};
const jst=ms=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
 year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms)).replace(/\//g,'-');
const rootOf=root=>{
 if(typeof root!=='string'||!path.isAbsolute(root))fail('NO12_SECONDS_PRIVATE_ROOT_REQUIRED');
 const s=fs.lstatSync(root);
 if(!s.isDirectory()||s.isSymbolicLink())fail('NO12_SECONDS_PRIVATE_ROOT_UNSAFE');
 return path.resolve(root);
};
const regular=file=>{
 const s=fs.lstatSync(file);
 if(!s.isFile()||s.isSymbolicLink())fail('NO12_SECONDS_PRIVATE_FILE_UNSAFE');
};
function atomic(file,data){
 const tmp=file+'.tmp-'+process.pid+'-'+randomUUID();let fd;
 try{
  fd=fs.openSync(tmp,'wx',0o600);
  fs.writeFileSync(fd,data);fs.fsyncSync(fd);
  fs.closeSync(fd);fd=undefined;fs.renameSync(tmp,file);
 }finally{
  if(fd!==undefined)fs.closeSync(fd);
  if(fs.existsSync(tmp))fs.unlinkSync(tmp);
 }
}
export function inspectNo12SecondsSnapshot({snapshot,now=new Date()}={}){
 if(snapshot?.schemaId!=='ARK_NO12_MSII_RSS_MARKET_SECONDS_OBSERVATION_V1'||
   snapshot.sourceFunction!=='RssMarket'||snapshot.evidenceMode!=='OBSERVED_READ_ONLY'||
   snapshot.symbol!=='7203.T'||snapshot.orderPermissionEnabled!==false||
   snapshot.privateAccountDataIncluded!==false||
   !Array.isArray(snapshot.samples)||snapshot.samples.length<3||
   snapshot.samples.length>30)
   fail('NO12_SECONDS_SOURCE_CONTRACT_INVALID');
 const captured=iso(snapshot.capturedAt,'NO12_SECONDS_CAPTURE_TIME_INVALID');
 const nowMs=now instanceof Date?now.getTime():iso(now,'NO12_SECONDS_NOW_INVALID');
 if(!Number.isFinite(nowMs)||captured>nowMs+1000||nowMs-captured>30000)
   fail('NO12_SECONDS_SOURCE_STALE_OR_FUTURE');
 let lastSample=-Infinity,sourceAdvance=0,prevSource=null;
 const observations=[];
 for(const sample of snapshot.samples){
  const sampled=iso(sample?.sampledAt,'NO12_SECONDS_SAMPLE_CLOCK_INVALID');
  if(sampled<=lastSample||sampled>captured+1000||
    jst(sampled)!==String(sample.marketDate??'').replaceAll('/','-'))
    fail('NO12_SECONDS_SAMPLE_ORDER_OR_DAY_INVALID');
  lastSample=sampled;
  if(typeof sample.marketClock!=='string'||!/^\d\d:\d\d:\d\d$/.test(sample.marketClock))
    fail('NO12_SECONDS_EXCHANGE_TIME_INVALID');
  const source=iso(sample.marketDate.replaceAll('/','-')+'T'+sample.marketClock+'+09:00',
    'NO12_SECONDS_EXCHANGE_TIMESTAMP_INVALID');
  if(source>sampled+1000)fail('NO12_SECONDS_FUTURE_EXCHANGE_TICK');
  if(typeof sample.lastPrice!=='number'||!Number.isFinite(sample.lastPrice)||sample.lastPrice<=0)
    fail('NO12_SECONDS_PRICE_INVALID');
  const quote=x=>x===null||x===undefined?null:
    typeof x==='number'&&Number.isFinite(x)&&x>0?x:fail('NO12_SECONDS_QUOTE_INVALID');
  const bid=quote(sample.bestBid),ask=quote(sample.bestAsk);
  if(bid!==null&&ask!==null&&bid>ask)
    fail('NO12_SECONDS_CROSSED_BID_ASK_UNVERIFIED');
  const ageMs=Math.max(0,sampled-source);
  if(prevSource!==null&&source>prevSource)sourceAdvance++;
  if(prevSource!==null&&source<prevSource)
    fail('NO12_SECONDS_SOURCE_CLOCK_REGRESSION');
  prevSource=source;
  observations.push({sampledAt:sample.sampledAt,sourceAsOf:new Date(source).toISOString(),
    lastPrice:sample.lastPrice,bestBid:bid,bestAsk:ask,ageMs});
 }
 return Object.freeze({
  schemaId:'ARK_NO12_RSS_SECONDS_SOURCE_AUDIT_V1',
  status:sourceAdvance>0?'PC_OBSERVED_EXCHANGE_SECONDS_ADVANCE_NOT_BROKER_CERTIFIED':
    'PC_OBSERVED_SAMPLES_WITHOUT_EXCHANGE_TIME_ADVANCE',
  symbol:snapshot.symbol,capturedAt:snapshot.capturedAt,
  sampleCount:observations.length,sourceTimeAdvanceCount:sourceAdvance,
  maxSourceAgeMs:Math.max(...observations.map(x=>x.ageMs)),
  observations:Object.freeze(observations),
  actualBrokerArrivalCertified:false,
  marketwideSelectorCertified:false,
  originalNativeState9Certified:false,
  productionReady:false,orderTransmission:false
 });
}
export function publishNo12PrivateSeconds({privateRoot,candidatePath,now=new Date()}={}){
 const root=rootOf(privateRoot),file=path.resolve(candidatePath??'');
 if(path.dirname(file)!==root||
   !/^seconds-candidate-[a-f0-9]{32}\.json$/.test(path.basename(file)))
   fail('NO12_SECONDS_PRIVATE_CANDIDATE_INVALID');
 regular(file);
 const bytes=fs.readFileSync(file);
 if(bytes.length>40000)fail('NO12_SECONDS_PRIVATE_INPUT_TOO_LARGE');
 const input=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
 const audit=inspectNo12SecondsSnapshot({snapshot:input,now});
 const body=Buffer.from(JSON.stringify(audit)+'\n');
 const receipt={
  schemaId:'ARK_NO12_PRIVATE_RSS_SECONDS_RECEIPT_V1',
  evidenceSha256:sha(body),sampleCount:audit.sampleCount,
  sourceTimeAdvanceCount:audit.sourceTimeAdvanceCount,
  capturedAt:audit.capturedAt,
  actualBrokerArrivalCertified:false,productionReady:false,orderTransmission:false
 };
 const out=path.join(root,'market-seconds-readonly-observed.json');
 const rec=path.join(root,'market-seconds-readonly-receipt.json');
 if(fs.existsSync(out))regular(out);
 if(fs.existsSync(rec))regular(rec);
 atomic(out,body);atomic(rec,Buffer.from(JSON.stringify(receipt)+'\n'));
 return Object.freeze({...audit,observations:undefined});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const args=process.argv.slice(2);
  if(args.length!==4||args[0]!=='--private-root'||args[2]!=='--candidate')
    fail('NO12_SECONDS_PRIVATE_CLI_USAGE');
  const r=publishNo12PrivateSeconds({privateRoot:args[1],candidatePath:args[3]});
  console.log('NO12_SECONDS_RSS_STATUS='+r.status);
  console.log('NO12_SECONDS_SAMPLE_COUNT='+r.sampleCount);
  console.log('NO12_SECONDS_SOURCE_TIME_ADVANCES='+r.sourceTimeAdvanceCount);
  console.log('NO12_SECONDS_MAX_OBSERVED_AGE_MS='+r.maxSourceAgeMs);
  console.log('ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False');
  console.log('NO12_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch{
  console.error('NO12_SECONDS_RSS_STATUS=BLOCKED');
  console.error('NO12_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
