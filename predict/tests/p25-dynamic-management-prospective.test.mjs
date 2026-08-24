import assert from 'node:assert/strict';
import {buildP253AKManagementRows,PHASE57_P25_3AK_POLICY,PHASE57_P25_3AK_SAFETY} from '../daytrade/phase57-p25-3ak-dynamic-management-prospective.js';

const bars=[
  {timestamp:'2026-08-24T00:00:00.000Z',open:100,high:100.4,low:99.8,close:100.2,volume:1000},
  {timestamp:'2026-08-24T00:05:00.000Z',open:100.2,high:100.9,low:100.1,close:100.8,volume:1200},
  {timestamp:'2026-08-24T00:10:00.000Z',open:100.8,high:101.5,low:100.7,close:101.3,volume:1400},
  {timestamp:'2026-08-24T00:15:00.000Z',open:101.3,high:101.8,low:101.1,close:101.6,volume:1300},
  {timestamp:'2026-08-24T00:20:00.000Z',open:101.6,high:101.7,low:100.9,close:101.0,volume:1600},
];
const frozen={
  entryAccepted:true,
  symbol:'7203.T',
  sessionDate:'2026-08-24',
  entryTimestamp:'2026-08-24T00:10:00.000Z',
  featureCutoff:'2026-08-24T00:10:00.000Z',
  signalDirection:1,
  direction:'LONG',
  baseHorizonBars:2,
  frozenBeforeOutcome:true,
  currentOutcomeUsed:false,
  outcomePending:true,
};

const out=buildP253AKManagementRows({frozenTrades:[frozen],sessionBarsBySymbol:{'7203.T':bars}});
assert.equal(out.rows.length,1);
assert.equal(out.blocked.length,0);
assert.equal(out.rows[0].entryPrice,101.3);
assert.equal(out.rows[0].contextBars.length,3);
assert.equal(out.rows[0].contextBars.at(-1).timestamp,frozen.entryTimestamp);
assert.equal(out.rows[0].futureBars.length,2);
assert.ok(out.rows[0].futureBars.every(bar=>bar.timestamp>frozen.entryTimestamp));
assert.equal(out.rows[0].frozenBeforeOutcome,true);
assert.equal(out.rows[0].currentOutcomeUsed,false);

const missing=buildP253AKManagementRows({frozenTrades:[{...frozen,entryTimestamp:'2026-08-24T00:12:00.000Z'}],sessionBarsBySymbol:{'7203.T':bars}});
assert.equal(missing.rows.length,0);
assert.equal(missing.blocked[0].status,'BLOCKED_ENTRY_BAR_MISSING');
assert.throws(()=>buildP253AKManagementRows({frozenTrades:[{...frozen,currentOutcomeUsed:true}],sessionBarsBySymbol:{'7203.T':bars}}),/frozen outcome-free Entry rows/);

assert.equal(PHASE57_P25_3AK_POLICY.sameFrozenUniverseAndEntryAsFixedBaseline,true);
assert.equal(PHASE57_P25_3AK_POLICY.postOutcomeRuleSelectionAllowed,false);
for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']) assert.equal(PHASE57_P25_3AK_SAFETY[key],false,key);

console.log('P25.3AK dynamic management prospective adapter regression test passed');
