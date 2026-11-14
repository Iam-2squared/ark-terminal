"""NEW LONG EXIT Early Failure Protection v0: +1 observed then CLOSE <= Entry."""
from __future__ import annotations
import argparse,gzip,hashlib,importlib.util,json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COND=ROOT/'scripts/phase57_new_long_entry_exit_conditional.py'
CONTRACT=ROOT/'docs/evidence/phase57-new-long-exit-early-failure-protect-v0-contract-2026-09-18.md'
OUT=ROOT/'docs/evidence/phase57-new-long-exit-early-failure-protect-v0-fast-fail';COST=.05
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted')}
ZERO={k:0 for k in ('selectorChanges','newEntryChanges','candidateAChanges','modelFit','modelPrediction','freshAccess','oosAccess','providerRequests','minuteResearch','capitalTuning','portfolioTuning','mainMerge')}
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
 b=enc(x);b=gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b;Path(p).write_bytes(b)
def q(a,p):
 s=sorted(a);i=(len(s)-1)*p;lo=math.floor(i);hi=math.ceil(i);return s[lo]+(s[hi]-s[lo])*(i-lo)
def stats(a):return {'n':len(a),'mean':statistics.mean(a),'p05':q(a,.05),'min':min(a),'max':max(a)}
def pf(a):
 pos=sum(x for x in a if x>0);neg=-sum(x for x in a if x<0);return pos/neg if neg else None
def rate(n,d):return {'n':n,'denominator':d,'rate':n/d if d else None}
def policy(bars,fixed):
 armed=False;peak=0.
 for i,b in enumerate(bars):
  if b.get('missing'):break
  peak=max(peak,b['h'])
  if not armed:
   if peak>=1:armed=True
   continue
  if b['c']<=0 and i+1<len(bars) and not bars[i+1].get('missing'):
   n=bars[i+1];return {'status':'EARLY_FAILURE_EXIT','signalBar':b['slot'],'exitBar':n['slot'],'grossPct':n['o'],'netPct':n['o']-COST}
 return {'status':'FIXED12_FALLBACK','exitBar':fixed['exitBar'],'grossPct':fixed['grossPct'],'netPct':fixed['netPct']}
def build():
 c=mod('efp_cond',COND)
 for p,h in c.PINS.items():assert sha(ROOT/p)==h,p
 for p,h in c.PARITY_PINS.items():assert sha(c.BASE/'entry-parity'/p)==h,p
 src=c.read(ROOT/c.PATHS);assert src['providerRequests']==src['freshAccess']==src['oosAccess']==0
 paths={e['selectorEventId']:e for e in src['events']};entries=c.read(c.BASE/'entry-parity/ledger.ndjson.gz')
 ids=sorted(x['anchorId'] for x in entries);assert hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()==c.ANCHOR_SHA
 runtime=c.module('efp_runtime',c.RUNTIME);ledger=[]
 for e0 in entries:
  raw=paths[e0['anchorId']]
  for key in ('initialEvent','secondaryEvent'):
   op=e0['decision'][key]
   if op is None:continue
   a=c.adapt(op,raw)
   if a['status']!='REFERENCE_POSITION':continue
   f=runtime.replay(a,'FIXED12')
   if f['status']!='EXIT_REFERENCE':continue
   bars=[b for b in a['future'] if b['slot']<=f['exitBar']];r=policy(bars,f)
   first3=next((b['slot'] for b in bars if not b['missing'] and b['h']>=3),None);first5=next((b['slot'] for b in bars if not b['missing'] and b['h']>=5),None)
   ev=e0['evaluator'];tags=[]
   if key=='secondaryEvent' and ev['primary60'] and ev.get('buyImprovementPct',0)>0:
    for d in (2,5):
     if ev['secondaryD30']['downside']>=d:tags.append(f'D30_{d}')
   ledger.append({'anchorId':e0['anchorId'],'cohort':op['eventType'],'fixed':f['netPct'],'result':r,'first3':first3,'first5':first5,'riskTags':tags})
 out={'status':'UNASSESSED','anchorIdentitySHA256':c.ANCHOR_SHA,'cohorts':{},'risk':{},'gates':{},'safety':SAFETY,'zeroCounters':ZERO}
 for cohort in ('INITIAL_ENTRY_OPPORTUNITY','DIP_REPRICE_OPPORTUNITY'):
  rs=[x for x in ledger if x['cohort']==cohort];base=[x['fixed'] for x in rs];pol=[x['result']['netPct'] for x in rs];w3=[x for x in rs if x['first3']];w5=[x for x in rs if x['first5']]
  out['cohorts'][cohort]={'n':len(rs),'fixed':stats(base),'policy':stats(pol),'fixedPF':pf(base),'policyPF':pf(pol),'signals':rate(sum(x['result']['status']=='EARLY_FAILURE_EXIT' for x in rs),len(rs)),'plus3':rate(sum(x['result']['exitBar']>=x['first3'] for x in w3),len(w3)),'plus5':rate(sum(x['result']['exitBar']>=x['first5'] for x in w5),len(w5))}
 for d,n in ((2,106),(5,21)):
  rs=[x for x in ledger if f'D30_{d}' in x['riskTags']];assert len(rs)==n,(d,len(rs))
  out['risk'][str(d)]={'n':n,'fixed':stats([x['fixed'] for x in rs]),'policy':stats([x['result']['netPct'] for x in rs])}
 g={}
 for cohort,x in out['cohorts'].items():
  g[f'{cohort}_mean']=x['policy']['mean']>=x['fixed']['mean'];g[f'{cohort}_pf']=x['policyPF']>=x['fixedPF'];g[f'{cohort}_p05']=x['policy']['p05']>=x['fixed']['p05'];g[f'{cohort}_plus3']=x['plus3']['rate']>=.9;g[f'{cohort}_plus5']=x['plus5']['rate']>=.9
 g['risk2_nonworse']=out['risk']['2']['policy']['mean']>=out['risk']['2']['fixed']['mean'];g['risk5_nonworse']=out['risk']['5']['policy']['mean']>=out['risk']['5']['fixed']['mean'];g['safety']=all(v is False for v in SAFETY.values()) and all(v==0 for v in ZERO.values())
 out['gates']=g;out['status']='NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V0_FAST_FAIL_PASS' if all(g.values()) else 'NEW_LONG_EXIT_EARLY_FAILURE_PROTECT_V0_FAST_FAIL_KILL'
 return ledger,out
def run(outdir):
 ledger,s=build();outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);write(outdir/'summary.json',s);write(outdir/'ledger.json.gz',ledger);write(outdir/'manifest.json',{'schemaVersion':1,'status':s['status'],'inputPins':{str(CONTRACT.relative_to(ROOT)):sha(CONTRACT),str(COND.relative_to(ROOT)):sha(COND),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},'anchorIdentitySHA256':s['anchorIdentitySHA256'],'safety':SAFETY,'zeroCounters':ZERO});print(json.dumps(s,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(OUT));a=p.parse_args();run(a.out)
