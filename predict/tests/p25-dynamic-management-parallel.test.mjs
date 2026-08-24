import assert from 'node:assert/strict';
import { evaluateP25DynamicManagementParallel, P25_DYNAMIC_MANAGEMENT_SAFETY } from '../daytrade/phase57-p25-dynamic-management-parallel.js';

const base='2026-08-24T00:';
const bars=[
  {timestamp:`${base}00:00.000Z`,open:100,high:100.5,low:99.5,close:100,volume:1000},
  {timestamp:`${base}05:00.000Z`,open:100,high:101,low:99.8,close:100.8,volume:1200},
  {timestamp:`${base}10:00.000Z`,open:100.8,high:102,low:100.7,close:101.8,volume:1300},
  {timestamp:`${base}15:00.000Z`,open:101.8,high:102.2,low:101.4,close:101.6,volume:900},
  {timestamp:`${base}20:00.000Z`,open:101.6,high:101.7,low:100.2,close:100.4,volume:1600},
  {timestamp:`${base}25:00.000Z`,open:100.4,high:100.5,low:99.4,close:99.7,volume:1800},
];
const row={
  symbol:'7203.T',sessionDate:'2026-08-24',entryTimestamp:`${base}10:00.000Z`,entryAccepted:true,
  frozenBeforeOutcome:true,currentOutcomeUsed:false,entryPrice:101.8,signalDirection:'LONG',baseHorizonBars:3,
  contextBars:bars.slice(0,2),futureBars:bars.slice(3),
};
const fixed={symbol:'7203.T',sessionDate:'2026-08-24',entryTimestamp:row.entryTimestamp,exitTimestamp:`${base}25:00.000Z`,exitReason:'FROZEN_HORIZON',netReturnPct:-2.112, barsHeld:3};
const out=evaluateP25DynamicManagementParallel({frozenEntryRows:[row],fixedResolvedTrades:[fixed]});
assert.equal(out.mode,'research_parallel_only');
assert.equal(out.executable,false);
assert.equal(out.frozenEntryCount,1);
assert.equal(out.dynamicOutcomeCount,1);
assert.equal(out.pairedCount,1);
assert.equal(out.methodology.fixedBaselineUntouched,true);
assert.equal(out.methodology.pointInTimeSequentialManagement,true);
assert.equal(out.methodology.performanceConclusionAllowed,false);
for(const value of Object.values(P25_DYNAMIC_MANAGEMENT_SAFETY)){
  if(typeof value==='boolean'&&['humanApprovalRequired'].includes('')) continue;
}
for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']) assert.equal(out.safety[key],false,key);
assert.throws(()=>evaluateP25DynamicManagementParallel({frozenEntryRows:[{...row,currentOutcomeUsed:true}],fixedResolvedTrades:[fixed]}),/outcome-free frozen Entry/);
console.log('P25 dynamic management parallel regression test passed');
