/**
 * No.1.2 RssChart 5-minute HISTORY BOOTSTRAP, READ ONLY.
 * The official MSII RSS spec (2026-03-30, p18) permits RssChart 1..3000 bars.
 * Past bars fetched today are historical reconstruction, NOT contemporaneous
 * proof of what was actually known at each past decision timestamp.
 */
import {createHash} from 'node:crypto';
import {NO12_CHART_SCHEMA,RSS_CHART_COLUMNS} from './msii_rss_chart_observation.mjs';

export const HISTORY_SCHEMA='ARK_NO12_RSS_5M_HISTORY_BOOTSTRAP_V1';
export const DEFAULT_RSS_HISTORY_BARS=500;
export const DEFAULT_REQUIRED_PREVIOUS_SESSIONS=5;
const invalid=code=>{throw Error(code)};
const jstDay=d=>new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(d)).replace(/\//g,'-');
const utcMs=(v,label)=>{
  if(typeof v!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(v)||!Number.isFinite(Date.parse(v)))
    invalid(label);
  return Date.parse(v);
};
const sha=b=>createHash('sha256').update(b).digest('hex');
const dayAndMinute=row=>{
  const day=row?.['日付'],hm=row?.['時刻'];
  if(typeof day!=='string'||!(/^\d{4}\/\d\d\/\d\d$/).test(day)||
     typeof hm!=='string'||!(/^\d\d:\d\d$/).test(hm))
    invalid('NO12_HISTORY_DATE_TIME_INVALID');
  const stamp=day.replaceAll('/','-')+'T'+hm+':00+09:00';
  const when=Date.parse(stamp);
  if(!Number.isFinite(when)||jstDay(when)!==day.replaceAll('/','-'))
    invalid('NO12_HISTORY_CALENDAR_INVALID');
  const minute=Number(hm.slice(0,2))*60+Number(hm.slice(3));
  if(minute%5!==0 || !(
    (minute>=540 && minute<=690)||(minute>=750 && minute<=930)
  ))invalid('NO12_HISTORY_NOT_REGULAR_5M_MARKET_BAR');
  const check=new Intl.DateTimeFormat('en-GB',{
    timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
  }).format(new Date(when));
  if(check!==hm)invalid('NO12_HISTORY_CLOCK_INVALID');
  return {day:day.replaceAll('/','-'),stamp,when,minute};
};
const num=(value,allowZero=false)=>{
  if(typeof value!=='number'||!Number.isFinite(value)|| (allowZero?value<0:value<=0))
    invalid('NO12_HISTORY_INVALID_OHLCV');
  return value;
};
export function normalizeNo12HistoricalChart({
  snapshot,now=new Date(),requiredPreviousSessions=DEFAULT_REQUIRED_PREVIOUS_SESSIONS,
  minimumBarsPerSession=60
}={}){
  if(!snapshot||snapshot.schemaId!==NO12_CHART_SCHEMA||snapshot.sourceFunction!=='RssChart'||
    snapshot.period!=='5M'||snapshot.evidenceMode!=='OBSERVED_READ_ONLY'||
    snapshot.privateAccountDataIncluded===true||snapshot.excelOrderEnabled===true||
    !/^[0-9A-Z]{4}\.T$/.test(snapshot.symbol??'')||
    !Array.isArray(snapshot.columns)||snapshot.columns.length!==RSS_CHART_COLUMNS.length||
    RSS_CHART_COLUMNS.some((name,i)=>snapshot.columns[i]!==name))
      invalid('NO12_HISTORY_SOURCE_CONTRACT_INVALID');
  if(!Array.isArray(snapshot.rows)||snapshot.rows.length>3000)
    invalid('NO12_HISTORY_ROWS_INVALID');
  if(!Number.isInteger(requiredPreviousSessions)||requiredPreviousSessions<2||
     requiredPreviousSessions>15||!Number.isInteger(minimumBarsPerSession)||
     minimumBarsPerSession<12||minimumBarsPerSession>66)
    invalid('NO12_HISTORY_COVERAGE_CONFIG_INVALID');
  const capture=utcMs(snapshot.capturedAt,'NO12_HISTORY_CAPTURE_TIME_INVALID');
  const current=now instanceof Date?now.getTime():utcMs(now,'NO12_HISTORY_NOW_INVALID');
  if(!Number.isFinite(current)||capture>current+1000||current-capture>30000)
    invalid('NO12_HISTORY_CAPTURE_IS_STALE');
  const session=jstDay(capture),seen=new Set(),historical=[],unclosed=[];
  for(const row of snapshot.rows){
    if(!row||typeof row!=='object'||Array.isArray(row)||row['足種']!=='5M')
      invalid('NO12_HISTORY_BAR_TYPE_INVALID');
    const {day,stamp,when,minute}=dayAndMinute(row);
    if(seen.has(stamp))invalid('NO12_HISTORY_DUPLICATE_BAR_TIME');
    seen.add(stamp);
    const open=num(row['始値']),high=num(row['高値']),low=num(row['安値']),
      close=num(row['終値']),volume=num(row['出来高'],true);
    if(!Number.isSafeInteger(volume)||low>Math.min(open,close)||
      high<Math.max(open,close)||high<low)
      invalid('NO12_HISTORY_OHLCV_INCONSISTENT');
    // Provider label start-vs-end convention is not yet physically certified;
    // one whole extra 5-minute interval is conservative, not a live time proof.
    if(when+300000>capture){unclosed.push(stamp);continue;}
    if(day>session)invalid('NO12_HISTORY_FUTURE_SESSION_BAR');
    historical.push({day,stamp,minute,open,high,low,close,volume,
      conservativeClosedAt:new Date(when+300000).toISOString()});
  }
  historical.sort((a,b)=>Date.parse(a.stamp)-Date.parse(b.stamp));
  const byDay=new Map();
  for(const bar of historical){
    if(!byDay.has(bar.day))byDay.set(bar.day,[]);
    byDay.get(bar.day).push(bar);
  }
  const days=[...byDay.keys()].sort().reverse();
  const previous=days.filter(day=>day<session).slice(0,requiredPreviousSessions);
  const perSession=[],selected=[];
  for(const day of previous){
    const rows=byDay.get(day),gaps=[];
    let last=null;
    for(const r of rows){
      const block=r.minute<=690?'AM':'PM';
      if(last&&block===(last.minute<=690?'AM':'PM')&&r.minute-last.minute!==5)
        gaps.push({after:last.stamp,before:r.stamp});
      last=r;
    }
    perSession.push({day,closedBars:rows.length,gaps:gaps.length});
    selected.push(...rows);
  }
  selected.sort((a,b)=>Date.parse(a.stamp)-Date.parse(b.stamp));
  const enough=previous.length===requiredPreviousSessions &&
    perSession.every(x=>x.closedBars>=minimumBarsPerSession&&x.gaps===0);
  const dateSet=selected.map(x=>x.day);
  const result={
    schemaId:HISTORY_SCHEMA,
    status:enough?'BACKFILL_5M_PREVIOUS_SESSIONS_AVAILABLE':'HISTORY_SOURCE_INCOMPLETE',
    symbol:snapshot.symbol,observedAt:snapshot.capturedAt,
    observedSessions:previous.length,requiredPreviousSessions,
    perSession,historyRows:selected,unclosedRowsExcluded:unclosed.length,
    selectedSessionIds:[...new Set(dateSet)].sort(),
    historicalBrokerArrivalProven:false,
    originalNativeFirstEntryCertified:false,originalFrozenSelectorCertified:false,
    originalNativeState9Certified:false,
    productionReady:false,orderTransmission:false
  };
  result.historySha256=sha(Buffer.from(JSON.stringify(selected)));
  return Object.freeze(result);
}
