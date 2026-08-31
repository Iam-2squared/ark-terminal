import assert from 'node:assert/strict';
import test from 'node:test';
import {scoreP25AdaptiveAllocationCandidate,simulateP25AdaptiveAllocationV2,PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY,PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY} from '../portfolio/phase57-p25-adaptive-allocation-v2.js';

const t0='2026-09-01T00:10:00.000Z',t1='2026-09-01T00:15:00.000Z';
function trade(symbol,{price=1000,exit=1010,confidence=.95,probability=.9,opp=.9,v2=.9}={}){return {entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,symbol,sector:'TEST',signalDirection:1,sessionDate:'2026-09-01',entryTimestamp:t0,entryPrice:price,exitTimestamp:t1,exitPrice:exit,exitReason:'TEST',confidence,probability,selectionOpportunityScore:opp,selectionV2Score:v2};}
function session(trades){const sessionBarsBySymbol={};for(const x of trades)sessionBarsBySymbol[x.symbol]=[{timestamp:t0,close:x.entryPrice},{timestamp:t1,close:x.exitPrice}];return {sessionDate:'2026-09-01',sessionBarsBySymbol,trades};}

test('candidate quality creates fixed S/A/B/C ranks from causal inputs',()=>{
  assert.equal(scoreP25AdaptiveAllocationCandidate(trade('S')).rank,'S');
  assert.equal(scoreP25AdaptiveAllocationCandidate(trade('A',{confidence:.75,probability:.72,opp:.74,v2:.72})).rank,'A');
  assert.equal(scoreP25AdaptiveAllocationCandidate(trade('B',{confidence:.60,probability:.60,opp:.60,v2:.60})).rank,'B');
  assert.equal(scoreP25AdaptiveAllocationCandidate(trade('C',{confidence:.30,probability:.30,opp:.30,v2:.30})).rank,'C');
});

test('one candidate can enter while retaining reserve cash',()=>{
  const x=simulateP25AdaptiveAllocationV2({sessions:[session([trade('1001.T')])],profile:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.allocationProfiles[0]});
  assert.equal(x.trade.accepted,1);
  const accepted=x.allocationDecisions.find(d=>d.status==='ACCEPTED');assert.ok(accepted);assert.equal(accepted.rank,'S');
  const first=x.equityCurve.find(r=>r.timestamp===t0);assert.ok(first.capitalUtilization>0);assert.ok(first.capitalUtilization<1);assert.ok(first.cashJpy>0);
});

test('concurrent holdings are capped at nine and excess high-quality candidates are audited',()=>{
  const trades=Array.from({length:12},(_,i)=>trade(`${1100+i}.T`,{price:500+i*10,exit:505+i*10}));
  const x=simulateP25AdaptiveAllocationV2({sessions:[session(trades)],profile:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.allocationProfiles[1]});
  assert.ok(x.capitalEfficiency.maxConcurrentPositions<=9);
  assert.ok(x.capitalEfficiency.missedHighQualityCandidates>=3);
  assert.equal(x.methodology.maximumConcurrentPositions,9);
});

test('equal rank and score weighting profiles stay parallel and no winner is selected',()=>{
  const trades=[trade('1201.T'),trade('1202.T',{confidence:.76,probability:.72,opp:.74,v2:.70}),trade('1203.T',{confidence:.60,probability:.60,opp:.60,v2:.60})];
  for(const profile of PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.allocationProfiles){const x=simulateP25AdaptiveAllocationV2({sessions:[session(trades)],profile});assert.equal(x.profile.id,profile.id);assert.equal(x.methodology.winnerSelectionAllowed,false);assert.equal(x.methodology.futureOutcomeVisibleToAllocator,false);}
});

test('v2 policy is frozen before first eligible Fresh day and safety stays fully disabled',()=>{
  assert.equal(PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.firstFreshEligibleDate,'2026-09-01');
  assert.equal(PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.minimumConcurrentPositions,1);
  assert.equal(PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.maximumConcurrentPositions,9);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY[key],false,key);
});
