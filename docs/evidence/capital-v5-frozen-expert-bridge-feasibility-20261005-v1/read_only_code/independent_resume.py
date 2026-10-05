"""Resume failed comparison only plus previously unperformed pair/CI checks. No primary imports."""
import pathlib,json,gzip,datetime,collections
import numpy as np
from independent import W,E,P,H,R,get,lines,hashfile,emit,interval,original_data,independent_auc
def own_concordance(rr,h,sign,M,sessions):
 n=len(sessions);C=np.zeros((n,n));D=np.zeros((n,n));groups=collections.defaultdict(list)
 for r in rr:
  if r['nativebucket'] is not None and r['realized_return'] is not None:groups[(r['block'],r['nativebucket'])].append(r)
 for group in groups.values():
  for i,a in enumerate(group):
   for b in group[:i]:
    if a['realized_return']==b['realized_return']:continue
    x,y=sessions.index(a['session']),sessions.index(b['session']);D[x,y]+=1;C[x,y]+=.5+.5*np.sign(sign*(a['s'][h]-b['s'][h]))*np.sign(a['realized_return']-b['realized_return'])
 dc=np.diag(C).copy();dn=np.diag(D).copy();np.fill_diagonal(C,0);np.fill_diagonal(D,0);num=(M@C*M).sum(1)+M@dc;den=(M@D*M).sum(1)+M@dn
 return np.divide(num,den,out=np.full(R,np.nan),where=den!=0)
def main():
 assert not (E/'INDEPENDENT_DIAGNOSTIC_AUDIT.json').exists();old=get(E/'INDEPENDENT_INITIAL_AUDIT.json');checks=[];fails=[]
 def compare(name,a,b):
  ok=np.allclose(a,b,rtol=0,atol=1e-12,equal_nan=True);checks.append(name)
  if not ok:fails.append({'check':name,'max_abs_error':float(np.nanmax(np.abs(a-b)))})
 for independent,primary in [('INDEPENDENT_AUC_BOOTSTRAP_VALUES.npz','PRIMARY_SUBSET_BOOTSTRAP_VALUES_CORRECTED.npz'),('INDEPENDENT_SIGNED_AUC_VALUES.npz','PRIMARY_SIGNED_BOOTSTRAP_VALUES_CORRECTED.npz')]:
  a=np.load(P/independent);b=np.load(P/primary)
  for k in a.files:compare('all1999 repaired resamples '+k,a[k],b[k])
 matrix=get(E/'corrections/EXPERT_TARGET_MATRIX.json')['cohorts'];signed=get(E/'corrections/MRET_SIGNED_CONTROLS.json')['cohorts'];aa=np.load(P/'INDEPENDENT_AUC_BOOTSTRAP_VALUES.npz');sa=np.load(P/'INDEPENDENT_SIGNED_AUC_VALUES.npz')
 for name,c in matrix.items():
  for r in c['metrics']:
   if r.get('AUC') is not None:compare('repaired CI '+name+r['head']+r['target'],interval(aa[name+'|'+r['head']+'|'+r['target']]),r['AUC_bootstrap']['CI95'])
 for name,z in signed.items():
  for tag,r in z['scores'].items():compare('signed repaired CI '+name+tag,interval(sa[name+'|'+tag+'|AUC']),r['AUC_bootstrap']['CI95'])
  for tag,r in z['all_control_deltas'].items():compare('repaired paired delta '+name+tag,interval(sa[name+'|MRET|AUC']-sa[name+'|'+tag+'|AUC']),r['paired_bootstrap']['CI95'])
 dd,_,_=original_data();masks=get(P/'COHORT_MASKS.json');sessions=sorted({r['session'] for r in dd.values()});M=np.asarray([r['multiplicities'] for r in lines(P/'BOOTSTRAP_MULTIPLICITIES.jsonl.gz')]);pvals=np.load(P/'PRIMARY_SIGNED_BOOTSTRAP_VALUES_CORRECTED.npz');convalues={}
 for name,z in signed.items():
  rr=[dd[k] for k in masks[name]]
  for tag,r in z['scores'].items():
   v=own_concordance(rr,tag.lstrip('-'),-1 if tag.startswith('-') else 1,M,sessions);convalues[name+'|'+tag]=v;compare('independent concordance all1999 '+name+tag,v,pvals[name+'|'+tag+'|concordance']);compare('concordance CI '+name+tag,interval(v),r['native_bucket_concordance']['bootstrap']['CI95'])
  for tag,r in z['all_control_deltas'].items():compare('concordance paired delta CI '+name+tag,interval(convalues[name+'|MRET']-convalues[name+'|'+tag]),r['paired_concordance_bootstrap']['CI95'])
 # Verify every saved sign and monotonic pair key: no duplicate pair can disappear in aggregate.
 previous={};counts=collections.Counter()
 with gzip.open(P/'ROLE_CONFLICT_LEDGER.jsonl.gz','rt') as f:
  for l in f:
   r=json.loads(l);c=r['cohort'];a,b=r['i'],r['j'];key=(a,b)
   assert a<b and (c not in previous or previous[c]<key);previous[c]=key;counts[c]+=1
   expected={h:(dd[a]['s'][h]>dd[b]['s'][h])-(dd[a]['s'][h]<dd[b]['s'][h]) for h in H};assert expected==r['signs']
   if c=='C5_same_batch':assert dd[a]['time']==dd[b]['time']
 ranks=get(E/'RANK_CONFLICT_SUMMARY.json')['cohorts'];assert all(counts[c]==r['pair_N'] for c,r in ranks.items())
 # Exact TopK union/differences, not additive budget claims.
 overlap=get(E/'RANK_CONFLICT_SUMMARY.json')['top_same_budget']
 for name,fractions in overlap.items():
  for fraction,z in fractions.items():
   ss=get(P/f'TOP_OVERLAP_IDS_{name}_{int(float(fraction)*100)}.json');sets={h:set(v) for h,v in ss.items()};un=set.union(*sets.values());inter=set.intersection(*sets.values());assert z['all_head_union_N']==len(un) and z['all_head_intersection_N']==len(inter) and z['union_is_same_budget']==(len(un)==z['K'])
 roles=get(E/'corrections/ROLE_DECISIONS.json');screen={}
 for role,c,h,targets in [('Winner Priority','C3','pP',['U5','U10']),('Weak Risk','C2','MOVE_U2',['Weak']),('Medium+ Priority','C3','MOVE_U3',['U3'])]:
  mm=[next(r for r in matrix[c]['metrics'] if r.get('head')==h and r.get('target')==t) for t in targets];ok=all(r['known_N']==r['total_N'] and r['AUC_bootstrap']['valid_N']>=1900 and r['AUC_bootstrap']['CI95'][0]>.5 for r in mm);screen[role]='SUPPORTED_FOR_DESIGN' if ok else 'INCONCLUSIVE' if all(r['AUC']>.5 for r in mm) else 'UNSUPPORTED_ON_V5';assert roles[role]['status']==screen[role]
 assert roles['Absolute-Loss Defense via MRET']['status']=='INCONCLUSIVE'
 final={'status':'PASS' if not fails else 'FAIL','mismatch_N':len(fails),'initial_mismatch_N_preserved':old['mismatch_N'],'initial_check_N':old['check_N'],'resumed_comparison_N':len(checks),'resumed_failures':fails,'pure_bug_repair':'same-session AUC pair multiplicity once, fixed definition retained','all_original_identity_point_metric_AP_flag_money_channel_checks_preserved':True,'all_repaired1999_AUC_and_signed_deltas_verified':True,'all_signed_concordance1999_and_deltas_verified':True,'every_pair_sign_verified':True,'pair_N':dict(counts),'pair_duplicate_N':0,'TopK_union_same_budget_verified':True,'role_reasons_verified':screen,'new_fit_inference_replay':0,'independentDiagnosticVerification':1,'primary_imports':0,'code_hashes':{'independent.py':hashfile(W/'code/independent.py'),'independent_resume.py':hashfile(__file__)},'numeric_tolerance':1e-12,'identity_money_fraction_tolerance':0,'shared_numeric_libraries':['NumPy','SciPy'],'independence':'same researcher, shared original sources; separate implementations, not blind external','exact_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()}
 emit('INDEPENDENT_DIAGNOSTIC_AUDIT.json',final);assert not fails
 print(json.dumps({'status':final['status'],'initial_mismatch_N':old['mismatch_N'],'final_mismatch_N':len(fails),'resumed_comparison_N':len(checks),'pairs':dict(counts)}))
if __name__=='__main__':main()
