import test from 'node:test';
import assert from 'node:assert/strict';
import {
  classifyP25ExitV2State,
  validateP25ExitV2AnalogPool,
  scoreP25ExitV2StateConditioned,
  simulateP25ExitV2StateConditioned,
  P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256,
  P25_EXIT_V2_STATE_CONDITIONED_SAFETY,
} from '../daytrade/phase57-p25-exit-v2-state-conditioned.js';

const ts=(day,hh='09:00')=>`${day}T${hh}:00.000Z`;
const baseState=(currentReturnPct,extra={})=>({
  currentReturnPct,
  bestReturnPct:Math.max(0,currentReturnPct),
  givebackPctPoints:0,
  atrPct:1,
  momentumPct:0,
  bodyPressure:0,
  directionalRangePos:0.5,
  elapsedBars:2,
  ...extra,
});
function analogs({bucket='WINNER_PROTECTION',label=-0.2,n=35,date='2026-08-10'}={}){
  const current=bucket==='WINNER_PROTECTION'?1:bucket==='LOSER_RESCUE'?-1:0;
  return Array.from({length:n},(_,i)=>({
    sessionDate:date,
    symbol:`T${i}`,
    direction:'LONG',
    timestamp:ts(date,'10:00'),
    fullyRealizedAt:ts(date,'10:30'),
    state:baseState(current,{elapsedBars:2+(i%3)}),
    labels:{1:label,3:label,6:label},
  }));
}
const observedWinner=[
  {timestamp:ts('2026-08-27','09:05'),open:100,high:101.5,low:99.8,close:101,volume:1000},
  {timestamp:ts('2026-08-27','09:10'),open:101,high:102,low:100.8,close:101.5,volume:1100},
];
const observedLoser=[
  {timestamp:ts('2026-08-27','09:05'),open:100,high:100.2,low:98.5,close:99,volume:1000},
  {timestamp:ts('2026-08-27','09:10'),open:99,high:99.2,low:97.8,close:98.5,volume:1100},
];

test('classifies zero-boundary states without legacy-outcome tuning',()=>{
  assert.equal(classifyP25ExitV2State(baseState(1)),'WINNER_PROTECTION');
  assert.equal(classifyP25ExitV2State(baseState(-1)),'LOSER_RESCUE');
  assert.equal(classifyP25ExitV2State(baseState(0)),'NEUTRAL_HOLD');
});

test('rejects any post-2026-08-12 development analog contamination',()=>{
  const contaminated=[...analogs(),...analogs({n:1,date:'2026-08-19'})];
  const checked=validateP25ExitV2AnalogPool(contaminated);
  assert.equal(checked.ready,false);
  assert.equal(checked.status,'BLOCKED_V2_POST_CUTOFF_DEVELOPMENT_DATA');
});

test('winner query only uses winner-state causal neighbors and can EXIT on rejected edge',()=>{
  const pool=[...analogs({bucket:'WINNER_PROTECTION',label:-0.25,n:35}),...analogs({bucket:'LOSER_RESCUE',label:5,n:35})];
  const score=scoreP25ExitV2StateConditioned({entryPrice:100,direction:'LONG',observedBars:observedWinner,timestamp:observedWinner.at(-1).timestamp,sessionDate:'2026-08-27',analogPool:pool});
  assert.equal(score.ready,true);
  assert.equal(score.stateBucket,'WINNER_PROTECTION');
  assert.equal(score.neighborCount,35);
  assert.equal(score.decision,'EXIT');
  assert.equal(score.policySha256,P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256);
});

test('loser query is conditioned separately and HOLDs when same-state edge remains positive',()=>{
  const pool=[...analogs({bucket:'LOSER_RESCUE',label:0.5,n:35}),...analogs({bucket:'WINNER_PROTECTION',label:-5,n:35})];
  const score=scoreP25ExitV2StateConditioned({entryPrice:100,direction:'LONG',observedBars:observedLoser,timestamp:observedLoser.at(-1).timestamp,sessionDate:'2026-08-27',analogPool:pool});
  assert.equal(score.ready,true);
  assert.equal(score.stateBucket,'LOSER_RESCUE');
  assert.equal(score.neighborCount,35);
  assert.equal(score.decision,'HOLD');
});

test('insufficient same-state evidence fails closed to HOLD',()=>{
  const pool=[...analogs({bucket:'WINNER_PROTECTION',label:-1,n:20}),...analogs({bucket:'LOSER_RESCUE',label:-1,n:35})];
  const score=scoreP25ExitV2StateConditioned({entryPrice:100,direction:'LONG',observedBars:observedWinner,timestamp:observedWinner.at(-1).timestamp,sessionDate:'2026-08-27',analogPool:pool});
  assert.equal(score.ready,false);
  assert.equal(score.decision,'HOLD');
  assert.equal(score.reason,'INSUFFICIENT_STATE_CONDITIONED_CAUSAL_ANALOGS');
  assert.equal(score.neighborCount,20);
});

test('simulation requires frozen outcome-free Entry and remains research-only',()=>{
  assert.throws(()=>simulateP25ExitV2StateConditioned({row:{entryAccepted:true,frozenBeforeOutcome:false,currentOutcomeUsed:false}}),/outcome-free frozen Entry/);
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(P25_EXIT_V2_STATE_CONDITIONED_SAFETY[k],false);
});