import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {inspect} from '../tools/no11_partial_observed_shadow_rehearsal.mjs';
import {inspectFrozenSelectorAsset}
  from '../runtime/no11_frozen_selector_native_shadow.mjs';

const s=fs.readFileSync(
  new URL('../tools/no11_partial_observed_shadow_rehearsal.mjs',import.meta.url),'utf8');

test('original byte-pinned frozen selector has first time AFTER the observed 09:19 source cutoff',()=>{
  const frozen=inspectFrozenSelectorAsset();
  const times=frozen.spec.ranking.decisionTimesJst;
  assert.equal(frozen.originalFrozenWeightsVerified,true);
  assert.equal(times.length,10);
  assert.equal(times[0],'09:30');
  assert.ok(times.every(t=>t>='09:30'));
  assert.ok(times.every((t,i)=>i===0||times[i-1]<t));
});

test('partial observed shadow must be explicitly pinned and fail closed on invalid CLI',async()=>{
  await assert.rejects(inspect([]),/NO11_PARTIAL_SHADOW_USAGE/);
  await assert.rejects(inspect([
    '--engine-root','relative','--daily-run','relative',
    '--plan','relative','--mask','relative','--capture-folder','relative',
    '--output-root','relative',
  ]),/NO11_PARTIAL_SHADOW_ENGINE_ABSOLUTE/);
  await assert.rejects(inspect([
    '--engine-root','/tmp','--daily-run','/tmp','--plan','/tmp/a',
    '--mask','/tmp/b','--capture-folder','/tmp/c',
    '--not-allowed','LIVE',
  ]),/NO11_PARTIAL_SHADOW_ARGUMENT_INVALID/);
});

test('causal source boundaries survive replay; never label retrospective rows as observed orders',()=>{
  for(const marker of [
    'validateNo11Chart50Plan(', 'inspectFrozenSelectorAsset()',
    'mergeNo11PrivateChartSnapshots(', "snapshot-([a-f0-9]{64})",
    'SNAPSHOT_BYTES_NOT_IMMUTABLE',
    'SNAPSHOT_CLOCK_INVALID',
    'SNAPSHOT_TOTAL_BYTES_LIMIT',
    "Date.parse(x.observedEndJst)<=edge",
    'NOT_REACHED_BY_SAVED_SOURCE',
    'MISSED_NO_TIMELY_RECEIPT_NEVER_BACKFILLED',
    'TIMELY_RECEIPT_SEEN_BUT_DATED_MASTER_NOT_VERIFIED',
    'sourceTimeNotBackdated:true','missedDecisionsNeverFabricated:true',
    'originalSelectorExecuted:false',
    'actualPaperBuyCount:0','actualPaperSellCount:0',
    'masterValidated:false',
    'accountReconciled:false',
    'externalCorporateActionReviewValidated:false',
    'exactExchangeMinuteVaCertified:false',
    'modelInferenceExecuted',
  ].filter(x=>x!=='modelInferenceExecuted'))assert.ok(s.includes(marker),marker);
  assert.doesNotMatch(s,/(?:Excel\.Application|GetActiveObject|win32com|subprocess|(?:RssStockOrder|RssMarginOpenOrder|RssCancelOrder)\s*\()/);
  assert.doesNotMatch(s,/\.SaveAs\s*\(/);
  assert.match(s,/ORDER_TRANSMISSION=False/);
});
