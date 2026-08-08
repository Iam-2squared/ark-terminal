import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeEntryResearchContext, PHASE56_3_SAFETY } from '../chart/phase56-entry-research-context.js';

function bars() {
  const closes = [100,102,101,104,103,106,105,108,107,110,109,112,111,114,113,116,115,118,117,120];
  return closes.map((close, index) => ({
    time: index,
    open: close - 0.4,
    high: close + 1,
    low: close - 1,
    close,
    volume: 1000 + index * 20,
    vwap: close - 0.3,
  }));
}

test('Phase56.3 stays research-only and never enables execution', () => {
  const result = analyzeEntryResearchContext({ bars: bars(), swingRadius: 1 });
  assert.equal(result.phase, '56.3');
  assert.equal(result.status, 'ENTRY_RESEARCH_CONTEXT_READY');
  assert.equal(result.researchOnly, true);
  assert.equal(result.recommendationAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.brokerWriteAllowed, false);
  assert.equal(result.excelOrderWriteAllowed, false);
  assert.equal(result.rssOrderFunctionAllowed, false);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.paperTradingAllowed, false);
  assert.equal(result.transmitted, false);
});

test('Phase56.3 fails closed when setup context is unavailable', () => {
  const result = analyzeEntryResearchContext({ bars: bars().slice(0, 2) });
  assert.equal(result.status, 'OBSERVE');
  assert.equal(result.posture, 'WAIT');
  assert.ok(result.blockers.includes('SETUP_CONTEXT_NOT_READY'));
  assert.equal(result.executionAllowed, false);
});

test('Phase56.3 safety boundary remains read-only', () => {
  assert.deepEqual(PHASE56_3_SAFETY, {
    mode: 'ENTRY_RESEARCH_CONTEXT_READ_ONLY',
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    paperTradingAllowed: false,
    humanApprovalRequired: true,
  });
});
