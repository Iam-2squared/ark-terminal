import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const contractUrl=new URL('../research/phase57-selector-oos-analysis-contract.json',import.meta.url);
const digestUrl=new URL('../research/phase57-selector-oos-analysis-contract.sha256',import.meta.url);
const v3FreezeUrl=new URL('../research/phase57-selector-v3-freeze.json',import.meta.url);

const contractBytes=fs.readFileSync(contractUrl);
const contract=JSON.parse(contractBytes);
const actualDigest=createHash('sha256').update(contractBytes).digest('hex');
const expectedDigest=fs.readFileSync(digestUrl,'utf8').trim().split(/\s+/)[0];
const v3Digest=createHash('sha256').update(fs.readFileSync(v3FreezeUrl)).digest('hex');

test('OOS Analysis Contract bytes are frozen and linked to unchanged V3.0',()=>{
  assert.equal(actualDigest,expectedDigest);
  assert.equal(contract.status,'FROZEN_BEFORE_UNTOUCHED_OOS_RELEASE');
  assert.equal(contract.selectorV3Freeze.sha256,v3Digest);
  assert.equal(contract.selectorV3Freeze.postValidationChangeAllowed,false);
  assert.equal(contract.evidenceBoundary.expectedSelectedV3Threshold,0.7);
  assert.equal(contract.evidenceBoundary.untouchedOos.sessionCount,19);
  assert.equal(contract.evidenceBoundary.untouchedOos.sessions.length,19);
  assert.equal(contract.evidenceBoundary.untouchedOos.sessions[0],'2026-08-10');
  assert.equal(contract.evidenceBoundary.untouchedOos.sessions.at(-1),'2026-09-04');
});

test('Primary, Secondary, diagnostics and winner rule cannot drift after OOS release',()=>{
  assert.equal(contract.primaryMetric.horizonBars,6);
  assert.equal(contract.primaryMetric.roundTripCostBps,10);
  assert.equal(contract.primaryMetric.acrossSessionAggregation,'EQUAL_WEIGHT_ARITHMETIC_MEAN');
  assert.equal(contract.statisticalInference.confidenceLevel,0.95);
  assert.match(contract.statisticalInference.interval,/STUDENT_T/);
  assert.ok(contract.winnerRule.requirementsAgainstEachOtherSelector.includes('TWO_SIDED_95_PERCENT_CI_LOWER_BOUND_GT_ZERO'));
  assert.equal(contract.winnerRule.secondaryMetricMayOverride,false);
  assert.equal(contract.winnerRule.diagnosticMayOverride,false);
  assert.equal(contract.winnerRule.sameCapacityMayOverride,false);
  assert.equal(contract.preRegisteredDiagnostics.sameCapacity.kDefinition,'V3_SELECTED_COUNT_AT_EACH_DECISION_TIMESTAMP');
  assert.ok(contract.secondaryMetrics.includes('POST_SELECTION_CLOSE_RETURN'));
  assert.ok(contract.preRegisteredDiagnostics.timeOfDayBuckets.includes('14:30-CLOSE'));
  for(const forbidden of [
    'V3_0_FEATURE_CHANGE','V3_0_THRESHOLD_CHANGE','V3_0_WEIGHT_CHANGE','METRIC_CHANGE',
    'PRIMARY_HORIZON_CHANGE','SAMPLE_EXCLUSION','SYMBOL_EXCLUSION','WINNER_RULE_CHANGE',
  ])assert.ok(contract.forbiddenAfterOosRelease.includes(forbidden));
});

test('Validation facts and external-review hypotheses are explicitly separated',()=>{
  const separation=contract.evidenceSeparation;
  assert.equal(separation.validationObservedFacts.primaryUtility30mBps.V1,83.76);
  assert.equal(separation.validationObservedFacts.primaryUtility30mBps.V3,84.25);
  assert.ok(separation.futureVersionHypothesesOnly.includes('ALREADY_MOVED_MAY_CONTAIN_CONTINUATION_OPPORTUNITY'));
  assert.ok(separation.externalReviewClaimsNotObservedByThisPilot.includes('INSTITUTIONAL_ORDER_FLOW_EXPLANATION'));
  assert.equal(separation.futureHypothesesMayModifyFrozenV3_0,false);
  assert.equal(separation.futureHypothesesMayChangeThisOosContract,false);
});

test('all execution, trading, promotion and transmission boundaries remain false',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
  ])assert.equal(contract.safety[key],false,key);
  assert.equal(contract.scope.laneYMainChangeAllowed,false);
  assert.equal(contract.scope.pullRequestMustRemainDraft,true);
  assert.equal(contract.afterOos.currentOosMayBeReusedToEvaluateV3_1OrV4,false);
});
