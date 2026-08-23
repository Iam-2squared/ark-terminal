import test from 'node:test';
import assert from 'node:assert/strict';
import { P25CheckpointResearchExportInternals } from './p25-checkpoint-research-export.js';

test('checkpoint research export safety remains fail-closed', () => {
  assert.equal(P25CheckpointResearchExportInternals.assertSafety(), undefined);
});
