import assert from 'node:assert/strict';
import test from 'node:test';
import {decideP25ExitV4,P25_EXIT_V4_POLICY,P25_EXIT_V4_SAFETY} from '../daytrade/phase57-p25-exit-v4-structural-risk.js';

const h1=(upper90Pct=-0.1,downsideProbability=0.7)=>({horizonBars:1,upper90Pct,downsideProbability});
const score=(stateBucket,{decision='EXIT',upper90Pct=-0.1,downsideProbability=0.7}={})=>({ready:true,stateBucket,decision,horizonScores:[h1(upper90Pct,downsideProbability)]});

test('loser rescue waits for non-improving downside trajectory',()=>{
  const first=decideP25ExitV4({baseScore:score('LOSER_RESCUE'),currentReturnPct:-0.4,mfePct:0,captureRatio:null,downsideHistory:[0.8],adverseExcursionScalePct:1});
  assert.equal(first.decision,'HOLD');
  const confirmed=decideP25ExitV4({baseScore:score('LOSER_RESCUE'),currentReturnPct:-0.4,mfePct:0,captureRatio:null,downsideHistory:[0.6],adverseExcursionScalePct:1});
  assert.equal(confirmed.decision,'EXIT');
  assert.equal(confirmed.reason,'V4_CONFIRMED_DOWNSIDE_TRAJECTORY');
});

test('winner protection requires giveback and two confirmations',()=>{
  const base=score('WINNER_PROTECTION');
  const a=decideP25ExitV4({baseScore:base,currentReturnPct:1,mfePct:3,captureRatio:1/3,winnerExitStreak:0});
  assert.equal(a.decision,'HOLD');assert.equal(a.winnerExitStreak,1);
  const b=decideP25ExitV4({baseScore:base,currentReturnPct:1,mfePct:3,captureRatio:1/3,winnerExitStreak:a.winnerExitStreak});
  assert.equal(b.decision,'EXIT');
});

test('winner remains held while capture ratio stays healthy',()=>{
  const x=decideP25ExitV4({baseScore:score('WINNER_PROTECTION'),currentReturnPct:2.5,mfePct:3,captureRatio:0.83,winnerExitStreak:1});
  assert.equal(x.decision,'HOLD');assert.equal(x.winnerExitStreak,0);
});

test('neutral persistent downside needs edge rejection',()=>{
  const a=decideP25ExitV4({baseScore:score('NEUTRAL_HOLD',{upper90Pct:0.2}),currentReturnPct:-1,neutralLossStreak:2});
  assert.equal(a.decision,'HOLD');
  const b=decideP25ExitV4({baseScore:score('NEUTRAL_HOLD'),currentReturnPct:-1,neutralLossStreak:2});
  assert.equal(b.decision,'EXIT');
});

test('8/31 is development evidence only and safety stays fully disabled',()=>{
  assert.equal(P25_EXIT_V4_POLICY.firstFreshEligibleDate,'2026-09-01');
  assert.equal(P25_EXIT_V4_POLICY.developmentEvidence.august31EligibleForV4PerformanceClaim,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(P25_EXIT_V4_SAFETY[key],false,key);
});
