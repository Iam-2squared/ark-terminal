import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const evidence = JSON.parse(fs.readFileSync(new URL('../research/phase57-exit-v4-jquants-stage1e-controlled-extraction-v1.json', import.meta.url)));
const paritySource = fs.readFileSync(new URL('../../scripts/phase57-stage1e-golden-input-parity.mjs', import.meta.url), 'utf8');

test('Stage 1E controlled acquisition is limited to the three pre-authorized sessions', () => {
  assert.deepEqual(evidence.allowedSessions, ['2025-08-27', '2025-10-09', '2025-11-25']);
  assert.equal(evidence.extractionTotals.zipDownloads, 3);
  assert.equal(evidence.extractionTotals.allowedSessionsExtracted, 3);
  assert.equal(evidence.extractionTotals.approvedMembersRead, 9);
  assert.equal(evidence.extractionTotals.unapprovedContentReads, 0);
  assert.equal(evidence.extractionTotals.goldenRows, 787);
  assert.equal(evidence.governanceChange.physicalAcquisitionIsResearchAccess, false);
});

test('container, extractor and subset lineage are complete and hash-shaped', () => {
  assert.match(evidence.freeze.extractorSha256, /^[0-9a-f]{64}$/);
  assert.match(evidence.freeze.configSha256, /^[0-9a-f]{64}$/);
  assert.match(evidence.freeze.parityRunnerSha256, /^[0-9a-f]{64}$/);
  for (const row of evidence.extraction) {
    assert.match(row.subsetSha256, /^[0-9a-f]{64}$/);
    assert.equal(row.approvedMembersRead, 3);
    assert.equal(row.unapprovedContentReads, 0);
    assert.equal(row.strippedFieldCount, 0);
    assert.equal(row.outputMembers.length, 3);
    for (const member of row.outputMembers) {
      assert.match(member.sourceMemberSha256, /^[0-9a-f]{64}$/);
      assert.match(member.outputSha256, /^[0-9a-f]{64}$/);
    }
  }
  assert.ok(evidence.sourceArtifacts.every((row) => row.containerDigestMatched));
});

test('allowed Golden input parity is exact and PIT safe', () => {
  assert.equal(evidence.parity.exactFloatTolerance, 0);
  assert.equal(evidence.parity.totals.featureRows, 1260);
  assert.equal(evidence.parity.totals.featureMismatches, 0);
  assert.equal(evidence.parity.totals.stateComparisons, 787);
  assert.equal(evidence.parity.totals.stateMismatches, 0);
  assert.equal(evidence.parity.totals.pitViolations, 0);
  assert.equal(evidence.negativeZeroNormalization.observed, 124);
  assert.equal(evidence.negativeZeroNormalization.result, 'NO_MSH_FEATURE_MISMATCH');
});

test('partial Hybrid and missing Entry Golden keep FULL and Tier 2 at zero', () => {
  assert.match(evidence.layerResults.hybridOutput, /^PARTIAL_/);
  assert.match(evidence.layerResults.entryEvent, /^NOT_RECOVERABLE_/);
  assert.equal(evidence.eligibility.fullReplayEligibleSessions, 0);
  assert.equal(evidence.eligibility.confirmedTier2Sessions, 0);
  assert.equal(evidence.eligibility.stage2AllocationAllowed, false);
  assert.equal(evidence.status, 'CONTROLLED_EXTRACTION_PARITY_PARTIAL');
  assert.equal(evidence.hardStop, 'ACTIVE');
});

test('parity path contains no EXIT invocation and access/safety remain closed', () => {
  assert.doesNotMatch(paritySource, /from ['"].*exit/i);
  assert.equal(evidence.accessLedger.jquantsApiCalls, 0);
  assert.equal(evidence.accessLedger.jquantsBulkDownloads, 0);
  assert.equal(evidence.accessLedger.unapprovedSessionContentInspected, 0);
  assert.equal(evidence.accessLedger.protected180To282, 0);
  assert.equal(evidence.accessLedger.freshValidationOrOos, 0);
  assert.equal(evidence.accessLedger.exitOutcome, 0);
  assert.equal(evidence.accessLedger.futureLabels, 0);
  assert.equal(evidence.accessLedger.exitInvocations, 0);
  assert.ok(Object.values(evidence.safety).every((value) => value === false));
  assert.equal(evidence.temporaryMaterial.allTemporaryZipsDeleted, true);
  assert.equal(evidence.temporaryMaterial.allTemporarySubsetsDeleted, true);
  assert.equal(evidence.temporaryMaterial.rawZipCommitted, false);
  assert.equal(evidence.temporaryMaterial.subsetCommitted, false);
});
