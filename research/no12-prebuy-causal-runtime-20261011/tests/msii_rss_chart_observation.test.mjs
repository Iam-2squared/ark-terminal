import test from 'node:test';
import assert from 'node:assert/strict';
import {
 NO12_CHART_SCHEMA,RSS_CHART_COLUMNS,inspectNo12RssChartSnapshot as inspect,
 bindNo12SyntheticChartReference as bind
} from '../runtime/msii_rss_chart_observation.mjs';
const capture='2026-10-13T09:36:10+09:00',decision='2026-10-13T09:36:20+09:00';
function fixture(){
 const bar=(time,close,day='2026/10/13')=>({
   '銘柄名称':'fixture','市場名称':'東証','足種':'5M','日付':day,
   '時刻':time,'始値':close,'高値':close+2,'安値':close-3,
   '終値':close,'出来高':1000
 });
 const snapshot={schemaId:NO12_CHART_SCHEMA,sourceFunction:'RssChart',
  period:'5M',evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
  columns:[...RSS_CHART_COLUMNS],capturedAt:capture,
  rows:[bar('09:25',1010),bar('09:30',1020),bar('09:35',1030)]};
 return {snapshot,decisionAt:decision,now:new Date('2026-10-13T09:36:22+09:00')};
}
test('closed 5M data produces only local observed read-only market record',()=>{
 const f=fixture(),x=inspect(f);
 assert.equal(x.status,'LOCAL_CHART_5M_BAR_OBSERVED_READONLY_NOT_LIVE_CERTIFIED');
 assert.equal(x.symbol,'7203.T');assert.equal(x.bar.close,1020);
 assert.equal(x.inProgressBars,1);assert.equal(x.retainedBars,2);
 assert.equal(x.sourceRecord.knownAt,capture);
 assert.equal(x.sourceRecord.barClosedAt,'2026-10-13T00:35:00.000Z');
 assert.equal(x.actualBrokerFeedArrivalCertified,false);
 assert.equal(x.providerBarLabelSemanticsCertified,false);
 assert.equal(x.nativeState9Certified,false);
 assert.equal(x.productionReady,false);
 assert.equal(x.orderTransmission,false);
});
test('exact normalized OHLCV values and clock contribute to audit receipt',()=>{
 const f=fixture();
 const a=inspect(f),again=inspect(f);
 assert.deepEqual(a,again);
 f.snapshot.rows[1]['終値']=1021;
 const b=inspect(f);
 assert.notEqual(a.sourcePayloadSha256,b.sourcePayloadSha256);
 assert.notEqual(a.sourceFrameSha256,b.sourceFrameSha256);
});
test('unclosed latest bar is not used as available price',()=>{
 const f=fixture();f.snapshot.rows=[f.snapshot.rows[2]];
 const r=inspect(f);
 assert.equal(r.status,'NO_CURRENT_SESSION_COMPLETED_BAR');
 assert.equal(r.sourceRecord,null);assert.equal(r.productionReady,false);
});
test('previous day rows can be observed, but never presented as fresh current-session data',()=>{
 const f=fixture();
 f.snapshot.rows=[{...f.snapshot.rows[0],'日付':'2026/10/09'}];
 const r=inspect(f);
 assert.equal(r.status,'NO_CURRENT_SESSION_COMPLETED_BAR');
 assert.equal(r.retainedBars,1);
});
test('duplicate bar timestamps, impossible O/H/L/C and invalid volume are blocked',()=>{
 const bads=[
  x=>x.snapshot.rows.push({...x.snapshot.rows[0]}),
  x=>x.snapshot.rows[0]['安値']=99999,
  x=>x.snapshot.rows[0]['高値']=1,
  x=>x.snapshot.rows[0]['出来高']=-3,
  x=>x.snapshot.rows[0]['出来高']=3.5,
  x=>x.snapshot.rows[0]['時刻']='99:99'
 ];
 for(const mutate of bads){const x=fixture();mutate(x);assert.throws(()=>inspect(x));}
});
test('source contract requires exactly official 10 columns and 5M chart, never order functions',()=>{
 for(const mutate of [
  x=>x.snapshot.columns.pop(),
  x=>x.snapshot.sourceFunction='RssStockOrder',
  x=>x.snapshot.period='1M',
  x=>x.snapshot.excelOrderEnabled=true,
  x=>x.snapshot.privateAccountDataIncluded=true
 ]){
  const x=fixture();mutate(x);assert.throws(()=>inspect(x),/NO12_CHART_READONLY_SOURCE_CONTRACT_INVALID|NO12_CHART_HEADER_NOT_OFFICIAL/);
 }
});
test('chart reference binding refuses a different symbol, invented price or future observation',()=>{
 const f=fixture(),a=inspect(f),base={symbol:'7203.T',entryId:'first-01',
    referencePrice:1020,firstEntryScore:0.7,firstEntryThreshold:0.5};
 const ok=bind({candidate:base,chartAudit:a,requestedDecisionAt:decision});
 assert.equal(ok.marketRecordId,a.sourceRecord.recordId);
 assert.equal(ok.referencePrice,1020);
 assert.equal(ok.liveNativeDecisionCertified,false);
 assert.throws(()=>bind({candidate:{...base,symbol:'6758.T'},chartAudit:a,requestedDecisionAt:decision}),/SYMBOL_MISMATCH/);
 assert.throws(()=>bind({candidate:{...base,referencePrice:1021},chartAudit:a,requestedDecisionAt:decision}),/PRICE_MISMATCH/);
 assert.throws(()=>bind({candidate:base,chartAudit:a,requestedDecisionAt:'2026-10-13T09:36:09+09:00'}),/NOT_YET_OBSERVED/);
});
test('captured time cannot be backdated/claimed fresh beyond a 30 second observation window',()=>{
 const f=fixture();
 f.now=new Date('2026-10-13T09:37:30+09:00');
 assert.throws(()=>inspect(f),/CLOCK_NOT_FRESH/);
 f.now=new Date('2026-10-13T09:36:22+09:00');
 f.snapshot.capturedAt='2026-10-13T09:36:25+09:00';
 assert.throws(()=>inspect(f),/CLOCK_NOT_FRESH/);
});
