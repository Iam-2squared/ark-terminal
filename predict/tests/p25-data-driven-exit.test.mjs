import assert from 'node:assert/strict';
import test from 'node:test';
import {buildP25DataDrivenExitAnalogPool,scoreP25DataDrivenExit,simulateP25DataDrivenExit,P25_DATA_DRIVEN_EXIT_POLICY,P25_DATA_DRIVEN_EXIT_SAFETY} from '../daytrade/phase57-p25-data-driven-exit.js';

function bars(date='2026-08-01',n=40,start=100,step=0.2){const out=[];for(let i=0;i<n;i++){const close=start+i*step;out.push({timestamp:`${date}T00:${String(i).padStart(2,'0')}:00.000Z`,open:close-step/2,high:close+0.3,low:close-0.3,close,volume:1000+i});}return out;}

test('policy does not use the 60m fixed horizon as an EXIT input',()=>{
  assert.equal(P25_DATA_DRIVEN_EXIT_POLICY.fixedHoldMinutesUsedAsDecisionInput,false);
  assert.equal(P25_DATA_DRIVEN_EXIT_POLICY.fixedHorizonUsedAsDecisionInput,false);
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(P25_DATA_DRIVEN_EXIT_SAFETY[k],false);
});

test('analog pool is built from fully realized historical sessions only',()=>{
  const pool=buildP25DataDrivenExitAnalogPool({historicalSessions:[{symbol:'7203.T',sessionDate:'2026-08-01',bars5m:bars()}]});
  assert.ok(pool.length>0);
  assert.ok(pool.every(x=>x.sessionDate==='2026-08-01'));
  assert.ok(pool.every(x=>x.fullyRealizedAt>x.timestamp));
  assert.ok(pool.every(x=>x.direction==='LONG'||x.direction==='SHORT'));
});

test('scorer fails open to HOLD when causal analog evidence is insufficient',()=>{
  const observed=bars('2026-08-20',3,200,1);
  const score=scoreP25DataDrivenExit({entryPrice:199,direction:'LONG',observedBars:observed,timestamp:observed.at(-1).timestamp,sessionDate:'2026-08-20',analogPool:[]});
  assert.equal(score.ready,false);assert.equal(score.decision,'HOLD');assert.equal(score.reason,'INSUFFICIENT_CAUSAL_ANALOGS');
});

test('future prospective rows cannot enter the causal neighbor set',()=>{
  const hist=bars('2026-08-01',40,100,-0.2),pool=buildP25DataDrivenExitAnalogPool({historicalSessions:[{symbol:'7203.T',sessionDate:'2026-08-01',bars5m:hist}]});
  const observed=bars('2026-08-20',4,100,-0.3),futureRows=pool.map(x=>({...x,sessionDate:'2026-08-21',fullyRealizedAt:'2026-08-21T06:00:00.000Z'}));
  const score=scoreP25DataDrivenExit({entryPrice:101,direction:'LONG',observedBars:observed,timestamp:observed.at(-1).timestamp,sessionDate:'2026-08-20',analogPool:futureRows});
  assert.equal(score.ready,false);assert.equal(score.neighborCount,0);
});

test('simulation consumes bars sequentially and preserves frozen Entry identity',()=>{
  const historicalSessions=[];for(let d=1;d<=8;d++)historicalSessions.push({symbol:'7203.T',sessionDate:`2026-08-${String(d).padStart(2,'0')}`,bars5m:bars(`2026-08-${String(d).padStart(2,'0')}`,40,100,-0.3)});
  const pool=buildP25DataDrivenExitAnalogPool({historicalSessions});
  const future=bars('2026-08-20',8,99,-0.5),row={entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,sessionDate:'2026-08-20',entryTimestamp:'2026-08-20T00:00:00.000Z',symbol:'7203.T',signalDirection:1,entryPrice:100,contextBars:[],futureBars:future};
  const out=simulateP25DataDrivenExit({row,analogPool:pool});
  assert.ok(out.barsHeld>=1&&out.barsHeld<=future.length);assert.ok(Array.isArray(out.managementDecisions));assert.equal(out.managementDecisions.length,out.barsHeld);assert.ok(['DATA_DRIVEN_EXPECTED_VALUE_EXIT','SESSION_END'].includes(out.exitReason));
});
