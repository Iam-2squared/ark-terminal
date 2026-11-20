/**
 * Experimental READ-ONLY 1-minute RssChart source for a future State9 adapter.
 * Official MSII RSS 2026-03-30 function list pp18,33: RssChart(...,"1M",1..3000).
 * Broker arrival time, original native State9 and BUY/SELL remain UNVERIFIED.
 */
import {createHash} from 'node:crypto';
import {RSS_CHART_COLUMNS} from './msii_rss_chart_observation.mjs';
import {isJpxCashTradingDay,previousJpxCashTradingDays} from './jpx_cash_calendar_2026_2027.mjs';
export const NO12_ONE_MINUTE_SCHEMA='ARK_NO12_MSII_RSS_CHART_1M_OBSERVATION_V1';
export const ONE_MINUTE_REQUEST_BARS=2000;
const fail=s=>{throw Error(s)};
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const epoch=(x,s)=>{
 if(typeof x!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(x)||!Number.isFinite(Date.parse(x)))fail(s);
 return Date.parse(x);
};
const jst=t=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
 year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t)).replace(/\//g,'-');
const num=(v,zero=false)=>{
 if(typeof v!=='number'||!Number.isFinite(v)||(zero?v<0:v<=0))fail('NO12_1M_BAD_OHLCV');
 return v;
};
function readRow(row){
 if(!row||typeof row!=='object'||Array.isArray(row)||row['足種']!=='1M'||
  typeof row['日付']!=='string'||!/^20\d\d\/\d\d\/\d\d$/.test(row['日付'])||
  typeof row['時刻']!=='string'||!/^\d\d:\d\d$/.test(row['時刻']))
  fail('NO12_1M_ROW_SCHEMA_INVALID');
 const at=row['日付'].replaceAll('/','-')+'T'+row['時刻']+':00+09:00';
 const ms=epoch(at,'NO12_1M_ROW_TIME_INVALID');
 if(jst(ms)!==row['日付'].replaceAll('/','-')||ms%60000!==0)
  fail('NO12_1M_ROW_CALENDAR_INVALID');
 const open=num(row['始値']),high=num(row['高値']),low=num(row['安値']),
  close=num(row['終値']),volume=num(row['出来高'],true);
 if(!Number.isSafeInteger(volume)||low>Math.min(open,close)||high<Math.max(open,close)||high<low)
  fail('NO12_1M_OHLCV_INCONSISTENT');
 const day=jst(ms),minute=Number(row['時刻'].slice(0,2))*60+Number(row['時刻'].slice(3));
 if(!((minute>=540&&minute<=690)||(minute>=750&&minute<=930)))
  fail('NO12_1M_OUTSIDE_JPX_MARKET_GRID');
 return {day,at,ms,minute,open,high,low,close,volume};
}
const grid=shift=>{
 const xs=[];
 for(const [a,b] of [[540,690],[750,930]])
  for(let m=a+shift;m<b+shift;m++)xs.push(m);
 return xs;
};
const START=grid(0),END=grid(1);
function coverage(rows){
 const seen=new Set(rows.map(x=>x.minute));
 const match=a=>rows.length===330&&a.every(m=>seen.has(m))&&
  rows.every(x=>a.includes(x.minute));
 return match(START)?'START_LABEL':match(END)?'END_LABEL':'INCOMPLETE';
}
export function inspectNo12OneMinuteObservation({
 snapshot,now=new Date(),decisionAt,requiredPreviousSessions=5
}={}){
 if(snapshot?.schemaId!==NO12_ONE_MINUTE_SCHEMA||
  snapshot.sourceFunction!=='RssChart'||snapshot.period!=='1M'||
  snapshot.evidenceMode!=='OBSERVED_READ_ONLY'||
  snapshot.privateAccountDataIncluded===true||snapshot.excelOrderEnabled===true||
  typeof snapshot.symbol!=='string'||!/^[0-9A-Z]{4}\.T$/.test(snapshot.symbol)||
  !Array.isArray(snapshot.columns)||snapshot.columns.length!==RSS_CHART_COLUMNS.length||
  RSS_CHART_COLUMNS.some((n,i)=>snapshot.columns[i]!==n)||
  !Array.isArray(snapshot.rows)||snapshot.rows.length>3000||
  !Number.isInteger(requiredPreviousSessions)||requiredPreviousSessions<1||
  requiredPreviousSessions>5)
  fail('NO12_1M_SOURCE_CONTRACT_INVALID');
 const captured=epoch(snapshot.capturedAt,'NO12_1M_CAPTURE_INVALID');
 const current=now instanceof Date?now.getTime():epoch(now,'NO12_1M_NOW_INVALID');
 const decision=decisionAt===undefined?captured:epoch(decisionAt,'NO12_1M_DECISION_INVALID');
 if(!Number.isFinite(current)||captured>current+1000||current-captured>30000||
   decision<captured||decision>current+1000)
  fail('NO12_1M_SOURCE_CLOCK_STALE_OR_FUTURE');
 const session=jst(captured),seen=new Set(),byDay=new Map(),unclosed=[];
 for(const raw of snapshot.rows){
  const b=readRow(raw);
  if(seen.has(b.at))fail('NO12_1M_DUPLICATE_BAR');
  seen.add(b.at);
  if(b.day>session)fail('NO12_1M_FUTURE_DAY_BAR');
  if(!isJpxCashTradingDay(b.day))fail('NO12_1M_NON_TRADING_DAY_BAR');
  if(b.ms+60000>captured){unclosed.push(b.at);continue;}
  if(!byDay.has(b.day))byDay.set(b.day,[]);
  byDay.get(b.day).push(b);
 }
 const days=previousJpxCashTradingDays(session,requiredPreviousSessions);
 const perSession=days.map(day=>{
  const bars=byDay.get(day)||[];
  return {day,bars:bars.length,timeLabel:coverage(bars)};
 });
 const conventions=new Set(perSession.map(x=>x.timeLabel));
 const historyComplete=perSession.every(x=>x.bars===330&&x.timeLabel!=='INCOMPLETE')&&
  conventions.size===1;
 const today=(byDay.get(session)||[]).sort((a,b)=>a.ms-b.ms);
 const last=today.at(-1)||null;
 const fresh=last!==null&&decision-(last.ms+60000)>=0&&
  decision-(last.ms+60000)<=180000;
 const sourceBar=fresh?{
  at:last.at,conservativeClosedAt:new Date(last.ms+60000).toISOString(),
  open:last.open,high:last.high,low:last.low,close:last.close,volume:last.volume
 }:null;
 const history=days.flatMap(d=>byDay.get(d)||[]).sort((a,b)=>a.ms-b.ms);
 const safeHistory=history.map(({day,at,open,high,low,close,volume})=>
   ({day,at,open,high,low,close,volume}));
 return Object.freeze({
  schemaId:'ARK_NO12_1M_SOURCE_REVIEW_V1',
  status:sourceBar?'ONE_MINUTE_CLOSED_BAR_LOCAL_OBSERVATION_ONLY':'CURRENT_1M_BAR_UNAVAILABLE',
  historyStatus:historyComplete?'BACKFILL_1M_PREVIOUS_SESSIONS_AVAILABLE':'HISTORY_SOURCE_INCOMPLETE',
  requiredPreviousSessions:days,perSession,
  historyLabelConvention:historyComplete?perSession[0].timeLabel:'UNVERIFIED',
  historyBars:safeHistory.length,historySha256:sha(safeHistory),
  capturedAt:snapshot.capturedAt,symbol:snapshot.symbol,
  currentBar:sourceBar,excludedUnclosedRows:unclosed.length,
  sourceKnownAt:sourceBar?snapshot.capturedAt:null,
  historicalArrivalCertified:false,actualBrokerArrivalCertified:false,
  originalNativeState9Certified:false,originalNativeFirstEntryCertified:false,
  productionReady:false,orderTransmission:false
 });
}
