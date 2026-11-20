import test from 'node:test';
import assert from 'node:assert/strict';
import {makeNo11RssVaProxyMinuteFeed}
  from '../runtime/no11_rss_vendor_va_shadow_adapter.mjs';
import {runOriginalFrozenSelectorShadow}
  from '../runtime/no11_frozen_selector_native_shadow.mjs';
import {OBSERVED_PASS_GATE_ID}
  from '../runtime/no11_observed_pass_watch_gate.mjs';

const day='2026-10-26';
const symbol='7203.T';
const when=(m,s)=>day+'T'+
  String(9+Math.floor(m/60)).padStart(2,'0')+':'+
  String(m%60).padStart(2,'0')+':'+
  String(s).padStart(2,'0')+'+09:00';
const hhmm=m=>String(9+Math.floor(m/60)).padStart(2,'0')+':'+
 String(m%60).padStart(2,'0');

function scenario(){
 const chartRows=[],marketObservations=[];
 let volume=1000,turnover=1000*101;
 marketObservations.push({
  symbol,marketDate:day,observedEndJst:when(0,8),
  cumulativeVolumeRaw:String(volume),
  cumulativeTurnoverRaw:String(turnover),
  vendorVolumeWeightedAverage:String(turnover/volume)
 });
 for(let i=0;i<59;i++){
  const price=100+0.1*i+0.15*Math.sin(i/6),v=105+(i%6);
  chartRows.push({
   Date:day,Code:symbol,Time:hhmm(i),
   O:price-0.02,H:price+0.15,L:price-0.15,C:price,Vo:v,
   knownAtJst:when(i+1,9)
  });
  volume+=v;turnover+=v*price;
  marketObservations.push({
   symbol,marketDate:day,observedEndJst:when(i+1,8),
   cumulativeVolumeRaw:String(volume),
   cumulativeTurnoverRaw:String(turnover),
   vendorVolumeWeightedAverage:String(turnover/volume)
  });
 }
 const feed=makeNo11RssVaProxyMinuteFeed({
  sessionDate:day,decisionAtJst:when(60,0),
  selectedSymbols:[symbol],chartRows,marketObservations
 });
 return feed;
}
const mask={
 schemaId:OBSERVED_PASS_GATE_ID,asOfSession:'2026-10-23',
 observedPassSymbols:[symbol],observedPassCount:1,
 shadowOnly:true,productionReady:false,orderTransmission:false,
 strictNoUnknownFallback:true
};
function run(feed){
 return runOriginalFrozenSelectorShadow({
  sessionDate:day,decisionTimeJst:'10:00',
  mask,sourceReceipt:feed.receipt,
  datedMaster:[{symbol,asOfSession:day,rawPreviousClose:98,
   segment:'PRIME',sector:'01',
   corporateActionsCleared:true,priceBasisVerified:true,
   commonEquity:true}],
  nativeMinuteRows:feed.rows,
  previousWatches:[]
 });
}
test('RSS-derived *approximate* cumulative Va now reaches actual Frozen Ridge',()=>{
 const feed=scenario();
 assert.equal(feed.rows.length,59);
 const result=run(feed);
 assert.equal(result.minuteVaMode,'RSS_MARKET_APPROX_60S');
 assert.equal(result.rssApproximateSourceAdopted,true);
 assert.equal(result.rssMinuteVaIsNotOriginalExact,true);
 assert.equal(result.frozenRidgeParametersUnchanged,true);
 assert.equal(result.frozenSourceFeatureDistributionUnchanged,false);
 assert.equal(result.selected.length,1,JSON.stringify(result.skippedCandidates));
 assert.equal(result.selected[0].symbol,symbol);
 assert.equal(result.orderTransmission,false);
 assert.equal(result.productionReady,false);
});
test('proxy receipt tampering and missing source bars cannot publish a frozen buy',()=>{
 const feed=scenario();
 assert.throws(()=>run({...feed,receipt:{...feed.receipt,
  nativeExactMinuteVaCertified:true}}),/RSS_APPROX_VA_SOURCE_UNUSABLE/);
 assert.throws(()=>run({...feed,receipt:{...feed.receipt,
  derivedMinuteRowsSha256:'0'.repeat(64)}}),/RSS_APPROX_VA_SOURCE_UNUSABLE/);
 const bad=[...feed.rows];
 bad[3]={...bad[3],Va:bad[3].Va+200};
 assert.throws(()=>run({...feed,rows:bad}),/RSS_APPROX_VA_SOURCE_UNUSABLE/);
});
