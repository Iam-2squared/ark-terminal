import test from 'node:test';
import assert from 'node:assert/strict';
import {projectCandidates} from './phase57_msh_entry_v2_paths.mjs';
const e={selectorEventId:'S',symbolSessionId:'2024-10-01|10000',symbol:'10000',sessionDate:'2024-10-01',decisionTimestamp:'2024-10-01T09:30:00+09:00',decisionPrice:100};
const b={symbol:'10000',sessionDate:e.sessionDate,barStartJst:e.decisionTimestamp,availableAtJst:'2024-10-01T09:35:00+09:00',open:100,high:102,low:97,close:101,observedMinutes:2};
test('all candidates retained regardless of label availability or old Entry',()=>{
 const rows=[{...e,label:{labelable:false},oldState:'SKIP'},{...e,selectorEventId:'T',symbol:'20000',label:{labelable:true},oldState:'ENTER'}];
 const p=projectCandidates([b],rows);assert.equal(p.length,2);assert.equal(p[0].future[0].missing,false);assert.equal(p[1].future[0].missing,true);
 assert.equal('label' in p[0],false);assert.equal('oldState' in p[0],false);
});
test('missing slots remain missing, sparse observed minutes disclosed',()=>{
 const p=projectCandidates([b],[e])[0];assert.equal(p.future[0].observedMinutes,2);assert.equal(p.future[1].missing,true);
});
test('lunch and zero remaining calendar use the frozen projector',()=>{
 const rows=[{...e,decisionTimestamp:'2024-10-01T11:30:00+09:00'},{...e,decisionTimestamp:'2024-10-01T15:00:00+09:00'}];
 const p=projectCandidates([],rows);assert.equal(p[0].future[0].minutes,65);assert.equal(p[1].expectedBars,0);
});
test('duplicate or delayed completed bar is an integrity failure',()=>{
 assert.throws(()=>projectCandidates([b,b],[e]),/BAR_IDENTITY/);
 assert.throws(()=>projectCandidates([{...b,availableAtJst:'2024-10-01T09:40:00+09:00'}],[e]),/INVALID_COMPLETED/);
});
