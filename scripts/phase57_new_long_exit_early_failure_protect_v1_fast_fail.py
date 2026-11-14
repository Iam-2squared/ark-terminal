"""Early Failure Protection v1: observed +2 then CLOSE <= Entry."""
from __future__ import annotations
import argparse,gzip,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];V0=ROOT/'scripts/phase57_new_long_exit_early_failure_protect_v0_fast_fail.py'
CONTRACT=ROOT/'docs/evidence/phase57-new-long-exit-early-failure-protect-v1-contract-2026-09-18.md';OUT=ROOT/'docs/evidence/phase57-new-long-exit-early-failure-protect-v1-fast-fail'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
 b=enc(x);b=gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b;Path(p).write_bytes(b)
def policy(bars,fixed):
 armed=False;peak=0.
 for i,b in enumerate(bars):
  if b.get('missing'):break
  peak=max(peak,b['h'])
  if not armed:
   if peak>=2:armed=True
   continue
  if b['c']<=0 and i+1<len(bars) and not bars[i+1].get('missing'):
   n=bars[i+1];return {'status':'EARLY_FAILURE_EXIT','signalBar':b['slot'],'exitBar':n['slot'],'grossPct':n['o'],'netPct':n['o']-.05}
 return {'status':'FIXED12_FALLBACK','exitBar':fixed['exitBar'],'grossPct':fixed['grossPct'],'netPct':fixed['netPct']}
def build():
 v0=mod('efp0_for_v1',V0);old=v0.policy;v0.policy=policy
 try:ledger,s=v0.build()
 finally:v0.policy=old
 s['status']='NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V1_FAST_FAIL_PASS' if all(s['gates'].values()) else 'NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V1_FAST_FAIL_KILL'
 return ledger,s
def run(outdir):
 ledger,s=build();outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);write(outdir/'summary.json',s);write(outdir/'ledger.json.gz',ledger);write(outdir/'manifest.json',{'schemaVersion':1,'status':s['status'],'inputPins':{str(CONTRACT.relative_to(ROOT)):sha(CONTRACT),str(V0.relative_to(ROOT)):sha(V0),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},'anchorIdentitySHA256':s['anchorIdentitySHA256'],'safety':s['safety'],'zeroCounters':s['zeroCounters']});print(json.dumps(s,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(OUT));a=p.parse_args();run(a.out)
