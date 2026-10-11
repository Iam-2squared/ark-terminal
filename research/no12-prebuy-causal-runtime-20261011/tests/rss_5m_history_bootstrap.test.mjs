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
