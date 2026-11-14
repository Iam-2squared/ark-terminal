"""Join saved 476-column causal matrices and the four frozen causal CONTEXT transforms.

Does not import the old State/signal runner; does not read target labels.
The full original 566-column R1 matrix was not archived. No legacy columns are regenerated.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
SUB=REPO/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'

def read(p):
    b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(grid, output):
    rows=read(grid);source_rows=read(SUB/'rows.json.gz');names=read(SUB/'names.json')
    freeze=read(HERE/'FEATURE_FAMILY_FREEZE.DRAFT.json')
    context=['CONTEXT/activeMinute','CONTEXT/pm','CONTEXT/lunchBoundary','CONTEXT/logClosedPrice']
    assert len(names)==476 and names+context==freeze['H0']
    assert not any(n.startswith(('STATE/','SIX/')) for n in names+context)
    manifest=read(SUB/'manifest.json')
    for f in ('rows.json.gz','names.json','raw-paths-evaluator-only.json.gz'):
        assert sha(SUB/f)==manifest[f],('SOURCE_HASH_MISMATCH',f)
    byday=collections.defaultdict(list)
    for r in source_rows:byday[r['session']].append(r)
    lookup={}
    for day, rr in byday.items():
        for index,r in enumerate(rr):
            assert r['id'] not in lookup
            lookup[r['id']]=(day,index,r)
    raw=read(SUB/'raw-paths-evaluator-only.json.gz')
    days=sorted({r['session'] for r in rows})
    wanted=collections.defaultdict(list)
    for i,r in enumerate(rows):wanted[r['session']].append((i,r))
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    x=np.lib.format.open_memmap(dest,mode='w+',dtype='float64',shape=(len(rows),480))
    sources=[];prefix_checks=0
    for di,day in enumerate(days):
        file=SUB/(day+'.npy.gz');h=sha(file)
        assert h==manifest[file.name],('SAVED_MATRIX_HASH_MISMATCH',day)
        with gzip.open(file,'rb') as f:base=np.load(f,allow_pickle=False)
        assert base.shape==(len(byday[day]),476)
        for i,r in wanted[day]:
            d,j,old=lookup[r['id']]
            assert d==day and old['eligible1'] and 0<=old['delay']<=30
            assert all(old[k]==r[k] for k in ('opportunity','session','minute','delay','quoteAvailable','computedThroughMinute'))
            assert r['computedThroughMinute'] is None or r['computedThroughMinute']<r['minute']
            prefix=[b for b in raw[r['opportunity']]['today'] if b[0]<r['minute']]
            assert not prefix or int(prefix[-1][0])==r['computedThroughMinute']
            now=r['minute'];age=now-540 if now<=690 else 150+now-750
            vals=[float(age),float(now>=750),float(now in (690,750,751)),math.log(float(prefix[-1][4])) if prefix else float('nan')]
            x[i,:476]=base[j];x[i,476:]=vals
            prefix_checks+=1
        blob=subprocess.check_output(['git','rev-parse','HEAD:'+str(file.relative_to(REPO))],cwd=REPO,text=True).strip()
        sources.append(dict(path=str(file.relative_to(REPO)),sha256=h,git_blob_sha=blob,rows=base.shape[0]))
        if di%20==0:print(json.dumps({'H0_saved_days_joined':di+1,'new_fits':0,'old_State_runs':0}),flush=True)
    x.flush();missing=int(np.isnan(x).sum());infinite=int(np.isinf(x).sum())
    assert infinite==0
    receipt=dict(status='H0_SAVED_CAUSAL_FEATURE_JOIN_PASS',rows=len(rows),features=480,
        saved_base_columns=476,mechanical_frozen_context_columns=4,legacy_columns_excluded=86,
        source_row_identity_checks=prefix_checks,source_matrices=sources,
        matrix_sha256=sha(dest),matrix_bytes=dest.stat().st_size,missing_numeric_cells=missing,
        infinite_cells=infinite,future_cutoff_violations=0,unknown_rows_dropped=0,
        source_feature_names_sha256=sha(SUB/'names.json'),source_rows_sha256=sha(SUB/'rows.json.gz'),
        original_R1_feature_names_sha256=sha(HERE/'R1_feature-names.json'),
        original_566_matrix_reconstructed=False,old_State_runs=0,old_signal_runs=0,old_policy_replays=0,
        target_label_reads=0,new_model_fits=0,provider_requests=0,protected_opens=0,
        numeric_basis='saved float32 476 columns promoted losslessly to float64; exact frozen four CONTEXT arithmetic on closed prefix',
        source_caveat='Inherited frozen Selector/upstream same-day metadata availability limitation; no new retrospective provider data.')
    (HERE/'H0_SAVED_FEATURE_JOIN_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_matrices'}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--grid',required=True);ap.add_argument('--output',required=True)
    a=ap.parse_args();run(a.grid,a.output)
