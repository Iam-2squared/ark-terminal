import test from 'node:test';
import assert from 'node:assert/strict';
import {P24_6_POLICY,scoreP2350PriorQuery,riskConditionedExitDecision} from '../daytrade/phase57-p24-p2350-risk-bridge.js';
import {P23_27_FEATURES} from '../daytrade/phase57-feature-polarity-segmentation.js';

const velocity=v=>Object.fromEntries(P23_27_FEATURES.map((k,i)=>[k,v*(1+i*.05)]));
const hist=[];
for(let i=0;i<40;i++){
  const day=String(i+1).padStart(2,'0');
  const bad=i%4===0;
  const classJitter=(i%7)*.01;
  hist.push({symbol:i%2?'AAA.T':'BBB.T',setup:'TEST_SETUP',direction:'UP',sessionDate:`2026-06-${day}`,timestamp:`2026-06-${day}T00:20:00.000Z`,fullyRealizedAt:`2026-06-${day}T01:00:00.000Z`,offsetBars:1,velocity:velocity(bad?1+classJitter:-.3-classJitter),actual:bad?1:0,nextDirectionalReturnPct:bad?-.2:.2});
}
const query={symbol:'CCC.T',setup:'TEST_SETUP',direction:'UP',sessionDate:'2026-07-15',timestamp:'2026-07-15T00:20:00.000Z',offsetBars:1,velocity:velocity(1.2)};

test('P24.6 remains fail closed and does not consume fresh holdout',()=>{
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'])assert.equal(P24_6_POLICY[k],false,k);
  assert.equal(P24_6_POLICY.freshHoldoutConsumed,false);
  assert.equal(P24_6_POLICY.riskTriggerQuantile,.75);
  assert.equal(P24_6_POLICY.thresholdSearchAllowed,false);
  assert.equal(P24_6_POLICY.parameterSweepAllowed,false);
});

test('P24.6 scores current query only from prior realized sessions and derives fixed Q4 threshold',()=>{
  const s=scoreP2350PriorQuery(query,hist);
  assert.ok(Number.isFinite(s.riskScore));
  assert.ok(Number.isFinite(s.riskThreshold));
  assert.equal(s.historyCount,40);
  assert.ok(s.thresholdHistoryCount>=20);
  const d=riskConditionedExitDecision({query,allHistoricalRows:hist});
  assert.equal(typeof d.triggered,'boolean');
});