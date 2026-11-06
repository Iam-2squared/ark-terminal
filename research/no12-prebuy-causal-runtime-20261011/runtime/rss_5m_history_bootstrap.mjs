/**
 * No.1.2 RssChart 5-minute HISTORY BOOTSTRAP, READ ONLY.
 * The official MSII RSS spec (2026-03-30, p18) permits RssChart 1..3000 bars.
 * Past bars fetched today are historical reconstruction, NOT contemporaneous
 * proof of what was actually known at each past decision timestamp.
 */
import {createHash} from 'node:crypto';
import {NO12_CHART_SCHEMA,RSS_CHART_COLUMNS} from './msii_rss_chart_observation.mjs';
import {isJpxCashTradingDay,previousJpxCashTradingDays} from './jpx_cash_calendar_2026_2027.mjs';

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
// A full normal JPX day has 30 AM + 36 PM five-minute bars. Provider
// timestamps could denote bar OPEN or CLOSE; both complete grids are
// accepted as historical SOURCE SHAPES, never as broker arrival proof.
const slotGrid=offset=>{
  const result=[];
  for(const [start,end] of [[540,690],[750,930]])
    for(let minute=start+offset;minute<end+offset;minute+=5)result.push(minute);
  return result;
};
const START_GRID=slotGrid(0),END_GRID=slotGrid(5);
const coverage=(rows,grid)=>{
  const expected=new Set(grid),actual=new Set(rows.map(r=>r.minute));
  return {
    missingBars:grid.filter(minute=>!actual.has(minute)).length,
    unexpectedBars:rows.filter(r=>!expected.has(r.minute)).length
  };
};
const fullSessionCoverage=rows=>{
  const start=coverage(rows,START_GRID),end=coverage(rows,END_GRID);
  const startExact=rows.length===66&&start.missingBars===0&&start.unexpectedBars===0;
  const endExact=rows.length===66&&end.missingBars===0&&end.unexpectedBars===0;
  return {
    labelMode:startExact?'START_LABEL':endExact?'END_LABEL':'UNVERIFIED',
    missingBars:Math.min(start.missingBars,end.missingBars),
    unexpectedBars:Math.min(start.unexpectedBars,end.unexpectedBars)
  };
};
export function normalizeNo12HistoricalChart({
  snapshot,now=new Date(),requiredPreviousSessions=DEFAULT_REQUIRED_PREVIOUS_SESSIONS
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
     requiredPreviousSessions>15)
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
    if(day>session)invalid('NO12_HISTORY_FUTURE_SESSION_BAR');
    if(!isJpxCashTradingDay(day))invalid('NO12_HISTORY_NON_TRADING_SESSION_BAR');
    if(when+300000>capture){unclosed.push(stamp);continue;}
    historical.push({day,stamp,minute,open,high,low,close,volume,
      conservativeClosedAt:new Date(when+300000).toISOString()});
  }
  historical.sort((a,b)=>Date.parse(a.stamp)-Date.parse(b.stamp));
  const byDay=new Map();
  for(const bar of historical){
    if(!byDay.has(bar.day))byDay.set(bar.day,[]);
    byDay.get(bar.day).push(bar);
  }
  // Independently derive the REQUIRED sessions from the pinned JPX calendar.
  // A missing newer session must never be replaced by an older observed day.
  const previous=previousJpxCashTradingDays(session,requiredPreviousSessions);
  const perSession=[],selected=[];
  for(const day of previous){
    const rows=byDay.get(day)??[],gaps=[];
    let last=null;
    for(const r of rows){
      const block=r.minute<=690?'AM':'PM';
      if(last&&block===(last.minute<=690?'AM':'PM')&&r.minute-last.minute!==5)
        gaps.push({after:last.stamp,before:r.stamp});
      last=r;
    }
    const c=fullSessionCoverage(rows);
    perSession.push({day,closedBars:rows.length,gaps:gaps.length,...c});
    selected.push(...rows);
  }
  selected.sort((a,b)=>Date.parse(a.stamp)-Date.parse(b.stamp));
  const labelModes=new Set(perSession.map(x=>x.labelMode));
  const enough=perSession.every(x=>x.closedBars===66&&x.gaps===0&&
    x.missingBars===0&&x.unexpectedBars===0&&x.labelMode!=='UNVERIFIED')&&
    labelModes.size===1;
  const dateSet=selected.map(x=>x.day);
  const result={
    schemaId:HISTORY_SCHEMA,
    status:enough?'BACKFILL_5M_PREVIOUS_SESSIONS_AVAILABLE':'HISTORY_SOURCE_INCOMPLETE',
    symbol:snapshot.symbol,observedAt:snapshot.capturedAt,
    observedSessions:perSession.filter(x=>x.closedBars>0).length,requiredPreviousSessions,
    expectedPreviousSessions:previous,
    historyTimeLabelConvention:enough?perSession[0].labelMode:'UNVERIFIED',
    providerTimeLabelPhysicallyCertified:false,
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
