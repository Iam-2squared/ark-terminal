import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const srcFile=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_rss_2026_source_replay_index.py');
test('No11 2026 RSS history index is purely source-only, immutable, and offline',()=>{
 const src=fs.readFileSync(srcFile,'utf8');
 assert.match(src,/POSTHOC_PRICE_INDEX_PASS_SELECTOR_ENTRY_NOT_REBUILT/);
 assert.match(src,/2026SupervisedTrainingExamples/);
 assert.match(src,/historicalActualKnownAtCertified/);
 assert.match(src,/FIRST950_OBSERVED/);
 assert.match(src,/ORDER_TRANSMISSION=False/);
 assert.doesNotMatch(src,/RssStockOrder|RssCancelOrder|Excel.Application|requests\.|urllib\.|socket\.|subprocess\./);
 const exe=process.platform==='win32'?'python':'python3';
 const r=spawnSync(exe,['-B',srcFile,'--offline-self-test'],
    {encoding:'utf8',timeout:30000});
 assert.equal(r.status,0,'No11 RSS prefix parser selftest failed: '+String(r.stderr||r.error||r.stdout));
 assert.match(r.stdout,/NO11_RSS_2026_REPLAY_INDEX_OFFLINE_SELFTEST=PASS/);
});
