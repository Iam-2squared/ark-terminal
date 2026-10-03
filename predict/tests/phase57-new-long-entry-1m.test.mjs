import test from 'node:test';
import assert from 'node:assert/strict';
import {MinuteEntry,MINUTE,SPEC,SPEC_SHA,SAFETY,canonical,digest,replayIntent,referenceFill,
  forwardWindow,outcome,pct,evaluateAnchor,aggregate,screen,distribution,frozenExitHandoff}
  from '../long-only/phase57-new-long-entry-1m.mjs';
import {run,validateInput} from '../../scripts/run_phase57_new_long_entry_1m.mjs';
const T=Date.parse('2024-09-17T09:30:00+09:00');
const anchor=(over={})=>({eventId:'synthetic-1',symbol:'TEST0',sessionDate:'2024-09-17',selectedAt:T,
  referencePrice:100,segmentEnd:Date.parse('2024-09-17T11:30:00+09:00'),direction:'LONG',...over});
const bar=(i,o=100,c=100,h=Math.max(o,c)+.1,l=Math.min(o,c)-.1,over={})=>({symbol:'TEST0',
  startAt:T+i*MINUTE,endAt:T+(i+1)*MINUTE,availableAt:T+(i+1)*MINUTE,open:o,high:h,low:l,close:c,...over});
const flat=(n=60)=>Array.from({length:n},(_,i)=>bar(i));
const falling=(n=60)=>Array.from({length:n},(_,i)=>bar(i,100-i*.1,100-(i+1)*.1));
const bullish=(n=60)=>Array.from({length:n},(_,i)=>bar(i,100+i*.1,100+(i+1)*.1));
const input=(bars=flat())=>({schema:'ARK_NEW_LONG_ENTRY_1M_REPLAY_INPUT_V1',dataKind:'SYNTHETIC_TEST',
  barIntervalSeconds:60,candidates:[{anchor:anchor(),bars}]});
const rejected=f=>assert.throws(f);

test('safety always false and no production promotion',()=>{
 assert.equal(Object.keys(SAFETY).length,9);assert.ok(Object.values(SAFETY).every(x=>x===false));
 assert.equal(SPEC.evidence,'UNVALIDATED_RESEARCH_PROTOTYPE');assert.equal(SPEC_SHA,digest(SPEC));
});
test('LONG-only anchor rejects SHORT',()=>rejected(()=>new MinuteEntry(anchor({direction:'SHORT'}))));
test('invalid prices and timestamps are rejected',()=>{
 for(const referencePrice of [0,-1,NaN,Infinity,'100',true])rejected(()=>new MinuteEntry(anchor({referencePrice})));
 rejected(()=>new MinuteEntry(anchor({selectedAt:T+100})));
 rejected(()=>new MinuteEntry(anchor({segmentEnd:T})));
});
test('session mismatch rejected',()=>rejected(()=>new MinuteEntry(anchor({sessionDate:'2024-09-18'}))));
test('constructor does not mutate selector snapshot',()=>{
 const a=anchor();const before=canonical(a);new MinuteEntry(a);assert.equal(canonical(a),before);
});
test('no t0 prediction or old Momentum routing',()=>{
 const e=new MinuteEntry(anchor({Momentum3:-999,score:999,futureWinner:true}));
 assert.equal(e.view().state,'WATCH');assert.equal(e.view().intent,null);
});
test('first bullish closed minute can confirm continuation at +1m',()=>{
 const e=new MinuteEntry(anchor());const s=e.close(bar(0,100,100.5),T+MINUTE);
 assert.equal(s.intent.route,'CONTINUATION');assert.equal(s.intent.eligibleOpenAt,T+MINUTE);
});
test('bearish close above reference is not bullish confirmation',()=>{
 const e=new MinuteEntry(anchor());assert.equal(e.close(bar(0,102,101),T+MINUTE).intent,null);
});
test('flat close does not trigger',()=>assert.equal(replayIntent(anchor(),flat()).state,'EXPIRED'));
test('a LOW dip inside bullish bar is not called a known prior pullback',()=>{
 const e=new MinuteEntry(anchor());const s=e.close(bar(0,100,101,102,95),T+MINUTE);
 assert.equal(s.intent.route,'CONTINUATION');assert.equal(s.pullbackAt,null);
});
test('closed dip arms pullback but cannot buy the same bar',()=>{
 const e=new MinuteEntry(anchor());const s=e.close(bar(0,99,99.5,100,98),T+MINUTE);
 assert.equal(s.state,'PULLBACK');assert.equal(s.intent,null);
});
test('later close over previous high confirms rebound',()=>{
 const e=new MinuteEntry(anchor());e.close(bar(0,100,99,100,98),T+MINUTE);
 const s=e.close(bar(1,99,100.2,100.3,98.9),T+2*MINUTE);
 assert.equal(s.intent.route,'PULLBACK_REBOUND');assert.equal(s.intent.eligibleOpenAt,T+2*MINUTE);
});
test('equal previous high is not a strict break',()=>{
 const e=new MinuteEntry(anchor());e.close(bar(0,100,99,100,98),T+MINUTE);
 assert.equal(e.close(bar(1,99,100,100,98.9),T+2*MINUTE).intent,null);
});
test('subsequent below-reference closes update observation without resetting deadline',()=>{
 const e=new MinuteEntry(anchor());for(let i=0;i<3;i++)e.close(bar(i,99-i,98-i),T+(i+1)*MINUTE);
 assert.equal(e.view().pullbackAt,T+MINUTE);assert.equal(e.view().deadline,T+30*MINUTE);
});
test('bar availability, not retrospective timestamp, governs decisions',()=>{
 const e=new MinuteEntry(anchor()),b=bar(0,100,101,102,99,{availableAt:T+MINUTE+500});
 rejected(()=>e.close(b,T+MINUTE));assert.equal(e.view().intent,null);
 const s=e.close(b,T+MINUTE+500);assert.equal(s.intent.eligibleOpenAt,T+2*MINUTE);
});
test('unclosed or wrong-duration bar rejected',()=>{
 const e=new MinuteEntry(anchor());rejected(()=>e.close(bar(0,100,101),T+100));
 rejected(()=>e.close(bar(0,100,101,102,99,{endAt:T+5*MINUTE,availableAt:T+5*MINUTE}),T+5*MINUTE));
});
test('wrong symbol cannot fill another stock',()=>{
 const e=new MinuteEntry(anchor());rejected(()=>e.close(bar(0,100,101,102,99,{symbol:'OTHER'}),T+MINUTE));
});
test('invalid OHLC is rejected',()=>{
 const e=new MinuteEntry(anchor());rejected(()=>e.close(bar(0,100,101,99,98),T+MINUTE));
 rejected(()=>e.close(bar(0,100,101,102,103),T+MINUTE));
});
test('first missing minute makes decision unknown, not safe SKIP',()=>{
 const s=replayIntent(anchor(),[bar(1,100,101)]);assert.equal(s.state,'UNKNOWN');assert.equal(s.intent,null);
});
test('missing between bars never restarts state',()=>{
 const s=replayIntent(anchor(),[bar(0,100,99),bar(2,99,103)]);assert.equal(s.state,'UNKNOWN');
});
test('unexpected future start reports gap',()=>{
 const e=new MinuteEntry(anchor());assert.equal(e.close(bar(2,100,101),T+3*MINUTE).state,'UNKNOWN');
});
test('exact duplicate close is idempotent, revision is rejected',()=>{
 const e=new MinuteEntry(anchor()),b=bar(0,100,99);const s=e.close(b,T+MINUTE);
 assert.deepEqual(e.close(b,T+MINUTE),s);
 rejected(()=>e.close({...b,close:99.1},T+MINUTE));
});
test('duplicate row in offline dataset rejected',()=>rejected(()=>replayIntent(anchor(),[bar(0),bar(0)])));
test('out of order bar rejected without state mutation',()=>{
 const e=new MinuteEntry(anchor());e.close(bar(0),T+MINUTE);e.close(bar(1),T+2*MINUTE);
 const before=e.view();rejected(()=>e.close(bar(0),T+3*MINUTE));assert.deepEqual(e.view(),before);
});
test('watch expires after 30 complete nonconfirming minutes',()=>{
 const s=replayIntent(anchor(),falling());assert.equal(s.state,'EXPIRED');assert.equal(s.intent,null);
});
test('confirmation at watch deadline is allowed when session remains open',()=>{
 const b=flat();b[29]=bar(29,100,101);const s=replayIntent(anchor(),b);
 assert.equal(s.intent.eligibleOpenAt,T+30*MINUTE);
});
test('cannot confirm after watch deadline',()=>{
 const b=bar(0,100,101,102,99,{availableAt:T+31*MINUTE});
 assert.equal(replayIntent(anchor(),[b]).state,'EXPIRED');
});
test('lunch/session boundary does not invent next open',()=>{
 const a=anchor({segmentEnd:T+MINUTE});const s=replayIntent(a,[bar(0,100,101)]);
 assert.equal(s.state,'EXPIRED');assert.equal(s.intent,null);
});
test('truncated observation is UNKNOWN rather than EXPIRE',()=>{
 const e=new MinuteEntry(anchor());e.close(bar(0),T+MINUTE);assert.equal(e.finish(T+30*MINUTE).state,'UNKNOWN');
});
test('terminal state forbids re-entry',()=>{
 const e=new MinuteEntry(anchor());const s=e.close(bar(0,100,101),T+MINUTE);
 assert.deepEqual(e.close(bar(1,101,90),T+2*MINUTE),s);
});
test('snapshot roundtrip preserves next decision',()=>{
 const e=new MinuteEntry(anchor());e.close(bar(0,100,99),T+MINUTE);
 const restored=MinuteEntry.restore(JSON.parse(JSON.stringify(e.snapshot()))),b=bar(1,99,101);
 assert.deepEqual(restored.close(b,T+2*MINUTE),e.close(b,T+2*MINUTE));
});
test('snapshot corruption rejected',()=>{
 const e=new MinuteEntry(anchor()),s=e.snapshot();s.payload.anchor.referencePrice=1;
 rejected(()=>MinuteEntry.restore(s));
});
test('returned state cannot mutate engine',()=>{
 const e=new MinuteEntry(anchor()),v=e.view();v.anchor.referencePrice=1;v.trace.push({});
 assert.equal(e.view().anchor.referencePrice,100);assert.equal(e.view().trace.length,0);
});
test('future label and noninput attributes cannot affect decision',()=>{
 const a=anchor(),b=bar(0,100,101),e=new MinuteEntry(a),f=new MinuteEntry({...a,futurePnL:-999});
 assert.deepEqual(e.close(b,T+MINUTE),f.close({...b,futureMFE:1e9,score:999,volume:999},T+MINUTE));
});
test('suffix poisoning preserves decision on 200 deterministic synthetic paths',()=>{
 for(let j=0;j<200;j++){
  const b=bullish(60),s=replayIntent(anchor(),b);
  const altered=b.map((r,i)=>i<1?r:bar(i,200+j,201+j,300+j,1));
  assert.deepEqual(replayIntent(anchor(),altered),s);
 }
});
test('reference fill uses only next OPEN, never signal LOW/HIGH',()=>{
 const a=anchor(),b=[bar(0,100,101,110,90),bar(1,103,104,200,1)],s=replayIntent(a,b);
 const f=referenceFill(a,s.intent,b);assert.equal(f.price,103);assert.equal(f.at,T+MINUTE);
 const r=[b[0],{...b[1],high:1e8,low:.01,close:150}];assert.deepEqual(referenceFill(a,s.intent,r),f);
});
test('missing expected open is not replaced by later bar',()=>{
 const a=anchor(),s=replayIntent(a,[bar(0,100,101)]);
 assert.equal(referenceFill(a,s.intent,[bar(2,111,112)]).status,'UNKNOWN_NEXT_OPEN');
});
test('one-minute latency sensitivity cannot alter entry rule',()=>{
 const a=anchor(),b=bullish(),s=replayIntent(a,b);
 assert.equal(referenceFill(a,s.intent,b,1).at,T+2*MINUTE);
 rejected(()=>referenceFill(a,s.intent,b,2));
});
test('fill after boundary remains unknown',()=>{
 const a=anchor({segmentEnd:T+2*MINUTE}),b=bullish(),s=replayIntent(a,b);
 assert.equal(referenceFill(a,s.intent,b,1).status,'UNKNOWN_BOUNDARY');
});
test('forward holding windows have equal 30-minute length',()=>{
 const a=anchor(),b=flat();assert.equal(forwardWindow(a,b,T,30).length,30);
 assert.equal(forwardWindow(a,b,T+30*MINUTE,30).length,30);
 assert.equal(forwardWindow(a,b,T+31*MINUTE,30),null);
});
test('no lunch bridging in evaluation',()=>assert.equal(forwardWindow(anchor({segmentEnd:T+20*MINUTE}),flat(),T,30),null));
test('risk before actual fill is excluded',()=>{
 const a=anchor(),b=flat();b[0]=bar(0,100,101,110,20);b[1]=bar(1,101,102,102.5,100.5);
 const r=evaluateAnchor(a,b);assert.ok(r.baseline30.D30>70);assert.ok(r.challenger30.D30<2);
});
test('price ratios and round-trip reference cost',()=>{
 assert.ok(Math.abs(pct(110,100)-10)<1e-10);rejected(()=>pct(1,0));
 const f={status:'REFERENCE_FILLED',price:100};const q=outcome([bar(0,100,100,105,98)],f);
 assert.ok(Math.abs(q.D30-2)<1e-10);assert.ok(Math.abs(q.MFE-5)<1e-10);assert.equal(q.netPct,-.05);
});
test('unobserved outcomes stay NULL',()=>{
 const r=evaluateAnchor(anchor(),[bar(0,100,101),bar(1,101,102)]);
 assert.equal(r.challenger30,null);assert.equal(r.challengerCommon,null);assert.equal(r.primaryPanel,false);
});
test('expired trade has no artificial D30 zero',()=>{
 const r=evaluateAnchor(anchor(),flat());assert.equal(r.challenger30,null);assert.equal(r.challenger.price,null);
});
test('aggregate preserves full candidate denominator',()=>{
 const rows=[evaluateAnchor(anchor(),flat()),evaluateAnchor(anchor({eventId:'x',symbol:'X0'}),bullish().map(b=>({...b,symbol:'X0'})))];
 const r=aggregate(rows);assert.equal(r.panel,2);assert.equal(r.entered,1);assert.equal(r.throughput,.5);
});
test('empty metrics remain unknown and cannot pass',()=>{
 const r=aggregate([]);assert.equal(r.baselineD30.mean,null);assert.equal(r.throughput,null);
 assert.equal(screen(r,'HISTORICAL_DEVELOPMENT').verdict,'BLOCKED_NO_PAIRED_MINUTE_EVIDENCE');
});
test('synthetic performance never promotes a candidate',()=>{
 const r=run(input(bullish()));assert.equal(r.result.verdict,'NOT_A_PERFORMANCE_TEST');
 assert.equal(r.result.actualHistoricalTrades,0);assert.equal(r.result.candidateAccepted,false);
});
test('5m input cannot masquerade as 1m data',()=>{
 rejected(()=>validateInput({...input(),barIntervalSeconds:300}));
 rejected(()=>run(input([bar(0,100,101,102,99,{endAt:T+5*MINUTE,availableAt:T+5*MINUTE})])));
});
test('duplicate first symbol-session rejected',()=>{
 const x=input();x.candidates.push({anchor:anchor({eventId:'duplicate'}),bars:flat()});rejected(()=>validateInput(x));
});
test('unbound historical data cannot pass synthetic bypass',()=>rejected(()=>run({...input(),dataKind:'HISTORICAL_DEVELOPMENT'})));
test('exit handoff has no order quantity and all write flags false',()=>{
 const a=anchor(),r=evaluateAnchor(a,bullish()),h=frozenExitHandoff(a,r);
 assert.equal(h.kind,'RESEARCH_ENTRY_REFERENCE');assert.equal(h.direction,'LONG');assert.equal(h.quantity,null);
 assert.deepEqual(h.safety,SAFETY);assert.equal(h.exitPolicyUnchanged,true);
});
test('handoff refuses different identity and no-entry',()=>{
 const a=anchor(),r=evaluateAnchor(a,bullish());rejected(()=>frozenExitHandoff(anchor({eventId:'bad'}),r));
 assert.equal(frozenExitHandoff(a,evaluateAnchor(a,flat())),null);
});
test('canonical hash insensitive to object field order',()=>assert.equal(digest({b:2,a:1}),digest({a:1,b:2})));
test('nonfinite canonical values rejected',()=>rejected(()=>canonical({x:Infinity})));
test('tail statistics include the worst ceil5percent observations',()=>{
 const r=distribution([1,2,3,4,5,6,7,8,9,10]);assert.equal(r.mean,5.5);assert.equal(r.es95,10);assert.equal(r.worst,10);
});

test('runtime rejects backwards availability clock',()=>{
 const e=new MinuteEntry(anchor());
 e.close(bar(0,100,99,100,98,{availableAt:T+3*MINUTE}),T+3*MINUTE);
 rejected(()=>e.close(bar(1,99,99.5),T+2*MINUTE));
});
test('fill time cannot precede intent or selection',()=>{
 rejected(()=>referenceFill(anchor(),{eligibleOpenAt:T-MINUTE},flat()));
 rejected(()=>referenceFill(anchor(),{eligibleOpenAt:T,decisionAt:T+1},flat()));
});
test('tiny positive synthetic sample never certifies an entry',()=>{
 const r=aggregate([evaluateAnchor(anchor(),bullish())]);
 assert.equal(screen(r,'HISTORICAL_DEVELOPMENT').verdict,'INCONCLUSIVE_INSUFFICIENT_SAMPLE');
});
