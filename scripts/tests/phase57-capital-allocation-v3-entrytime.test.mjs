import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CONTRACT, SAFETY, buildEntryTimeOpportunity, groupOpportunitySets, allocateV3, summarizePhaseA, recentRealizedVolatility,
} from '../lib/phase57-capital-allocation-v3-entrytime.mjs';

const features = {
  directionalReturnFromOpenPct:1,
  directionalVwapDistancePct:0.4,
  directionalMomentum3Pct:0.3,
  directionalMomentumAccelerationPct:0.1,
  directionalPullback6Pct:-0.2,
  relativeVolume5:1.4,
  minutesSinceFirstSelection:10,
  hybridReciprocalRank:0.5,
  priorSelectionCount:2,
  direction:-1,
};
function event(symbol, score, hybridRank=1) {
  return {
    eventId:`2026-09-01|2026-09-01T01:00:00.000Z|${symbol}`,
    symbolSessionId:`2026-09-01|${symbol}`,
    sessionDate:'2026-09-01',
    decisionTimestamp:'2026-09-01T01:00:00.000Z',
    symbol,
    hybridRank,
    hybridScore:0.8,
    sourceClass:'DEVELOPMENT_ONLY',
    selectionLineage:'fixture',
    stateAfter:'ENTERED',
    entryCount:1,
    decision:{action:'ENTER',direction:-1,probability:score},
    directionFeatures:[
      {direction:1,features:{...features,direction:1}},
      {direction:-1,features},
    ],
  };
}
const calm7=[100,100.1,100.2,100.3,100.4,100.5,100.6];

test('all execution safety flags remain false', () => {
  for (const [k,v] of Object.entries(SAFETY)) assert.equal(v,false,k);
});

test('risk lookback is frozen to exactly seven completed closes', () => {
  assert.equal(CONTRACT.riskFeature.returnCount,6);
  assert.ok(Number.isFinite(recentRealizedVolatility(calm7)));
  assert.equal(recentRealizedVolatility(calm7.slice(0,6)),null);
});

test('builder accepts only first ENTER above frozen threshold and no outcomes', () => {
  const row=buildEntryTimeOpportunity(event('1111.T',0.71),{recentCloses:calm7});
  assert.equal(row.outcomeUsed,false); assert.equal(row.exitUsed,false);
  assert.equal(row.mshScore,0.71); assert.ok(row.recentRealizedVolatility>0);
  assert.throws(()=>buildEntryTimeOpportunity({...event('1111.T',0.71),futureReturn:1},{recentCloses:calm7}),/OUTCOME_FIELD_FORBIDDEN/);
  assert.throws(()=>buildEntryTimeOpportunity(event('1111.T',0.60),{recentCloses:calm7}),/ENTRY_THRESHOLD_MISMATCH/);
  assert.throws(()=>buildEntryTimeOpportunity(event('1111.T',0.71),{recentCloses:calm7.slice(0,6)}),/RISK_FEATURE_WINDOW_INVALID/);
});

test('equal and MSH-probability ordinal rank policies are deterministic', () => {
  const ops=[
    buildEntryTimeOpportunity(event('1111.T',0.90,99),{recentCloses:calm7}),
    buildEntryTimeOpportunity(event('2222.T',0.80,1),{recentCloses:calm7}),
    buildEntryTimeOpportunity(event('3333.T',0.70,2),{recentCloses:calm7}),
  ];
  const set=groupOpportunitySets(ops)[0];
  assert.deepEqual(set.candidates.map(x=>x.symbol),['1111.T','2222.T','3333.T']);
  assert.deepEqual(allocateV3(set,'V3_0_EQUAL').map(x=>Number(x.weight.toFixed(6))),[0.333333,0.333333,0.333333]);
  assert.deepEqual(allocateV3(set,'V3_A_RANK').map(x=>Number(x.weight.toFixed(6))),[0.5,0.333333,0.166667]);
});

test('risk-only policy gives lower weight to higher recent volatility', () => {
  const a=buildEntryTimeOpportunity(event('1111.T',0.80),{recentCloses:calm7});
  const b=buildEntryTimeOpportunity(event('2222.T',0.79),{recentCloses:[100,103,97,104,96,105,95]});
  const set=groupOpportunitySets([a,b])[0];
  const alloc=allocateV3(set,'V3_B_RISK');
  const map=Object.fromEntries(alloc.map(x=>[x.symbol,x.weight]));
  assert.ok(map['1111.T']>map['2222.T']);
});

test('phase A summary exposes distribution only, not realized performance', () => {
  const set=groupOpportunitySets([
    buildEntryTimeOpportunity(event('1111.T',0.90),{recentCloses:calm7}),
    buildEntryTimeOpportunity(event('2222.T',0.80),{recentCloses:calm7}),
  ]);
  const out=summarizePhaseA(set,'V3_A_RANK');
  assert.equal(out.opportunitySetCount,1);
  assert.ok(Number.isFinite(out.meanHhi));
  assert.equal('netReturn' in out,false);
  assert.equal('profitFactor' in out,false);
});
