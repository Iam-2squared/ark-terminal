import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const location=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_price_only_scorecard_audit.py');
const py=process.platform==='win32'?'python':'python3';
const run=(code)=>spawnSync(py,['-B',...code],{encoding:'utf8',timeout:30000});

test('2026 RSS price-only observed future count audit: zero order and no Frozen model dispatch',()=>{
 const src=fs.readFileSync(location,'utf8');
 assert.match(src,/NO11_2026_PRICE_ONLY_SCORECARD=PASS_RESEARCH_ONLY/);
 assert.match(src,/sourceReportSha256/);
 assert.match(src,/definiteNotHitInObservedProxy/);
 assert.match(src,/unknownWithIncompleteFuture/);
 assert.match(src,/new2026SupervisedTrainingRows/);
 assert.doesNotMatch(src,/RssStockOrder|RssCancelOrder|Excel.Application|requests\.|urllib\.|socket\./);
 const r=run([location,'--offline-self-test']);
 assert.equal(r.status,0,'Python scorecard selftest failed '+String(r.stderr||r.error||r.stdout));
 assert.match(r.stdout,/NO11_2026_PRICE_ONLY_SCORECARD_OFFLINE_SELFTEST=PASS/);
});

test('2026 RSS scorecard rejects a future label-counting mismatch across 8x10 clocks',()=>{
 const code=[
  'import importlib,sys',
  'sys.path.insert(0,sys.argv[1])',
  "m=importlib.import_module('no11_2026_price_only_scorecard_audit')",
  'row={k:0 for k in m.COUNT_FIELDS}',
  "row.update(priceAnchors=100,fullFutureWindow=20,withFutureObserved=96,highTouch2Observed=15,highTouch3Observed=7,highTouch5Observed=3,highTouch2Unknown=77,highTouch3Unknown=78,highTouch5Unknown=79,lowTouch2Observed=11,lowTouch3Observed=7,lowTouch5Observed=2,lowTouch2Unknown=77,lowTouch3Unknown=78,lowTouch5Unknown=79)",
  'm.clock_counts(row)',
  "d={'schemaId':m.SOURCE_SCHEMA,'status':'PRICE_ONLY_OBSERVED_FUTURE_NO_FROZEN_SELECTOR','source5mRows':337023,'source5mSha256':'63389666d55a2cb4c21d9f9ba2fb8fbae2a92cdf3044d2b949798c66997d1f74','decisionPriceAnchors':59712,'nativeSelectorExecuted':False,'firstEntryExecuted':False,'nativeState9Executed':False,'new2026FrozenH235TrainingRows':0,'modelFitPerformed':False,'productionReady':False,'orderTransmission':False,'terminalAuctionsNotIncludedInHighLow':True,'futureUnknownNeverConvertedToNegative':True,'byDayDecision':{day:{clock:dict(row) for clock in m.CLOCKS} for day in m.DAYS}}",
  'out=m.verify_and_sum(d,enforce_production_evidence=False)',
  "assert out['sourceWindow']['clockSnapshots']==80",
  "assert out['counts']['priceAnchors']==8000",
  "assert out['thresholdBounds']['high5']['unknownWithIncompleteFuture']==6320",
  "assert out['thresholdBounds']['high5']['definiteNotHitInObservedProxy']==1440",
  "assert out['new2026SupervisedTrainingRows']==0",
  "d['byDayDecision'][m.DAYS[0]][m.CLOCKS[0]]['highTouch5Unknown']=99",
  'try:',
  ' m.verify_and_sum(d,enforce_production_evidence=False)',
  'except RuntimeError as e:',
  " assert 'UNKNOWN_OR_HIT_OVERCOUNT' in str(e) or 'UNKNOWN_OR_HIT_OVERCOUNT' in str(e),str(e)",
  'else:',
  " raise AssertionError('UNKNOWN_FUTURE_BAD_COUNT_WAS_ACCEPTED')",
  "print('NO11_80_CLOCK_PRICE_SCORECARD_CAUSAL_BOUNDARY=PASS')"
 ].join('\n');
 const r=run(['-c',code,path.dirname(location)]);
 assert.equal(r.status,0,String(r.stderr||r.error||r.stdout));
 assert.match(r.stdout,/NO11_80_CLOCK_PRICE_SCORECARD_CAUSAL_BOUNDARY=PASS/);
});
