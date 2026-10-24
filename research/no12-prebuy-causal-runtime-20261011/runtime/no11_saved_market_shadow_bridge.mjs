/**
 * User-observed, saved Ark_No11_MARKET_RSS.xlsx -> PowerShell -> market_shadow_v2.json
 * bridge. Converts only the observed market component to a No.1.1 Shadow
 * envelope. Does NOT connect or execute Frozen Selector/Entry/State9/ML/orders.
 * The market day was inferred from the PC, not certified by MarketSpeed II.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const fail=x=>{throw Error(x)};
const stamp=(s,reason)=>{
 if(typeof s!=='string'||!/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(s)||!Number.isFinite(Date.parse(s)))
  fail(reason);
 return Date.parse(s);
};
const jst=t=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
 year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t)).replaceAll('/','-');
export function inspectSavedNo11MarketShadow({
 snapshot,now=new Date(),maxObservationAgeMs=15000,maxMarketAgeMs=30000
}={}){
 if(!Number.isSafeInteger(maxObservationAgeMs)||maxObservationAgeMs<0||maxObservationAgeMs>15000||
    !Number.isSafeInteger(maxMarketAgeMs)||maxMarketAgeMs<0||maxMarketAgeMs>30000)
  fail('NO11_MARKET_SHADOW_LIMIT_INVALID');
 if(snapshot?.schemaId!=='ARK_NO11_LOCAL_MARKET_SHADOW_V2'||
    snapshot.symbol!=='7203.T'||snapshot.orderTransmission!==false||
    snapshot.productionReady!==false||snapshot.brokerArrivalCertified!==false||
    snapshot.originalNo11DecisionEngineConnected!==false)
  fail('NO11_MARKET_SHADOW_CONTRACT_INVALID');
 if(snapshot.status==='BLOCKED')fail('NO11_MARKET_SHADOW_PRODUCER_BLOCKED');
 if(snapshot.source!=='MarketSpeedII_RssMarket'||
    snapshot.marketDaySource!=='PC_JST_INFERRED_NOT_BROKER_CERTIFIED'||
    snapshot.nonAtomicExcelCellRead!==true||
    !['LOCAL_MARKET_OBSERVED_FRESH','LOCAL_MARKET_OBSERVED_STALE'].includes(snapshot.status))
  fail('NO11_MARKET_SHADOW_SOURCE_UNVERIFIED');
 if(typeof snapshot.price!=='number'||!Number.isFinite(snapshot.price)||snapshot.price<=0||
    typeof snapshot.marketClock!=='string'||!/^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$/.test(snapshot.marketClock))
  fail('NO11_MARKET_SHADOW_PRICE_OR_CLOCK_INVALID');
 const seen=stamp(snapshot.observedAt,'NO11_MARKET_SHADOW_OBSERVED_INVALID');
 const source=stamp(snapshot.sourceAsOf,'NO11_MARKET_SHADOW_SOURCE_INVALID');
 const current=now instanceof Date?now.getTime():stamp(now,'NO11_MARKET_SHADOW_NOW_INVALID');
 if(!Number.isFinite(current)||seen>current+1000||source>seen+1000||
    jst(seen)!==jst(source)||seen>current||
    new Date(source).toLocaleTimeString('en-GB',{timeZone:'Asia/Tokyo',hour12:false})!==snapshot.marketClock)
  fail('NO11_MARKET_SHADOW_CLOCK_INCONSISTENT');
 const age=seen-source;
 if(typeof snapshot.sourceAgeSeconds!=='number'||
    !Number.isFinite(snapshot.sourceAgeSeconds)||
    Math.abs(age/1000-snapshot.sourceAgeSeconds)>0.011)
  fail('NO11_MARKET_SHADOW_AGE_INCONSISTENT');
 const wasFresh=age>=0&&age<=30000;
 if(snapshot.marketFresh!==wasFresh||
    snapshot.status!==(wasFresh?'LOCAL_MARKET_OBSERVED_FRESH':'LOCAL_MARKET_OBSERVED_STALE'))
  fail('NO11_MARKET_SHADOW_STATUS_INCONSISTENT');
 if(current-seen>maxObservationAgeMs)fail('NO11_MARKET_SHADOW_OBSERVATION_STALE');
 if(current-source>maxMarketAgeMs||!wasFresh)
  fail('NO11_MARKET_SHADOW_SOURCE_STALE');
 return Object.freeze({
  schemaId:'ARK_NO11_SAVED_RSS_MARKET_ASOF_ONLY_V1',
  status:'LOCAL_MARKET_ASOF_ONLY_NO_DECISION',
  market:Object.freeze({
   kind:'MARKETSPEED_II_RSS_MARKET_OBSERVATION',
   symbol:snapshot.symbol,
   lastPrice:snapshot.price,
   sourceAsOf:new Date(source).toISOString(),
   priceAsOf:new Date(source).toISOString(),
   receivedAt:new Date(seen).toISOString(),
   // Only the verifier's own clock is a conservative known-at bound.
   knownAt:new Date(current).toISOString(),
   brokerArrivalCertified:false,productionReady:false,orderTransmission:false
  }),
  pcInferredMarketDay:true,nonAtomicExcelCellRead:true,
  sourceHashCertifiedByBroker:false,
  originalFrozenSelectorConnected:false,
  originalFrozenFirstEntryConnected:false,
  originalFrozenState9Connected:false,
  originalFrozenH2H3H5Executed:false,
  originalFrozenCapitalExitConnected:false,
  originalFrozenAsOfGatePassed:false,
  productionReady:false,orderTransmission:false
 });
}
export function readSavedNo11MarketShadow({file,now=new Date()}={}){
 if(typeof file!=='string'||!path.isAbsolute(file)||
    path.basename(file)!=='market_shadow_v2.json')
  fail('NO11_MARKET_SHADOW_FILE_PATH_INVALID');
 const st=fs.lstatSync(file);
 if(!st.isFile()||st.isSymbolicLink()||st.size<50||st.size>10000)
  fail('NO11_MARKET_SHADOW_FILE_UNSAFE');
 const bytes=fs.readFileSync(file);
 const obj=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
 const result=inspectSavedNo11MarketShadow({snapshot:obj,now});
 return Object.freeze({...result,localSnapshotSha256:createHash('sha256').update(bytes).digest('hex')});
}
