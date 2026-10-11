import test from 'node:test';
import assert from 'node:assert/strict';
import {deriveNo12ClosedFiveMinuteFromOneMinute as derive} from '../runtime/no12_1m_to_5m_causal.mjs';
import {NO12_ONE_MINUTE_SCHEMA,inspectNo12OneMinuteObservation} from '../runtime/rss_1m_history_observation.mjs';
import {RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
const past=['2026/10/05','2026/10/06','2026/10/07','2026/10/08','2026/10/09'];
const hm=m=>String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0');
const bar=(d,m,p=1000,v=10)=>({'銘柄名称':'T','市場名称':'東証','足種':'1M',
 '日付':d,'時刻':hm(m),'始値':p,'高値':p+2,'安値':p-2,'終値':p,'出来高':v});
function fixture(shift=0){
 const rows=[];
 for(const d of past)for(const [a,b] of [[540,690],[750,930]])
  for(let m=a+shift;m<b+shift;m++)rows.push(bar(d,m));
 for(let m=550+shift;m<=555+shift;m++)rows.push(bar('2026/10/13',m,1000+m-550-shift));
 return {snapshot:{schemaId:NO12_ONE_MINUTE_SCHEMA,sourceFunction:'RssChart',
  period:'1M',evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
  columns:[...RSS_CHART_COLUMNS],capturedAt:'2026-10-13T09:17:00+09:00',
  privateAccountDataIncluded:false,rows},
  now:new Date('2026-10-13T09:17:01+09:00')};
}
test('five completed 1M candles aggregate to one timestamp-aligned source-only 5M bar',()=>{
 const x=fixture(),r=derive(x);
 assert.equal(r.status,'LOCAL_DERIVED_5M_OBSERVED_NOT_PROVIDER_CERTIFIED');
 assert.equal(r.completedBarCount,1);
 assert.equal(r.latestBar.timestamp,'2026-10-13T09:10:00+09:00');
 assert.equal(r.latestBar.open,1000);
 assert.equal(r.latestBar.high,1006);
 assert.equal(r.latestBar.low,998);
 assert.equal(r.latestBar.close,1004);
 assert.equal(r.latestBar.volume,50);
 assert.equal(r.latestBar.sourceKnownAt,x.snapshot.capturedAt);
 assert.equal(r.latestBar.barClosedAt,'2026-10-13T00:15:00.000Z');
 assert.equal(r.originalProviderFiveMinuteParityCertified,false);
 assert.equal(r.originalNativeState9Certified,false);
 assert.equal(r.orderTransmission,false);
});
test('end-labelled 1M source gives the end-labelled 5M bar, not a lookahead start',()=>{
 const x=fixture(1),r=derive(x);
 assert.equal(r.latestBar.timestamp,'2026-10-13T09:15:00+09:00');
 assert.equal(r.latestBar.barLabelConvention,'END_LABEL');
 assert.equal(r.latestBar.barClosedAt,'2026-10-13T00:15:00.000Z');
});
test('missing 1M interior bar is never interpolated or called a complete 5M candle',()=>{
 const x=fixture(),src=x.snapshot.rows;
 x.snapshot.rows=src.filter(b=>!(b['日付']==='2026/10/13'&&b['時刻']==='09:12'));
 const r=derive(x);
 assert.equal(r.status,'COMPLETE_CURRENT_5M_UNAVAILABLE');
 assert.equal(r.latestBar,null);
 assert.equal(r.completedBarCount,0);
 assert(r.partialOrMissingFiveMinuteGroups.some(v=>v.slot==='09:10'));
});
test('all 5 values in the group must be genuine: do not cross the JPX lunch interval',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(r=>r['日付']!=='2026/10/13');
 for(let m=687;m<690;m++)x.snapshot.rows.push(bar('2026/10/13',m));
 for(let m=750;m<752;m++)x.snapshot.rows.push(bar('2026/10/13',m));
 x.snapshot.capturedAt='2026-10-13T12:34:00+09:00';
 x.now=new Date('2026-10-13T12:34:01+09:00');
 const r=derive(x);
 assert.equal(r.completedBarCount,0);
 assert.equal(r.status,'COMPLETE_CURRENT_5M_UNAVAILABLE');
});
test('reject incomplete previous-session history, mixed or unsupported label semantics',()=>{
 const x=fixture();
 x.snapshot.rows=x.snapshot.rows.filter(r=>!(r['日付']==='2026/10/09'&&r['時刻']==='09:00'));
 assert.throws(()=>derive(x),/NO12_AGG_1M_SOURCE_NOT_READY/);
 const y=fixture();
 const reviewed={...inspectNo12OneMinuteObservation(y),historyLabelConvention:'UNVERIFIED'};
 assert.throws(()=>derive({...y,reviewed}),/NO12_AGG_1M_SOURCE_NOT_READY/);
});
test('reject date/time mismatch, duplicate, broken OHLCV, stale and forged source record',()=>{
 const x=fixture();
 x.snapshot.rows.push({...x.snapshot.rows.at(-1)});
 assert.throws(()=>derive(x),/NO12_1M_DUPLICATE_BAR/);
 const y=fixture();
 const reviewed={...inspectNo12OneMinuteObservation(y),capturedAt:'2026-10-13T09:18:00+09:00'};
 assert.throws(()=>derive({...y,reviewed}),/NO12_AGG_1M_SOURCE_NOT_READY/);
 const z=fixture();
 z.now=new Date('2026-10-13T09:19:00+09:00');
 assert.throws(()=>derive(z),/NO12_1M_SOURCE_CLOCK_STALE_OR_FUTURE/);
});
test('a derivation is never certified as RssChart-vendor identical nor as BUY/SELL input',()=>{
 const r=derive(fixture());
 assert.equal(r.originalProviderFiveMinuteParityCertified,false);
 assert.equal(r.historicalBrokerArrivalCertified,false);
 assert.equal(r.originalNativeState9Certified,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
});
