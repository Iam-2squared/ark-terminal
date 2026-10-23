"""NEW LONG EXIT Profit Protection v3: 50% running-MFE giveback."""
from __future__ import annotations
import argparse,gzip,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];V0=ROOT/'scripts/phase57_new_long_exit_profit_protection_v0_fast_fail.py'
CONTRACT=ROOT/'docs/evidence/phase57-new-long-exit-profit-protection-v3-contract-2026-09-18.md';OUT=ROOT/'docs/evidence/phase57-new-long-exit-profit-protection-v3-fast-fail'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
 b=enc(x);b=gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b;Path(p).write_bytes(b)
def sim(rows,fallback):
 protect=False;peak=0.;trans=[]
 for i,b in enumerate(rows):
  if b.get('missing'):return {'status':'UNKNOWN_MISSING','policyReturnPct':None,'transitions':trans}
  peak=max(peak,b['h'])
  if not protect:
   if peak>=3:protect=True;trans.append([b['slot'],'ENTER_PROTECT',peak,b['c']])
   continue
  if b['c']<=peak*.5:
   if i+1>=len(rows):break
   n=rows[i+1]
   if n.get('missing'):return {'status':'UNKNOWN_EXIT_REFERENCE','policyReturnPct':None,'signalBar':b['slot'],'transitions':trans}
   trans.append([b['slot'],'HALF_MFE_GIVEBACK',peak,b['c']])
   return {'status':'EXIT_REFERENCE','signalBar':b['slot'],'exitBar':n['slot'],'grossPct':n['o'],'policyReturnPct':n['o'],'transitions':trans}
 return {'status':'HOLD_TO_HORIZON','grossPct':fallback,'policyReturnPct':fallback,'transitions':trans}
def build():
 v0=mod('pp_v0_for_v3',V0);old=v0.sim;v0.sim=sim
 try:ledger,s=v0.build()
 finally:v0.sim=old
 s['status']='NEW_LONG_EXIT_PROFIT_PROTECTION_V3_FAST_FAIL_PASS' if all(s['gates'].values()) else 'NEW_LONG_EXIT_PROFIT_PROTECTION_V3_FAST_FAIL_KILL'
 return ledger,s
def run(outdir):
 ledger,s=build();outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
 write(outdir/'summary.json',s);write(outdir/'ledger.json.gz',[{k:v for k,v in x.items() if k!='rows'} for x in ledger])
 write(outdir/'manifest.json',{'schemaVersion':1,'status':s['status'],'inputPins':{str(CONTRACT.relative_to(ROOT)):sha(CONTRACT),str(V0.relative_to(ROOT)):sha(V0),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},'anchorIdentitySHA256':s['anchorIdentitySHA256'],'safety':s['safety'],'zeroCounters':s['zeroCounters']})
 print(json.dumps({'status':s['status'],'gates':s['gates'],'cohorts':s['cohorts']},indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(OUT));a=p.parse_args();run(a.out)
