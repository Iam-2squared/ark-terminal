"""Candidate A robustness/freeze audit; no policy mutation."""
from __future__ import annotations
import argparse,collections,gzip,hashlib,importlib.util,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CA=ROOT/'scripts/phase57_new_long_exit_candidate_a.py';COND=ROOT/'scripts/phase57_new_long_entry_exit_conditional.py'
CONTRACT=ROOT/'docs/evidence/phase57-new-long-exit-candidate-a-robustness-contract-2026-09-18.md';OUT=ROOT/'docs/evidence/phase57-new-long-exit-candidate-a-robustness'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
 b=enc(x);b=gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b;Path(p).write_bytes(b)
def mean(a):return statistics.mean(a) if a else None
def build():
 ca=mod('ca_audit',CA);c=mod('ca_cond',COND);ledger,base=ca.build()
 entries=c.read(c.BASE/'entry-parity/ledger.ndjson.gz')
 meta={}
 sessions=sorted({e['sessionDate'] for e in entries})
 for e in entries:
  for key in ('initialEvent','secondaryEvent'):
   op=e['decision'][key]
   if op is None:continue
   tags=[];ev=e['evaluator']
   if key=='secondaryEvent' and ev['primary60'] and ev.get('buyImprovementPct',0)>0:
    for d in (2,5):
     if ev['secondaryD30']['downside']>=d:tags.append(f'D30_{d}')
   meta[(e['anchorId'],op['eventType'])]={'symbol':e['symbol'],'session':e['sessionDate'],'block':1+sessions.index(e['sessionDate'])//19,'tags':tags}
 rows=[]
 for x in ledger:
  m=meta[(x['anchorId'],x['cohort'])];rows.append({**x,**m,'delta':x['result']['netPct']-x['fixed']})
 out={'status':'UNASSESSED','cohorts':{},'risk':{},'gates':{},'safety':base['safety'],'baseStatus':base['status']}
 for cohort in ('INITIAL_ENTRY_OPPORTUNITY','DIP_REPRICE_OPPORTUNITY'):
  rs=[x for x in rows if x['cohort']==cohort];cnt=collections.Counter(x['symbol'] for x in rs);top=[s for s,_ in cnt.most_common(3)]
  blocks={str(b):{'n':len(z:= [x for x in rs if x['block']==b]),'meanDelta':mean([x['delta'] for x in z])} for b in range(1,5)}
  ex=[x for x in rs if x['symbol'] not in top]
  out['cohorts'][cohort]={'blocks':blocks,'nonnegativeBlocks':sum(v['meanDelta'] is not None and v['meanDelta']>=0 for v in blocks.values()),'top3':top,'excludeTop3N':len(ex),'excludeTop3MeanDelta':mean([x['delta'] for x in ex]),'plus3Preservation':base['cohorts'][cohort]['plus3Preservation'],'plus5Preservation':base['cohorts'][cohort]['plus5Preservation']}
 for d,n in ((2,106),(5,21)):
  rs=[x for x in rows if f'D30_{d}' in x['tags']];assert len(rs)==n,(d,len(rs))
  out['risk'][str(d)]={'n':n,'fixedMean':mean([x['fixed'] for x in rs]),'candidateMean':mean([x['result']['netPct'] for x in rs]),'meanDelta':mean([x['delta'] for x in rs])}
 g={}
 for cohort,x in out['cohorts'].items():
  g[f'{cohort}_blocks3of4']=x['nonnegativeBlocks']>=3
  g[f'{cohort}_excludeTop3']=x['excludeTop3MeanDelta']>=0
  g[f'{cohort}_plus3']=x['plus3Preservation']['rate']==1
  g[f'{cohort}_plus5']=x['plus5Preservation']['rate']>=.9
 g['risk2_nonworse']=out['risk']['2']['meanDelta']>=0
 g['risk5_nonworse']=out['risk']['5']['meanDelta']>=0
 g['safety']=all(v is False for v in out['safety'].values())
 out['gates']=g;out['status']='NEW_LONG_EXIT_CANDIDATE_A_DEVELOPMENT_FREEZE_READY' if all(g.values()) else 'NEW_LONG_EXIT_CANDIDATE_A_ROBUSTNESS_BLOCKED'
 return rows,out
def run(outdir):
 rows,s=build();outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);write(outdir/'summary.json',s);write(outdir/'ledger.json.gz',rows)
 write(outdir/'manifest.json',{'schemaVersion':1,'status':s['status'],'inputPins':{str(CONTRACT.relative_to(ROOT)):sha(CONTRACT),str(CA.relative_to(ROOT)):sha(CA),str(COND.relative_to(ROOT)):sha(COND),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},'safety':s['safety']})
 print(json.dumps(s,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(OUT));a=p.parse_args();run(a.out)
