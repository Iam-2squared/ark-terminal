import test from 'node:test';
import assert from 'node:assert/strict';
import {compareNo11SavedChartParity as compare} from '../runtime/no11_saved_chart_parity.mjs';
const stamp=(h,m)=>'2026-10-13T'+String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':00+09:00';
const bar=(h,m,price)=>({label:stamp(h,m),open:price,high:price+1,low:price-1,close:price,volume:100});
const fixture=()=>({
 schemaId:'ARK_NO11_RSS_CHART_DUAL_EVIDENCE_V1',symbol:'7203.T',sourceFunction:'RssChart',
 evidenceMode:'OBSERVED_READ_ONLY',privateAccountDataIncluded:false,
 excelOrderEnabled:false,labelSemanticsCertified:false,brokerArrivalCertified:false,
 originalNativeState9Certified:false,productionReady:false,orderTransmission:false,
 capturedAt:stamp(14,20),
 periods:{
  '1M':{observedAt:stamp(14,19),requestedBars:300,validRows:5,
   rows:[0,1,2,3,4].map(m=>bar(14,m,100+m))},
  '5M':{observedAt:stamp(14,20),requestedBars:100,validRows:1,
   rows:[{label:stamp(14,0),open:100,high:105,low:99,close:104,volume:500}]}
 }
});
test('matching start/start five-bar OHLCV is counted without certification',()=>{
 const r=compare({evidence:fixture(),now:new Date(stamp(14,21))});
 const a=r.combinations.find(x=>x.oneMinuteLabel==='START'&&x.fiveMinuteLabel==='START');
 assert.equal(a.completeGroupsCompared,1);assert.equal(a.matched,1);
 assert.equal(r.frozenState9ParityCertified,false);
 assert.equal(r.sufficientEvidenceToCertifyProviderLabelSemantics,false);
 assert.equal(r.orderTransmission,false);
});
test('OHLCV mismatch is detected, not called a match',()=>{
 const e=fixture();e.periods['5M'].rows[0].volume=400;
 const r=compare({evidence:e,now:new Date(stamp(14,21))});
 assert.equal(r.combinations[0].mismatched,1);
});
test('incomplete minute groups are not compared',()=>{
 const e=fixture();e.periods['1M'].rows.pop();e.periods['1M'].validRows=4;
 const r=compare({evidence:e,now:new Date(stamp(14,21))});
 assert.equal(r.combinations[0].completeGroupsCompared,0);
});
