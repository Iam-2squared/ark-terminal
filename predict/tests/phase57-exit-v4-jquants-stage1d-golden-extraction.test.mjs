import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import {
  ALLOWED_SESSIONS,
  SAFETY,
  assertAllowedSession,
  assertSourceLineage,
  deterministicSubsetSha256,
  evaluateGithubArtifactApi,
  stripOutcomeFields,
  validateExtractionRequest,
} from '../../scripts/lib/phase57-stage1d-golden-extraction-contract.mjs';

const evidenceUrl = new URL('../research/phase57-exit-v4-jquants-stage1d-golden-extraction-v1.json', import.meta.url);
const digestUrl = new URL('../research/phase57-exit-v4-jquants-stage1d-golden-extraction-v1.sha256', import.meta.url);
const evidenceBytes = fs.readFileSync(evidenceUrl);
const evidence = JSON.parse(evidenceBytes);
const expectedDigest = fs.readFileSync(digestUrl, 'utf8').trim().split(/\s+/)[0];

const lineage = {
  runId: 34355199082,
  artifactId: 10106663226,
  artifactName: 'entry-holdout29-features-0-34355199082',
  digest: 'sha256:803b33bcc8f26acd4afbcea090215ef7e58214ad833206baf79cbaa367d18173',
};

test('Stage 1D evidence is hash locked at the unsupported extraction gate', () => {
  assert.equal(createHash('sha256').update(evidenceBytes).digest('hex'), expectedDigest);
  assert.equal(evidence.status, 'READ_ONLY_EXTRACTION_NOT_SUPPORTED');
  assert.equal(evidence.hardStop, 'ACTIVE');
  assert.equal(evidence.extraction.executed, false);
  assert.equal(evidence.extraction.fullArtifactDownloaded, 0);
});

test('allowed session filter is an exact three-date allowlist', () => {
  assert.deepEqual(ALLOWED_SESSIONS, ['2025-08-27', '2025-10-09', '2025-11-25']);
  for (const date of ALLOWED_SESSIONS) assert.equal(assertAllowedSession(date), date);
  assert.throws(() => assertAllowedSession('2025-08-28'), /UNAPPROVED_SESSION/);
  assert.throws(() => assertAllowedSession('180'), /INVALID_SESSION_DATE/);
});

test('outcome and future-label fields are recursively stripped from synthetic fixtures', () => {
  const clean = stripOutcomeFields({
    sessionDate: '2025-08-27',
    symbol: 'TEST',
    directionalReturnFromOpenPct: 0.1,
    futureReturn: 4,
    outcome: 'WIN',
    nested: {mfeBps: 10, label6: 1, direction: 'LONG'},
  });
  assert.deepEqual(clean, {
    sessionDate: '2025-08-27',
    symbol: 'TEST',
    directionalReturnFromOpenPct: 0.1,
    nested: {direction: 'LONG'},
  });
});

test('subset digest is deterministic and independent of object key order', () => {
  const a = {sessionDate: '2025-08-27', rows: [{symbol: 'A', rank: 1}]};
  const b = {rows: [{rank: 1, symbol: 'A'}], sessionDate: '2025-08-27'};
  assert.equal(deterministicSubsetSha256(a), deterministicSubsetSha256(b));
});

test('source lineage is mandatory and malformed lineage fails closed', () => {
  assert.equal(assertSourceLineage(lineage), true);
  assert.throws(() => assertSourceLineage({...lineage, digest: null}), /SOURCE_DIGEST_REQUIRED/);
  assert.throws(() => assertSourceLineage({...lineage, artifactId: 0}), /SOURCE_ARTIFACT_ID_REQUIRED/);
});

test('full archive, local filtering, EXIT and protected/fresh paths are denied', () => {
  const valid = {
    sessionDate: '2025-08-27', lineage, readOnly: true,
    materializesFullArtifact: false, transport: 'SERVER_SIDE_MEMBER_FILTER',
    providerSupportsMemberFilter: true, invokesExit: false, accessesProtectedOrFresh: false,
  };
  assert.equal(validateExtractionRequest(valid), true);
  assert.throws(() => validateExtractionRequest({...valid, materializesFullArtifact: true}), /FULL_ARTIFACT/);
  assert.throws(() => validateExtractionRequest({...valid, transport: 'DOWNLOAD_THEN_FILTER'}), /SERVER_SIDE_MEMBER_FILTER_REQUIRED/);
  assert.throws(() => validateExtractionRequest({...valid, invokesExit: true}), /EXIT_INVOCATION_FORBIDDEN/);
  assert.throws(() => validateExtractionRequest({...valid, accessesProtectedOrFresh: true}), /PROTECTED_OR_FRESH/);
});

test('official GitHub artifact boundary fails closed without member filtering', () => {
  const result = evaluateGithubArtifactApi({
    serverSideMemberFilter: false,
    serverSideMemberListing: false,
    downloadUnit: 'ZIP_ARCHIVE',
  });
  assert.equal(result.status, 'READ_ONLY_EXTRACTION_NOT_SUPPORTED');
  assert.equal(result.fullArtifactDownloadRequired, true);
  assert.equal(result.extractionExecuted, false);
});

test('all access counters and safety flags remain closed', () => {
  assert.ok(Object.values(evidence.accessLedger).every((value) => value === 0));
  assert.ok(Object.values(SAFETY).every((value) => value === false));
  assert.deepEqual(evidence.safety, SAFETY);
  assert.equal(evidence.eligibility.fullReplayEligibleSessions, 0);
  assert.equal(evidence.eligibility.confirmedTier2Sessions, 0);
});
