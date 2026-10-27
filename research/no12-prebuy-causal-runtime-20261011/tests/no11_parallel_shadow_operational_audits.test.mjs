import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {inspect} from '../tools/no11_parallel_saved_chart_watch.mjs';

const py=fs.readFileSync(new URL('../tools/no11_parallel_frozen_asset_probe.py',import.meta.url),'utf8');
const chart=fs.readFileSync(new URL('../tools/no11_parallel_saved_chart_watch.mjs',import.meta.url),'utf8');

test('concurrent disk-only C50 observer fails closed before file I/O on bad CLI arguments',async()=>{
 await assert.rejects(inspect([]),/NO11_PARALLEL_CHART_WATCH_REQUIRED_ARGUMENTS/);
 await assert.rejects(inspect(['--engine-root','a','--daily-run','b','--mask','c','--plan','d']),
   /NO11_PARALLEL_CHART_WATCH_ENGINE_ABSOLUTE_REQUIRED/);
 await assert.rejects(inspect(['--engine-root','/tmp','--daily-run','/tmp',
   '--mask','/tmp/x','--plan','/tmp/y','--change-mode','LIVE']),
   /NO11_PARALLEL_CHART_WATCH_UNKNOWN_OR_DUPLICATE_ARGUMENT/);
});
test('original capture plan and immutable private snapshot checks are non-negotiable',()=>{
 for(const marker of [
  "path.join(engine,'runtime/no11_rss_chart_50_prescreen.mjs')",
  'prescreen.validateNo11Chart50Plan',
  "path.join(engine,'tools/no11_saved_chart_diagnostics.mjs')",
  'diagnoser.diagnoseCaptures(frames)',
  'sha(bytes)===x.name.slice(9,73)',
  'SNAPSHOT_CONTENT_SHA_CHANGED',
  'SNAPSHOT_CURRENTLY_WRITING_RETRY_LATER',
  'SOURCE_PLAN_OR_READONLY_DIFFERENCE',
  'EXCEL_TOUCHED=False',
  'NOT_SELECTOR_NOT_BUY_SELL',
  'ORDER_TRANSMISSION=False',
 ])assert.ok(chart.includes(marker),marker);
 for(const forbidden of [
   /\bExcel\.Application\b/,/\bGetActiveObject\b/,/\bStart-Process\b/,
   /\b(?:writeFileSync|mkdirSync|renameSync|unlinkSync)\s*\(/,
   /\b(?:RssStockOrder|RssMarginOpenOrder|RssCancelOrder)\s*\(/
 ])assert.doesNotMatch(chart,forbidden);
});
test('frozen asset verifier loads pinned ORIGINAL components but never the live bootstrap',()=>{
 for(const marker of [
  'FrozenP1Scorer(p1_root, engine.parents[1], session)',
  'FrozenH235AsOf(h235_root, session)',
  'h235.original_model_count == 24',
  'original_arrival_tables(arrival)',
  'load_original_exit()',
  'original_p1_root(local)',
  'modelInferenceExecuted": False',
  'integratedShadowPreflightPassed": False',
  'externalCorporateActionReviewVerified": False',
  'realAccountReconciled": False',
  'orderTransmission": False',
 ])assert.ok(py.includes(marker),marker);
 for(const forbidden of [
  /\b(?:GetActiveObject|Excel\.Application|Workbooks|win32com|Dispatch|requests\.|urllib\.request)\b/,
  /\b(?:import no11_received_session_bootstrap|RssStockOrder|RssMarginOpenOrder|RssCancelOrder)\b/,
  /\b(?:fit|fit_transform|joblib\.dump|pickle\.dump)\s*\(/
 ])assert.doesNotMatch(py,forbidden);
});
