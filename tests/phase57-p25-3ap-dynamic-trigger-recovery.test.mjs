import assert from 'node:assert/strict';
import fs from 'node:fs';

const workflow=fs.readFileSync('.github/workflows/phase57-p25-dynamic-management-persistence.yml','utf8');
assert.match(workflow,/predict\/daytrade\/phase57-p25-2f-postsession-point-in-time-replay\.js/);
for(const forbidden of ['executionAllowed: true','brokerWriteAllowed: true','excelOrderWriteAllowed: true','rssOrderFunctionAllowed: true','liveTradingAllowed: true','paperTradingAllowed: true']) assert.equal(workflow.includes(forbidden),false,forbidden);
console.log('P25.3AP dynamic persistence trigger recovery test passed');
