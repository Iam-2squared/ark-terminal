import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeNo12HistoricalChart as warm,DEFAULT_RSS_HISTORY_BARS} from '../runtime/rss_5m_history_bootstrap.mjs';
import {NO12_CHART_SCHEMA,RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
const capture='2026-10-13T09:16:00+09:00';
const past=['2026/10/05','2026/10/06','2026/10/07','2026/10/08','2026/10/09'];
const five=(n)=>String(n).padStart(2,'0');
const bar=(day,h,m,close=1000)=>({
 '銘柄名称':'TEST','市場名称':'東証','足種':'5M','日付':day,
 '時刻':five(h)+':'+five(m),'始値':close,'高値':close+1,
 '安値':close-1,'終値':close,'出来高':1000
});
function fixture(){
 const rows=[];
 for(const day of past){
  for(let minute=540;minute<690;minute+=5)rows.push(bar(day,Math.floor(minute/60),minute%60));
  for(let minute=750;minute<930;minute+=5)rows.push(bar(day,Math.floor(minute/60),minute%60));
 }
 rows.push(bar('2026/10/13',9,0),bar('2026/10/13',9,5),bar('2026/10/13',9,15));
 const snapshot={schemaId:NO12_CHART_SCHEMA,sourceFunction:'RssChart',period:'5M',
  evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',capturedAt:capture,
  columns:[...RSS_CHART_COLUMNS],rows,privateAccountDataIncluded:false};
 return {snapshot,now:new Date('2026-10-13T09:16:00+09:00')};
}
test('five prior complete 66-bar market sessions are available immediately on Tue startup',()=>{
 assert.equal(DEFAULT_RSS_HISTORY_BARS,500);
 const r=warm(fixture());
 assert.equal(r.status,'BACKFILL_5M_PREVIOUS_SESSIONS_AVAILABLE');
 assert.equal(r.observedSessions,5);
 assert.equal(r.historyRows.length,330);
 assert.equal(r.unclosedRowsExcluded,1);
 assert.deepEqual(r.selectedSessionIds,past.map(x=>x.replaceAll('/','-')));
 assert.equal(r.historicalBrokerArrivalProven,false);
 assert.equal(r.productionReady,false);assert.equal(r.orderTransmission,false);
});
test('partial same-day session is not counted as one of five PREVIOUS sessions',()=>{
 const r=warm(fixture());assert.equal(r.perSession.length,5);
 assert(r.perSession.every(x=>x.closedBars===66&&x.gaps===0));
 assert(!r.selectedSessionIds.includes('2026-10-13'));
});
test('missing one previous session is incomplete, not substituted with an old day',()=>{
 const x=fixture();x.snapshot.rows=x.snapshot.rows.filter(r=>r['日付']!=='2026/10/05');
 const r=warm(x);assert.equal(r.status,'HISTORY_SOURCE_INCOMPLETE');
 assert.equal(r.observedSessions,4);
});
test('a missing interval in recent session fails coverage rather than filling invented candles',()=>{
 const x=fixture();x.snapshot.rows=x.snapshot.rows.filter(
  r=>!(r['日付']==='2026/10/09'&&r['時刻']==='10:00'));
 const r=warm(x);
 assert.equal(r.status,'HISTORY_SOURCE_INCOMPLETE');
 assert.equal(r.perSession[0].gaps,1);
});
test('duplicate, invalid OHLC and future source timestamps fail closed',()=>{
 let x=fixture();x.snapshot.rows.push({...x.snapshot.rows[0]});
 assert.throws(()=>warm(x),/NO12_HISTORY_DUPLICATE_BAR_TIME/);
 x=fixture();x.snapshot.rows[1]['高値']=0;
 assert.throws(()=>warm(x),/NO12_HISTORY_INVALID_OHLCV/);
 x=fixture();x.snapshot.rows[2]['時刻']='09:02';
 assert.throws(()=>warm(x),/NO12_HISTORY_NOT_REGULAR_5M_MARKET_BAR/);
 x=fixture();x.snapshot.capturedAt='2026-10-13T09:10:00+09:00';
 assert.throws(()=>warm(x),/NO12_HISTORY_CAPTURE_IS_STALE/);
});
test('holiday and overnight gaps are not fabricated as active trading bars',()=>{
 const r=warm(fixture());
 assert.equal(r.perSession.at(0).day,'2026-10-09');
 assert.equal(r.historyRows.length,330);
 assert(r.historyRows.every(x=>x.day!=='2026-10-12'));
});
test('history backfill cannot be relabelled an original live market or strategy input',()=>{
 const x=fixture();x.snapshot.excelOrderEnabled=true;
 assert.throws(()=>warm(x),/NO12_HISTORY_SOURCE_CONTRACT_INVALID/);
 const y=warm(fixture());
 assert.equal(y.originalNativeFirstEntryCertified,false);
 assert.equal(y.originalFrozenSelectorCertified,false);
 assert.equal(y.originalNativeState9Certified,false);
});

test('JPX October holiday is skipped in the EXPECTED prior five sessions',async()=>{
 const {previousJpxCashTradingDays,isJpxCashTradingDay}=await import('../runtime/jpx_cash_calendar_2026_2027.mjs');
 assert.equal(isJpxCashTradingDay('2026-10-12'),false);
 assert.equal(isJpxCashTradingDay('2026-10-13'),true);
 assert.deepEqual(previousJpxCashTradingDays('2026-10-13',5),
  ['2026-10-09','2026-10-08','2026-10-07','2026-10-06','2026-10-05']);
 assert.equal(warm(fixture()).expectedPreviousSessions.length,5);
});
test('an older session cannot replace an omitted NEWER required JPX session',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(r=>r['日付']!=='2026/10/08');
 for(const [a,b] of [[540,690],[750,930]])for(let m=a;m<b;m+=5)
  x.snapshot.rows.push(bar('2026/10/02',Math.floor(m/60),m%60));
 const r=warm(x);
 assert.equal(r.status,'HISTORY_SOURCE_INCOMPLETE');
 assert.equal(r.observedSessions,4);
 assert(r.perSession.some(s=>s.day==='2026-10-08'&&s.closedBars===0));
 assert(!r.selectedSessionIds.includes('2026-10-02'));
});
test('missing opening bar or closing bar never counts as a complete session',()=>{
 for(const clock of ['09:00','15:25']){
  const x=fixture();
  x.snapshot.rows=x.snapshot.rows.filter(r=>!(r['日付']==='2026/10/09'&&r['時刻']===clock));
  const r=warm(x);
  assert.equal(r.status,'HISTORY_SOURCE_INCOMPLETE');
  assert.equal(r.perSession[0].closedBars,65);
  assert(r.perSession[0].missingBars>=1);
 }
});
test('60 contiguous bars without opening or close cannot bypass strict full-day gate',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(r=>!(r['日付']==='2026/10/09'&&
   (r['時刻']<'09:15'||r['時刻']>'15:10')));
 const r=warm({...x,minimumBarsPerSession:12});
 assert.equal(r.status,'HISTORY_SOURCE_INCOMPLETE');
 assert(r.perSession[0].closedBars<66);
});
test('complete END-labelled grid is supported without presuming vendor time semantics',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(r=>r['日付']==='2026/10/13');
 for(const day of past)for(const [a,b] of [[545,695],[755,935]])
  for(let m=a;m<b;m+=5)x.snapshot.rows.push(bar(day,Math.floor(m/60),m%60));
 const r=warm(x);
 assert.equal(r.status,'BACKFILL_5M_PREVIOUS_SESSIONS_AVAILABLE');
 assert.equal(r.historyTimeLabelConvention,'END_LABEL');
 assert.equal(r.providerTimeLabelPhysicallyCertified,false);
 assert.equal(r.historicalBrokerArrivalProven,false);
});
test('mixed START and END time grids across prior days cannot pass as one contract',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(r=>r['日付']!=='2026/10/09');
 for(const [a,b] of [[545,695],[755,935]])
  for(let m=a;m<b;m+=5)x.snapshot.rows.push(bar('2026/10/09',Math.floor(m/60),m%60));
 const r=warm(x);
 assert.equal(r.status,'HISTORY_SOURCE_INCOMPLETE');
 assert.equal(r.historyTimeLabelConvention,'UNVERIFIED');
});
test('a weekday JPX cash holiday with fake bars is rejected even if synthetic',()=>{
 const x=fixture();
 x.snapshot.rows.push(bar('2026/10/12',9,0));
 assert.throws(()=>warm(x),/NO12_HISTORY_NON_TRADING_SESSION_BAR/);
});
test('future session bar is rejected BEFORE unfinished-bar exclusion',()=>{
 const x=fixture();
 x.snapshot.rows.push(bar('2026/10/14',9,0));
 assert.throws(()=>warm(x),/NO12_HISTORY_FUTURE_SESSION_BAR/);
});
test('unreviewed calendar year fails closed, never assumes weekday equals session',async()=>{
 const {previousJpxCashTradingDays}=await import('../runtime/jpx_cash_calendar_2026_2027.mjs');
 assert.throws(()=>previousJpxCashTradingDays('2028-04-04',5),/NO12_JPX_CASH_CALENDAR_YEAR_UNPINNED/);
});
