import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const filename=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_rss_2026_frozen_selector_source_proxy.py');
test('No11 RSS Selector source proxy self test rejects partial 5M and future observation',()=>{
 const source=fs.readFileSync(filename,'utf8');
 assert.match(source,/eligibleForFrozenSelectorRuntime/);
 assert.match(source,/historicalBarArrivalTimeCertified/);
 assert.match(source,/ORDER_TRANSMISSION=False/);
 assert.doesNotMatch(source,/RssStockOrder|RssCancelOrder|Excel.Application|requests\.|urllib\.|socket\./);
 const exe=process.platform==='win32'?'python':'python3';
 const result=spawnSync(exe,['-B',filename,'--offline-self-test'],{encoding:'utf8',timeout:30000});
 assert.equal(result.status,0,'selftest: '+String(result.stderr||result.stdout||result.error));
 assert.match(result.stdout,/SOURCE_BRIDGE_OFFLINE_SELFTEST=PASS/);
});
test('No11 source proxy integration synthetic 3-runs: SHA, deterministic 5M, idempotence, tamper rejection',()=>{
 const dir=path.dirname(filename);
 const py="import gzip,hashlib,importlib,json,subprocess,sys,tempfile\nfrom pathlib import Path\nfrom types import SimpleNamespace\nsys.dont_write_bytecode=True\nsys.path.insert(0,sys.argv[1])\nm=importlib.import_module('no11_rss_2026_frozen_selector_source_proxy')\nassert m.PRIORITY_WATCH_COUNT==950, 'PRODUCTION_PRIORITY_COUNT_UNDEFINED_OR_CHANGED'\nm.EXPECTED_TOTAL=(30,29,1,290)\nm.RUN_LIMITS=(20,5,5)\nm.RUN_REQUESTED=(20,10,5)\nm.PRIORITY_WATCH_COUNT=5\nfull=[f'{1100+i:04d}.T' for i in range(30)]\nm.load_symbols=lambda path:full[20:]\nwith tempfile.TemporaryDirectory() as tmp:\n root=Path(tmp)\n master=root/'master.txt';master.write_text('\\n'.join(full)+'\\n')\n date='2026-10-13'\n bars=[]\n for n in range(565,575):\n  hh,mi=divmod(n,60)\n  bars.append({'label':f'{date}T{hh:02d}:{mi:02d}:00+09:00',\n               'open':100+n-565,'high':102+n-565,\n               'low':99+n-565,'close':101+n-565,'volume':10})\n offset=0\n runs=[]\n idx=[]\n cp_hashes=[]\n for ri,(n,req) in enumerate(zip(m.RUN_LIMITS,m.RUN_REQUESTED)):\n  name='rss-'+str(ri+1)*32\n  folder=root/name;folder.mkdir()\n  files=[];observed=0;unavailable=0;rows=0\n  for local in range(n):\n   pos=offset+local\n   sym=full[pos]\n   missing=(pos==20)\n   per=[] if missing else bars\n   status=m.EMPTY if missing else m.GOOD\n   source={'schemaId':'ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1',\n       'symbol':sym,'period':'1M','sourceFunction':'RssChart',\n       'evidenceMode':'OBSERVED_READ_ONLY',\n       'requestedBars':3000,'numericRows':len(per),'validRows':len(per),\n       'invalidRows':0,'duplicateRows':0,'status':status,\n       'rows':per,'productionReady':False,'orderTransmission':False,\n       'privateAccountDataIncluded':False,'vendorLabelCertified':False,\n       'actualHistoricalKnownAtCertified':False,\n       'vendorDecimalTokenCertified':False,'nativeSelectorProduced':False,\n       'modelTrainingReady':False}\n   filename=f'{local+1:05d}-{sym.replace(\".\",\"_\")}-1M.json'\n   blob=json.dumps(source,separators=(',',':')).encode()\n   (folder/filename).write_bytes(blob)\n   srcsha=hashlib.sha256(blob).hexdigest()\n   files.append({'symbol':sym,'file':filename,'sha256':srcsha,\n                 'status':status,'rows':len(per)})\n   idx.append({'symbol':sym,'sourceSha256':srcsha,\n                'productionReady':False,'orderTransmission':False})\n   if missing:unavailable+=1\n   else:observed+=1;rows+=len(per)\n  cp={'schemaId':'ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1',\n      'completed':n,'requested':req,'files':files,\n      'productionReady':False,'orderTransmission':False}\n  cp_file=folder/f'progress-{n:05d}.json'\n  cp_blob=json.dumps(cp).encode();cp_file.write_bytes(cp_blob)\n  cp_hash=hashlib.sha256(cp_blob).hexdigest();cp_hashes.append(cp_hash)\n  runs.append({'runDirectory':name})\n  offset+=n\n m.RUN_END_SHA=tuple(cp_hashes)\n index_path=root/'index.jsonl'\n idx_blob=('\\n'.join(json.dumps(x,separators=(',',':')) for x in idx)+'\\n').encode()\n index_path.write_bytes(idx_blob)\n m.INDEX_SHA256=hashlib.sha256(idx_blob).hexdigest()\n audit={'result':'SOURCE_SHA256_AND_ROW_AUDIT_PASS_NOT_SUPERVISED_TRAINING',\n        'symbolsRequested':4327,'dataRows':3705797,\n        'orderTransmission':False,'productionReady':False,'runs':runs}\n audit_path=root/'audit.json'\n audit_blob=json.dumps(audit).encode();audit_path.write_bytes(audit_blob)\n m.AUDIT_SHA256=hashlib.sha256(audit_blob).hexdigest()\n replay={'schemaId':'ARK_NO11_2026_RSS_CAUSAL_SOURCE_REPLAY_INDEX_V1',\n         'sourceIndexSha256':m.INDEX_SHA256,\n         'sourceAuditSha256':m.AUDIT_SHA256,\n         'nativeSelectorRebuilt':False,'nativeFirstEntryRebuilt':False,\n         'productionReady':False,'orderTransmission':False}\n replay_path=root/'replay.json'\n replay_blob=json.dumps(replay).encode();replay_path.write_bytes(replay_blob)\n m.REPLAY_SHA256=hashlib.sha256(replay_blob).hexdigest()\n frozen={'freezePayload':{'selectorSpecification':{\n  'featureUniverse':{'orderedNames':list(m.REQUIRED_FEATURES)},\n  'ranking':{'decisionTimesJst':list(m.DECISIONS),'topN':5},\n  'eligibility':{'maximumAgeWallClockMinutes':5,'forwardFillAllowed':False}}}}\n frozen_path=root/'predict'/'research'/'phase57-long-only-frozen-selector-v1.json'\n frozen_path.parent.mkdir(parents=True)\n frozen_path.write_text(json.dumps(frozen))\n subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)\n git=subprocess.run(['git','-C',str(root),'hash-object',\n    '--path=predict/research/phase57-long-only-frozen-selector-v1.json',\n    str(frozen_path)],capture_output=True,text=True,check=True)\n m.FREEZE_BLOB=git.stdout.strip()\n opts=SimpleNamespace(scope='all4327',capture_root=root,out_dir=root,\n      original_symbols=master,audit_report=audit_path,\n      replay_report=replay_path,source_index=index_path,\n      frozen_selector=frozen_path)\n m.main(opts)\n reports=list(root.glob('no11-2026-selector-source-gap-*.json'))\n assert len(reports)==1\n report=json.loads(reports[0].read_text())\n assert report['symbolsInspected']==30\n assert report['symbolsWithSourceBars']==29\n assert report['oneMinuteSourceRows']==290\n assert report['completeProvisionalFiveMinuteRows']==58\n assert report['provisionalDecisionPriceAvailableSymbolsBySession'][date]['09:30']==29\n assert report['provisionalDecisionPriceAvailableSymbolsBySession'][date]['10:00']==0\n assert report['priority950ProvisionalDecisionPriceAvailableSymbolsBySession'][date]['09:30']==5\n assert report['nativeSelectorRun'] is False\n assert report['supervisedTrainingRowsAdded2026']==0\n gz=root/report['fiveMinuteGzipPrivateFilename']\n out=list(gzip.open(gz,'rt'))\n assert len(out)==58\n assert all(json.loads(x)['eligibleForFrozenSelectorRuntime'] is False for x in out)\n m.main(opts)\n assert len(list(root.glob('no11-2026-5m-proxy-*.jsonl.gz')))==1\n bad=root/runs[0]['runDirectory']/f'00001-{full[0].replace(\".\",\"_\")}-1M.json'\n bad.write_bytes(b'TAMPER')\n try:m.main(opts)\n except RuntimeError as e: assert 'RAW_ARCHIVE_HASH_CHANGED' in str(e),str(e)\n else:raise AssertionError('tampered 1M source accepted')\n print('NO11_RSS_SELECTOR_PROXY_SYNTHETIC_THREE_RUNS=PASS')\n";
 const exe=process.platform==='win32'?'python':'python3';
 const result=spawnSync(exe,['-B','-c',py,dir],{encoding:'utf8',timeout:60000});
 assert.equal(result.status,0,'integration: '+String(result.stderr||result.stdout||result.error));
 assert.match(result.stdout,/NO11_RSS_SELECTOR_PROXY_SYNTHETIC_THREE_RUNS=PASS/);
});

test('No11 4327-symbol source index larger than 5MB passes SHA, tamper and 32MiB limit fail closed',()=>{
 const dir=path.dirname(filename);
 const py="import hashlib,importlib, json, sys, tempfile\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nsys.path.insert(0,sys.argv[1])\nm=importlib.import_module('no11_rss_2026_frozen_selector_source_proxy')\nwith tempfile.TemporaryDirectory() as temp:\n    p=Path(temp)/'index.jsonl'\n    with p.open('wb') as out:\n        for i in range(4327):\n            row={'symbol':f'{i:04d}.T',\n                 'sourceSha256':'a'*64,\n                 'sessions':{'2026-10-01':327, '2026-10-02':327},\n                 'firstSeenBarLabels':{'2026-10-01':'2026-10-01T09:00:00+09:00'},\n                 'lastSeenBarLabels':{'2026-10-01':'2026-10-01T15:30:00+09:00'},\n                 'paddingForRealistic8SessionCoverage':'S'*1280}\n            out.write((json.dumps(row,separators=(',',':'))+'\\n').encode())\n    n=p.stat().st_size\n    assert 5_000_000 < n < m.MAX_SOURCE_INDEX_BYTES, n\n    digest=hashlib.sha256(p.read_bytes()).hexdigest()\n    rows=m.strict_index(p,digest)\n    assert len(rows)==4327 and rows[0]['symbol']=='0000.T'\n    with p.open('r+b') as out:\n        out.write(b'X')\n    try:\n        m.strict_index(p,digest)\n    except RuntimeError as e:\n        assert 'INDEX_HASH_MISMATCH' in str(e),str(e)\n    else:\n        raise AssertionError('same-size content tamper passed')\n    with p.open('wb') as out:\n        out.truncate(m.MAX_SOURCE_INDEX_BYTES+1)\n    try:\n        m.strict_index(p,digest)\n    except RuntimeError as e:\n        assert 'FILE_SIZE_INVALID' in str(e),str(e)\n    else:\n        raise AssertionError('unbounded oversized file passed')\nprint('NO11_RSS_INDEX_5MB_BOUNDARY_SHA256_AND_SIZE_CAP=PASS')\n";
 const exe=process.platform==='win32'?'python':'python3';
 const result=spawnSync(exe,['-B','-c',py,dir],{encoding:'utf8',timeout:60000});
 assert.equal(result.status,0,'oversize regression: '+String(result.stderr||result.stdout||result.error));
 assert.match(result.stdout,/NO11_RSS_INDEX_5MB_BOUNDARY_SHA256_AND_SIZE_CAP=PASS/);
});

test('No11 production module defines every referenced global, including priority950 across full scope',()=>{
 const directory=path.dirname(filename);
 const python=[
   'import builtins,dis,importlib,inspect,sys,types',
   'sys.dont_write_bytecode=True',
   'sys.path.insert(0,sys.argv[1])',
   "module=importlib.import_module('no11_rss_2026_frozen_selector_source_proxy')",
   "assert module.PRIORITY_WATCH_COUNT==950",
   'names=set(vars(module))|set(vars(builtins))',
   'missing=set()',
   'def scan(code):',
   ' for op in dis.get_instructions(code):',
   "  if op.opname in ('LOAD_GLOBAL','LOAD_NAME') and op.argval not in names: missing.add(op.argval)",
   ' for c in code.co_consts:',
   '  if isinstance(c,types.CodeType): scan(c)',
   'for obj in vars(module).values():',
   ' if inspect.isfunction(obj) and obj.__module__==module.__name__: scan(obj.__code__)',
   "assert not missing, 'UNBOUND_GLOBALS: '+','.join(sorted(missing))",
   "print('NO11_PRODUCTION_GLOBAL_SYMBOLS_BOUND=PASS')",
 ].join('\n');
 const exe=process.platform==='win32'?'python':'python3';
 const r=spawnSync(exe,['-B','-c',python,directory],{encoding:'utf8',timeout:30000});
 assert.equal(r.status,0,'unbound globals in production source bridge: '+String(r.stderr||r.stdout||r.error));
 assert.match(r.stdout,/NO11_PRODUCTION_GLOBAL_SYMBOLS_BOUND=PASS/);
});
