import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectNo12OneMinuteObservation as inspect,NO12_ONE_MINUTE_SCHEMA,
 ONE_MINUTE_REQUEST_BARS} from '../runtime/rss_1m_history_observation.mjs';
import {RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
const past=['2026/10/05','2026/10/06','2026/10/07','2026/10/08','2026/10/09'];
const stamp=m=>String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0');
const bar=(day,m,p=1000)=>({'銘柄名称':'fixture','市場名称':'東証','足種':'1M',
 '日付':day,'時刻':stamp(m),'始値':p,'高値':p+2,'安値':p-2,
 '終値':p,'出来高':1000});
function fixture(shift=0){
 const rows=[];
 for(const day of past)for(const [a,b] of [[540,690],[750,930]])
  for(let m=a+shift;m<b+shift;m++)rows.push(bar(day,m));
 rows.push(bar('2026/10/13',554),bar('2026/10/13',555));
 return {snapshot:{schemaId:NO12_ONE_MINUTE_SCHEMA,sourceFunction:'RssChart',
  period:'1M',evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
  columns:[...RSS_CHART_COLUMNS],capturedAt:'2026-10-13T09:16:00+09:00',
  privateAccountDataIncluded:false,rows},
  now:new Date('2026-10-13T09:16:01+09:00')};
}
test('1M is the published RssChart period and 2000 bars covers a 5-session bootstrap',()=>{
 const x=fixture();const r=inspect(x);
 assert.equal(ONE_MINUTE_REQUEST_BARS,2000);
 assert.equal(r.status,'ONE_MINUTE_CLOSED_BAR_LOCAL_OBSERVATION_ONLY');
 assert.equal(r.historyStatus,'BACKFILL_1M_PREVIOUS_SESSIONS_AVAILABLE');
 assert.equal(r.historyBars,1650);
 assert.deepEqual(r.perSession.map(s=>s.bars),[330,330,330,330,330]);
 assert.equal(r.historyLabelConvention,'START_LABEL');
 assert.equal(r.currentBar.at,'2026-10-13T09:15:00+09:00');
 assert.equal(r.sourceKnownAt,x.snapshot.capturedAt);
 assert.equal(r.actualBrokerArrivalCertified,false);
 assert.equal(r.originalNativeState9Certified,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
});
test('fully end-labelled 1M history remains recognized only as a source shape',()=>{
 const r=inspect(fixture(1));
 assert.equal(r.historyStatus,'BACKFILL_1M_PREVIOUS_SESSIONS_AVAILABLE');
 assert.equal(r.historyLabelConvention,'END_LABEL');
 assert.equal(r.historicalArrivalCertified,false);
});
test('missing recent session cannot be substituted with an older observed session',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(b=>b['日付']!=='2026/10/08');
 for(const [a,b] of [[540,690],[750,930]])for(let m=a;m<b;m++)
  x.snapshot.rows.push(bar('2026/10/02',m));
 const r=inspect(x);
 assert.equal(r.historyStatus,'HISTORY_SOURCE_INCOMPLETE');
 assert.equal(r.perSession.find(s=>s.day==='2026-10-08').bars,0);
 assert.equal(r.historyBars,1320);
});
test('missing first or last one-minute candle does not pass full-history gate',()=>{
 for(const clock of ['09:00','15:29']){
  const x=fixture();
  x.snapshot.rows=x.snapshot.rows.filter(b=>!(b['日付']==='2026/10/09'&&b['時刻']===clock));
  const r=inspect(x);
  assert.equal(r.historyStatus,'HISTORY_SOURCE_INCOMPLETE');
  assert.equal(r.perSession[0].bars,329);
 }
});
test('mixed START and END label sessions cannot be certified as consistent',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(b=>b['日付']!=='2026/10/09');
 for(const [a,b] of [[541,691],[751,931]])for(let m=a;m<b;m++)
  x.snapshot.rows.push(bar('2026/10/09',m));
 const r=inspect(x);
 assert.equal(r.historyStatus,'HISTORY_SOURCE_INCOMPLETE');
 assert.equal(r.historyLabelConvention,'UNVERIFIED');
});
test('JPX Oct12 holiday and a future-day bar are rejected, not carried into source',()=>{
 const h=fixture();h.snapshot.rows.push(bar('2026/10/12',540));
 assert.throws(()=>inspect(h),/NO12_1M_NON_TRADING_DAY_BAR/);
 const f=fixture();f.snapshot.rows.push(bar('2026/10/14',540));
 assert.throws(()=>inspect(f),/NO12_1M_FUTURE_DAY_BAR/);
});
test('unclosed or absent current bars are not treated as live market truth',()=>{
 const x=fixture();x.snapshot.rows=x.snapshot.rows.filter(b=>b['日付']!=='2026/10/13');
 const r=inspect(x);
 assert.equal(r.status,'CURRENT_1M_BAR_UNAVAILABLE');
 assert.equal(r.currentBar,null);
 const y=fixture();y.snapshot.rows.push(bar('2026/10/13',556));
 const s=inspect(y);
 assert.equal(s.currentBar.at,'2026-10-13T09:15:00+09:00');
 assert.equal(s.excludedUnclosedRows,1);
});
test('duplicate, bad period, invalid OHLC, and stale capture fail closed',()=>{
 const a=fixture();a.snapshot.rows.push({...a.snapshot.rows[0]});
 assert.throws(()=>inspect(a),/NO12_1M_DUPLICATE_BAR/);
 const b=fixture();b.snapshot.period='5M';
 assert.throws(()=>inspect(b),/NO12_1M_SOURCE_CONTRACT_INVALID/);
 const c=fixture();c.snapshot.rows[0]['高値']=0;
 assert.throws(()=>inspect(c),/NO12_1M_BAD_OHLCV/);
 const d=fixture();d.now=new Date('2026-10-13T09:17:00+09:00');
 assert.throws(()=>inspect(d),/NO12_1M_SOURCE_CLOCK_STALE_OR_FUTURE/);
});
test('the source is strictly read-only and not an original state or trading adapter',()=>{
 const x=inspect(fixture());
 assert.equal(x.originalNativeFirstEntryCertified,false);
 assert.equal(x.historicalArrivalCertified,false);
 assert.equal(x.actualBrokerArrivalCertified,false);
 assert.equal(x.productionReady,false);
 assert.equal(x.orderTransmission,false);
});
