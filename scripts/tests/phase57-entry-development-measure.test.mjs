import test from 'node:test';
import assert from 'node:assert/strict';
import {labels,stateful} from '../lib/phase57-entry-development-measure.mjs';
import {FEATURES} from '../lib/phase57-minimal-stateful-entry.mjs';
import {developmentUniverse} from '../lib/phase57-entry-development-universe.mjs';
test('issue-code collision cannot contaminate common-issue bars or metadata',()=>{
 const common={sourceCode:'25930',symbol:'2593.T',marketCode:'0111',productCategory:'011',sector:'common'};
 const other={...common,sourceCode:'25935',sector:'other'};
 const bar={sourceCode:common.sourceCode,symbol:common.symbol,close:100};
 const source={members:['2593.T'],master:[common,other],bars:[bar,{...bar,sourceCode:other.sourceCode,close:200}]};
 const result=developmentUniverse(source);assert.deepEqual(result.bars,[bar]);assert.equal(result.meta.get('2593.T').sector,'common');
 assert.throws(()=>developmentUniverse({...source,members:[]}),/ADMISSION_MEMBER_SET_MISMATCH/);
 const alias={...common,sourceCode:'2593'};
 assert.throws(()=>developmentUniverse({...source,master:[common,alias],bars:[bar,{...bar,sourceCode:'2593'}]}),/AMBIGUOUS_COMMON_ISSUE_SYMBOL/);
});
test('future labels use exact same-session grid and5bps; missing stays missing',()=>{
 const e={sessionDate:'2025-10-09',decisionTimestamp:'2025-10-09T01:00:00.000Z',priceReference:100};
 const b=Array.from({length:3},(_,i)=>({sessionDate:e.sessionDate,timestamp:new Date(Date.parse(e.decisionTimestamp)+i*300000).toISOString(),availableAt:new Date(Date.parse(e.decisionTimestamp)+(i+1)*300000).toISOString(),open:100,high:102,low:99,close:101,volume:10}));
 const y=labels(e,b);assert(Math.abs(y[3].LONG.net-95)<1e-9);assert.equal(y[6],null);assert.equal(labels(e,b.slice(1))[3],null);
});
test('late-day labels never use following session',()=>{assert.equal(labels({sessionDate:'2025-10-09',decisionTimestamp:'2025-10-09T06:30:00.000Z',priceReference:100},[])[1],null);});
test('state input rejects outcome-bearing objects',()=>assert.throws(()=>stateful([{eventId:'x',labels:{}}],{},0.5),/OUTCOME_IN_STATE_INPUT/));
test('one ENTER per symbol-session; label availability is not a decision input',()=>{
 const row=d=>({features:Object.fromEntries(FEATURES.map(k=>[k,k==='direction'?d:0]))});
 const e={symbolSessionId:'x',stateBefore:'WATCHING',directionFeatures:[row(1),row(-1)]};
 const model={weights:FEATURES.map(k=>k==='direction'?1:0),intercept:0,means:FEATURES.map(()=>0),scales:FEATURES.map(()=>1)};
 const r=stateful([{...e,eventId:'1'},{...e,eventId:'2'}],model,0.5);assert.equal(r.entered,1);assert.equal(r.noAction,1);
});
