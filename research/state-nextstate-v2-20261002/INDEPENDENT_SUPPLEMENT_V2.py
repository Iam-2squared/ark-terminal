"""Independent primitive audit of saved CIs, family matrices and fixed gates.
No candidate imports, fits, target generation, provider or random draws.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,csv,math,statistics
R=Path(__file__).resolve().parent;checks=Counter();errors=[]
def check(ok,kind,detail=None):
 checks[kind]+=1
 if not ok:errors.append({'kind':kind,'detail':detail})
def number(x):return None if x in ['',None] else float(x)
def near(a,b):return a is None and b is None if a is None or b is None else abs(float(a)-float(b))<=1e-8
def percentile(xs,q):
 xs=sorted(xs);pos=(len(xs)-1)*q;lo=math.floor(pos);hi=math.ceil(pos);return xs[lo]+(xs[hi]-xs[lo])*(pos-lo)
def interval(xs,tail):return (percentile(xs,tail),percentile(xs,1-tail),len(xs)) if xs else (None,None,0)
def read(n):return list(csv.DictReader((R/n).open()))
def precision(rr,state):
 n=sum(r['predicted']==state for r in rr);return sum(r['actual']==r['predicted']==state for r in rr)/n if n else None
def main():
 rs=list(map(json.loads,(R/'OOF_ALL.jsonl').read_text().splitlines()));g=defaultdict(list)
 for r in rs:g[(r['task'],r['control'],r['model'])].append(r)
 boot=json.loads((R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').read_text());dates=boot['dates'];draws=boot['draws'];ts=json.loads((R/'TARGET_SCHEMA_V2.json').read_text());ag={(r['task'],r['control'],r['model']):r for r in read('MODEL_METRICS_AGGREGATE.csv')}
 for r in read('BOOTSTRAP_METRIC_INTERVALS.csv'):
  rr=g.get((r['task'],r['control'],r['model']),[]);c={d:(sum(x['date']==d for x in rr),sum(x['date']==d and x['actual']==x['predicted'] for x in rr)) for d in dates};vals=[]
  for draw in draws:
   den=sum(c[dates[i]][0] for i in draw)
   if den:vals.append(sum(c[dates[i]][1] for i in draw)/den)
  lo,hi,n=interval(vals,.025);check(near(number(r['CI95_low']),lo) and near(number(r['CI95_high']),hi) and int(r['valid_global_vectors'])==n,'accuracy_CI_saved_vectors')
 for name,kind in [('MOTION_FAMILY_METRICS.csv','motion'),('TREND_CONTEXT_FAMILY_METRICS.csv','context')]:
  mapping={s:f for f,ss in ts[kind].items() for s in ss}
  for r in read(name):
   rr=g.get((r['task'],r['control'],r['model']),[]);f=r['family'];c={d:(sum(x['date']==d and mapping[x['predicted']]==f for x in rr),sum(x['date']==d and mapping[x['predicted']]==mapping[x['actual']]==f for x in rr)) for d in dates};vals=[]
   for draw in draws:
    den=sum(c[dates[i]][0] for i in draw)
    if den:vals.append(sum(c[dates[i]][1] for i in draw)/den)
   lo,hi,n=interval(vals,.025);check(near(number(r['precision_CI95_low']),lo) and near(number(r['precision_CI95_high']),hi) and int(r['valid_global_vectors'])==n,'family_precision_CI_saved_vectors')
 for r in read('FAMILY_CONFUSION_MATRIX.csv'):
  mapping={s:f for f,ss in ts[r['mapping']].items() for s in ss};rr=g.get((r['task'],r['control'],r['model']),[]);n=sum(mapping[x['actual']]==r['actual'] and mapping[x['predicted']]==r['predicted'] for x in rr);check(int(r['N'])==n,'family_matrix_direct')
 for r in read('B1_B2_B3_INCREMENTAL.csv'):
  a=ag[(r['task'],'REAL',r['candidate'])];b=ag[(r['task'],'REAL',r['baseline'])]
  for output,metric,sign in [('accuracy_difference','accuracy',1),('macro_F1_difference','macro_F1',1),('date_equal_log_loss_reduction','date_equal_log_loss',-1),('date_equal_Brier_reduction','date_equal_Brier',-1)]:
   av,bv=number(a[metric]),number(b[metric]);v=None if av is None or bv is None else sign*(av-bv);check(near(number(r[output]),v),'incremental_direct',r['task']+output)
 controls={(r['task'],r['control'],r['model']):r for r in read('NEGATIVE_CONTROL_V2.csv')}
 for r in controls.values():
  absolute=number(r['control_log_loss']) is not None and number(r['REAL_log_loss']) is not None and float(r['control_log_loss'])<=float(r['REAL_log_loss']);cg,rg=number(r['control_gain_vs_B1']),number(r['REAL_gain_vs_B1']);gain=cg is not None and rg is not None and cg>0 and rg>0 and cg>=.9*rg;expected=(absolute or gain) and r['model']!='B0';check((r['warning']=='True')==expected,'fixed_control_warning_rule')
 for filename,pathgate in [('STATE_PROMOTION_ASSESSMENT.csv',False),('PATH_INCREMENTAL_ASSESSMENT_V2.csv',True)]:
  for r in read(filename):
   task=r['task'];model=r['model'];baseline='B2' if pathgate else 'B1';a=g[(task,'REAL',model)];b=g[(task,'REAL',baseline)];state=r['State'];av,bv=precision(a,state),precision(b,state);column='precision_improvement_vs_B2' if pathgate else 'precision_improvement_vs_B1';check(near(number(r[column]),None if av is None or bv is None else av-bv),'gate_precision_diff',state)
   pn=sum(x['predicted']==state for x in a);an=sum(x['actual']==state for x in a);adequate=pn>=50 and an>=50 and len({x['date'] for x in a})>=6 and len({x['fold'] for x in a if x['predicted']==state})>=2 and len({x['fold'] for x in a if x['actual']==state})>=2
   am,bm=ag[(task,'REAL',model)],ag[(task,'REAL',baseline)];cal=number(am['date_equal_Brier']) is not None and float(am['date_equal_Brier'])<=float(bm['date_equal_Brier']) and float(am['date_equal_log_loss'])<=float(bm['date_equal_log_loss']);positive=0
   for fold in [1,2,3]:
    ar=[x for x in a if x['fold']==fold];br=[x for x in b if x['fold']==fold];ap,bp=precision(ar,state),precision(br,state);positive+=int(ap is not None and bp is not None and ap>bp and any(x['actual']==state for x in ar))
   dcs=[]
   for rr in [a,b]:dcs.append({d:(sum(x['date']==d and x['predicted']==state for x in rr),sum(x['date']==d and x['actual']==x['predicted']==state for x in rr)) for d in dates})
   vals=[]
   for draw in draws:
    nums=[sum(c[dates[i]][1] for i in draw) for c in dcs];dens=[sum(c[dates[i]][0] for i in draw) for c in dcs]
    if all(dens):vals.append(nums[0]/dens[0]-nums[1]/dens[1])
   lo,hi,n=interval(vals,1/720);check(near(number(r['adjusted_CI_low']),lo) and near(number(r['adjusted_CI_high']),hi) and int(r['valid_vectors'])==n,'gate_CI_saved_vectors')
   dc=Counter();sc=Counter();bykey={x['row_key']:x for x in b}
   for x in a:
    old=bykey[x['row_key']];gain=int(x['actual']==x['predicted']==state)-int(old['actual']==old['predicted']==state)
    if gain>0:dc[x['date']]+=gain;sc[x['security_id']]+=gain
   total=sum(dc.values());ds=max(dc.values())/total if total else None;ss=max(sc.values())/total if total else None;veto=controls[(task,'TRUE_NULL',model)]['warning']=='True';passed=adequate and positive>=2 and lo is not None and lo>0 and cal and ds is not None and ss is not None and ds<=.5 and ss<=.5 and not veto
   for col,value in [('support_adequate',adequate),('global_calibration_not_worse',cal),('true_null_veto',veto),('Path_incremental_evidence' if pathgate else 'promotable',passed)]:check((r[col]=='True')==value,'fixed_gate_'+col,state)
   check(int(r['positive_folds'])==positive and near(number(r['max_date_gross_positive_share']),ds) and near(number(r['max_security_gross_positive_share']),ss),'fixed_fold_concentration',state)
 result={'status':'PASS' if not errors else 'FAIL','assertion_N':sum(checks.values()),'mismatch_N':len(errors),'counts':dict(checks),'errors':errors,'candidate_helper_imports':0,'new_draws':0,'model_refit_N':0,'provider_requests':0};(R/'INDEPENDENT_SUPPLEMENT_V2.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','assertion_N','mismatch_N']}))
if __name__=='__main__':main()
