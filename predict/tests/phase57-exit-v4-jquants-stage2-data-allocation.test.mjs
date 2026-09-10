import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import {
  SAFETY, assertMinimumProtectionWhenFrozen,
  assertNoOutcomeOrFutureFields, canonicalSha256, expectedFirstEnterCapacity,
  validateManifest, validateStage2Contract,
} from '../../scripts/lib/phase57-stage2-data-allocation-contract.mjs';

const research = (name) => new URL(`../research/${name}`, import.meta.url);
const read = (name) => JSON.parse(fs.readFileSync(research(name), 'utf8'));
const byteSha = (name) => crypto.createHash('sha256').update(fs.readFileSync(research(name))).digest('hex');
const contract = read('phase57-exit-v4-stage2-data-allocation-contract-v1.json');
const manifest = read('phase57-exit-v4-stage2-allocation-manifest-v1.json');
const summary = read('phase57-exit-v4-stage2-capacity-eligibility-summary-v1.json');
const inventory = read('phase57-exit-v4-stage2-session-metadata-inventory-v1.json');
const audit = read('phase57-exit-v4-jquants-stage2-fast-allocation-freeze-v1.json');
const handoff = read('phase57-exit-v4-stage2-dev-a-handoff-v1.json');
const artifactFiles = {
  inventorySha256: 'phase57-exit-v4-stage2-session-metadata-inventory-v1.json',
  allocationManifestSha256: 'phase57-exit-v4-stage2-allocation-manifest-v1.json',
  allocationContractSha256: 'phase57-exit-v4-stage2-data-allocation-contract-v1.json',
  capacitySummarySha256: 'phase57-exit-v4-stage2-capacity-eligibility-summary-v1.json',
  devAHandoffSha256: 'phase57-exit-v4-stage2-dev-a-handoff-v1.json',
};

test('Stage 2 allocation is frozen result-blind and remains at hard stop', () => {
  assert.deepEqual(validateStage2Contract(contract, manifest), {
    status: 'FROZEN_RESULT_BLIND', finalGate: 'DATA_ALLOCATION_CAPACITY_CONSTRAINED_BUT_USABLE',
  });
  assert.equal(audit.status, 'DATA_ALLOCATION_CAPACITY_CONSTRAINED_BUT_USABLE');
  assert.equal(audit.hardStop, 'ACTIVE');
});

test('Tier 2 contract and eligibility schema digests remain pinned', () => {
  assert.equal(contract.tier2Contract.sha256, '2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70');
  assert.equal(contract.tier2Contract.eligibilitySchemaSha256, 'f060c654f0d5af5f105f8ba20c47b78950ad433305b735d42f6cbd68f8e2823b');
  assert.equal(contract.tier2Contract.modifiedHere, false);
});

test('exact inventory classifies 205 eligible and 179 prior-exposure diagnostics', () => {
  assert.equal(inventory.status, 'EXACT_METADATA_INVENTORY_COMPLETE');
  assert.equal(inventory.sessions.length, 384);
  assert.deepEqual(summary.pool, {discovered: 487, eligible: 205, blocked: 0, diagnosticPriorExposure: 179, protectedExternal: 103, freshExternal: 25});
  assert.equal(contract.pool.exactSessionLevelInventoryAvailable, true);
  assert.equal(contract.pool.confirmedEligibleSessions, 205);
  assert.equal(contract.pool.confirmedBlockedSessions, 0);
});

test('manifest is deterministic, ordered, complete and one-session-one-split', () => {
  assert.deepEqual(validateManifest(manifest), {sessionCount: 384, uniqueSessionCount: 384});
  assert.equal(canonicalSha256(manifest), canonicalSha256(JSON.parse(JSON.stringify(manifest))));
  assert.equal(contract.allocation.manifestComplete, true);
  assert.equal(new Set(manifest.sessions.map((row) => row.sessionDate)).size, manifest.sessions.length);
});

test('allocation counts and chronological boundaries are exact', () => {
  assert.deepEqual(contract.allocation.sessionCounts, {devA: 70, devB: 20, validation: 30, historicalHoldout: 25, untouchedOos: 30, futureReserve: 30});
  assert.deepEqual(contract.allocation.dateBoundaries, {
    devA: {first: '2024-09-10', last: '2024-12-20', count: 70},
    devB: {first: '2024-12-23', last: '2025-01-24', count: 20},
    validation: {first: '2025-01-27', last: '2025-03-11', count: 30},
    historicalHoldout: {first: '2025-03-12', last: '2026-06-15', count: 25},
    untouchedOos: {first: '2026-06-16', last: '2026-07-28', count: 30},
    futureReserve: {first: '2026-07-29', last: '2026-09-09', count: 30},
  });
  assert.equal(contract.allocation.purgeEmbargoDecision, 'NONE_SESSION_LOCAL_SELECTOR_AND_ENTRY_STATE');
});

test('only metadata-outcome-untouched eligible sessions enter frozen splits', () => {
  const diagnostic = manifest.sessions.filter((row) => row.allocationClass === 'DIAGNOSTIC_ONLY');
  const eligible = manifest.sessions.filter((row) => row.eligibilityStatus === 'ELIGIBLE');
  assert.equal(diagnostic.length, 179);
  assert(diagnostic.every((row) => row.exposureStatus === 'PRIOR_RESEARCH_EXPOSED'));
  assert.equal(eligible.length, 205);
  assert(eligible.every((row) => row.exposureStatus === 'METADATA_ONLY_OUTCOME_UNTOUCHED'));
  assert.equal(eligible.filter((row) => ['UNTOUCHED_OOS_SEALED', 'FUTURE_RESERVE_SEALED'].includes(row.allocationClass)).length, 60);
});

test('Protected and Fresh reservations are external, untouched and not reallocatable', () => {
  assert.deepEqual(manifest.externalProtectionLedger, {
    protected180To282: {sessions: 103, newAccess: 0, allocationAllowed: false},
    freshValidationOrOos: {sessions: 25, newAccess: 0, allocationAllowed: false},
  });
  assert.equal(contract.protection.protected180To282ReallocationAllowed, false);
  assert.equal(contract.protection.freshValidationOrOosReallocationAllowed, false);
  assert.equal(contract.protection.resultBasedReshuffleAllowed, false);
});

test('First ENTER capacity is arithmetic only and records the constrained gate', () => {
  assert.deepEqual(expectedFirstEnterCapacity(70), {conservative: 140, base: 203, optimistic: 238});
  assert.deepEqual(expectedFirstEnterCapacity(20), {conservative: 40, base: 58, optimistic: 68});
  assert.deepEqual(summary.allocation.devA.expectedFirstEnter, {conservative: 140, base: 203, optimistic: 238});
  assert.deepEqual(summary.allocation.devB.expectedFirstEnter, {conservative: 40, base: 58, optimistic: 68});
  assert.equal(summary.devATarget200.base, true);
  assert.equal(summary.devBTarget500.base, false);
  assert.equal(summary.finalGate, 'DATA_ALLOCATION_CAPACITY_CONSTRAINED_BUT_USABLE');
});

test('minimum protected split sizes pass after freeze', () => {
  assert.deepEqual(assertMinimumProtectionWhenFrozen(contract), {checked: true});
});

test('outcome and future-label fields are rejected recursively', () => {
  assert.throws(() => assertNoOutcomeOrFutureFields({nested:{mfe:1}}), /PROHIBITED_OUTCOME_FIELD/);
  assert.throws(() => assertNoOutcomeOrFutureFields({futureLabel:'x'}), /PROHIBITED_OUTCOME_FIELD/);
  for (const artifact of [contract, manifest, summary, inventory, audit, handoff]) assertNoOutcomeOrFutureFields(artifact);
});

test('DEV-A is locked and requires separate authorization', () => {
  assert.equal(contract.stage3.devAUnlockCandidate, true);
  assert.equal(contract.stage3.developmentUnlocked, false);
  assert.equal(handoff.status, 'DEV_A_LOCKED_READY_FOR_SEPARATE_AUTHORIZATION');
  assert.equal(handoff.devASessions.length, 70);
  assert.equal(handoff.developmentUnlocked, false);
  assert.equal(handoff.explicitFutureAuthorizationRequired, true);
});

test('all safety flags and access counters remain false or zero', () => {
  for (const artifact of [contract, manifest, inventory, audit, handoff]) assert.deepEqual(artifact.safety, SAFETY);
  for (const ledger of [contract.accessLedger, inventory.accessLedger, audit.accessLedger]) assert(Object.values(ledger).every((value) => value === 0));
});

test('byte SHA evidence files match every current frozen artifact', () => {
  for (const name of Object.values(artifactFiles)) {
    const expected = fs.readFileSync(research(name.replace(/\.json$/, '.sha256')), 'utf8').trim().split(/\s+/)[0];
    assert.equal(byteSha(name), expected, name);
  }
});

test('audit and DEV-A handoff pin the same artifact bytes', () => {
  for (const [field, name] of Object.entries(artifactFiles)) assert.equal(audit.artifacts[field], byteSha(name), field);
  assert.equal(handoff.allocationContractDigest, audit.artifacts.allocationContractSha256);
  assert.equal(handoff.allocationManifestDigest, audit.artifacts.allocationManifestSha256);
  assert.equal(handoff.sessionMetadataInventoryDigest, audit.artifacts.inventorySha256);
});

test('Stage 2 implementation has no EXIT invocation import', () => {
  const source = fs.readFileSync(new URL('../../scripts/lib/phase57-stage2-data-allocation-contract.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /from\s+['\"][^'\"]*exit[^'\"]*['\"]/i);
});
