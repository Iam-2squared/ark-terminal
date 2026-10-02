"""Independent bucket, control, F1, concentration and gate oracle. No fit/draw."""
from collections import Counter,defaultdict
import math,statistics,json,csv,hashlib,numpy as np
def run(a,grouped,features,ratio,ci):
 R=a.R;cl=a.jread('REVERSAL_TARGET_SCHEMA.json')['classes']['CONTEXT_REVERSAL'];get=lambda model:grouped.get(('CONTEXT_REVERSAL','REAL',model,True),[])
 # Reliability bucket direct oracle, independently reconstructing each bin.
 for row in a.cread('CALIBRATION_BUCKETS_V4.csv'):
  rr=grouped.get((row['task'],row['control'],row['model'],row['calibrated']=='True'),[]);bucket=int(row['bucket']);kind=row['kind']
  p=lambda r:max(r['probabilities']) if kind=='TOP_LABEL' else r['probabilities'][1]
  rr=[r for r in rr if min(math.floor(p(r)*10),9)==bucket];emp=lambda r:r['actual']==r['predicted'] if kind=='TOP_LABEL' else r['actual']=='DOWN_REVERSAL'
  a.check(len(rr)==int(row['N']) and len({r['date'] for r in rr})==int(row['date_N']),'independent_reliability_bucket_support')
  mean=statistics.fmean(p(r) for r in rr) if rr else None;rate=statistics.fmean(emp(r) for r in rr) if rr else None
  a.check(a.near(mean,a.parse(row['mean_predicted_probability'])) and a.near(rate,a.parse(row['empirical_rate'])),'independent_reliability_bucket_rate')
 for row in a.cread('NEGATIVE_CONTROL_V4.csv'):
  key=(row['task'],row['control'],row['model'],row['calibrated']=='True');r={x['row_key']:x for x in grouped.get((row['task'],'REAL',row['model'],key[3]),[])};c={x['row_key']:x for x in grouped.get(key,[])};keys=sorted(r.keys()&c.keys());clt=a.jread('REVERSAL_TARGET_SCHEMA.json')['classes'][row['task']]
  real1={x['row_key']:x for x in grouped.get((row['task'],'REAL','R1',key[3]),[])};con1={x['row_key']:x for x in grouped.get((row['task'],row['control'],'R1',key[3]),[])}
  av=a.metric_ref([r[k] for k in keys],clt)[0]['date_equal_log_loss'];bv=a.metric_ref([c[k] for k in keys],clt)[0]['date_equal_log_loss'];ar=a.metric_ref([real1[k] for k in keys],clt)[0]['date_equal_log_loss'];br=a.metric_ref([con1[k] for k in keys],clt)[0]['date_equal_log_loss'];gain=ar-av if av is not None else None;cg=br-bv if bv is not None else None
  a.check(a.near(gain,a.parse(row['REAL_gain_vs_R1'])) and a.near(cg,a.parse(row['control_gain_vs_R1'])),'independent_control_gain_vs_R1')
 boot=a.jread('BOOTSTRAP_GLOBAL_DATE_DRAWS.json');dates=boot['dates'];di={d:i for i,d in enumerate(dates)};mass=np.asarray([np.bincount(v,minlength=len(dates)) for v in boot['draws']],float)
 def f1draw(rr,kind):
  truth=np.zeros((len(dates),4));pred=truth.copy();correct=truth.copy()
  for r in rr:
   d=di[r['date']];i=cl.index(r['actual']);j=cl.index(r['predicted']);truth[d,i]+=1;pred[d,j]+=1
   if i==j:correct[d,i]+=1
  t=mass@truth;p=mass@pred;c=mass@correct;f=np.divide(2*c,t+p,out=np.full((1000,4),np.nan),where=(t>0)&(p>0))
  return np.where(np.isfinite(f),f,0).mean(1) if kind=='macro_F1' else f[:,cl.index(kind)]
 gains={}
 for row in a.cread('MAJOR_METRIC_GAIN_GATE_V4.csv'):
  model,baseline,kind=row['model'],row['baseline'],row['metric'];test=get(model);base=get(baseline);mm,mc,mp=a.metric_ref(test,cl);bm,bc,bp=a.metric_ref(base,cl)
  v=mm['macro_F1'] if kind=='macro_F1' else mp[cl.index(kind)]['F1'];u=bm['macro_F1'] if kind=='macro_F1' else bp[cl.index(kind)]['F1'];lo,hi,n=ci(f1draw(test,kind)-f1draw(base,kind),.05/12);positive=0
  for f in [1,2,3]:
   aa=a.metric_ref([r for r in test if r['fold']==f],cl);bb=a.metric_ref([r for r in base if r['fold']==f],cl);x=aa[0]['macro_F1'] if kind=='macro_F1' else aa[2][cl.index(kind)]['F1'];y=bb[0]['macro_F1'] if kind=='macro_F1' else bb[2][cl.index(kind)]['F1'];positive+=int(x is not None and y is not None and x>y)
  predicted=kind=='macro_F1' or mp[cl.index(kind)]['Predicted_N']>=100;passed=predicted and v is not None and u is not None and v>u and lo is not None and lo>0 and positive>=2
  a.check(a.near(v-u if v is not None and u is not None else None,a.parse(row['point_improvement'])) and a.near(lo,a.parse(row['adjusted_CI_low'])) and a.near(hi,a.parse(row['adjusted_CI_high'])) and n==int(row['valid_draws']),'independent_major_F1_point_CI')
  a.check(positive==int(row['positive_folds']) and (row['predicted_support_gate']=='True')==predicted and (row['PASS']=='True')==passed,'independent_major_F1_gate');gains[(model,baseline,kind)]=passed
 comparisons=defaultdict(list);primary=get('R2');support=Counter(r['actual'] for r in primary);mm=a.metric_ref(primary,cl)[0];adequate=mm['date_N']>=8 and mm['fold_N']>=2 and support['DOWN_REVERSAL']>=100 and support['UP_CONTINUE']>=100
 controls=a.cread('NEGATIVE_CONTROL_V4.csv')
 for row in a.cread('PROMOTION_GATE_V4.csv'):
  model,baseline=row['model'],row['baseline'];test=get(model);base=get(baseline);tm=a.metric_ref(test,cl);bm=a.metric_ref(base,cl);b={r['row_key']:r for r in base};out={}
  for name,rr in [('correctness',[r for r in test if r['actual']==r['predicted'] and b[r['row_key']]['actual']!=b[r['row_key']]['predicted']]),('dangerous_reduction',[r for r in test if b[r['row_key']]['predicted']=='UP_CONTINUE' and b[r['row_key']]['actual']=='DOWN_REVERSAL' and not(r['predicted']=='UP_CONTINUE' and r['actual']=='DOWN_REVERSAL')])]:
   ds=Counter(r['date'] for r in rr);ss=Counter(r['security_id'] for r in rr);out[name+'_gross_gain_N']=len(rr);out[name+'_max_date_share']=max(ds.values())/len(rr) if rr else None;out[name+'_max_security_share']=max(ss.values())/len(rr) if rr else None
  for k,v in out.items():a.check(a.near(v,a.parse(row[k])),'independent_positive_gain_concentration')
  concentration=all(out[n+'_'+k] is not None and out[n+'_'+k]<=.5 for n in ['correctness','dangerous_reduction'] for k in ['max_date_share','max_security_share'])
  danger=lambda rr:ratio(rr,lambda r:r['predicted']=='UP_CONTINUE' and r['actual']=='DOWN_REVERSAL',lambda r:r['predicted']=='UP_CONTINUE')
  lo,hi,n=ci(danger(base)-danger(test));point=lambda rr:sum(r['predicted']=='UP_CONTINUE' and r['actual']=='DOWN_REVERSAL' for r in rr)/sum(r['predicted']=='UP_CONTINUE' for r in rr) if any(r['predicted']=='UP_CONTINUE' for r in rr) else None
  p=point(base);q=point(test);dangerpass=lo is not None and lo>0 and p is not None and q is not None and p>q;major=any(gains[(model,baseline,k)] for k in ['DOWN_REVERSAL','UP_CONTINUE','macro_F1']);cal=tm[0]['date_equal_log_loss'] is not None and bm[0]['date_equal_log_loss'] is not None and tm[0]['date_equal_log_loss']<=1.05*bm[0]['date_equal_log_loss'] and tm[0]['date_equal_Brier']<=1.05*bm[0]['date_equal_Brier'];rec=tm[2][1]['Recall'];br=bm[2][1]['Recall'];recall=rec is not None and br is not None and rec>=br-.02;null=any(x['task']=='CONTEXT_REVERSAL' and x['control']=='TRUE_NULL' and x['model']==model and x['calibrated']=='True' and x['warning']=='True' for x in controls);passed=adequate and dangerpass and major and cal and recall and concentration and not null
  a.check(a.near(p-q if p is not None and q is not None else None,a.parse(row['dangerous_point_improvement'])) and a.near(lo,a.parse(row['dangerous_CI95_low'])) and a.near(hi,a.parse(row['dangerous_CI95_high'])) and n==int(row['dangerous_valid_draws']),'independent_promotion_risk_delta_CI')
  for k,v in {'core_support_PASS':adequate,'dangerous_improvement_PASS':dangerpass,'major_metric_PASS':major,'calibration_not_fatally_worse_PASS':cal,'DOWN_recall_guard_PASS':recall,'concentration_PASS':concentration,'TRUE_NULL_equivalent_or_better':null,'comparison_PASS':passed}.items():a.check((row[k]=='True')==v,'independent_literal_gate_'+k)
  comparisons[model].append(passed)
 promoted=sorted(k for k,v in comparisons.items() if all(v));nullfail=any(x['task']=='CONTEXT_REVERSAL' and x['control']=='TRUE_NULL' and x['model'] in ['R2','R3','R4'] and x['calibrated']=='True' and x['warning']=='True' for x in controls)
 status='BLOCKED_V4_INTEGRITY' if nullfail else 'STATE_REVERSAL_INTELLIGENCE_DEV_CANDIDATE_READY_FOR_ENTRY_RESEARCH' if promoted else 'STATE_REVERSAL_INTELLIGENCE_MEASURED_NO_PROMOTABLE_SIGNAL' if adequate else 'STATE_REVERSAL_INTELLIGENCE_LIMITED_SAMPLE';gate=a.jread('GATE_ASSESSMENT_V4.json')
 a.check(status==gate['status_pending_independent_audit'] and ([] if nullfail else promoted)==gate['promoted_models'] and promoted==gate['comparison_qualifying_before_global_integrity'] and gate['core_support_adequate']==adequate and gate['class_support']==dict(support),'independent_final_status_and_support')
 # Incremental tables including risk and probability quality, with no helper calculations.
 for row in a.cread('R0_R1_R2_R3_R4_INCREMENTAL_V4.csv'):
  key=(row['task'],'REAL',row['calibrated']=='True');base=grouped.get((key[0],key[1],row['baseline'],key[2]),[]);test=grouped.get((key[0],key[1],row['model'],key[2]),[]);ct=a.jread('REVERSAL_TARGET_SCHEMA.json')['classes'][key[0]];am=a.metric_ref(base,ct);bm=a.metric_ref(test,ct)
  for k in ['accuracy','macro_F1','balanced_accuracy','log_loss','Brier','date_equal_log_loss','date_equal_Brier','top_label_ECE']:
   v=(bm[0][k]-am[0][k])*(1 if k in ['accuracy','macro_F1','balanced_accuracy'] else -1) if bm[0][k] is not None and am[0][k] is not None else None;a.check(a.near(v,a.parse(row[k+'_improvement'])),'independent_incremental_'+k)
  if key[0]=='CONTEXT_REVERSAL':
   for c in ['DOWN_REVERSAL','UP_CONTINUE']:
    aa=am[2][ct.index(c)]['F1'];bb=bm[2][ct.index(c)]['F1'];a.check(a.near(bb-aa if aa is not None and bb is not None else None,a.parse(row[c+'_F1_improvement'])),'independent_incremental_class_F1')
 return status
