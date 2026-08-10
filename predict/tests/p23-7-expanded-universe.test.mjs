import assert from 'node:assert/strict';
import test from 'node:test';
import { EXPANDED_UNIVERSE, EXPANDED_UNIVERSE_POLICY } from '../daytrade/phase57-expanded-universe.js';

test('P23.7 expanded universe is frozen, unique, and preserves original five', () => {
  assert.equal(EXPANDED_UNIVERSE.length, 30);
  assert.equal(new Set(EXPANDED_UNIVERSE).size, 30);
  for (const symbol of ['7203.T','6758.T','9984.T','8306.T','8035.T']) {
    assert.ok(EXPANDED_UNIVERSE.includes(symbol));
  }
  assert.equal(EXPANDED_UNIVERSE_POLICY.frozenBeforeMeasurement, true);
  assert.equal(EXPANDED_UNIVERSE_POLICY.selectedFromP23_6Outcomes, false);
  assert.equal(EXPANDED_UNIVERSE_POLICY.dynamicWinnerFilteringAllowed, false);
  assert.equal(EXPANDED_UNIVERSE_POLICY.perSymbolExitTuningAllowed, false);
});
