import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const root = new URL('../../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const json = path => JSON.parse(read('predict/research/' + path));
const audit = json('phase57-entry-baseline-resume-four-gates-2026-09-09.json');
const original = json('phase57-hybrid-p21-entry-baseline-precommit.json');
const cost = json('phase57-entry-baseline-cost-contract-v1.json');
test('resume amendment preserves exact 17 dates and does not allocate protected190', () => {
  assert.deepEqual(audit.allocation.sessionIds, original.allocation.sessions);
  assert.equal(new Set(audit.allocation.sessionIds).size, 17);
  assert.equal(audit.policyAmendment.protected190AuditIsBaselinePrerequisite, false);
  assert.equal(audit.protectedReserve.protectedBlocks.reduce((n, [a, b]) => n + b - a + 1, 0), 190);
  for (const key of ['entryDevelopmentAllocatedCount', 'entryValidationAllocatedCount', 'entryOosAllocatedCount', 'newlyOpenedCount', 'newOutcomeViewedCount', 'newPerformanceComputedCount']) assert.equal(audit.protectedReserve[key], 0);
  assert.equal(audit.protectedReserve.crossResearchStatus, 'UNKNOWN');
  assert.ok(Object.values(audit.safety).every(v => v === false));
});
test('archive file discovery cannot become fabricated universe or decision coverage', () => {
  const gate = audit.gates.marketWideRawArchive;
  assert.equal(gate.archiveMetadata.length, 4);
  assert.equal(gate.archiveMetadata.flatMap(x => x.files).length, 18);
  assert.equal(gate.fullyVerifiedSessions, 0);
  assert.equal(gate.universeCoverage, null);
  assert.equal(gate.decisionPointCoverage, null);
  assert.equal(audit.perSession.length, 17);
  assert.ok(audit.perSession.every(x => x.status === 'BLOCKED' && x.rawCoverage === null));
});
test('available artifact identity and synthetic parity do not assert causal replay GO', () => {
  const prior = audit.gates.p21PriorPack, adapter = audit.gates.hybridP21Adapter;
  assert.equal(prior.canonicalArtifactId, 9213298657);
  assert.equal(prior.artifactExpired, false);
  assert.notEqual(prior.artifactArchiveSha256, prior.canonicalSnapshotSha256);
  assert.equal(prior.sourceBytesVerified, false);
  assert.equal(prior.fullyVerifiedCausalSessions, 0);
  assert.equal(adapter.outputParityUsesExplicitSyntheticCachedBundle, true);
  assert.equal(adapter.actualPriorSelectionRefitParity, false);
  assert.equal(adapter.gateFullyPassed, false);
  assert.equal(audit.status, 'NO_GO_NOT_MEASURED');
  assert.equal(audit.measurement.allowed, false);
  assert.equal(audit.measurement.measuredSessions, 0);
  assert.equal(audit.measurement.performanceMetrics, null);
  assert.equal(audit.measurement.pitViolations, null);
  assert.equal(audit.allocation.baselineDiagnosticUsed, false);
});
test('cost is pinned to downstream return convention, not selector or paper costs', () => {
  assert.equal(cost.roundTripCostBps, 5);
  assert.equal(cost.roundTripCostPct * 100, cost.roundTripCostBps);
  assert.equal(cost.netReturnBpsFormula, 'grossDirectionalReturnBps - 5');
  assert.equal(cost.baselineOutcomesViewedAtFreeze, false);
  assert.equal(cost.automaticCostOverrideAllowed, false);
  assert.equal(cost.measurementAllowedByThisContractAlone, false);
  assert.equal(cost.excludedContracts[1].slippageBpsPerFill, 10);
  for (const source of cost.sources) {
    const bytes = Buffer.from(read(source.path));
    assert.equal(createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex'), source.gitBlobSha);
  }
  const exit = read(cost.sources[0].path);
  assert.ok(exit.includes('roundTripCostPct=0.05'));
  assert.ok(exit.includes('netReturnPct:gross-Number(roundTripCostPct)'));
});
test('audit and cost bytes match immutable evidence fingerprints', () => {
  const lines = read('predict/research/phase57-entry-baseline-resume-2026-09-09.sha256').trim().split('\n');
  assert.equal(lines.length, 2);
  for (const line of lines) {
    const [expected, path] = line.split('  ');
    assert.equal(createHash('sha256').update(read(path)).digest('hex'), expected);
  }
});
