/**
 * Read-only 1M -> 5M completed-bar aggregation under one fixed label mode.
 * Deliberately NOT an authenticated native RssChart 5M feed/strategy producer.
 * No ticks, incomplete candles, OHLC interpolation or lookahead.
 */
import {inspectNo12OneMinuteObservation} from './rss_1m_history_observation.mjs';
export const NO12_DERIVED_5M_SCHEMA='ARK_NO12_SYNTHETIC_DERIVED_5M_V1';
const fail=s=>{throw Error(s)};
const ms=(x,label)=>{
 if(typeof x!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(x)||!Number.isFinite(Date.parse(x)))
  fail(label);
 return Date.parse(x);
};
const jstDay=x=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
 year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(x)).replace(/\//g,'-');
const hm=m=>String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0');
function minuteBar(row){
 const day=String(row['日付']??'').replaceAll('/','-');
 const at=day+'T'+String(row['時刻']??'')+':00+09:00';
 const time=ms(at,'NO12_AGG_1M_TIME_INVALID');
 if(jstDay(time)!==day||time%60000!==0)fail('NO12_AGG_1M_CALENDAR_INVALID');
 const fields=['始値','高値','安値','終値','出来高'];
 if(fields.some(k=>typeof row[k]!=='number'||!Number.isFinite(row[k]))||
   row['始値']<=0||row['高値']<=0||row['安値']<=0||row['終値']<=0||
   !Number.isSafeInteger(row['出来高'])||row['出来高']<0||
   row['安値']>Math.min(row['始値'],row['終値'])||
   row['高値']<Math.max(row['始値'],row['終値']))
  fail('NO12_AGG_1M_BAD_OHLCV');
 return {day,at,time,minute:Number(row['時刻'].slice(0,2))*60+Number(row['時刻'].slice(3)),
   open:row['始値'],high:row['高値'],low:row['安値'],close:row['終値'],volume:row['出来高']};
}
export function deriveNo12ClosedFiveMinuteFromOneMinute({
 snapshot,reviewed=null,now=new Date(),maximumAgeMinutes=10
}={}){
 const validation=reviewed??inspectNo12OneMinuteObservation({snapshot,now});
 if(validation?.historyStatus!=='BACKFILL_1M_PREVIOUS_SESSIONS_AVAILABLE'||
   validation?.status!=='ONE_MINUTE_CLOSED_BAR_LOCAL_OBSERVATION_ONLY'||
   !['START_LABEL','END_LABEL'].includes(validation.historyLabelConvention)||
   validation.productionReady!==false||validation.orderTransmission!==false||
   validation.symbol!==snapshot?.symbol||validation.capturedAt!==snapshot?.capturedAt)
  fail('NO12_AGG_1M_SOURCE_NOT_READY');
 if(!Number.isInteger(maximumAgeMinutes)||maximumAgeMinutes<1||maximumAgeMinutes>30)
  fail('NO12_AGG_5M_FRESHNESS_CONFIG_INVALID');
 const label=validation.historyLabelConvention,offset=label==='START_LABEL'?0:1;
 const capture=ms(snapshot.capturedAt,'NO12_AGG_CAPTURE_CLOCK_INVALID');
 const today=jstDay(capture);
 const groups=new Map(),seen=new Set();
 for(const row of snapshot.rows){
  if(row['日付']?.replaceAll('/','-')!==today)continue;
  const b=minuteBar(row);
  if(seen.has(b.at))fail('NO12_AGG_DUPLICATE_ONE_MINUTE');
  seen.add(b.at);
  if(b.time+60000>capture)continue;
  const block=b.minute>=540+offset&&b.minute<690+offset?540:
   b.minute>=750+offset&&b.minute<930+offset?750:null;
  if(block===null)fail('NO12_AGG_OUTSIDE_1M_SESSION');
  const slot=block+5*Math.floor((b.minute-block-offset)/5);
  const key=today+'|'+slot;
  if(!groups.has(key))groups.set(key,{slot,block,rows:[]});
  groups.get(key).rows.push(b);
 }
 const complete=[],gaps=[];
 for(const g of [...groups.values()].sort((a,b)=>a.slot-b.slot)){
  const xs=g.rows.sort((a,b)=>a.minute-b.minute);
  const required=Array.from({length:5},(_,i)=>g.slot+offset+i);
  if(xs.length!==5||required.some((n,i)=>xs[i]?.minute!==n)){
    gaps.push(Object.freeze({slot:hm(g.slot),observedMinutes:xs.length}));
    continue;
  }
  const start=today+'T'+hm(g.slot)+':00+09:00';
  const endTime=ms(start,'NO12_AGG_5M_SLOT_INVALID')+300000;
  if(endTime>capture)continue;
  const sumVolume=xs.reduce((n,x)=>n+x.volume,0);
  if(!Number.isSafeInteger(sumVolume))fail('NO12_AGG_5M_VOLUME_OVERFLOW');
  const timestamp=today+'T'+hm(g.slot+(label==='END_LABEL'?5:0))+':00+09:00';
  complete.push(Object.freeze({timestamp,open:xs[0].open,high:Math.max(...xs.map(x=>x.high)),
   low:Math.min(...xs.map(x=>x.low)),close:xs[4].close,volume:sumVolume,
   sourceKnownAt:snapshot.capturedAt,
   barClosedAt:new Date(endTime).toISOString(),barLabelConvention:label}));
 }
 const latest=complete.at(-1)||null;
 const fresh=latest!==null&&capture-ms(latest.barClosedAt,'NO12_AGG_BAR_CLOSE_INVALID')<=
   maximumAgeMinutes*60000;
 return Object.freeze({schemaId:NO12_DERIVED_5M_SCHEMA,
  status:fresh?'LOCAL_DERIVED_5M_OBSERVED_NOT_PROVIDER_CERTIFIED':'COMPLETE_CURRENT_5M_UNAVAILABLE',
  symbol:snapshot.symbol,asOf:snapshot.capturedAt,
  completedBarCount:complete.length,partialOrMissingFiveMinuteGroups:Object.freeze(gaps),
  bars:Object.freeze(complete),latestBar:fresh?latest:null,
  originalProviderFiveMinuteParityCertified:false,
  historicalBrokerArrivalCertified:false,originalNativeState9Certified:false,
  productionReady:false,orderTransmission:false});
}
