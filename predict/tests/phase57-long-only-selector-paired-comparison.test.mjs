import test from 'node:test';
import assert from 'node:assert/strict';
import {equalBudgetTopN,summarizeFrozenSelector,PAIRED_SELECTOR_COMPARISON_CONTRACT} from '../long-only/phase57-long-only-selector-paired-comparison.js';

const features=[1,2,3].flatMap(day=>[1,2,3,4,5,6].map(rank=>({sessionDate:`2024-01-0${day}`,symbol:`${day}${rank}`,decisionTimeJst:'10:00',selectorRank:rank,segment:rank%3===0?'GROWTH':'PRIME',liquidityBucket:'MID',gapBucket:'NON_GAP'})));
const targets=features.map((row,index)=>({sessionDate:row.sessionDate,symbol:row.symbol,decisionTimeJst:row.decisionTimeJst,y30Bps:index%2?50:-10,futureMfe30Pct:1.2,futureMae30Pct:-0.4,remainingUpsidePct:2,winner:index%4===0}));

test('equal-budget comparison preserves the frozen score order and caps each point',()=>{
  const selected=equalBudgetTopN(features,5);
  assert.equal(selected.length,15);
  assert.deepEqual(selected.filter(row=>row.sessionDate==='2024-01-01').map(row=>row.selectorRank),[1,2,3,4,5]);
});

test('paired summary reports signed continuation and excursion metrics',()=>{
  const summary=summarizeFrozenSelector({selected:equalBudgetTopN(features,5),targetRows:targets});
  assert.equal(summary.candidateCount,15);
  assert.equal(summary.sessionCount,3);
  assert.equal(summary.meanFutureMfePct,1.2);
  assert.equal(summary.meanFutureMaePct,-0.4);
  assert.equal(summary.mfeToAbsMae,3);
  assert.equal(summary.byMarket.GROWTH.candidateCount,3);
});

test('comparison contract keeps sealed partitions and frozen selectors',()=>{
  assert.equal(PAIRED_SELECTOR_COMPARISON_CONTRACT.newSelectorMayChange,false);
  assert.equal(PAIRED_SELECTOR_COMPARISON_CONTRACT.oldSelectorMayChange,false);
  assert.equal(PAIRED_SELECTOR_COMPARISON_CONTRACT.validationOpened,false);
  assert.equal(PAIRED_SELECTOR_COMPARISON_CONTRACT.oosOpened,false);
});
