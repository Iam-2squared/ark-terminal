import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const file=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_state9_first_entry_source_join.py');
const python=process.platform==='win32'?'python':'python3';
const invoke=(args,timeout=60000)=>spawnSync(python,['-B',...args],{
  encoding:'utf8',timeout,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}
});

test('2026 RSS State9 x price asof bridge: rejects lookahead, false native First Entry and future fields',()=>{
 const text=fs.readFileSync(file,'utf8');
 for(const literal of [
  'originalSelectorWatchObserved','originalFirstEntryP1ScoreObserved',
  'firstEntryOriginalP1Q70FeatureInputsAvailable','nativeFirstEntryExecuted',
  'futurePriceOrTeacherIncluded','FROZEN_STATE9_ENTRY_EXCLUDED',
  'NO11_STAGE4_STATE_COUNT_OR_CLOCK_CONTRACT_DRIFT'
 ])assert.ok(text.includes(literal),'missing '+literal);
 for(const pattern of [/RssStockOrder/,/RssCancelOrder/,
   /Excel.Application/,/requests[.]/,/urllib[.]/,/socket[.]/])
    assert.doesNotMatch(text,pattern);
 const p=invoke([file,'--offline-self-test']);
 assert.equal(p.status,0,p.stderr||String(p.error||p.stdout));
 assert.match(p.stdout,/NO11_STAGE4_FIRST_ENTRY_RSS_STATE9_ASOF_JOIN_SYNTHETIC=PASS/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});

test('2026 RSS private 2x327 State9 + price gzip end-to-end rejects corrupted SHA and missing bars',()=>{
 const code="import gzip,hashlib,importlib,json,sys,tempfile\nfrom pathlib import Path\nfrom datetime import datetime,timedelta\nsys.dont_write_bytecode=True\nsys.path.insert(0,sys.argv[1])\nm=importlib.import_module('no11_2026_state9_first_entry_source_join')\ndef clock(n):return f'{n//60:02d}:{n%60:02d}'\ndef sr(sym,n,observed=False,state=None):\n label=f'{m.DAY}T{clock(n)}:00+09:00'\n return {\n  'schemaId':m.STATE_SCHEMA,\n  'scheduledClock':clock(n),'researchAssumedBarEnd':\n   (datetime.fromisoformat(label)+timedelta(minutes=1)).isoformat(),\n  'sourceLabel':label,'originalNumericStatus':'ACCEPTED',\n  'state9CurrentObserved':observed,'formalPrimary':state if observed else None,\n  'basis':'OBSERVED_FRESH' if observed else None,\n  'directionBasis':None,'activity':None,'originalSource':m.STATE_SOURCE,\n  'missingSourceBar':False,'actualBrokerKnownAtCertified':False,\n  'firstEntryP1NativeFeatureRowCertified':False,\n  'eligibleForNativeSelectorOrFirstEntry':False,\n  'futureOutcomeIncluded':False,'productionReady':False,\n  'orderTransmission':False,'symbol':sym,'session':m.DAY,\n  'sourceArchiveSha256':'f'*64\n }\ndef px(sym,time,day=None):\n day=day or m.DAY\n t=m.clock_number(time)\n start=clock(t-5)\n return {\n  'schemaId':m.PRICE_SCHEMA,\n  'researchId':f'{day}|{time}|{sym}',\n  'symbol':sym,'session':day,'decisionClockJst':time,\n  'observedReferencePrice':1250.0,'sourceBarWindow':start,\n  'researchAssumedSourceClosedAt':f'{day}T{time}:00+09:00',\n  'observedPriceAgeMin':0,\n  'frozenSelectorScoreAvailable':False,'modelReady':False,\n  'productionReady':False,'orderTransmission':False\n }\nwith tempfile.TemporaryDirectory() as d:\n root=Path(d)\n stfile=root/'asof.gz'\n with gzip.open(stfile,'wt',encoding='utf8') as w:\n  for sym in ('1001.T','1002.T'):\n   for minute in m.SESSION_TICKS:\n    r=sr(sym,minute,minute in (569,599),\n        'PULLBACK' if minute==599 and sym=='1001.T' else 'RISE')\n    if sym=='1002.T' and minute==599:\n      r.update(missingSourceBar=True,sourceLabel=None,researchAssumedBarEnd=None,\n       originalSource=None,originalNumericStatus='NOT_AVAILABLE',\n       state9CurrentObserved=False,formalPrimary=None,basis=None)\n    w.write(json.dumps(r,separators=(',',':'))+'\\n')\n stamp=hashlib.sha256(stfile.read_bytes()).hexdigest()\n state_iter=m.stream_gzip(root,stfile.name,stamp)\n lookup,symbols,counts=m.inspect_asof_rows(\n    state_iter,{'1001.T':0,'1002.T':1},expected_symbols=2,\n    expected_rows=654,expected_accepted=653,expected_missing=1,\n    expected_observed=3)\n assert len(symbols)==2 and counts['stateRows']==654\n pricefile=root/'prices.gz'\n with gzip.open(pricefile,'wt',encoding='utf8') as w:\n  for row in (px('1001.T','09:30'),px('1001.T','10:00'),\n              px('1002.T','09:30'),px('1002.T','10:00')):\n   w.write(json.dumps(row,separators=(',',':'))+'\\n')\n pricehash=hashlib.sha256(pricefile.read_bytes()).hexdigest()\n prices,pc=m.inspect_price_rows(\n   m.stream_gzip(root,pricefile.name,pricehash),\n   set(symbols),expected_total=4,expected_today=4)\n joined,summary,clocks=m.join_day_sources(lookup,symbols,prices)\n assert len(joined)==20\n assert summary['stateAndPriceResearchOverlap']==3,summary\n assert summary['overlapWithoutFrozenExcludedStates']==2,summary\n assert summary['reason:STATE9_CURRENT_NOT_OBSERVED']==1\n assert all(not x['nativeFirstEntryCandidateEmitted'] for x in joined)\n assert all(not x['productionReady'] and not x['orderTransmission'] for x in joined)\n assert not any('futureHigh' in x for x in joined)\n with pricefile.open('ab') as f:f.write(b'TAMPER')\n try:list(m.stream_gzip(root,pricefile.name,pricehash))\n except RuntimeError as exc:\n  assert 'GZIP_SHA_MISMATCH' in str(exc),str(exc)\n else:raise AssertionError('tampered source gzip accepted')\n print('NO11_STAGE4_SYNTHETIC_2_GROUP_GZIP_JOIN_TAMPER=PASS')\n";
 const p=invoke(['-c',code,path.dirname(file)]);
 assert.equal(p.status,0,p.stderr||String(p.error||p.stdout));
 assert.match(p.stdout,/NO11_STAGE4_SYNTHETIC_2_GROUP_GZIP_JOIN_TAMPER=PASS/);
});
