import assert from 'node:assert/strict';
import crypto from 'node:crypto';

export const SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

export const ALLOCATION_CLASSES = Object.freeze([
  'DEV_A_LOCKED',
  'DEV_B_LOCKED',
  'VALIDATION_LOCKED',
  'HISTORICAL_HOLDOUT_LOCKED',
  'UNTOUCHED_OOS_SEALED',
  'FUTURE_RESERVE_SEALED',
  'PURGE_EMBARGO',
  'DIAGNOSTIC_ONLY',
  'BLOCKED_NOT_USABLE',
  'PROTECTED_EXTERNAL',
  'FRESH_EXTERNAL',
  'UNKNOWN_NOT_ALLOCATED',
]);

const FORBIDDEN_KEYS = /^(exit(Return|Outcome|Price|Path)?|profit|pnl|pf|winRate|winner|loser|mfe|mae|future(Label|Return|Price|Volume|Path|State|Selection))$/i;
const ALLOCATED = new Set([
  'DEV_A_LOCKED', 'DEV_B_LOCKED', 'VALIDATION_LOCKED',
  'HISTORICAL_HOLDOUT_LOCKED', 'UNTOUCHED_OOS_SEALED',
  'FUTURE_RESERVE_SEALED', 'PURGE_EMBARGO',
]);
const OOS_OR_RESERVE = new Set(['UNTOUCHED_OOS_SEALED', 'FUTURE_RESERVE_SEALED']);
const OUTCOME_UNTOUCHED = new Set(['SEALED_UNTOUCHED', 'METADATA_ONLY_OUTCOME_UNTOUCHED']);
const SPLIT_KEYS = Object.freeze({
  DEV_A_LOCKED: 'devA',
  DEV_B_LOCKED: 'devB',
  VALIDATION_LOCKED: 'validation',
  HISTORICAL_HOLDOUT_LOCKED: 'historicalHoldout',
  UNTOUCHED_OOS_SEALED: 'untouchedOos',
  FUTURE_RESERVE_SEALED: 'futureReserve',
});

export function assertNoOutcomeOrFutureFields(value, path = '$') {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => assertNoOutcomeOrFutureFields(entry, `${path}[${index}]`));
    return true;
  }
  if (!value || typeof value !== 'object') return true;
  for (const [key, entry] of Object.entries(value)) {
    assert(!FORBIDDEN_KEYS.test(key), `PROHIBITED_OUTCOME_FIELD:${path}.${key}`);
    assertNoOutcomeOrFutureFields(entry, `${path}.${key}`);
  }
  return true;
}

export function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function canonicalSha256(value) {
  return crypto.createHash('sha256').update(canonicalJson(value)).digest('hex');
}

export function validateManifest(manifest) {
  assertNoOutcomeOrFutureFields(manifest);
  assert.equal(manifest.schemaId, 'PHASE57_EXIT_V4_STAGE2_ALLOCATION_MANIFEST_V1');
  const seen = new Set();
  let previous = '';
  for (const row of manifest.sessions) {
    assert(ALLOCATION_CLASSES.includes(row.allocationClass), `UNKNOWN_ALLOCATION_CLASS:${row.allocationClass}`);
    assert(!seen.has(row.sessionDate), `DUPLICATE_SESSION:${row.sessionDate}`);
    assert(previous <= row.sessionDate, `NON_MONOTONIC_SESSION:${row.sessionDate}`);
    seen.add(row.sessionDate);
    previous = row.sessionDate;
    if (row.eligibilityStatus !== 'ELIGIBLE') assert(!ALLOCATED.has(row.allocationClass), `INELIGIBLE_ALLOCATED:${row.sessionDate}`);
    if (!OUTCOME_UNTOUCHED.has(row.exposureStatus)) assert(!OOS_OR_RESERVE.has(row.allocationClass), `EXPOSED_ASSIGNED_TO_OOS:${row.sessionDate}`);
    if (row.eligibilityStatus === 'UNKNOWN') assert(['DIAGNOSTIC_ONLY', 'UNKNOWN_NOT_ALLOCATED'].includes(row.allocationClass));
  }
  return {sessionCount: manifest.sessions.length, uniqueSessionCount: seen.size};
}

export function validateStage2Contract(contract, manifest) {
  assertNoOutcomeOrFutureFields(contract);
  validateManifest(manifest);
  assert.equal(contract.contractId, 'PHASE57_EXIT_V4_STAGE2_DATA_ALLOCATION_CONTRACT_V1');
  assert.equal(contract.contractVersion, '1.1.0');
  assert.equal(contract.status, 'FROZEN_RESULT_BLIND');
  assert(['DATA_ALLOCATION_READY', 'DATA_ALLOCATION_CAPACITY_CONSTRAINED_BUT_USABLE'].includes(contract.finalGate));
  assert.equal(contract.tier2Contract.sha256, '2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70');
  assert.equal(contract.tier2Contract.eligibilitySchemaSha256, 'f060c654f0d5af5f105f8ba20c47b78950ad433305b735d42f6cbd68f8e2823b');
  assert.equal(contract.tier2Contract.modifiedHere, false);
  assert.equal(contract.pool.confirmedEligibleSessions, 205);
  assert.equal(contract.pool.confirmedBlockedSessions, 0);
  assert.equal(contract.pool.diagnosticPriorExposureSessions, 179);
  assert.equal(contract.pool.exactSessionLevelInventoryAvailable, true);
  assert.equal(contract.allocation.frozen, true);
  assert.equal(contract.allocation.manifestComplete, true);
  assert.equal(contract.allocation.purgeEmbargoDecision, 'NONE_SESSION_LOCAL_SELECTOR_AND_ENTRY_STATE');

  const eligible = manifest.sessions.filter((row) => row.eligibilityStatus === 'ELIGIBLE');
  assert.equal(eligible.length, contract.pool.confirmedEligibleSessions);
  const allocatedCount = Object.values(contract.allocation.sessionCounts).reduce((sum, count) => sum + count, 0);
  assert.equal(allocatedCount, eligible.length);
  for (const [allocationClass, splitKey] of Object.entries(SPLIT_KEYS)) {
    const rows = eligible.filter((row) => row.allocationClass === allocationClass);
    const boundary = contract.allocation.dateBoundaries[splitKey];
    assert.equal(rows.length, contract.allocation.sessionCounts[splitKey], `SPLIT_COUNT_MISMATCH:${splitKey}`);
    assert.equal(rows[0]?.sessionDate, boundary.first, `SPLIT_FIRST_MISMATCH:${splitKey}`);
    assert.equal(rows.at(-1)?.sessionDate, boundary.last, `SPLIT_LAST_MISMATCH:${splitKey}`);
    assert.equal(rows.length, boundary.count, `SPLIT_BOUNDARY_COUNT_MISMATCH:${splitKey}`);
  }

  assert.equal(contract.stage3.devAUnlockCandidate, true);
  assert.equal(contract.stage3.developmentUnlocked, false);
  assert.equal(contract.stage3.explicitFutureAuthorizationRequired, true);
  assert.equal(contract.protection.exposedAssignedOosOrReserve, 0);
  assert.equal(contract.protection.protected180To282ReallocationAllowed, false);
  assert.equal(contract.protection.freshValidationOrOosReallocationAllowed, false);
  assert.equal(contract.protection.resultBasedReshuffleAllowed, false);
  assert.deepEqual(contract.safety, SAFETY);
  assert(Object.values(contract.accessLedger).every((value) => value === 0));
  return {status: contract.status, finalGate: contract.finalGate};
}

export function assertMinimumProtectionWhenFrozen(contract) {
  if (!contract.allocation.frozen) return {checked: false, reason: 'ALLOCATION_NOT_FROZEN'};
  const counts = contract.allocation.sessionCounts;
  assert(counts.validation >= 30, 'VALIDATION_MINIMUM_NOT_MET');
  assert(counts.historicalHoldout >= 25, 'HOLDOUT_MINIMUM_NOT_MET');
  assert(counts.untouchedOos >= 30, 'OOS_MINIMUM_NOT_MET');
  assert(counts.futureReserve >= 30, 'RESERVE_MINIMUM_NOT_MET');
  return {checked: true};
}

export function expectedFirstEnterCapacity(sessionCount) {
  assert(Number.isInteger(sessionCount) && sessionCount >= 0);
  return {
    conservative: Number((sessionCount * 2.0).toFixed(1)),
    base: Number((sessionCount * 2.9).toFixed(1)),
    optimistic: Number((sessionCount * 3.4).toFixed(1)),
  };
}
