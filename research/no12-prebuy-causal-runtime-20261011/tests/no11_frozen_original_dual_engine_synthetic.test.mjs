import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import path from 'node:path';

test('Frozen original two State9 engines: deterministic synthetic sanity, strictly read only',()=>{
 const src=path.resolve('research/state9-structural-exit-v2-20261003/FROZEN_SOURCE');
 const py="import json,sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nfrozen=Path(sys.argv[1])\nsys.path.insert(0,str(frozen))\nfrom candidate.api import Engine as Candidate\nfrom independent.api import Engine as Independent\nprofile=json.loads((frozen/'profile.json').read_text())\na=Candidate(profile);b=Independent(profile)\nseen=0\nfor t in list(range(1,34))+[151,211,212,213,214]:\n    c=100+(t%11)\n    raw={'t':t,'o':str(c),'h':str(c+1),'l':str(c-1),'c':str(c),'known_at':t,'source':'OFFLINE_SYNTHETIC_ONLY','auction':('TERMINAL_AUCTION_MINUTE' if t==151 else 'OPENING_MIXED_MINUTE' if t in (1,211) else 'CONTINUOUS')}\n    x=a.step(t,raw,case_id='SYNTHETIC_SMOKE')\n    y=b.step(t,raw,case_id='SYNTHETIC_SMOKE')\n    assert x['numeric_status']=='ACCEPTED' and y['numeric_status']=='ACCEPTED'\n    assert all(x.get(k)==y.get(k) for k in ('primary','basis','current_semantics_observed','activity','context','leg_direction','fast_flag','observed_at','numeric_status')),str(t)\n    seen+=1\nassert seen==38\nprint('NO11_FROZEN_ORIGINAL_DUAL_ENGINE_SYNTHETIC=PASS')\n";
 const exe=process.platform==='win32'?'python':'python3';
 const p=spawnSync(exe,['-B','-c',py,src],{encoding:'utf8',timeout:60000,
   env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
 assert.equal(p.status,0,'python failed: '+String(p.stderr||p.error));
 assert.match(p.stdout,/NO11_FROZEN_ORIGINAL_DUAL_ENGINE_SYNTHETIC=PASS/);
});
