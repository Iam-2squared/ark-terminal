import test from 'node:test';
import assert from 'node:assert/strict';
import {makeNo11RssVaProxyMinuteFeed,RSS_VA_PROXY_RECEIPT}
  from '../runtime/no11_rss_vendor_va_shadow_adapter.mjs';

const day='2026-10-26';
const code='7203.T';
const iso=(h,m,s=8)=>day+'T'+String(h).padStart(2,'0')+':'+
  String(m).padStart(2,'0')+':'+String(s).padStart(2,'0')+'+09:00';
const hhmm=m=>String(9+Math.floor(m/60)).padStart(2,'0')+':'+
  String(m%60).padStart(2,'0');
const market=(m,volume=1000+100*m)=>
 ({symbol:code,marketDate:day,observedEndJst:iso(9,m,8),
 cumulativeVolumeRaw:String(volume),
 cumulativeTurnoverRaw:String(volume*101/1000),
 vendorVolumeWeightedAverage:'101'});
const chart=m=>({
 Date:day,Code:code,Time:hhmm(m),
 O:101,H:102,L:100,C:101,Vo:100,
 knownAtJst:iso(9,m+1,9)
});
function synthetic(n=59){
 return {
  sessionDate:day,decisionAtJst:iso(10,0,0),
  selectedSymbols:[code],
  chartRows:Array.from({length:n},(_,m)=>chart(m)),
  marketObservations:Array.from({length:n+1},(_,m)=>market(m)),
 };
}
test('from 60s bracketed RSS cumulative observations produce Va proxy',()=>{
 const x=makeNo11RssVaProxyMinuteFeed(synthetic());
 assert.equal(x.receipt.schemaId,RSS_VA_PROXY_RECEIPT);
 assert.equal(x.rows.length,59);
 assert.equal(x.rows[0].Date,day);
 assert.equal(x.rows[0].Time,'09:00');
 assert.equal(x.rows[0].Vo,100);
 assert.equal(x.rows[0].Va,10100);
 assert.equal(x.rows[0].knownAtJst,iso(9,1,9));
 assert.equal(x.receipt.nativeExactMinuteVaCertified,false);
 assert.equal(x.receipt.historicalOriginalVaParityNotRequired,true);
 assert.equal(x.receipt.modelInputDistributionChanged,true);
 assert.equal(x.receipt.productionReady,false);
 assert.equal(x.receipt.orderTransmission,false);
});
test('no sell/buy orders and unknown symbols cannot be introduced',()=>{
 const x=synthetic();
 x.chartRows.push({...chart(3),Code:'9999.T'});
 assert.throws(()=>makeNo11RssVaProxyMinuteFeed(x),
   /CHART_BAR_IDENTITY_INVALID/);
});
test('missing market minute never fabricates Va, and mismatched volume drops the bar',()=>{
 let x=synthetic(3);
 x.marketObservations=x.marketObservations.filter(row=>
    row.observedEndJst!==iso(9,2,8));
 const y=makeNo11RssVaProxyMinuteFeed(x);
 assert.equal(y.rows.length,1);
 assert.equal(y.rows[0].Time,'09:00');
 assert.equal(y.receipt.skippedBarsByReason.MISSING_OR_AMBIGUOUS_CUMULATIVE_BRACKET,2);
 x=synthetic(3);
 x.chartRows[1].Vo=99;
 const z=makeNo11RssVaProxyMinuteFeed(x);
 assert.equal(z.rows.length,2);
 assert.match(JSON.stringify(z.receipt.skippedBarsByReason),
   /BLOCKED_CHART_VOLUME_AND_CUMULATIVE_DELTA_MISMATCH/);
});
test('reversed vendor counters, late or duplicate samples cannot create trades',()=>{
 let x=synthetic(2);
 x.marketObservations[1]=market(1,999);
 assert.equal(makeNo11RssVaProxyMinuteFeed(x).rows.length,0);
 x=synthetic(2);
 x.marketObservations[1].observedEndJst=iso(9,1,45);
 const later=makeNo11RssVaProxyMinuteFeed(x);
 assert.equal(later.rows.length,0);
 x=synthetic(2);
 x.marketObservations.push({...x.marketObservations[0]});
 assert.throws(()=>makeNo11RssVaProxyMinuteFeed(x),
   /DUPLICATE_MARKET_RECEIPT_INSTANT/);
});
test('future minute, late bar, malformed bid: automatic exclusion not data synthesis',()=>{
 let x=synthetic(1);
 x.chartRows[0].knownAtJst=iso(10,0,1);
 assert.equal(makeNo11RssVaProxyMinuteFeed(x).rows.length,0);
 x=synthetic(2);
 x.chartRows[0].C=null;
 assert.equal(makeNo11RssVaProxyMinuteFeed(x).rows.length,1);
});
