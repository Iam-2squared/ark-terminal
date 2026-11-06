/**
 * Bridges a PRIVATE, locally observed RssMarket HH:MM:SS receipt into the
 * Frozen No.1.1 AS-OF Shadow input envelope. No model, ranking or order.
 *
 * This does NOT prove original Frozen Selector/State9/First Entry, the
 * broker's actual arrival timestamp, data licensing or trade readiness.
 * Crucially, knownAt is the time this adapter verifies the file, NOT the
 * earlier exchange timestamp or the snapshot's write-start timestamp.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const fail=x=>{throw Error(x)};
const sha=b=>createHash('sha256').update(b).digest('hex');
const timestamp=(x,label)=>{
 if(typeof x!=='string'||!/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(x)||
   !Number.isFinite(Date.parse(x)))fail(label);
 return Date.parse(x);
};
const jst=x=>new Intl.DateTimeFormat('en-CA',{
 timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(x)).replace(/\//g,'-');
function safeRoot(p){
 if(typeof p!=='string'||!path.isAbsolute(p))fail('NO11_RSS_SECONDS_ABSOLUTE_ROOT_REQUIRED');
 const s=fs.lstatSync(p);
 if(!s.isDirectory()||s.isSymbolicLink())fail('NO11_RSS_SECONDS_UNSAFE_ROOT');
 return path.resolve(p);
}
function readPrivate(file,limit){
 const s=fs.lstatSync(file);
 if(!s.isFile()||s.isSymbolicLink()||s.size<10||s.size>limit)
  fail('NO11_RSS_SECONDS_UNSAFE_PRIVATE_FILE');
 return fs.readFileSync(file);
}
const positive=(n,label)=>{
 if(typeof n!=='number'||!Number.isFinite(n)||n<=0)fail(label);
 return n;
};
const quote=(n,label)=>{
 if(n===null)return null;
 return positive(n,label);
};
export function readNo11LocalRssSecondsAsOf({
 privateRoot,decisionAt,now=new Date()
}={}){
 const root=safeRoot(privateRoot);
 const raw=readPrivate(path.join(root,'market-seconds-readonly-observed.json'),50000);
 const rec=JSON.parse(readPrivate(path.join(root,'market-seconds-readonly-receipt.json'),5000).toString('utf8'));
 const obj=JSON.parse(raw.toString('utf8'));
 if(rec?.schemaId!=='ARK_NO12_PRIVATE_RSS_SECONDS_RECEIPT_V1'||
   obj?.schemaId!=='ARK_NO12_RSS_SECONDS_SOURCE_AUDIT_V1'||
   rec.evidenceSha256!==sha(raw)||
   rec.productionReady!==false||rec.orderTransmission!==false||
   rec.actualBrokerArrivalCertified!==false||
   obj.productionReady!==false||obj.orderTransmission!==false||
   obj.actualBrokerArrivalCertified!==false||
   obj.marketwideSelectorCertified!==false||
   obj.originalNativeState9Certified!==false||
   obj.symbol!=='7203.T'||
   !['PC_OBSERVED_EXCHANGE_SECONDS_ADVANCE_NOT_BROKER_CERTIFIED',
     'PC_OBSERVED_SAMPLES_WITHOUT_EXCHANGE_TIME_ADVANCE'].includes(obj.status)||
   !Array.isArray(obj.observations)||obj.observations.length<3||
   obj.observations.length>30||
   obj.sampleCount!==obj.observations.length||
   rec.sampleCount!==obj.sampleCount||
   rec.capturedAt!==obj.capturedAt||
   rec.sourceTimeAdvanceCount!==obj.sourceTimeAdvanceCount)
   fail('NO11_RSS_SECONDS_RECEIPT_IDENTITY_INVALID');
 const nowMs=now instanceof Date?now.getTime():timestamp(now,'NO11_RSS_SECONDS_NOW_INVALID');
 const decision=timestamp(decisionAt,'NO11_RSS_SECONDS_DECISION_INVALID');
 const captured=timestamp(obj.capturedAt,'NO11_RSS_SECONDS_CAPTURE_INVALID');
 if(!Number.isFinite(nowMs)||captured>nowMs||nowMs>decision||
   decision-nowMs>5000||nowMs-captured>30000||
   jst(captured)!==jst(decision))
   fail('NO11_RSS_SECONDS_DECISION_NOT_CAUSAL_OR_STALE');
 let lastSample=-Infinity,lastSource=-Infinity,advance=0,latest=null,maxAge=0;
 for(const o of obj.observations){
  const sampled=timestamp(o?.sampledAt,'NO11_RSS_SECONDS_SAMPLE_INVALID');
  const source=timestamp(o?.sourceAsOf,'NO11_RSS_SECONDS_EXCHANGE_INVALID');
  if(sampled<=lastSample||sampled>captured||source>sampled||
    source<lastSource||jst(sampled)!==jst(decision)||jst(source)!==jst(decision)||
    o.ageMs!==sampled-source)
   fail('NO11_RSS_SECONDS_SAMPLE_CHRONOLOGY_INVALID');
  const price=positive(o.lastPrice,'NO11_RSS_SECONDS_PRICE_INVALID');
  const bid=quote(o.bestBid,'NO11_RSS_SECONDS_BID_INVALID');
  const ask=quote(o.bestAsk,'NO11_RSS_SECONDS_ASK_INVALID');
  if(bid!==null&&ask!==null&&bid>ask)
   fail('NO11_RSS_SECONDS_CROSSED_QUOTES');
  if(lastSource!==-Infinity&&source>lastSource)advance++;
  maxAge=Math.max(maxAge,sampled-source);
  lastSource=source;lastSample=sampled;latest={price,source,sampled};
 }
 if(advance!==obj.sourceTimeAdvanceCount||
    obj.maxSourceAgeMs!==maxAge||
    obj.status!==(advance>0?'PC_OBSERVED_EXCHANGE_SECONDS_ADVANCE_NOT_BROKER_CERTIFIED':
      'PC_OBSERVED_SAMPLES_WITHOUT_EXCHANGE_TIME_ADVANCE'))
  fail('NO11_RSS_SECONDS_ADVANCE_COUNT_MISMATCH');
 if(decision-latest.source>30000)
  fail('NO11_RSS_SECONDS_LATEST_PRICE_TOO_OLD');
 const market=Object.freeze({
  kind:'MARKETSPEED_II_RSS_MARKET_OBSERVATION',
  symbol:obj.symbol,
  sourceAsOf:new Date(latest.source).toISOString(),
  priceAsOf:new Date(latest.source).toISOString(),
  receivedAt:new Date(latest.sampled).toISOString(),
  // Conservative availability: only after the hash-verified file was read.
  knownAt:new Date(nowMs).toISOString(),
  lastPrice:latest.price,
  receiptSha256:rec.evidenceSha256,
  brokerArrivalCertified:false,productionReady:false,orderTransmission:false
 });
 return Object.freeze({
  schemaId:'ARK_NO11_RSS_SECONDS_ASOF_MARKET_ONLY_V1',
  status:'LOCAL_RSS_SECONDS_ASOF_MARKET_SOURCE_ONLY',
  market,
  localReceiptSha256:rec.evidenceSha256,
  marketSourceFreshnessMs:decision-latest.source,
  originalFrozenSelectorCertified:false,
  originalFrozenFirstEntryCertified:false,
  originalFrozenState9Certified:false,
  originalFrozenH2H3H5Executed:false,
  marketDataRightsCertified:false,
  actualBrokerArrivalCertified:false,
  productionReady:false,orderTransmission:false
 });
}
