import test from 'node:test';
import assert from 'node:assert/strict';
import {mergeNo11PrivateChartSnapshots,CAPTURE_SCHEMA}
  from '../tools/no11_import_chart50_continuous_snapshot.mjs';
const day='2026-10-26',code='7203.T',hash='a'.repeat(64);
const iso=(h,m,s=8)=>day+'T'+String(h).padStart(2,'0')+':'+
 String(m).padStart(2,'0')+':'+String(s).padStart(2,'0')+'+09:00';
function market(m,vol=1000+100*m){
 return {symbol:code,marketDate:day,cumulativeVolumeRaw:String(vol),
  cumulativeTurnoverRaw:String(vol*101/1000),
  vendorVolumeWeightedAverage:'101'};
}
const bar=(m,changed=false)=>({
 Date:day,Code:code,Time:'09:'+String(m).padStart(2,'0'),
 O:101,H:102,L:100,C:changed?102:101,Vo:100,
 knownAtJst:iso(9,m+1,9)
});
const snap=(m,chartRows=[],marketOverrides={})=>({
 schemaId:CAPTURE_SCHEMA,sessionDate:day,chartPlanSha256:hash,
 selectedSymbols:[code],
 source:'RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY',
 marketObservedAtJst:iso(9,m,8),observedEndJst:iso(9,m,15),
 chartRows,marketObservations:[{...market(m),...marketOverrides}],
 shadowOnly:true,productionReady:false,orderTransmission:false
});
const config=snapshots=>({
 sessionDate:day,decisionAtJst:iso(9,3,0),
 chartPlanSha256:hash,selectedSymbols:[code],snapshots
});
test('realistic three bulk Excel snapshots generate two 1m turnover proxies',()=>{
 const result=mergeNo11PrivateChartSnapshots(config([
  snap(0),
  snap(1,[bar(0)]),
  snap(2,[bar(0),bar(1)])
 ]));
 assert.equal(result.receipt.importedSnapshots,3);
 assert.equal(result.receipt.marketRowsImported,3);
 assert.equal(result.receipt.approximateMinuteVaRows,2);
 assert.equal(result.receipt.duplicateRepeatedChartRows,1);
 assert.equal(result.rows[0].Va,10100);
 assert.equal(result.rows[0].knownAtJst,iso(9,1,9));
 assert.equal(result.rows[1].Time,'09:01');
 assert.equal(result.receipt.orderTransmission,false);
 assert.equal(result.receipt.proxyReceipt.nativeExactMinuteVaCertified,false);
 assert.equal(result.receipt.nativeSelectorExecuted,false);
});
test('revised historical chart bars are invalidated instead of backfilled',()=>{
 const result=mergeNo11PrivateChartSnapshots(config([
  snap(0),
  snap(1,[bar(0)]),
  snap(2,[bar(0,true),bar(1)])
 ]));
 assert.equal(result.receipt.invalidatedRevisedChartRows,1);
 assert.equal(result.rows.length,1);
 assert.equal(result.rows[0].Time,'09:01');
});
test('null source date, market missing or broken cumulative volume never invent Va',()=>{
 const result=mergeNo11PrivateChartSnapshots(config([
  snap(0,[],{marketDate:null}),
  snap(1,[bar(0)]),
  snap(2,[bar(0),bar(1)],{cumulativeVolumeRaw:'bad'})
 ]));
 assert.equal(result.rows.length,0);
 assert.equal(result.receipt.approximateMinuteVaRows,0);
});
test('mismatched plan, source timestamp, symbols and intraday future fail closed',()=>{
 const base=[snap(0),snap(1,[bar(0)])];
 assert.throws(()=>mergeNo11PrivateChartSnapshots(config([
  {...base[0],chartPlanSha256:'f'.repeat(64)},base[1]])),
  /CAPTURE_HEADER_INVALID/);
 assert.throws(()=>mergeNo11PrivateChartSnapshots(config([
  base[0],{...base[1],marketObservedAtJst:iso(9,2,0)}])),
  /MARKET_RECEIPT_CLOCK_INVALID/);
 assert.throws(()=>mergeNo11PrivateChartSnapshots(config([
  base[0],{...base[1],chartRows:[{...bar(0),Code:'9999.T'}]}])),
  /CHART_ROW_IDENTITY_OR_CAUSALITY_INVALID/);
 assert.throws(()=>mergeNo11PrivateChartSnapshots(config([
  base[1],base[0]])),/SNAPSHOT_CLOCK_INVALID/);
});
test('same repeated minute in one workbook snapshot is a malformed capture',()=>{
 const s=snap(1,[bar(0),bar(0)]);
 assert.throws(()=>mergeNo11PrivateChartSnapshots(config([snap(0),s])),
  /DUPLICATE_SAME_SNAPSHOT_CHART/);
});
