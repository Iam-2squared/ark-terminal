"""Separate read-only audit path from original saved prices and masks."""
from __future__ import annotations
import collections,gzip,json,hashlib,math
from decimal import Decimal
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'docs/evidence/phase57-post-prr-phase-a'
NEW=ROOT/'docs/evidence/phase57-post-prr-phase-a-plus/cycle-20260929-01'
def j(path):
 if path.exists():return json.loads(path.read_text())
 with gzip.open(Path(str(path)+'.gz'),'rt') as f:return json.load(f)
def gz(path):
 with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def d(x):return Decimal(str(x))
def check():
 manifest=j(OLD/'MANIFEST.json')
 for f,h in manifest['fileSha256'].items():assert sha(OLD/f)==h,('old source changed',f)
 for f,h in manifest['scriptSha256'].items():assert sha(ROOT/f)==h,('old script changed',f)
 assert sha(NEW/'A_PLUS_PRECOMMIT.json')==(NEW/'A_PLUS_PRECOMMIT.sha256').read_text().split()[0]
 assert sha(NEW/'ANALYSIS_SPEC.json')==(NEW/'ANALYSIS_SPEC.sha256').read_text().split()[0]
 orig=gz(OLD/'ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz');m=gz(OLD/'COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz');a=gz(NEW/'INTENT_UNIVERSE_ROWS.jsonl.gz')
 assert len(orig)==len(m)==len(a)==1725
 O={(x['world'],x['arm'],x['entryId']):x for x in orig};M={(x['world'],x['arm'],x['entryId']):x for x in m};A={(x['world'],x['arm'],x['entryId']):x for x in a}
 assert len(O)==len(M)==len(A)==1725 and O.keys()==M.keys()==A.keys()
 maskErrors=[];accountErrors=[];intentErrors=[]
 for k,x in O.items():
  v=M[k];r=A[k];pair=x['controlExitPrice'] is not None and x['ccmgExitPrice'] is not None
  assert pair==v['paired_outcome_known']==r['labelKnown']
  if pair:
   dc=d(x['ccmgExitPrice'])*d(x['quantity'])-d(x['entryCostJpy'])*d('1.0005')
   dr=d(x['controlExitPrice'])*d(x['quantity'])-d(x['entryCostJpy'])*d('1.0005')
   dy=dc-dr;dn=100*dy/d(x['entryCostJpy'])
   if dy!=d(r['deltaPnlJpy']) or dn!=d(r['deltaNetPp']) or dc!=d(x['normalizedCcmgPnlJpy']) or dr!=d(x['normalizedControlPnlJpy']):accountErrors.append(k)
  else:
   if r['deltaPnlJpy'] is not None or r['deltaNetPp'] is not None:maskErrors.append(k)
  c=x['ccmgFirstIntentMinute'];control=x['controlDecisionMinute']
  cls='NO_CCMG_INTENT_IN_RECORDED_SCOPE' if c is None else 'CCMG_FIRST_WHILE_CONTROL_ACTIVE' if c<control else 'CONTROL_INTENT_ALREADY_ISSUED' if c>control else 'SAME_TIME_INTENT_UNRESOLVED'
  if cls!=r['intentClass'] or (c is not None)!=r['firstIntentKnown']:intentErrors.append(k)
 assert not maskErrors and not accountErrors and not intentErrors
 census=j(NEW/'INTENT_CENSUS.json')['arms'];group=j(NEW/'FINE_BUCKET_ROUTE_RESULTS.json')['rows'];decomp=j(NEW/'ACCOUNTING_AND_PRIMARY_DECOMPOSITION.json')['byArmComparison']
 checks={}
 for arm,n,ni,nk in [('IM',819,376,728),('R1',795,343,706)]:
  aa=[r for r in a if r['world']=='ALL_100' and r['arm']==arm]
  assert len(aa)==n and sum(x['firstIntentKnown'] for x in aa)==ni and sum(x['labelKnown'] for x in aa)==nk
  miss={r['entryId'] for r in aa if r['firstIntentKnown'] and not r['labelKnown']}
  conly={r['entryId'] for r in aa if r['controlOutcomeKnown'] and not r['ccmgOutcomeKnown']}
  assert miss==conly and len(miss)==80 and census[arm]['I_minus_K_IDs']==sorted(miss)
  assert all(r['fillStatus']=='MISSING_EXECUTION_REFERENCE' for r in aa if r['entryId'] in miss)
  for band,lo,hi in [('<1',None,1),('[1,3)',1,3),('[3,5)',3,5),('[5,10)',5,10),('[10,inf)',10,None)]:
   bandrows=[r for r in aa if (lo is None or d(r['futureUpsidePctEvaluatorOnly'])>=lo) and (hi is None or d(r['futureUpsidePctEvaluatorOnly'])<hi)]
   known=[r for r in bandrows if r['labelKnown']]
   x=group[f'{arm}|ALL_100|ALL|ALL|{band}']['component']
   assert len(bandrows)==x['N_total'] and len(known)==x['N_known']
   assert sum((d(r['deltaPnlJpy']) for r in known),Decimal(0))==d(x['sumDeltaJpy'])
  total=sum((d(r['deltaPnlJpy']) for r in aa if r['labelKnown']),Decimal(0))
  comp=group[f'{arm}|ALL_100|ALL|ALL|ALL']['component'];same=group[f'{arm}|ALL_100|ALL|ALL|ALL']['frozenRouteOnPairedMask']
  assert total==d(comp['sumDeltaJpy']) and comp['N_known']==same['N_known']==nk
  prim=[r for r in aa if r['primary'] and r['labelKnown']]
  funded={r['entryId']:r for r in a if r['world']=='PRIMARY_FUNDED' and r['arm']==arm}
  qty=sum(((d(funded[r['entryId']]['quantity'])-100)*(d(r['ccmgExitPrice'])-d(r['controlExitPrice'])) for r in prim),Decimal(0))
  assert qty==d(decomp[arm+'|component']['quantityTermJpy'])
  assert d(decomp[arm+'|component']['identityResidualJpy'])==0
  checks[arm]={'all100N':n,'intentN':ni,'pairedN':nk,'unknownIntentN':80,'deltaJpy':str(total),'quantityTermJpy':str(qty)}
 tail=j(NEW/'TAIL_AND_LOO.json');
 for arm in ('IM','R1'):
  rs=[r for r in a if r['world']=='ALL_100' and r['arm']==arm]
  name=arm+'|ALL_100|ALL|component';grossPlus=sum((max(d(r['deltaPnlJpy']),Decimal(0)) for r in rs if r['labelKnown']),Decimal(0));grossMinus=sum((max(-d(r['deltaPnlJpy']),Decimal(0)) for r in rs if r['labelKnown']),Decimal(0))
  assert grossPlus==d(tail['tail'][name]['grossGainJpy']) and grossMinus==d(tail['tail'][name]['grossLossJpy'])
  ss=sorted(set(x['session'] for x in rs));sy=sorted(set(x['symbol'] for x in rs));l=tail['allLeaveOneOut'][name]
  assert len([x for x in l if x['axis']=='session'])==len(ss)==24 and len([x for x in l if x['axis']=='symbol'])==len(sy)
  for item in l:
   z=sum((d(r['deltaPnlJpy']) for r in rs if r[item['axis']]!=item['omitted'] and r['labelKnown']),Decimal(0))
   assert z==d(item['remaining']['sumDeltaJpy'])
 spec=j(NEW/'BOOTSTRAP_SPEC.json');draw=np.load(NEW/'SESSION_DRAWS.npz')['session_counts'];rng=np.random.Generator(np.random.PCG64(20260929));ids=rng.integers(0,24,size=(10000,24),dtype=np.int16)
 expected=np.zeros_like(draw)
 for k in range(24):expected[:,k]=(ids==k).sum(axis=1)
 assert np.array_equal(draw,expected) and sha(NEW/'SESSION_DRAWS.npz')==spec['drawSha256']
 ci=j(NEW/'CLUSTER_CI_RESULTS.json');assert ci['bootstrapSpecSha256']==sha(NEW/'BOOTSTRAP_SPEC.json')
 # Independent vector arithmetic for the headline point and percentile.
 for arm in ('IM','R1'):
  rs=[r for r in a if r['world']=='ALL_100' and r['arm']==arm and r['labelKnown']]
  per=[sum((float(d(r['deltaPnlJpy'])) for r in rs if r['session']==day),0.) for day in spec['sessionIds']]
  replicate=draw@np.asarray(per);target=ci['estimates'][arm+'|ALL_100|ALL|component']['sumDeltaJpy']
  assert math.isclose(float(sum(per)),float(target['point']),rel_tol=0,abs_tol=1e-7)
  assert math.isclose(float(np.quantile(replicate,.025,method='linear')),target['low'],abs_tol=1e-7)
  assert math.isclose(float(np.quantile(replicate,.975,method='linear')),target['high'],abs_tol=1e-7)
 result={'schema':'phase57-a-plus-independent-audit-v1','status':'PASS_SAVED_ROWS_RECALCULATION_WITH_SOURCE_BLOCKERS','basisHead':'c70b981fd07128dfd9b18893b4aca3a387d17e3b','phaseAManifestVerifiedFiles':len(manifest['fileSha256']),'rowsRebuilt':len(a),'checks':checks,'bootstrapDrawExact':True,'bootstrapHeadlineCiVerified':True,'tailAndAllLooVerified':True,'upstreamSource':'static text inspected; binary trace and price path not independently opened','StateSignalAsOf':'BLOCKED_SOURCE','futureSuffixTest':'BLOCKED_SOURCE','newFit':0,'newPolicyReplay':0,'providerRequests':0,'protectedOpenings':0,'externalLlmRequests':0,'orders':0,'mainMerges':0}
 out=NEW/'INDEPENDENT_AUDIT.json'
 if out.exists():
  assert j(out)==result,'INDEPENDENT_AUDIT_REPRODUCIBILITY_DRIFT'
  print('INDEPENDENT_AUDIT_REPRO_PASS',result['status'])
 else:
  out.write_text(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
  print('INDEPENDENT_AUDIT',result['status'])
if __name__=='__main__':check()
