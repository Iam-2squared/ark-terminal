import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {advanceReceivedPipeline,MASTER,pinCollectedWatches,restoreCheckpoint}
  from '../tools/no11_received_pipeline_tick.mjs';
import {makeNo11G1Chart50Plan} from '../runtime/no11_rss_chart_50_prescreen.mjs';
import {OBSERVED_PASS_GATE_ID} from '../runtime/no11_observed_pass_watch_gate.mjs';
import {CAPTURE_SCHEMA} from '../tools/no11_import_chart50_continuous_snapshot.mjs';
import {runOriginalFrozenSelectorShadow} from '../runtime/no11_frozen_selector_native_shadow.mjs';
const day='2026-10-26',code='7203.T';
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const at=(n,s=15,ms=200)=>day+'T'+String(9+Math.floor(n/60)).padStart(2,'0')+':'+
  String(n%60).padStart(2,'0')+':'+String(s).padStart(2,'0')+'.'+String(ms).padStart(3,'0')+'+09:00';
function source(){
  const mask={schemaId:OBSERVED_PASS_GATE_ID,asOfSession:'2026-10-23',planId:'b'.repeat(64),
    observedPassSymbols:[code],observedPassCount:1,strictNoUnknownFallback:true,
    shadowOnly:true,productionReady:false,orderTransmission:false};
  const chartPlan=makeNo11G1Chart50Plan({mask,sessionDate:day,
    priorityRows:[{symbol:code,minMarginPct:1,meanMarginPct:2}]});
  const master={schemaId:MASTER,sessionDate:day,knownAtJst:at(-1,0,0),
    rows:[{symbol:code,asOfSession:day,rawPreviousClose:98,segment:'PRIME',sector:'01',
      corporateActionsCleared:true,priceBasisVerified:true,commonEquity:true}],
    productionReady:false,orderTransmission:false};
  // Explicit same-session receipt, before the first decision.
  master.knownAtJst=day+'T08:55:00.000+09:00';
  let volume=1000,turnover=101000;
  const snapshots=[];
  for(let n=0;n<=360;n++){
    const p=100+.025*(n-1)+.1*Math.sin((n-1)/5);
    if(n){volume+=100;turnover+=100*p;}
    const payload={schemaId:CAPTURE_SCHEMA,sessionDate:day,
      chartPlanSha256:chartPlan.planSha256,selectedSymbols:[code],
      source:'RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY',
      marketObservedAtJst:at(n,8,456),observedEndJst:at(n),
      marketObservations:[{symbol:code,marketDate:day,cumulativeVolumeRaw:String(volume),
        cumulativeTurnoverRaw:String(turnover),vendorVolumeWeightedAverage:String(turnover/volume)}],
      chartRows:n?[{Date:day,Code:code,Time:at(n-1).slice(11,16),O:p-.02,H:p+.2,L:p-.2,C:p,
        Vo:100,knownAtJst:at(n,9,123)}]:[],
      shadowOnly:true,productionReady:false,orderTransmission:false};
    snapshots.push({sha256:sha(payload),payload});
  }
  return {sessionDate:day,chartPlan,mask,master,snapshots};
}
function tick(s,end,previous=null,start=0){
  return advanceReceivedPipeline({...s,previous,incoming:s.snapshots.slice(start,end+1),throughJst:at(end,20)});
}
test('incremental physical-shaped receipts reach actual Frozen Ridge with milliseconds',()=>{
  const s=source(),r=tick(s,60);
  assert.equal(r.state.rows.length,60);
  assert.equal(r.summary.executedSlots,1);
  assert.equal(r.summary.missedSlots,1);
  const e=r.selectorEnvelopes[0];
  assert.equal(e.payload.decisionTimestamp,day+'T10:00:00+09:00');
  assert.equal(e.receivedAtJst,at(60,20));
  assert.equal(e.payload.evaluatedAtJst,at(60,20));
  assert.equal(e.payload.selected.length,1,JSON.stringify(e.payload.skippedCandidates));
  assert.equal(e.payload.frozenRidgeParametersUnchanged,true);
  assert.equal(r.state.orderTransmission,false);
});
test('same snapshot prefix and restart never select the same clock twice',()=>{
  const s=source(),a=tick(s,60);
  const b=advanceReceivedPipeline({...s,previous:a.state,incoming:[],throughJst:at(60,25)});
  assert.equal(b.selectorEnvelopes.length,1);
  assert.deepEqual(b.selectorEnvelopes,a.selectorEnvelopes);
  assert.equal(b.state.watches[0].refreshCount,0);
  assert.equal(b.state.rows.length,a.state.rows.length);
});
test('first refresh is 0 to 1, chart Watch is pinned without changing collected universe',()=>{
  const s=source(),a=tick(s,60),b=tick(s,90,a.state,61);
  assert.equal(b.state.watches[0].refreshCount,1);
  assert.equal(b.state.watches[0].firstSelectedAtJst,day+'T10:00:00+09:00');
  const p=pinCollectedWatches(s.chartPlan,a.state.watches,s.mask);
  assert.deepEqual(p.allRequestedChartSymbols,s.chartPlan.allRequestedChartSymbols);
  assert.ok(p.protectedChartSymbols.includes(code));
  assert.ok(p.activeWatchSymbols.includes(code));
  assert.equal(p.totalChartFunctionsBudgeted,1);
});
test('all original ten times run once in an observed synthetic day, no new clock',()=>{
  const s=source();let previous=null,start=0,last;
  for(const n of [30,60,90,120,150,240,270,300,330,360]){
    last=tick(s,n,previous,start);previous=last.state;start=n+1;
  }
  assert.equal(last.summary.executedSlots,10);
  assert.equal(last.summary.missedSlots,0);
  assert.equal(last.selectorEnvelopes.length,10);
  assert.equal(new Set(last.selectorEnvelopes.map(e=>e.payload.decisionTimestamp)).size,10);
  assert.ok(last.selectorEnvelopes.every(e=>e.payload.selected.length<=5));
});
test('late startup marks elapsed slots missed instead of backdating results',()=>{
  const s=source(),r=tick(s,66);
  assert.equal(r.summary.executedSlots,0);
  assert.equal(r.summary.missedSlots,2);
  assert.deepEqual(r.selectorEnvelopes,[]);
});
test('a new bar beyond scheduled cutoff cannot enter delayed selector evaluation',()=>{
  const s=source();
  const r=advanceReceivedPipeline({...s,incoming:s.snapshots.slice(0,62),throughJst:at(61,20)});
  assert.equal(r.state.rows.length,61);
  const e=r.selectorEnvelopes.find(e=>e.payload.decisionTimestamp.endsWith('T10:00:00+09:00'));
  assert.ok(e);
  assert.equal(e.payload.nativeMinuteRowsInspected,60);
});
test('new snapshot timestamps cannot be in the future',()=>{
  const s=source();
  assert.throws(()=>advanceReceivedPipeline({...s,incoming:s.snapshots.slice(0,62),throughJst:at(60,20)}),
    /CAPTURE_HEADER_OR_CLOCK_INVALID/);
});
test('revision of a previously used closed bar fails instead of rewriting the past',()=>{
  const s=source(),a=tick(s,60),bad=structuredClone(s.snapshots[61]);
  bad.payload.chartRows.push({...a.state.rows[0],C:a.state.rows[0].C+.01,knownAtJst:at(61,9)});
  bad.sha256=sha(bad.payload);
  assert.throws(()=>advanceReceivedPipeline({...s,previous:a.state,incoming:[bad],throughJst:at(61,20)}),
    /USED_CLOSED_BAR_REVISED/);
});
test('checkpoint mutation, input-master change and reversed service clock are rejected',()=>{
  const s=source(),a=tick(s,60),bad=structuredClone(a.state);
  bad.rows[0].Va+=10;
  assert.throws(()=>advanceReceivedPipeline({...s,previous:bad,throughJst:at(61,20)}),/CHECKPOINT_CHANGED/);
  const master=structuredClone(s.master);master.rows[0].rawPreviousClose=90;
  assert.throws(()=>advanceReceivedPipeline({...s,master,previous:a.state,throughJst:at(61,20)}),/CHECKPOINT_CHANGED/);
  assert.throws(()=>advanceReceivedPipeline({...s,previous:a.state,throughJst:at(59,20)}),/PROCESS_CLOCK_REVERSED/);
});
test('metadata missing cannot be fabricated for native selector',()=>{
  const s=source();s.master.rows[0].corporateActionsCleared=false;
  assert.throws(()=>tick(s,60),/DATED_MASTER_INCOMPLETE/);
});
test('native received-time is opt-in and bounded to ninety seconds',()=>{
  const s=source(),r=tick(s,60),rows=r.feed.rows;
  const a={sessionDate:day,decisionTimeJst:'10:00',mask:s.mask,chartPlan:s.chartPlan,
    datedMaster:s.master.rows,sourceReceipt:r.feed.receipt.proxyReceipt,nativeMinuteRows:rows};
  assert.throws(()=>runOriginalFrozenSelectorShadow(a),/RSS_APPROX_VA_SOURCE_UNUSABLE/);
  assert.throws(()=>runOriginalFrozenSelectorShadow({...a,evaluatedAtJst:at(61,31)}),/EVALUATION_CLOCK_INVALID/);
  const input=structuredClone(a);input.evaluatedAtJst=at(60,20);
  input.nativeMinuteRows.at(-1).knownAtJst=at(60,21);
  input.sourceReceipt.derivedMinuteRowsSha256=sha(input.nativeMinuteRows);
  assert.throws(()=>runOriginalFrozenSelectorShadow(input),/MINUTE_NOT_CAUSAL_OR_NOT_OBSERVED/);
});
test('processing that finishes outside grace emits no delayed Watch or candidate',()=>{
  const s=source();
  const r=advanceReceivedPipeline({...s,incoming:s.snapshots.slice(0,61),throughJst:at(60,20),
    completionClock:()=>at(61,31)});
  assert.equal(r.selectorEnvelopes.length,0);
  assert.ok(r.state.slots.some(x=>x.status==='MISSED_PROCESSING_DEADLINE'));
});
test('source gap is omitted rather than invented as zero turnover or a fake bar',()=>{
  const s=source();
  const r=advanceReceivedPipeline({...s,incoming:[s.snapshots[0],s.snapshots[3]],throughJst:at(3,20)});
  assert.equal(r.state.rows.length,0);
  assert.equal(r.selectorEnvelopes.length,0);
});
