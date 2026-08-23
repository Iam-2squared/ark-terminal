import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const cli=fs.readFileSync('scripts/build_p25_research_paper_scoreboard.mjs','utf8');

test('scoreboard CLI enforces the predeclared research cost policy',()=>{
  assert.match(cli,/P25_RESEARCH_COST_POLICY_V1/);
  assert.match(cli,/commission does not match predeclared cost policy/);
  assert.match(cli,/slippage does not match predeclared cost policy/);
});

test('scoreboard CLI remains research-only and does not contain execution paths',()=>{
  assert.match(cli,/executable:false/);
  assert.doesNotMatch(cli,/RssStockOrder|RssMarginOpenOrder|RssMarginCloseOrder|RssModifyOrder|RssCancelOrder/);
  assert.doesNotMatch(cli,/executionAllowed\s*[:=]\s*true|brokerWriteAllowed\s*[:=]\s*true|paperTradingAllowed\s*[:=]\s*true|liveTradingAllowed\s*[:=]\s*true/);
});
