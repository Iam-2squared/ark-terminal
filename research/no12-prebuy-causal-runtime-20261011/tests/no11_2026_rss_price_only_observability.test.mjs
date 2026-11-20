import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';

const script=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_rss_price_only_observability.py');
const run=code=>spawnSync(process.platform==='win32'?'python':'python3',['-B',...code],{encoding:'utf8',timeout:60000});
test('Observed RSS future evaluator never writes future values into as-of inputs, and refuses order APIs',()=>{
 const source=fs.readFileSync(script,'utf8');
 assert.match(source,/futureWindowFullyObserved/);
 assert.match(source,/highTouchPct/);
 assert.match(source,/SOURCE_RECEIPT_SHA/);
 assert.match(source,/new2026FrozenH235TrainingRows/);
 assert.doesNotMatch(source,/RssStockOrder|RssCancelOrder|Excel.Application|requests\\.|urllib\\.|socket\\.|subprocess\\./);
 const proc=run([script,'--offline-self-test']);
 assert.equal(proc.status,0,String(proc.stderr||proc.error||proc.stdout));
 assert.match(proc.stdout,/NO11_2026_PRICE_ONLY_OFFLINE_SELFTEST=PASS/);
});
test('Synthetic private 5M archive yields split as-of/evaluator files, fail-closed SHA and idempotence',()=>{
 const code="import gzip,hashlib,importlib,json,sys,tempfile\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nsys.path.insert(0,sys.argv[1])\nm=importlib.import_module('no11_2026_rss_price_only_observability')\nm.BARS=6\nm.ANCHORS=1\nday=m.DAYS[-1]\nwith tempfile.TemporaryDirectory() as directory:\n root=Path(directory)\n master=root/'original.txt'\n symbols=[f'{1000+i:04d}.T' for i in range(4326)]+['7203.T']\n master.write_text('\\n'.join(symbols)+'\\n',encoding='utf8')\n m.MASTER_SHA=m.sha(master)\n def bar(start):\n  hh,mm=divmod(start,60)\n  end=start+5\n  eh,em=divmod(end,60)\n  lh,lm=divmod(end-1,60)\n  return {\n   'schemaId':m.BAR_SCHEMA,'symbol':'7203.T','session':day,\n   'sourceIdentity':'MARKETSPEED_II_RSS_CHART_1M',\n   'componentOneMinuteRows':5,\n   'eligibleForFrozenSelectorRuntime':False,\n   'vendorFiveMinuteParityCertified':False,\n   'actualVendorAvailableAtCertified':False,\n   'productionReady':False,'orderTransmission':False,\n   'syntheticHistoricalAvailabilityRule':'LAST_LABEL_PLUS_1M',\n   'fiveMinuteWindowStart':f'{hh:02d}:{mm:02d}',\n   'lastSourceLabel':f'{day}T{lh:02d}:{lm:02d}:00+09:00',\n   'researchAssumedNotBefore':f'{day}T{eh:02d}:{em:02d}:00+09:00',\n   'open':100,'high':101,'low':99,'close':100,'volume':100\n  }\n source=root/'5m.gz'\n with source.open('wb') as fh:\n  with m.gzip_writer(fh) as z:\n   for minute in range(895,925,5):\n    z.write((json.dumps(bar(minute),sort_keys=True)+'\\n').encode())\n byday={d:0 for d in m.DAYS};byday[day]=6\n elig={d:{t:0 for t in m.CLOCKS} for d in m.DAYS}\n elig[day]['15:00']=1\n audit={\n  'schemaId':m.SOURCE_SCHEMA,\n  'status':'RESEARCH_PRICE_SOURCE_PROXY_CREATED_NOT_NATIVE_SELECTOR',\n  'scope':'all4327','completeProvisionalFiveMinuteRows':6,\n  'frozenDecisionClocksJst':list(m.CLOCKS),\n  'nonPriceFrozenFeatureMetadataNotInRssCapture':list(m.MISSING),\n  'nativeSelectorRun':False,'nativeFirstEntryRun':False,'nativeState9Run':False,\n  'productionReady':False,'orderTransmission':False,\n  'fiveMinuteGzipPrivateFilename':source.name,'fiveMinuteGzipSha256':m.sha(source),\n  'observedCompleteFiveMinuteRowsBySession':{day:6},\n  'provisionalDecisionPriceAvailableSymbolsBySession':elig\n }\n receipt=root/'receipt.json'\n receipt.write_text(json.dumps(audit),encoding='utf8')\n m.SOURCE_RECEIPT_SHA=m.sha(receipt)\n m.main(receipt,source,master,root)\n reports=list(root.glob('no11-2026-price-only-observability-*.json'))\n assert len(reports)==1\n report=json.loads(reports[0].read_text())\n assert report['decisionPriceAnchors']==1\n assert report['byDayDecision'][day]['15:00']['fullFutureWindow']==1\n assert report['byDayDecision'][day]['15:00']['highTouch2Observed']==0\n inp=list(gzip.open(root/report['asofOnlyPrivateFilename'],'rt'))\n ev=list(gzip.open(root/report['futureEvaluatorPrivateFilename'],'rt'))\n assert len(inp)==len(ev)==1\n a=json.loads(inp[0]);b=json.loads(ev[0])\n assert 'highTouchPct' not in a and 'observedReferencePrice' not in b\n assert b['highTouchPct']['2'] is False and b['futureWindowFullyObserved'] is True\n m.main(receipt,source,master,root)\n assert len(list(root.glob('no11-2026-price-only-observability-*.json')))==1\n with source.open('wb') as fh:fh.write(b'INVALID')\n try:\n  m.main(receipt,source,master,root)\n except RuntimeError as e:\n  assert '5M_SOURCE_SHA_MISMATCH' in str(e),str(e)\n else:\n  raise AssertionError('source file corruption accepted')\n print('NO11_2026_PRICE_ONLY_RESEARCH_SYNTHETIC=PASS')\n";
 const proc=run(['-c',code,path.dirname(script)]);
 assert.equal(proc.status,0,String(proc.stderr||proc.error||proc.stdout));
 assert.match(proc.stdout,/NO11_2026_PRICE_ONLY_RESEARCH_SYNTHETIC=PASS/);
});
