import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const name=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_rss_original_rc2_dual_technical.py');
const py=process.platform==='win32'?'python':'python3';
const run=(code,timeout=120000)=>spawnSync(py,['-B',...code],{
 encoding:'utf8',timeout,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}
});

test('2026 Frozen RC2 original technical engines accept full-source clock prefix and reject omitted minutes',()=>{
 const src=fs.readFileSync(name,'utf8');
 assert.match(src,/ORIGINAL_RC2_TECHNICAL/);
 assert.match(src,/previousReturnPairs/);
 assert.match(src,/actualBrokerFirstSeenTimeCertified/);
 assert.match(src,/NO11_RC2_FULL_SESSION_REQUIRED/);
 assert.match(src,/sourceBarLabelIntervalCertified/);
 assert.doesNotMatch(src,/RssStockOrder\\s*\\(|RssCancelOrder\\s*\\(|Excel\\.Application|requests\\.|urllib\\.|socket\\./);
 const p=run([name,'--offline-self-test']);
 assert.equal(p.status,0,p.stderr||String(p.error||p.stdout));
 assert.match(p.stdout,/NO11_RC2_2026_SYNTHETIC_TECHNICAL_SELFTEST=PASS/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});
test('2026 Frozen RC2 genuine full 327x2-bar synthetic duel and no native live claim',()=>{
 const code="import importlib,sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nsys.path.insert(0,sys.argv[1])\nm=importlib.import_module('no11_2026_rss_original_rc2_dual_technical')\nmodule=m.load_frozen(Path(sys.argv[2]))\ndates=m.SESSION_DAYS[-2:]\ndef make(day):\n rows=[]\n for n in m.SCHEDULE:\n  label=f'{day}T{n//60:02d}:{n%60:02d}:00+09:00'\n  price=200+(n-540)//30\n  rows.append({'label':label,'open':price,'high':price+1,\n     'low':price-1,'close':price,'volume':200})\n return rows\nold,current=make(dates[0]),make(dates[1])\nx=m.original_rc2_replay(old,current,'e'*64,module)\nassert x['acceptedRows']==327,x\nassert x['previousReturnPairs']==321\nassert x['twoOriginalEnginesAgreed'] is True\nassert x['actualHistoricalKnownAtCertified'] is False\nassert x['nativeLiveState9Connected'] is False\nassert x['jquantsSourceIdentityCertified'] is False\nprint('NO11_ORIGINAL_RC2_FULL_327_TWO_ENGINE_PARITY=PASS')\n";
 const dir=path.dirname(name);
 const frozen=path.resolve('research/state9-structural-exit-v2-20261003/FROZEN_SOURCE');
 const p=run(['-c',code,dir,frozen],180000);
 assert.equal(p.status,0,p.stderr||String(p.error||p.stdout));
 assert.match(p.stdout,/NO11_ORIGINAL_RC2_FULL_327_TWO_ENGINE_PARITY=PASS/);
});
