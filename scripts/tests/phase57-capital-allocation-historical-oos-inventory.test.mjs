import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {auditHistoricalOosInventory,renderHistoricalOosInventoryReport} from '../phase57-capital-allocation-historical-oos-inventory.mjs';

test('Historical OOS inventory fails closed when no unused causal block exists',()=>{
  const inventory=JSON.parse(fs.readFileSync('predict/research/phase57-capital-allocation-historical-oos-inventory-v1.json','utf8'));
  const audit=auditHistoricalOosInventory();
  assert.equal(audit.status,'NO_TRULY_UNUSED_CAUSAL_ELIGIBLE_HISTORICAL_BLOCK');
  assert.equal(audit.discoveredMarketSessions,487);
  assert.equal(audit.firstCausalEligibleDate,'2026-06-19');
  assert.equal(audit.trulyUnusedCausalEligibleHistoricalSessionCount,0);
  assert.equal(audit.historicalOosOpened,false);
  assert.equal(audit.validationUnlockCreated,false);
  assert.equal(audit.validationRunnerExecuted,false);
  assert.equal(audit.fourArmPerformanceMeasured,false);
  assert.equal(audit.nextCleanOpportunity.firstDateUnderCurrentCrossResearchReservations,'2026-10-22');
  assert.match(renderHistoricalOosInventoryReport(inventory,audit),/clear no-data result/);
  assert.ok(Object.values(audit.claims).every(value=>value===false));
  assert.ok(Object.values(audit.safety).every(value=>value===false));
});

test('Historical inventory roles remain preserved while current refreeze is explicit',()=>{
  const audit=auditHistoricalOosInventory();
  assert.equal(audit.frozenCandidateAtInventoryTime.roles.MAX_5_V5,'PRIMARY_OOS_CANDIDATE_WHEN_A_CLEAN_BLOCK_EXISTS');
  assert.equal(audit.frozenCandidateAtInventoryTime.roles.MAX_10_V5,'LEGACY_BUDGET_BASELINE');
  assert.equal(audit.frozenCandidateAtInventoryTime.roles.MAX_3_V5,'AGGRESSIVE_OOS_REFERENCE');
  assert.equal(audit.currentRefreeze.roles.MAX_3_V5,'PRIMARY_INTEGRATED_DEVELOPMENT_CANDIDATE');
  assert.equal(audit.currentRefreeze.roles.MAX_5_V5,'CONSERVATIVE_INTEGRATED_SUB_CANDIDATE');
  assert.equal(audit.currentRefreeze.roles.MAX_10_V5,'LEGACY_BUDGET_BASELINE');
});
