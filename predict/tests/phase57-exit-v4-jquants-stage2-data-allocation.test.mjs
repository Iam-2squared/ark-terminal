import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import {
  ALLOCATION_CLASSES,
  SAFETY,
  assertMinimumProtectionWhenFrozen,
  assertNoOutcomeOrFutureFields,
  canonicalSha256,
  expectedFirstEnterCapacity,
  validateManifest,
  validateStage2Contract,
} from '../../scripts/lib/phase57-stage2-data-allocation-contract.mjs';

const research = (name) => new URL(`../research/${name}`, import.meta.url);
const read = (name) => JSON.parse(fs.readFileSync(research(name), 'utf8'));
const contract = read('phase57-exit-v4-stage2-data-allocation-contract-v1.json');
const manifest = read('phase57-exit-v4-stage2-allocation-manifest-v1.json');
const summary = read('phase57-exit-v4-stage2-capacity-eligibility-summary-v1.json');
const audit = read('phase57-exit-v4-jquants-stage2-data-allocation-freeze-v1.json');
const handoff = read('phase57-exit-v4-stage2-dev-a-handoff-stub-v1.json');

test('Stage 2 truthfully stops at integrity blocked without a frozen allocation', () => {
  assert.deepEqual(validateStage2Contract(contract, manifest), {
    status: 'NOT_FROZEN_INTEGRITY_BLOCKED', finalGate: 'DATA_ALLOCATION_INTEGRITY_BLOCKED',
  });
  assert.equal(audit.status, 'DATA_ALLOCATION_INTEGRITY_BLOCKED');
  assert.equal(audit.hardStop, 'ACTIVE');
});

test('Tier 2 contract and eligibility schema digests remain pinned', () => {
  assert.equal(contract.tier2Contract.sha256, '2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70');
  assert.equal(contract.tier2Contract.eligibilitySchemaSha256, 'f060c654f0d5af5f105f8ba20c47b78950ad433305b735d42f6cbd68f8e2823b');
  assert.equal(contract.tier2Contract.modifiedHere, false);
});

test('unknown planning range is not treated as eligible or allocated', () => {
  assert.deepEqual(contract.pool.unknownPlanningBand, [300, 360]);
  assert.equal(contract.pool.unknownPlanningBandIsAllocation, false);
  assert.equal(contract.pool.confirmedEligibleSessions, 0);
  assert.equal(summary.candidatePool.allocationPermitted, false);
});

test('manifest is deterministic, date ordered and one session one split', () => {
  assert.deepEqual(validateManifest(manifest), {sessionCount: 3, uniqueSessionCount: 3});
  assert.equal(canonicalSha256(manifest), canonicalSha256(JSON.parse(JSON.stringify(manifest))));
  assert.deepEqual(manifest.sessions.map((row) => row.sessionDate), ['2025-08-27', '2025-10-09', '2025-11-25']);
});

test('all exposed sessions remain diagnostic and cannot become OOS', () => {
  for (const row of manifest.sessions) {
    assert.equal(row.exposureStatus, 'DIAGNOSTIC_USED');
    assert.equal(row.allocationClass, 'DIAGNOSTIC_ONLY');
    assert.equal(row.eligibilityStatus, 'UNKNOWN');
  }
});

test('Protected and Fresh reservations are external and untouched', () => {
  assert.equal(manifest.externalProtectionLedger.protected180To282.sessions, 103);
  assert.equal(manifest.externalProtectionLedger.protected180To282.newAccess, 0);
  assert.equal(manifest.externalProtectionLedger.freshValidationOrOos.sessions, 25);
  assert.equal(manifest.externalProtectionLedger.freshValidationOrOos.newAccess, 0);
  assert.equal(contract.protection.protected180To282ReallocationAllowed, false);
  assert.equal(contract.protection.freshValidationOrOosReallocationAllowed, false);
});

test('allocation classes are exact and no session is assigned to a split', () => {
  assert.deepEqual(contract.allocationClasses, ALLOCATION_CLASSES);
  assert(Object.values(contract.allocation.sessionCounts).every((count) => count === 0));
  assert.equal(contract.allocation.dateBoundaries, null);
});

test('First ENTER capacity estimates are arithmetic only', () => {
  assert.deepEqual(expectedFirstEnterCapacity(100), {conservative: 200, base: 290, optimistic: 340});
  assert.deepEqual(summary.confirmedAllocationCapacity.devAExpectedFirstEnter, {conservative: 0, base: 0, optimistic: 0});
  assert.deepEqual(summary.planningBandCapacityNotAllocation.expectedFirstEnter.base, [870, 1044]);
});

test('minimum protection is not falsely asserted before freeze', () => {
  assert.deepEqual(assertMinimumProtectionWhenFrozen(contract), {checked: false, reason: 'ALLOCATION_NOT_FROZEN'});
});

test('outcome and future-label fields are rejected recursively', () => {
  assert.throws(() => assertNoOutcomeOrFutureFields({nested:{mfe:1}}), /PROHIBITED_OUTCOME_FIELD/);
  assert.throws(() => assertNoOutcomeOrFutureFields({futureLabel:'x'}), /PROHIBITED_OUTCOME_FIELD/);
  for (const artifact of [contract, manifest, summary, audit, handoff]) assertNoOutcomeOrFutureFields(artifact);
});

test('DEV-A is not ready and no split is unlockable', () => {
  assert.equal(contract.stage3.devAUnlockCandidate, false);
  assert.equal(contract.stage3.developmentUnlocked, false);
  assert.equal(handoff.status, 'BLOCKED_NOT_READY');
  assert.deepEqual(handoff.devASessions, []);
});

test('all safety flags and all access counters remain false or zero', () => {
  for (const artifact of [contract, manifest, audit]) assert.deepEqual(artifact.safety, SAFETY);
  assert(Object.values(contract.accessLedger).every((value) => value === 0));
  assert(Object.values(audit.accessLedger).every((value) => value === 0));
});

test('byte SHA evidence files match each frozen artifact', () => {
  for (const name of [
    'phase57-exit-v4-stage2-data-allocation-contract-v1.json',
    'phase57-exit-v4-stage2-allocation-manifest-v1.json',
    'phase57-exit-v4-stage2-capacity-eligibility-summary-v1.json',
    'phase57-exit-v4-stage2-dev-a-handoff-stub-v1.json',
    'phase57-exit-v4-jquants-stage2-data-allocation-freeze-v1.json',
  ]) {
    const expected = fs.readFileSync(research(name.replace(/\.json$/, '.sha256')), 'utf8').trim().split(/\s+/)[0];
    const actual = crypto.createHash('sha256').update(fs.readFileSync(research(name))).digest('hex');
    assert.equal(actual, expected, name);
  }
});

test('audit and blocked DEV-A handoff pin the same artifact bytes', () => {
  assert.equal(audit.artifacts.allocationContractSha256, 'b3eb3c438ad2c5ec75d2a2900840570d49e03c483808336b6649f8cf46e150b9');
  assert.equal(audit.artifacts.allocationManifestSha256, '7a3c1fc986eec469b81f6382fc158cc9e54af3c6af24a334432f68a5b868394f');
  assert.equal(audit.artifacts.capacitySummarySha256, '7227119f2442bf867780f04dfa02c8ab5e964bb1cb389a863d5d02102e5f8252');
  assert.equal(audit.artifacts.devAHandoffSha256, 'ab267b0d61a3fc580e50dae5420d6da63a23093087cc4e9da691af6129f9e598');
  assert.equal(handoff.allocationContractDigest, audit.artifacts.allocationContractSha256);
  assert.equal(handoff.allocationManifestDigest, audit.artifacts.allocationManifestSha256);
});

test('Stage 2 implementation has no EXIT invocation import', () => {
  const source = fs.readFileSync(new URL('../../scripts/lib/phase57-stage2-data-allocation-contract.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /from\s+['\"][^'\"]*exit[^'\"]*['\"]/i);
});
