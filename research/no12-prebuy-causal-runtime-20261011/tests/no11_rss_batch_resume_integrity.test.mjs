import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

test('No11 immutable RSS capture resume preserves completed checkpoint and rejects tampering',()=>{
 const script=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_rss_batch_resume_manifest.py');
 const src=fs.readFileSync(script,'utf8');
 assert.match(src,/ORIGINAL_DATA_UNCHANGED=True/);
 assert.match(src,/ORDER_TRANSMISSION=False/);
 assert.match(src,/NO11_RESUME_DATA_SHA256/);
 assert.doesNotMatch(src,/RssStockOrder\s*\(|requests\.|urllib\.|Excel\.Application|subprocess\./);
 const py="import hashlib,importlib.util,json,pathlib,re,sys,tempfile\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nloc=Path(sys.argv[1]).resolve()\nspec=importlib.util.spec_from_file_location('no11_resume',loc)\nm=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(m)\nrow={'label':'2026-10-13T09:01:00+09:00','open':100,'high':102,'low':99,'close':101,'volume':300}\ndef source(symbol):\n return {'schemaId':'ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1',\n   'symbol':symbol,'period':'1M','sourceFunction':'RssChart',\n   'evidenceMode':'OBSERVED_READ_ONLY','requestedBars':3000,\n   'status':m.GOOD,'numericRows':1,'validRows':1,'invalidRows':0,\n   'duplicateRows':0,'rows':[row],\n   'privateAccountDataIncluded':False,'vendorLabelCertified':False,\n   'actualHistoricalKnownAtCertified':False,'vendorDecimalTokenCertified':False,\n   'nativeSelectorProduced':False,'modelTrainingReady':False,\n   'productionReady':False,'orderTransmission':False}\nwith tempfile.TemporaryDirectory() as temp:\n p=Path(temp)\n orig=p/'all.txt'\n syms=[f'{n:04d}.T' for n in range(4327)]\n b=('\\n'.join(syms)+'\\n').encode()\n orig.write_bytes(b)\n m.MASTER_SHA256=hashlib.sha256(b).hexdigest()\n r=p/('rss-'+'a'*32);r.mkdir()\n entries=[]\n for k in range(20):\n  symbol=syms[k+20]\n  name=f'{k+1:05d}-{symbol.replace(\".\",\"_\")}-1M.json'\n  d=json.dumps(source(symbol),separators=(',',':')).encode()\n  (r/name).write_bytes(d)\n  entries.append({'symbol':symbol,'file':name,'sha256':hashlib.sha256(d).hexdigest(),'rows':1,'status':m.GOOD})\n progress={'schemaId':'ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1',\n    'completed':20,'requested':4307,'observedSymbols':20,\n    'unavailableSymbols':0,'rows':20,'files':entries,\n    'productionReady':False,'orderTransmission':False}\n (r/'progress-00020.json').write_text(json.dumps(progress),encoding='utf-8')\n sys.argv=['audit','--original-symbols',str(orig),'--prior-run',str(r),\n           '--expected-completed','20']\n m.main()\n out=list(p.glob('resume-after-*.txt'))\n assert len(out)==1\n left=out[0].read_text().splitlines()\n assert len(left)==4287 and left[0]=='0040.T' and left[-1]=='4326.T'\n assert out[0].with_suffix('.receipt.json').exists()\n # Any tampering in previously captured files is blocked.\n (r/entries[0]['file']).write_bytes(b'corrupt')\n try:\n  m.main()\n except RuntimeError as e:\n  assert 'NO11_RESUME_DATA_SHA256' in str(e),str(e)\n else:\n  raise AssertionError('corrupted stored data accepted')\nprint('NO11_IMMUTABLE_RESUME_SYNTHETIC=PASS')\n";
 const exe=process.platform==='win32'?'python':'python3';
 const p=spawnSync(exe,['-B','-c',py,script],{encoding:'utf8',timeout:60000});
 assert.equal(p.status,0,'offline python failed: '+String(p.stderr||p.error||p.stdout));
 assert.match(p.stdout,/NO11_IMMUTABLE_RESUME_SYNTHETIC=PASS/);
});
