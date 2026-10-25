"""NEW LONG EXIT v1: prior completed bar LOW breakdown FAST-FAIL."""
from __future__ import annotations
import argparse,gzip,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
V0=ROOT/'scripts/phase57_new_long_exit_loss_defense_fast_fail.py'
CONTRACT=ROOT/'docs/evidence/phase57-new-long-exit-v1-prior-low-break-contract-2026-09-18.md'
OUT=ROOT/'docs/evidence/phase57-new-long-exit-v1-prior-low-break-fast-fail'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
 b=enc(x);b=gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b;Path(p).write_bytes(b)

def sim(rows,fallback,cost=0,maxslot=None):
 state='HOLD';start=None;trans=[]
 for i,b in enumerate(rows):
  if b.get('missing'):return {'status':'UNKNOWN_MISSING','policyReturnPct':None,'transitions':trans}
  c=b['c']
  if state=='HOLD':
   if c<0:state='DEFENSIVE';start=b['slot'];trans.append([b['slot'],'DEFENSIVE',c])
  elif c>=0:
   state='HOLD';start=None;trans.append([b['slot'],'RECLAIM',c])
  else:
   prior=rows[i-1]
   if c < prior['l']:
    if i+1>=len(rows) or (maxslot is not None and rows[i+1]['slot']>maxslot):break
    n=rows[i+1]
    if n.get('missing'):return {'status':'UNKNOWN_EXIT_REFERENCE','policyReturnPct':None,'signalBar':b['slot'],'transitions':trans}
    trans.append([b['slot'],'PRIOR_BAR_LOW_BREAK',c,prior['l']])
    return {'status':'EXIT_REFERENCE','signalBar':b['slot'],'exitBar':n['slot'],'grossPct':n['o'],'policyReturnPct':n['o']-cost,'defensiveStartBar':start,'transitions':trans}
 return {'status':'HOLD_TO_HORIZON','grossPct':fallback,'policyReturnPct':fallback-cost,'transitions':trans}

def build():
 v0=mod('ld_v0_for_v1',V0);old=v0.sim;v0.sim=sim
 try:own,fixed,s=v0.build()
 finally:v0.sim=old
 s['rule']='HOLD -> negative CLOSE => DEFENSIVE; unreclaimed current CLOSE < immediately prior completed bar LOW => EXIT at next regular OPEN'
 s['status']='NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_PASS' if all(s['gates'].values()) else 'NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_KILL'
 return own,fixed,s

def run(outdir):
 own,fixed,s=build();outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
 write(outdir/'summary.json',s)
 write(outdir/'ledger.json.gz',[{'anchorId':x['anchorId'],'cohort':x['cohort'],'baseline':x['baseline'],'mfe':x['mfe'],'result':x['result']} for x in own])
 write(outdir/'manifest.json',{'schemaVersion':1,'status':s['status'],'inputPins':{str(CONTRACT.relative_to(ROOT)):sha(CONTRACT),str(V0.relative_to(ROOT)):sha(V0),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},'anchorIdentitySHA256':s['anchorIdentitySHA256'],'safety':s['safety'],'zeroCounters':s['zeroCounters']})
 print(json.dumps({'status':s['status'],'gates':s['gates'],'own60':{k:{'baselineMean':v['baseline']['mean'],'policyMean':v['policy']['mean'],'plus3':v['winnerPreservation']['3']['rate'],'plus5':v['winnerPreservation']['5']['rate'],'signals':v['signals']['rate']} for k,v in s['own60'].items()},'risk':s['risk']},indent=2))
 return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(OUT));a=p.parse_args();run(a.out)
