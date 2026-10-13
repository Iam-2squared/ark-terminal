import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import path from 'node:path';

test('Frozen original two State9 engines: deterministic synthetic sanity, strictly read only',()=>{
 const src=path.resolve('research/state9-structural-exit-v2-20261003/FROZEN_SOURCE');
 const py=String.raw\`
import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
frozen=Path(sys.argv[1])
sys.path.insert(0,str(frozen))
from candidate.api import Engine as Candidate
from independent.api import Engine as Independent
profile=json.loads((frozen/'profile.json').read_text())
a=Candidate(profile);b=Independent(profile)
seen=0
for t in list(range(1,34))+[151,211,212,213,214]:
    c=100+(t%11)
    raw={'t':t,'o':str(c),'h':str(c+1),'l':str(c-1),'c':str(c),'known_at':t,'source':'OFFLINE_SYNTHETIC_ONLY','auction':('TERMINAL_AUCTION_MINUTE' if t==151 else 'OPENING_MIXED_MINUTE' if t in (1,211) else 'CONTINUOUS')}
    x=a.step(t,raw,case_id='SYNTHETIC_SMOKE')
    y=b.step(t,raw,case_id='SYNTHETIC_SMOKE')
    assert x['numeric_status']=='ACCEPTED' and y['numeric_status']=='ACCEPTED'
    assert all(x.get(k)==y.get(k) for k in ('primary','basis','current_semantics_observed','activity','context','leg_direction','fast_flag','observed_at','numeric_status')),str(t)
    seen+=1
assert seen==38
print('NO11_FROZEN_ORIGINAL_DUAL_ENGINE_SYNTHETIC=PASS')
\`;
 const exe=process.platform==='win32'?'python':'python3';
 const p=spawnSync(exe,['-B','-c',py,src],{encoding:'utf8',timeout:60000,
    env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
 assert.equal(p.status,0,\`python failed: \${p.stderr||p.error}\`);
 assert.match(p.stdout,/NO11_FROZEN_ORIGINAL_DUAL_ENGINE_SYNTHETIC=PASS/);
});
