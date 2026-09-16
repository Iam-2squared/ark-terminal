import test from 'node:test';
import assert from 'node:assert/strict';
import {pathFor,pathType,replay} from './phase57_long_exit_architecture_diagnostic.mjs';
const event={decisionTimestamp:'2024-10-01T09:30:00+09:00',decisionPrice:100,sessionDate:'2024-10-01',direction:'LONG'};
function bar(min,open=100,high=101,low=99,close=100){const t=Date.parse('2024-10-01T09:00:00+09:00')+min*60000;return {sessionDate:event.sessionDate,barStartJst:new Date(t).toISOString(),availableAtJst:new Date(t+300000).toISOString(),open,high,low,close,volume:10,observedMinutes:5};}
test('strict horizons detect gap/lunch/end and never fill',()=>{
 assert.equal(pathFor([bar(30)],event,10).reason,'PROVIDER_GAP');
 assert.equal(pathFor([],{...event,decisionTimestamp:'2024-10-01T11:20:00+09:00'},30).reason,'LUNCH_RECESS');
 assert.equal(pathFor([],{...event,decisionTimestamp:'2024-10-01T14:50:00+09:00'},30).reason,'SESSION_BOUNDARY');
});
test('same-bar extrema and recovery do not infer order',()=>{
 const p=pathFor([bar(30,100,105,95,101)],event,5);
 assert.equal(p.ordering,'UNKNOWN_INTRABAR_ORDER');assert.equal(p.adverse[-1].laterHighReturnPct,null);assert.equal(pathType(p),'G_UNKNOWN');
});
test('distinct bars yield ordering and later-only recovery',()=>{
 const p=pathFor([bar(30,100,100,97,99),bar(35,99,104,99,103)],event,10);
 assert.equal(p.ordering,'MAE_FIRST');assert.ok(p.adverse[-2].laterHighReturnPct>3);assert.equal(pathType(p),'A_EARLY_ADVERSE_THEN_RECOVERY');
});
test('replay rejects SHORT, incomplete paths and incomplete context',()=>{
 assert.throws(()=>replay([],{...event,direction:'SHORT'},{available:true}),/LONG_ONLY/);
 assert.equal(replay([],event,{available:false}).eligible,false);
 assert.equal(replay([],event,{available:true}).reason,'INCOMPLETE_PIT_CONTEXT');
});
test('frozen ratchet previous-bar stop and same-day adapter, no overrides',()=>{
 const bars=[];for(let min=0;min<360;min+=5){if(min>=150&&min<210)continue;bars.push(bar(min));}
 const at=bars.findIndex(b=>Date.parse(b.barStartJst)===Date.parse(event.decisionTimestamp));bars[at]=bar(30,90,100,85,95);
 const p=pathFor(bars,event,'SESSION_END'),r=replay(bars,event,p);
 assert.equal(p.available,true);assert.equal(r.eligible,true);assert.equal(r.exitPrice,90);assert.equal(r.intrabarExit,true);assert.ok(Math.abs(r.netReturnPct+10.05)<1e-8);assert.equal(r.holdingMinutesLower,0);assert.equal(r.holdingMinutesUpper,5);assert.ok(r.maeBeforeExitLowerPct<r.maeBeforeExitUpperPct);
});
test('context cannot borrow a missing bar from future',()=>{
 const bars=[];for(let min=5;min<360;min+=5){if(min>=150&&min<210)continue;bars.push(bar(min));}
 assert.equal(replay(bars,event,pathFor(bars,event,'SESSION_END')).reason,'INCOMPLETE_PIT_CONTEXT');
});
