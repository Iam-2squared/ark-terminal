import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {replayFrozenV5Bar5,observeBar5Prefix,V5_BAR5} from './lib/phase57-long-exit-v5-bar5-adapter.mjs';
const base='docs/evidence/phase57-long-exit-v5-fast-track';
const original=fs.readFileSync(`${base}/final-sweep-source.txt`,'utf8');
const box={};vm.createContext(box);
vm.runInContext(original.slice(original.indexOf('const costPct='),original.indexOf('const dd='))+'\nglobalThis.reference=t=>sim(t,5);',box);
const trade=(closes,first=closes[0])=>({direction:'LONG',causalEligible:true,firstBarDirectionalCloseReturnBps:first*100,v4:{netReturnPct:2,exitTimestamp:'SYNTHETIC'},management:{v4:closes.map((x,i)=>({holdingBars:i+1,currentReturnPct:x,timestamp:'SYNTHETIC'}))}});
test('archived final source identity; hard BAR5',()=>{assert.equal(createHash('sha256').update(original).digest('hex'),'209f2857a62c1cb7e655417d2769b952b4b9fa3ce4e3c2e99e4c228d6c9664f7');assert.equal(V5_BAR5.horizon,5);assert.equal(V5_BAR5.costPct,.05);});
test('selected sim(t,5) parity including first non-adverse, reclaim, timeout and early-v4 fallback',()=>{
 for(const c of [[0],[1],[-1,0],[-1,-2,-3,-4,0],[-1,-2,-3,-4,-5,9],[-1,-2]]){
  const t=trade(c),a=replayFrozenV5Bar5(t),b=box.reference(t);assert.equal(a.netReturnPct,b.net);assert.equal(a.reason,b.reason);assert.equal(a.onlineRuntimeClaim,false);
 }
});
test('absent causal v4 blocks even unrecovered five-bar path; no default net',()=>{for(const c of [[1],[-1,0],[-1,-2,-3,-4,-5]]){const t=trade(c);t.causalEligible=false;const a=replayFrozenV5Bar5(t);assert.equal(a.status,'V5_RUNTIME_SEMANTICS_BLOCKED');assert.equal(a.netReturnPct,null);assert.equal(box.reference(t),null);}});
test('no SHORT; invalid/null first price does not coerce to zero',()=>{assert.throws(()=>replayFrozenV5Bar5({...trade([1]),direction:'SHORT'}),/LONG_ONLY/);assert.equal(replayFrozenV5Bar5({direction:'LONG',causalEligible:true,v4:{netReturnPct:1},firstBarDirectionalCloseReturnBps:null}).status,'V5_RUNTIME_SEMANTICS_BLOCKED');});
const event=cs=>({future:cs.map((c,i)=>({slot:i+1,c,minutes:5*(i+1),end:'SYNTHETIC',missing:false}))});
test('prefix preserves state uncertainty and exact bar5 equality',()=>{
 assert.equal(observeBar5Prefix(event([-1,-2,0])).reclaimBar,3);
 assert.equal(observeBar5Prefix(event([-1,-2,-3,-4,0])).reclaimBar,5);
 assert.equal(observeBar5Prefix(event([-1,-2,-3,-4,-5,5])).state,'NO_RECLAIM_THROUGH_BAR5_OBSERVED');
 const e=event([-1,-2,1]);e.future[1].missing=true;assert.equal(observeBar5Prefix(e).state,'UNKNOWN');
 assert.equal(observeBar5Prefix(event([-1])).reason,'SESSION_END_BEFORE_BAR5_REQUIRES_V4');
});
test('prefix cannot inspect prices beyond bar5, and lunch remains elapsed clock',()=>{
 const e=event([-1,-2,-3,-4,-5,99]);const a=observeBar5Prefix(e);e.future[5].c=-99;assert.deepEqual(observeBar5Prefix(e),a);
 const lunch=event([-1,0]);lunch.future[0].minutes=65;lunch.future[1].minutes=70;assert.equal(observeBar5Prefix(lunch).reclaimBar,2);assert.equal(observeBar5Prefix(lunch).reclaimClockMinutes,70);
});
