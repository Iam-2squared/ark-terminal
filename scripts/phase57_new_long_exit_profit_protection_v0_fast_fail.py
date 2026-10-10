"""NEW LONG EXIT Profit Protection v0 FAST-FAIL; Development only."""
from __future__ import annotations
import argparse,gzip,hashlib,importlib.util,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'scripts/phase57_new_long_exit_path_study.py'
COND=ROOT/'scripts/phase57_new_long_entry_exit_conditional.py'
CONTRACT=ROOT/'docs/evidence/phase57-new-long-exit-profit-protection-v0-contract-2026-09-18.md'
OUT=ROOT/'docs/evidence/phase57-new-long-exit-profit-protection-v0-fast-fail'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted')}
ZERO={k:0 for k in ('selectorChanges','newEntryChanges','entryTimingResearch','existingExitChanges','lossDefenseIntegration','modelFit','modelPrediction','freshAccess','oosAccess','providerRequests','minuteResearch','capitalTuning','portfolioTuning','mainMerge')}
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
 b=enc(x);b=gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b;Path(p).write_bytes(b)
def rate(n,d):return {'n':n,'denominator':d,'rate':n/d if d else None}
def dist(a):return {'n':len(a),'mean':statistics.mean(a) if a else None,'min':min(a) if a else None,'max':max(a) if a else None}

def sim(rows,fallback):
 protect=False;peak=0.;prev=None;lower=0;trans=[]
 for i,b in enumerate(rows):
  if b.get('missing'):return {'status':'UNKNOWN_MISSING','policyReturnPct':None,'transitions':trans}
  newpeak=b['h']>peak;peak=max(peak,b['h'])
  if not protect:
   if peak>=3:
    protect=True;prev=b['c'];lower=0;trans.append([b['slot'],'ENTER_PROTECT',peak,b['c']])
   continue
  if newpeak:
   lower=0;prev=b['c'];trans.append([b['slot'],'NEW_HIGH',peak,b['c']]);continue
  lower=lower+1 if b['c']<prev else 0
  prev=b['c']
  if lower>=2:
   if i+1>=len(rows):break
   n=rows[i+1]
   if n.get('missing'):return {'status':'UNKNOWN_EXIT_REFERENCE','policyReturnPct':None,'signalBar':b['slot'],'transitions':trans}
   trans.append([b['slot'],'PERSISTENT_GIVEBACK',peak,b['c']])
   return {'status':'EXIT_REFERENCE','signalBar':b['slot'],'exitBar':n['slot'],'grossPct':n['o'],'policyReturnPct':n['o'],'transitions':trans}
 return {'status':'HOLD_TO_HORIZON','grossPct':fallback,'policyReturnPct':fallback,'transitions':trans}

def first_hit(rows,k):return next((b['slot'] for b in rows if b['h']>=k),None)
def full_retrace_after3(rows):
 t=first_hit(rows,3)
 if t is None:return None
 return next((b['slot'] for b in rows if b['slot']>t and b['c']<=0),None)
def preserve5(r,rows):
 t=first_hit(rows,5);assert t is not None
 if r['status']!='EXIT_REFERENCE':return True
 if r['exitBar']!=t:return r['exitBar']>t
 return next(b for b in rows if b['slot']==t)['o']>=5

def build():
 s=mod('pp_study',STUDY);c=mod('pp_cond',COND)
 for p,h in c.PINS.items():assert sha(ROOT/p)==h,p
 for p,h in c.PARITY_PINS.items():assert sha(c.BASE/'entry-parity'/p)==h,p
 src=c.read(ROOT/c.PATHS);assert src['providerRequests']==src['freshAccess']==src['oosAccess']==0
 paths={e['selectorEventId']:e for e in src['events']};entries=c.read(c.BASE/'entry-parity/ledger.ndjson.gz')
 ids=sorted(x['anchorId'] for x in entries);assert len(ids)==len(set(ids))==2743
 assert hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()==c.ANCHOR_SHA
 ledger=[]
 for e in entries:
  raw=paths[e['anchorId']]
  for key in ('initialEvent','secondaryEvent'):
   op=e['decision'][key]
   if op is None:continue
   p=s.prepare(op,raw);cov,rows=s.window(p,60)
   if not rows:continue
   base=rows[-1]['c'];r=sim(rows,base);mfe=max(0,max(b['h'] for b in rows));fr=full_retrace_after3(rows)
   ledger.append({'anchorId':e['anchorId'],'cohort':op['eventType'],'baseline':base,'mfe':mfe,'fullRetraceAfter3Bar':fr,'result':r,'rows':rows})
 out={'status':'UNASSESSED','anchorIdentitySHA256':c.ANCHOR_SHA,'cohorts':{},'gates':{},'safety':SAFETY,'zeroCounters':ZERO}
 for cohort in ('INITIAL_ENTRY_OPPORTUNITY','DIP_REPRICE_OPPORTUNITY'):
  rs=[x for x in ledger if x['cohort']==cohort];comp=[x for x in rs if x['result']['policyReturnPct'] is not None]
  w3=[x for x in rs if x['mfe']>=3];w5=[x for x in rs if x['mfe']>=5]
  fr=[x for x in w3 if x['fullRetraceAfter3Bar'] is not None]
  rescued=[x for x in fr if x['result']['status']=='EXIT_REFERENCE' and x['result']['exitBar']<x['fullRetraceAfter3Bar'] and x['result']['policyReturnPct']>0]
  out['cohorts'][cohort]={'n':len(rs),'baseline':dist([x['baseline'] for x in comp]),'policy':dist([x['result']['policyReturnPct'] for x in comp]),'signals':rate(sum(x['result']['status']=='EXIT_REFERENCE' for x in rs),len(rs)),
   'plus3':{'n':len(w3),'baseline':dist([x['baseline'] for x in w3]),'policy':dist([x['result']['policyReturnPct'] for x in w3])},
   'plus5Preservation':rate(sum(preserve5(x['result'],x['rows']) for x in w5),len(w5)),
   'fullRetraceAfter3':{'n':len(fr),'rescuedBeforeRetracePositive':rate(len(rescued),len(fr))}}
 g={}
 for cohort,x in out['cohorts'].items():
  g[f'G1_{cohort}_plus5']=x['plus5Preservation']['rate']>=.9
  g[f'G2_{cohort}_plus3_mean_nonworse']=x['plus3']['policy']['mean']>=x['plus3']['baseline']['mean']
  g[f'G3_{cohort}_overall_nonworse']=x['policy']['mean']>=x['baseline']['mean']
  g[f'G4_{cohort}_retrace_rescue50']=x['fullRetraceAfter3']['rescuedBeforeRetracePositive']['rate']>=.5
 g['G5_safety']=all(v is False for v in SAFETY.values()) and all(v==0 for v in ZERO.values())
 out['gates']=g;out['status']='NEW_LONG_EXIT_PROFIT_PROTECTION_V0_FAST_FAIL_PASS' if all(g.values()) else 'NEW_LONG_EXIT_PROFIT_PROTECTION_V0_FAST_FAIL_KILL'
 return ledger,out
def run(outdir):
 ledger,s=build();outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
 write(outdir/'summary.json',s);write(outdir/'ledger.json.gz',[{k:v for k,v in x.items() if k!='rows'} for x in ledger])
 write(outdir/'manifest.json',{'schemaVersion':1,'status':s['status'],'inputPins':{str(CONTRACT.relative_to(ROOT)):sha(CONTRACT),str(STUDY.relative_to(ROOT)):sha(STUDY),str(COND.relative_to(ROOT)):sha(COND),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},'anchorIdentitySHA256':s['anchorIdentitySHA256'],'safety':SAFETY,'zeroCounters':ZERO})
 print(json.dumps({'status':s['status'],'gates':s['gates'],'cohorts':s['cohorts']},indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(OUT));a=p.parse_args();run(a.out)
