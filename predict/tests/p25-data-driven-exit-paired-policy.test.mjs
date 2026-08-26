import test from 'node:test';
import assert from 'node:assert/strict';
import {P25_DATA_DRIVEN_PAIRED_SAFETY} from '../daytrade/phase57-p25-data-driven-exit-multisession.js';

test('paired lane cannot enable execution or consume fresh holdout',()=>{
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.executionAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.brokerWriteAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.excelOrderWriteAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.rssOrderFunctionAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.liveTradingAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.paperTradingAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.automaticPromotionAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.productionUpdateAllowed,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.transmitted,false);
  assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY.freshHoldoutConsumed,false);
});
