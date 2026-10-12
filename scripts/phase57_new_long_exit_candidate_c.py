"""NEW LONG EXIT Candidate C: Candidate A for INITIAL, Candidate B two-stage for DIP."""
from __future__ import annotations
import argparse,gzip,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CA=ROOT/'scripts/phase57_new_long_exit_candidate_a.py';CB=ROOT/'scripts/phase57_new_long_exit_candidate_b.py';CONTRACT=ROOT/'docs/evidence/phase57-new-long-exit-candidate-c-contract-2026-09-18.md';OUT=ROOT/'docs/evidence/phase57-new-long-exit-candidate-c-development'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
 b=enc(x);b=gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b;Path(p).write_bytes(b)
def build():
 ca=mod('cc_ca',CA);cb=mod('cc_cb',CB);la,sa=ca.build();lb,sb=cb.build()
 # exact same opportunity identity/order by cohort
 ka=[(x['anchorId'],x['cohort']) for x in la];kb=[(x['anchorId'],x['cohort']) for x in lb];assert ka==kb
 init='INITIAL_ENTRY_OPPORTUNITY';dip='DIP_REPRICE_OPPORTUNITY'
 out={'status':'UNASSESSED','cohorts':{},'risk':sb['risk'],'gates':{},'safety':sb['safety']}
 a=sa['cohorts'][init]
 out['cohorts'][init]={'n':a['n'],'candidateA':a['policy'],'policy':a['policy'],'candidateAPF':a['policyPF'],'policyPF':a['policyPF'],'plus3':a['plus3Preservation'],'plus5':a['plus5Preservation'],'route':'CANDIDATE_A'}
 out['cohorts'][dip]=dict(sb['cohorts'][dip]);out['cohorts'][dip]['route']='TWO_STAGE_DIP'
 g={}
 for cohort,x in out['cohorts'].items():
  g[f'{cohort}_mean']=x['policy']['mean']>=x['candidateA']['mean'];g[f'{cohort}_pf']=x['policyPF']>=x['candidateAPF'];g[f'{cohort}_p05']=x['policy']['p05']>=x['candidateA']['p05'];g[f'{cohort}_plus3']=x['plus3']['rate']>=.9;g[f'{cohort}_plus5']=x['plus5']['rate']>=.9
 g['risk2']=sb['risk']['2']['policy']['mean']>=sb['risk']['2']['candidateA']['mean'];g['risk5']=sb['risk']['5']['policy']['mean']>=sb['risk']['5']['candidateA']['mean'];g['safety']=all(v is False for v in out['safety'].values())
 out['gates']=g;out['status']='NEW_LONG_EXIT_CANDIDATE_C_DEVELOPMENT_PASS' if all(g.values()) else 'NEW_LONG_EXIT_CANDIDATE_C_KILL'
 ledger=[]
 amap={(x['anchorId'],x['cohort']):x for x in la}
 for x in lb:
  k=(x['anchorId'],x['cohort']);row=dict(x)
  if x['cohort']==init:
   row['candidateCNetPct']=x['candidateA'];row['route']='CANDIDATE_A'
  else:
   row['candidateCNetPct']=x['result']['netPct'];row['route']='TWO_STAGE_DIP'
  ledger.append(row)
 return ledger,out
def run(outdir):
 ledger,s=build();outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);write(outdir/'summary.json',s);write(outdir/'ledger.json.gz',ledger);write(outdir/'manifest.json',{'schemaVersion':1,'status':s['status'],'inputPins':{str(CONTRACT.relative_to(ROOT)):sha(CONTRACT),str(CA.relative_to(ROOT)):sha(CA),str(CB.relative_to(ROOT)):sha(CB),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},'safety':s['safety']});print(json.dumps(s,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(OUT));a=p.parse_args();run(a.out)
