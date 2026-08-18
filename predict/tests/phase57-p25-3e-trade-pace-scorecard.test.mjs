import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {
  buildP253TradePaceScorecard,
  PHASE57_P25_3E_POLICY,
  PHASE57_P25_3E_SAFETY,
} from '../daytrade/phase57-p25-3e-trade-pace-scorecard.js';

const variants=['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'];
const safety=()=>({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

function fakeEvaluation(){
  const frequency={},results={};
  variants.forEach((variant,index)=>{
    const frozen=20+index*10;
    frequency[variant]={
      target:400,
      validFrozenEntries:frozen,
      tradingSessions:2,
      validFrozenEntriesPerTradingSession:frozen/2,
      observedDaysToTarget:null,
      paceEstimatedDaysToTarget:400/(frozen/2),
    };
    results[variant]={
      evaluatedTradingSessions:2,
      validFrozenEntries:frozen-1,
      hitRate:0.5+index*0.01,
      tradeWinRate:0.48+index*0.01,
      afterCostNetPct:index===0?99-index:-99+index,
      profitFactor:1.1+index*0.05,
      maxDrawdownPct:12-index,
      meanNetReturnPct:0.1+index*0.01,
      coverage:0.02+index*0.001,
      coverageDenominator:1000,
      sameTimeCorrelation:{conservativeEffectiveIndependentEntries:10+index,conservativeIndependenceRatio:0.5},
      sessionEqualWeightPortfolio:{afterCostNetPct:1+index},
      symbolConcentration:{largestShare:0.2,hhi:0.1},
      sectorConcentration:{largestShare:0.25,hhi:0.12},
    };
  });
  return {
    phase:'57.p25.3d.autonomous-evidence-evaluation',
    status:'P25_3_AUTONOMOUS_EVIDENCE_EVALUATED',
    lineageManifestHeadSha256:'a'.repeat(64),
    frozenReadySessionInputCount:2,
    expectedSessionCount:2,
    methodology:{currentOuterOosDoesNotSelectDynamicN:true,allFiveVariantsRetained:true},
    safety:safety(),
    result:{
      phase:'57.p25.2i.end-to-end-prospective-evaluation',
      readyPacketCount:2,
      blockedSessionCount:0,
      safety:safety(),
      evidence:{
        phase:'57.p25.2h.multisession-evidence-accumulator',
        operationalTradeFrequency:frequency,
        safety:safety(),
        comparison:{
          phase:'57.p25.2d.precommitted-prospective-comparison',
          results,
          safety:safety(),
        },
      },
    },
  };
}

test('scorecard retains fixed five-variant order and never ranks by performance',()=>{
  const card=buildP253TradePaceScorecard({evaluationArtifact:fakeEvaluation()});
  assert.equal(card.status,'P25_3_TRADE_PACE_SCORECARD_READY');
  assert.deepEqual(card.rows.map(row=>row.variant),variants);
  assert.equal(card.methodology.variantsRankedByPerformance,false);
  assert.equal(card.methodology.currentOuterOosDoesNotSelectDynamicN,true);
  assert.equal(card.methodology.performanceConclusionAllowed,false);
  assert.equal(Object.hasOwn(card,'winnerVariant'),false);
  assert.equal(Object.hasOwn(card,'selectedDynamicN'),false);
  assert.equal(card.rows[0].afterCostNetPct,99);
  assert.equal(card.rows.at(-1).afterCostNetPct,-95);
});

test('scorecard exposes arithmetic 400-trade pace targets without relaxing Entry',()=>{
  const card=buildP253TradePaceScorecard({evaluationArtifact:fakeEvaluation()});
  assert.equal(card.targetTradeCount,400);
  assert.deepEqual(card.paceTargets,[
    {tradingDays:30,requiredEntriesPerTradingSession:13.333333},
    {tradingDays:20,requiredEntriesPerTradingSession:20},
  ]);
  const fixed5=card.rows[0];
  assert.equal(fixed5.frozenEntries,20);
  assert.equal(fixed5.resolvedEntries,19);
  assert.equal(fixed5.unresolvedFrozenEntries,1);
  assert.equal(fixed5.entriesPerTradingSession,10);
  assert.equal(fixed5.paceEstimatedDaysTo400,40);
  assert.equal(fixed5.targetProgress[0].currentlyAtOrAboveTargetPace,false);
  assert.equal(fixed5.targetProgress[1].currentlyAtOrAboveTargetPace,false);
  assert.equal(card.methodology.entryThresholdRelaxed,false);
  assert.equal(card.methodology.targetPaceIsArithmeticOnly,true);
});

test('CLI wrapper shape is accepted but missing a precommitted variant fails closed',()=>{
  const evaluation=fakeEvaluation();
  const wrapped={phase:'57.p25.3d.autonomous-evidence-evaluation-cli',evaluation};
  assert.equal(buildP253TradePaceScorecard({evaluationArtifact:wrapped}).rows.length,5);
  delete evaluation.result.evidence.operationalTradeFrequency.DYNAMIC_50;
  assert.throws(()=>buildP253TradePaceScorecard({evaluationArtifact:evaluation}),/operational frequency missing DYNAMIC_50/);
});

test('scorecard safety stays read-only and does not require MARKETSPEED, board or Tick',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_3E_SAFETY[key],false,key);
  }
  assert.equal(PHASE57_P25_3E_POLICY.dailyMarketSpeedRequired,false);
  assert.equal(PHASE57_P25_3E_POLICY.boardOrTickUsed,false);
  assert.equal(PHASE57_P25_3E_POLICY.microstructureUsed,false);
  assert.equal(PHASE57_P25_3E_POLICY.variantRankingAllowed,false);
  assert.equal(PHASE57_P25_3E_POLICY.winnerSelectionAllowed,false);
});

test('daily evidence evaluation workflow builds, persists and uploads the descriptive scorecard',()=>{
  const workflowUrl=new URL('../../.github/workflows/phase57-p25-evidence-evaluate.yml',import.meta.url);
  const workflow=fs.readFileSync(workflowUrl,'utf8');
  assert.match(workflow,/build_p25_trade_pace_scorecard\.mjs/);
  assert.match(workflow,/data\/p25-scorecards/);
  assert.match(workflow,/same lineage head already has a scorecard/);
  assert.match(workflow,/p25-trade-pace-scorecard\.json/);
  assert.doesNotMatch(workflow,/RssMarket|RssTickList|ARK_ORDER|win32com|phase58_excel/i);
});
