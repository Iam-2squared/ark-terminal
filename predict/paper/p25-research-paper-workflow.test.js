import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const workflow = fs.readFileSync('.github/workflows/phase57-p25-research-paper.yml', 'utf8');

test('research Paper workflow is downstream of completed checkpoint evaluation', () => {
  assert.match(workflow, /workflow_run:/);
  assert.match(workflow, /Phase57 P25 Checkpointed Evaluation/);
  assert.match(workflow, /conclusion == 'success'/);
});

test('research Paper workflow persists to a separate research-only branch', () => {
  assert.match(workflow, /automation\/p25-paper-data/);
  assert.match(workflow, /data\/p25-paper\/state\.json/);
  assert.match(workflow, /data\/p25-paper\/daily\/\$\{SESSION_DATE\}\.json/);
  assert.doesNotMatch(workflow, /automation\/p25-evaluation-data:data\/p25-evaluations/);
});

test('workflow contains an explicit non-executable safety assertion', () => {
  assert.match(workflow, /state\.mode!=='research_offline_only'/);
  assert.match(workflow, /state\.executable!==false/);
  for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','freshHoldoutConsumed']) {
    assert.match(workflow, new RegExp(key));
  }
});

test('workflow never invokes broker, Excel, RSS or MARKETSPEED order commands', () => {
  assert.doesNotMatch(workflow, /RssStockOrder|RssMarginOpenOrder|RssMarginCloseOrder|RssModifyOrder|RssCancelOrder/);
  assert.doesNotMatch(workflow, /executionAllowed\s*[:=]\s*true|brokerWriteAllowed\s*[:=]\s*true|paperTradingAllowed\s*[:=]\s*true|liveTradingAllowed\s*[:=]\s*true/);
});
