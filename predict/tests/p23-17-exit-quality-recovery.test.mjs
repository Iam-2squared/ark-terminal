import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { P23_8D_FROZEN_RATCHET_CONFIG } from '../daytrade/phase57-frozen-ratchet-exit.js';

// The runner has top-level market acquisition. This is a constant-contract test,
// not permission to execute that runner, acquire data, or remeasure EXIT.
// Evaluate the actual exported literal only; no copied/fabricated config fixture.
const source = fs.readFileSync(new URL('../daytrade/run-phase57-p23-17-exit-quality-recovery.mjs', import.meta.url), 'utf8');
const declarations = [...source.matchAll(/export const P23_17_PATIENT_EXIT_CONFIG = Object\.freeze\(\{([\s\S]*?)\}\);/g)];
assert.equal(declarations.length, 1, 'exactly one canonical constant declaration required');
const P23_17_PATIENT_EXIT_CONFIG = vm.runInNewContext(
  `Object.freeze({${declarations[0][1]}})`, {P23_8D_FROZEN_RATCHET_CONFIG}, {timeout: 1000});

assert.equal(P23_17_PATIENT_EXIT_CONFIG.configId,'STATE_PATIENT_RATCHET_V2');
assert.equal(P23_17_PATIENT_EXIT_CONFIG.hardStopAtr,P23_8D_FROZEN_RATCHET_CONFIG.hardStopAtr);
assert.equal(P23_17_PATIENT_EXIT_CONFIG.roundTripCostPct,P23_8D_FROZEN_RATCHET_CONFIG.roundTripCostPct);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.ratchetActivationAtr>=P23_8D_FROZEN_RATCHET_CONFIG.ratchetActivationAtr);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.ratchetGivebackAtrHold>=P23_8D_FROZEN_RATCHET_CONFIG.ratchetGivebackAtrHold);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.cautionConfirmBars>=P23_8D_FROZEN_RATCHET_CONFIG.cautionConfirmBars);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.minBarsBeforeStateExit>=P23_8D_FROZEN_RATCHET_CONFIG.minBarsBeforeStateExit);
console.log('P23.17 exit recovery regression test passed');
