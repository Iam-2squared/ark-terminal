import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

// Metadata-only tests. No market source, model, label generator or network import.
const base = new URL('../../predict/research/', import.meta.url);
const inventoryName = 'phase57-entry-historical-inventory-2026-09-08.json';
const freezeName = 'phase57-entry-allocation-freeze-2026-09-08.json';
const read = name => JSON.parse(readFileSync(new URL(name, base), 'utf8'));
const inventory = read(inventoryName);
const freeze = read(freezeName);
const old = read('phase57-hybrid-p21-entry-baseline-precommit.json');
const profiles = inventory.governanceProfiles;
const rows = inventory.sessions;
const profile = row => profiles[row.governanceProfile];
const reserve = rows.filter(row => Number.isInteger(row.parentOrdinal));
const protectedRows = reserve.filter(row => profile(row).SEALED);

test('identity domain is explicit, not a complete repository claim', () => {
  assert.equal(rows.length, 429);
  assert.equal(new Set(rows.map(row => row.sessionId)).size, 429);
  assert.equal(inventory.counts.totalRepositoryUniqueHistoricalSessions, null);
  assert.equal(inventory.discovery.contentCoverageComplete, false);
  assert.equal(inventory.status, 'PARTIAL_INVENTORY_FAIL_CLOSED_NOT_COMPLETE');
});

test('reserve is exactly pinned ordinals 1 through 282, not invented weekdays', () => {
  assert.deepEqual(reserve.map(row => row.parentOrdinal), Array.from({length:282}, (_, i) => i + 1));
  assert.equal(reserve[0].sessionDate, '2025-04-15');
  assert.equal(reserve.at(-1).sessionDate, '2026-06-11');
  assert.ok(reserve.slice(1, -1).every(row => row.sessionDate === null));
  assert.equal(rows.filter(row => row.sessionDate !== null).length, 149);
});

test('dated identities contain no duplicate dates', () => {
  const dates = rows.flatMap(row => row.sessionDate === null ? [] : [row.sessionDate]);
  assert.equal(new Set(dates).size, dates.length);
});

test('protected 190 partition is exhaustive and disjoint', () => {
  const partition = inventory.protected190Partition;
  assert.deepEqual([partition.X_entryDevelopment, partition.Y_entryValidation,
    partition.Z_certifiedEntryUntouchedOos, partition.W_unavailableUnderExistingSelectorReservation,
    partition.U_remainingReserveCrossResearchUnknown], [0,0,0,87,103]);
  assert.equal(protectedRows.length, 190);
  assert.equal(87 + 103, partition.total);
  const protectedOrdinals = new Set(protectedRows.map(row => row.parentOrdinal));
  const expected = freeze.protectedReserve.protectedOrdinalRanges.flatMap(([start, end]) =>
    Array.from({length:end-start+1}, (_, i) => start+i));
  assert.deepEqual([...protectedOrdinals], expected);
});

test('190 does not equal never-opened or Entry-available', () => {
  assert.equal(inventory.counts.neverOpenedGloballyConfirmed, 0);
  for (const row of protectedRows) {
    const p = profile(row);
    assert.equal(p.NEVER_OPENED, null);
    assert.equal(p.OPENED, null);
    assert.equal(p.eligibleForEntryDevelopment, false);
    assert.equal(p.eligibleForEntryValidation, false);
    assert.equal(p.eligibleForEntryUntouchedOOS, false);
  }
});

test('all 190 retain cross-research unknowns', () => {
  for (const row of protectedRows) for (const line of ['Entry','EXIT','Allocation']) {
    assert.ok(Object.values(profile(row).exposure[line]).every(v => v === 'UNKNOWN_GOVERNANCE'));
  }
});

test('structural admission is not represented as wholly unviewed data', () => {
  const structural = reserve.filter(row =>
    row.parentOrdinal >= 121 && row.parentOrdinal <= 179 && row.parentOrdinal !== 150);
  assert.equal(structural.length, 58);
  assert.ok(structural.every(row => profile(row).structuralAdmissionAlreadyPerformed === true));
  assert.ok(structural.every(row => profile(row).exposure.Selector.MARKET_DATA === 'UNKNOWN_GOVERNANCE'));
});

test('source validation and all five purge sessions remain excluded', () => {
  assert.equal(rows.filter(row => row.governanceProfile === 'SOURCE_VALIDATION').length, 8);
  assert.equal(rows.filter(row => row.governanceProfile === 'PURGE').length, 5);
  for (const row of rows.filter(row => ['SOURCE_VALIDATION','PURGE'].includes(row.governanceProfile))) {
    for (const k of ['eligibleForEntryDevelopment','eligibleForEntryValidation','eligibleForEntryUntouchedOOS'])
      assert.equal(profile(row)[k], false);
  }
});

test('already opened groups agree with closeout evidence', () => {
  assert.equal(rows.filter(row => profile(row).OPENED === true).length, 226);
  assert.equal(rows.filter(row => profile(row).USED === true).length, 226);
  assert.equal(reserve.filter(row => profile(row).OPENED === true).length, 89);
  assert.equal(rows.filter(row => profile(row).governanceClassification === 'UNKNOWN_GOVERNANCE').length, 203);
});

test('source snapshots cannot accidentally count old release flags as current permission', () => {
  assert.equal(inventory.metadataEvidence.allocation.reserve.sessionCount, 282);
  assert.equal(inventory.metadataEvidence.closeout.capacityReserve.protectedOutcomeUnopenedNonPurgeSessions, 190);
  assert.equal(freeze.protectedReserve.releaseAllowed, false);
  assert.equal(freeze.protectedReserve.reallocationAllowed, false);
});

test('Baseline17 dates unchanged, distinct from model-development admission', () => {
  const a = freeze.roles.A_baselineDiagnostic;
  assert.deepEqual(a.sessionDates, old.allocation.sessions);
  assert.equal(a.sessionCount, 17);
  assert.equal(a.measurementAllowed, false);
  assert.equal(a.admitted, false);
  assert.equal(a.fittingAllowed, false);
  assert.ok(rows.filter(row => row.governanceProfile === 'BASELINE17')
    .every(row => !profile(row).eligibleForEntryUntouchedOOS));
});

test('Development, Validation and OOS are explicitly unallocated, not silently guessed', () => {
  for (const role of ['B_entryDevelopment','C_entryValidation','D_entryUntouchedOos']) {
    assert.deepEqual(freeze.roles[role].sessionIds, []);
    assert.equal(freeze.roles[role].sessionCount, 0);
    assert.equal(freeze.roles[role].permission, false);
  }
  assert.equal(freeze.admission.finalInventoryComplete, false);
  assert.equal(freeze.admission.finalAllocationComplete, false);
});

test('priority conservation saves 103 without certifying or releasing it', () => {
  assert.deepEqual(freeze.protectedReserve.priorityConservationOrdinalRange, [180,282]);
  assert.equal(freeze.protectedReserve.priorityConservationSessions, 103);
  assert.equal(freeze.protectedReserve.priorityDoesNotCertifyOosOrTransferOwnership, true);
  assert.equal(freeze.protectedReserve.protectedSessions, 190);
});

test('P21 historical chronology blocker retained', () => {
  assert.ok(freeze.chronology.historicalReserveLatest < freeze.chronology.currentFrozenP21PriorEnd);
  assert.ok(freeze.chronology.historicalReserveLatest < freeze.chronology.baselineDiagnosticEarliest);
  assert.equal(freeze.chronology.reserveEligibleForCurrentFrozenP21Baseline, false);
  assert.equal(freeze.chronology.historicalReconstructedP21IsDifferentClass, true);
});

test('future prospective reservation is policy only and cannot backdate OOS', () => {
  const p = freeze.roles.E_prospective;
  assert.equal(p.earliestSessionStrictlyAfter, '2026-09-08');
  assert.equal(p.automaticRelease, false);
  assert.equal(p.retrospectiveProspectiveClaimAllowed, false);
});

test('source fingerprints and unresolved data remain explicit', () => {
  assert.ok(inventory.sources.every(s => /^[a-f0-9]{40}$/.test(s.ref) && /^[a-f0-9]{40}$/.test(s.gitBlobSha)));
  for (const row of rows) {
    assert.ok(profiles[row.governanceProfile]);
    assert.ok(inventory.datasets.some(d => d.datasetId === row.datasetId));
    assert.ok(row.sourceRefs.every(id => inventory.sources.some(s => s.id === id)));
  }
  const pinned = inventory.unresolvedDatasets.find(d => d.datasetId === 'P25_PINNED_HISTORY');
  assert.equal(pinned.reportedSessionCount, 190);
  assert.equal(pinned.uniqueSessionDates, null);
});

test('cross-research counts are unknown instead of false zeroes', () => {
  for (const key of ['entryUsedGlobally','exitUsedGlobally','allocationUsedGlobally'])
    assert.equal(inventory.counts[key], null);
  assert.equal(inventory.counts.hybridP21Measured, 0);
});

test('all safety flags stay false and no new data or outcomes were used', () => {
  assert.equal(Object.keys(inventory.safety).length, 9);
  for (const doc of [inventory, freeze]) {
    assert.ok(Object.values(doc.safety).every(v => v === false));
    for (const k of ['sealedContentOpened','outcomeNewlyViewed','performanceNewlyComputed','modelFittingPerformed'])
      assert.equal(doc.audit[k], false);
    assert.equal(doc.audit.baselineSessionsMeasured, 0);
  }
  assert.equal(freeze.admission.baselineMeasurementGo, false);
  assert.equal(freeze.admission.newEntryResearchGo, false);
});

test('immutable evidence byte fingerprints match', () => {
  const lines = readFileSync(new URL('phase57-entry-governance-2026-09-08.sha256', base), 'utf8').trim().split('\n');
  assert.equal(lines.length, 2);
  for (const line of lines) {
    const [digest, name] = line.split(/\s+/);
    assert.ok([inventoryName, freezeName].includes(name));
    assert.equal(createHash('sha256').update(readFileSync(new URL(name, base))).digest('hex'), digest);
  }
});
