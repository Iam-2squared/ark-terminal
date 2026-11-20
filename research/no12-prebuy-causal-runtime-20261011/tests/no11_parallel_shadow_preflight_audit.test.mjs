import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {audit} from '../tools/no11_parallel_shadow_preflight_audit.mjs';

const source=fs.readFileSync(new URL('../tools/no11_parallel_shadow_preflight_audit.mjs',import.meta.url),'utf8');
test('parallel audit fails closed on wrong inputs, before ANY spreadsheet operation',async ()=>{
  await assert.rejects(audit([]),/NO11_PARALLEL_REQUIRED_ARGUMENT_MISSING/);
  await assert.rejects(audit(['--engine-root','../../relative','--daily-run','x',
    '--mask','x','--chart','x','--previous-stage','x']),
    /NO11_PARALLEL_SOURCE_DIRECTORY_ABSOLUTE_REQUIRED/);
  await assert.rejects(audit(['--engine-root','/tmp','--daily-run','/tmp',
    '--mask','/tmp/a','--chart','/tmp/b','--previous-stage','/tmp/c','--evil','yes']),
    /NO11_PARALLEL_ARGUMENT_INVALID/);
});
test('parallel audit verifies source hashes and original chart membership',()=>{
  for(const marker of [
    'io.codeIdentity()','io.loadCaptures(run,full)',
    'makeObservedPassWatchMask(full,captures)',
    'validateNo11Chart50Plan({chartPlan:plan,mask,sessionDate:',
    'stage.chartPlanSha256===plan.planSha256',
    'PREVIOUS_COVERAGE_MEMBERSHIP_MISMATCH',
    'EXTERNALLY_REVIEWED','INTEGRATED_PREFLIGHT=NOT_PASSED',
    'DISK_READONLY_NO_EXCEL','ORDER_TRANSMISSION=False'
  ])assert.ok(source.includes(marker),marker);
  for(const forbidden of [
    /\b(?:Workbooks|Excel\.Application|GetActiveObject)\b/,
    /(?:writeFileSync|mkdirSync|renameSync|unlinkSync|spawnSync|execFileSync|subprocess|fetch\()/,
    /(?:RssStockOrder|RssMarginOpenOrder|RssCancelOrder)\s*\(/
  ])assert.doesNotMatch(source,forbidden);
});
test('only explicitly verified actual session/master can ever be reported, never automatically approved',()=>{
  assert.match(source,/fullShadow:false/);
  assert.match(source,/canLaunchFullShadow:false/);
  assert.match(source,/NOT_PASSED/);
  assert.match(source,/FILES_PRESENT_REVIEW_NOT_CERTIFIED/);
  assert.match(source,/PRESENT_NOT_INDEPENDENTLY_VERIFIED/);
});
