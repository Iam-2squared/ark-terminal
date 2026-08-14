import assert from 'node:assert/strict';
import { P23_17_PATIENT_EXIT_CONFIG } from '../daytrade/run-phase57-p23-17-exit-quality-recovery.mjs';
import { P23_8D_FROZEN_RATCHET_CONFIG } from '../daytrade/phase57-frozen-ratchet-exit.js';

assert.equal(P23_17_PATIENT_EXIT_CONFIG.configId,'STATE_PATIENT_RATCHET_V2');
assert.equal(P23_17_PATIENT_EXIT_CONFIG.hardStopAtr,P23_8D_FROZEN_RATCHET_CONFIG.hardStopAtr);
assert.equal(P23_17_PATIENT_EXIT_CONFIG.roundTripCostPct,P23_8D_FROZEN_RATCHET_CONFIG.roundTripCostPct);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.ratchetActivationAtr>=P23_8D_FROZEN_RATCHET_CONFIG.ratchetActivationAtr);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.ratchetGivebackAtrHold>=P23_8D_FROZEN_RATCHET_CONFIG.ratchetGivebackAtrHold);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.cautionConfirmBars>=P23_8D_FROZEN_RATCHET_CONFIG.cautionConfirmBars);
assert.ok(P23_17_PATIENT_EXIT_CONFIG.minBarsBeforeStateExit>=P23_8D_FROZEN_RATCHET_CONFIG.minBarsBeforeStateExit);
console.log('P23.17 exit recovery regression test passed');