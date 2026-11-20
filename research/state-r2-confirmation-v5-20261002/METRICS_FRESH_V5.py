"""Frozen metrics, a single global cluster-vector generation, gates not retuned."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,math,hashlib
import numpy as np
R=Path(__file__).resolve().parent;C=['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;assert not p.exists(),'ALREADY_FIXED:'+n;p.write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def output(n,rows,columns=None):
 cols=columns or sorted(set().union(*(r.keys() for r in rows))) if rows else columns or ['status']
 with (R/n).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def safe_ratio(a,b):return float(a/b) if b else None
def stats(rs,w=None):
 if not rs:return {'N':0,'dates':0,'securities':0,'dangerous_numerator':0,'dangerous_denominator':0,'dangerous_rate':None}
 y=np.array([C.index(r['actual']) for r in rs]);p=np.array([r['probabilities'] for r in rs]);hard=p.argmax(1);w=np.ones(len(rs)) if w is None else np.asarray(w,float);n=w.sum()
 if not n:return None
 cm=np.zeros((4,4));np.add.at(cm,(y,hard),w);tp=cm.diagonal();support=cm.sum(1);predn=cm.sum(0);precision=np.divide(tp,predn,out=np.zeros(4),where=predn>0);recall=np.divide(tp,support,out=np.zeros(4),where=support>0);f1=np.divide(2*precision*recall,precision+recall,out=np.zeros(4),where=(precision+recall)>0)
 ll=-np.log(p[np.arange(len(rs)),y]);br=((p-np.eye(4)[y])**2).sum(1);dates=defaultdict(list)
 for i,r in enumerate(rs):dates[r['date']].append(i)
 dw={d:float(w[ix].mean()) for d,ix in dates.items()};dn=sum(dw.values());dLL=sum(dw[d]*float(ll[ix].mean()) for d,ix in dates.items())/dn;dBR=sum(dw[d]*float(br[ix].mean()) for d,ix in dates.items())/dn;mx=p.max(1);bins=np.minimum((mx*10).astype(int),9);ece=0.
 for b in range(10):
  ix=bins==b;z=w[ix].sum()
  if z:ece+=z/n*abs(float(np.average(mx[ix],weights=w[ix]))-float(np.average((hard[ix]==y[ix]),weights=w[ix])))
 r={'N':int(n) if n.is_integer() else float(n),'dates':sum(z>0 for z in dw.values()),'securities':len({r['security_id'] for i,r in enumerate(rs) if w[i]>0}),'accuracy':float(tp.sum()/n),'balanced_accuracy':float(recall[support>0].mean()),'macro_F1':float(f1.mean()),'row_LL':float(np.average(ll,weights=w)),'date_equal_LL':dLL,'Brier':float(np.average(br,weights=w)),'date_equal_Brier':dBR,'ECE':float(ece),'dangerous_numerator':int(cm[1,0]),'dangerous_denominator':int(cm[:,0].sum()),'dangerous_rate':safe_ratio(cm[1,0],cm[:,0].sum())}
 for k,c in enumerate(C):r.update({c+'_support':int(support[k]),c+'_Precision':float(precision[k]),c+'_Recall':float(recall[k]),c+'_F1':float(f1[k])})
 return r
def interval(values,informative):
 finite=[float(v) for v in values if v is not None and math.isfinite(float(v))]
 return (float(np.quantile(finite,.025)),float(np.quantile(finite,.975)),len(finite)) if informative and finite else (None,None,len(finite))
def main():
 pre=json.loads((R/'PREDICTIVENESS_V5_PRECOMMIT.json').read_text())
 for n,h in pre['hashes'].items():assert sha(R/n)==h,'V5_PRECOMMIT_BREACH:'+n
 oo=list(map(json.loads,(R/'R1_R2_FRESH_OOF_V5.jsonl').open()));groups={(c,m,t):[r for r in oo if r['control']==c and r['model']==m and r['calibrated']==t] for c in ['REAL','TRUE_NULL'] for m in ['R1','R2'] for t in [False,True]};ds=sorted({r['date'] for r in oo});draw=[]
 assert not (R/'BOOTSTRAP_GLOBAL_DATE_DRAWS_V5.json').exists(),'NO_DUPLICATE_BOOTSTRAP'
 if ds:draw=np.random.default_rng(pre['bootstrap_seed']).integers(0,len(ds),size=(1000,len(ds))).tolist()
 save('BOOTSTRAP_GLOBAL_DATE_DRAWS_V5.json',{'seed':pre['bootstrap_seed'],'dates':ds,'draws':draw,'generated_vector_N':len(draw),'generation_invocation_N':int(bool(ds)),'reason':None if ds else 'NO_EVALUABLE_FRESH_OOF_DATES_NO_GENERATION'})
 save('BOOTSTRAP_GLOBAL_1000_RECEIPT_V5.json',{'seed':pre['bootstrap_seed'],'bootstrap_total_generated_draws':len(draw),'generated_vector_N':len(draw),'generation_invocation_N':int(bool(ds)),'independent_checker_new_draws':0,'SHA256':sha(R/'BOOTSTRAP_GLOBAL_DATE_DRAWS_V5.json'),'V1_3000_cap1000_breach_preserved':True,'inherited_known_cumulative_vectors':6000,'cumulative_known_generated_vectors':6000+len(draw),'reason':None if ds else 'NO_FRESH_TEST_DATES','same_vectors_all_metrics':True})
 index={d:i for i,d in enumerate(ds)};multiplicities=np.array([np.bincount(v,minlength=len(ds)) for v in draw]) if ds else np.zeros((0,0),int);metrics=[];calibration=[];risk=[];buckets=[];comparison=[]
 # All model/metric intervals consume exactly the same stored vectors.
 cached={}
 for control in ['REAL','TRUE_NULL']:
  for model in ['R1','R2']:
   for calibrated in [False,True]:
    rr=groups[(control,model,calibrated)]
    for fold in [0]+sorted({r['fold'] for r in rr}):
     rs=[r for r in rr if not fold or r['fold']==fold];s=stats(rs);record={'control':control,'model':model,'calibrated':calibrated,'fold':fold or 'ALL',**s};rep=[stats(rs,[w[index[r['date']]] for r in rs]) for w in multiplicities] if rs else [];informative=len({r['date'] for r in rs})>=2
     for k in ['dangerous_rate','DOWN_REVERSAL_Precision','DOWN_REVERSAL_Recall','DOWN_REVERSAL_F1','UP_CONTINUE_Precision','UP_CONTINUE_Recall','UP_CONTINUE_F1','balanced_accuracy','macro_F1','row_LL','date_equal_LL','Brier','ECE']:
      lo,hi,n=interval([x.get(k) if x else None for x in rep],informative);record.update({k+'_CI_low':lo,k+'_CI_high':hi})
     record['CI_informative']=informative;metrics.append(record);calibration.append({k:v for k,v in record.items() if k in ['control','model','calibrated','fold','N','dates','row_LL','date_equal_LL','Brier','date_equal_Brier','ECE','row_LL_CI_low','row_LL_CI_high','date_equal_LL_CI_low','date_equal_LL_CI_high','Brier_CI_low','Brier_CI_high','ECE_CI_low','ECE_CI_high','CI_informative']})
     if not fold:cached[(control,model,calibrated)]=(s,rep)
    if rr:
     p=np.array([r['probabilities'] for r in rr]);y=np.array([C.index(r['actual']) for r in rr]);hard=p.argmax(1)
     for kind,score,actual in [('TOP_LABEL',p.max(1),hard==y),('DOWN_REVERSAL',p[:,1],y==1)]:
      bid=np.minimum((score*10).astype(int),9)
      for b in range(10):
       ix=np.where(bid==b)[0];rows=[rr[i] for i in ix];buckets.append({'control':control,'model':model,'calibrated':calibrated,'kind':kind,'bucket':b,'lower':b/10,'upper':(b+1)/10,'upper_inclusive':b==9,'N':len(ix),'dates':len({r['date'] for r in rows}),'securities':len({r['security_id'] for r in rows}),'mean_predicted_probability':float(score[ix].mean()) if len(ix) else None,'actual_rate':float(actual[ix].mean()) if len(ix) else None})
 # Dangerous numerator/denominator and paired R1-R2 rate improvement for all slices.
 for cal in [False,True]:
  r1=groups[('REAL','R1',cal)];r2={r['row_key']:r for r in groups[('REAL','R2',cal)]};assert set(r2)=={r['row_key'] for r in r1},'MATCHED_MODEL_KEYS'
  slices=[('ALL','ALL',r1)]
  for kind,col in [('fold','fold'),('date','date'),('security','security_id'),('current_primary','current_primary')]:
   slices.extend((kind,str(value),[r for r in r1 if r[col]==value]) for value in sorted({r[col] for r in r1},key=str))
  for kind,value,a in slices:
   b=[r2[r['row_key']] for r in a];st=[stats(a),stats(b)];rep=[[stats(x,[w[index[r['date']]] for r in x]) for w in multiplicities] for x in [a,b]] if a else [[],[]];informative=len({r['date'] for r in a})>=2
   for model,s,rr in zip(['R1','R2'],st,rep):
    lo,hi,n=interval([x['dangerous_rate'] if x else None for x in rr],informative);risk.append({'calibrated':cal,'group_kind':kind,'group':value,'model':model,'N':s['N'],'dates':s['dates'],'numerator':s['dangerous_numerator'],'denominator':s['dangerous_denominator'],'rate':s['dangerous_rate'],'rate_CI_low':lo,'rate_CI_high':hi,'improvement_pp':None,'improvement_CI_low_pp':None,'improvement_CI_high_pp':None,'finite_bootstrap_N':n,'CI_informative':informative})
   diffs=[100*(x['dangerous_rate']-y['dangerous_rate']) if x and y and x['dangerous_rate'] is not None and y['dangerous_rate'] is not None else None for x,y in zip(*rep)];lo,hi,n=interval(diffs,informative);point=100*(st[0]['dangerous_rate']-st[1]['dangerous_rate']) if all(x['dangerous_rate'] is not None for x in st) else None;risk.append({'calibrated':cal,'group_kind':kind,'group':value,'model':'R1_MINUS_R2','N':st[0]['N'],'dates':st[0]['dates'],'numerator':None,'denominator':None,'rate':None,'rate_CI_low':None,'rate_CI_high':None,'improvement_pp':point,'improvement_CI_low_pp':lo,'improvement_CI_high_pp':hi,'finite_bootstrap_N':n,'CI_informative':informative})
 # Candidate-local NULL and original positive-gain equivalence, no R3 rescue.
 for cal in [False,True]:
  real=cached[('REAL','R2',cal)][0];null=cached[('TRUE_NULL','R2',cal)][0];r1=cached[('REAL','R1',cal)][0];n1=cached[('TRUE_NULL','R1',cal)][0];available=bool(real['N']);gain=r1['date_equal_LL']-real['date_equal_LL'] if available else None;ngain=n1['date_equal_LL']-null['date_equal_LL'] if available else None;llfail=null['date_equal_LL']<=real['date_equal_LL']+1e-12 if available else None;equiv=(gain>1e-12 and ngain>0 and ngain+1e-12>=.9*gain) if available else None
  comparison.append({'model':'R2','calibrated':cal,'N':real['N'],'dates':real['dates'],'REAL_date_equal_LL':real.get('date_equal_LL'),'TRUE_NULL_date_equal_LL':null.get('date_equal_LL'),'REAL_R1_to_R2_gain':gain,'NULL_R1_to_R2_gain':ngain,'NULL_LL_equivalent_or_better':llfail,'positive_gain_equivalence_fail':equiv,'promotion_control_variant':cal,'control_status':'FAIL' if available and (llfail or equiv) else 'PASS' if available else 'NOT_EVALUABLE'})
 a=groups[('REAL','R1',True)];b={r['row_key']:r for r in groups[('REAL','R2',True)]};positive={'dangerous_error_reduction':[],'class_correctness_gain':[]}
 for r in a:
  s=b[r['row_key']]
  if r['actual']=='DOWN_REVERSAL' and r['predicted']=='UP_CONTINUE' and s['predicted']!='UP_CONTINUE':positive['dangerous_error_reduction'].append(r)
  if r['predicted']!=r['actual'] and s['predicted']==s['actual']:positive['class_correctness_gain'].append(r)
 concentration=[];cp=True
 for gain,rs in positive.items():
  for kind,col in [('date','date'),('security','security_id'),('current_primary','current_primary'),('fold','fold')]:
   counts=Counter(r[col] for r in rs);maximum=max(counts.values())/len(rs) if rs else None;passed=maximum is not None and maximum<=.5+1e-12
   if kind in ['date','security']:cp=cp and passed
   concentration.append({'gain':gain,'group_kind':kind,'group':'MAXIMUM','positive_gross_N':len(rs),'group_N':max(counts.values()) if counts else 0,'share':maximum,'gate_applies':kind in ['date','security'],'PASS':passed if kind in ['date','security'] else None})
   concentration.extend({'gain':gain,'group_kind':kind,'group':str(k),'positive_gross_N':len(rs),'group_N':n,'share':n/len(rs),'gate_applies':False,'PASS':None} for k,n in sorted(counts.items(),key=lambda x:str(x[0])))
 r1=cached[('REAL','R1',True)][0];r2=cached[('REAL','R2',True)][0];raw=cached[('REAL','R2',False)][0];riskall=next(x for x in risk if x['calibrated'] and x['group_kind']=='ALL' and x['model']=='R1_MINUS_R2');sample=r2['N']>0 and r2['dates']>=8 and len({r['fold'] for r in a})>=2 and r2['DOWN_REVERSAL_support']>=100 and r2['UP_CONTINUE_support']>=100
 hard=riskall['improvement_pp'] is not None and riskall['improvement_pp']>0 and riskall['improvement_CI_low_pp'] is not None and riskall['improvement_CI_low_pp']>0;reversal=r2['N']>0 and any(r2[k]>r1[k]+1e-12 for k in ['DOWN_REVERSAL_F1','UP_CONTINUE_F1','macro_F1']) and r2['DOWN_REVERSAL_Recall']>=r1['DOWN_REVERSAL_Recall']-.02
 calgate=r2['N']>0 and r2['date_equal_LL']<=1.05*raw['date_equal_LL']+1e-12 and r2['Brier']<=1.05*raw['Brier']+1e-12;control=next(x for x in comparison if x['calibrated'])['control_status']
 gate={'fresh_OOF_anchors':r2['N'],'OOF_dates':r2['dates'],'evaluable_folds':len({r['fold'] for r in a}),'DOWN_support':r2.get('DOWN_REVERSAL_support',0),'UP_support':r2.get('UP_CONTINUE_support',0),'sample_PASS':bool(sample),'dangerous_hard_PASS':bool(hard),'major_reversal_PASS':bool(reversal),'concentration_PASS':bool(cp),'calibration_PASS':bool(calgate),'R2_TRUE_NULL':control,'R1_calibrated':r1,'R2_uncalibrated':raw,'R2_calibrated':r2,'dangerous_improvement':riskall,'direct_integrity':'PENDING_INDEPENDENT_AUDIT','fresh_scope_expansion_after_labels':0,'result_driven_changes':0,'R3_R4_fresh_fits':0,'secondary_9State':'NOT_RUN_OPTIONAL_BUDGET_FOCUS_ON_R2_CONFIRMATION'}
 output('R1_R2_REVERSAL_METRICS_V5.csv',metrics);output('CALIBRATION_METRICS_V5.csv',calibration);output('CALIBRATION_BUCKETS_V5.csv',buckets,['control','model','calibrated','kind','bucket','lower','upper','upper_inclusive','N','dates','securities','mean_predicted_probability','actual_rate']);output('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V5.csv',risk);output('TRUE_NULL_R2_V5.csv',comparison);output('CONCENTRATION_V5.csv',concentration);save('FRESH_GATE_MEASUREMENTS_V5.json',gate)
 print(json.dumps({'gate':{k:v for k,v in gate.items() if k not in ['R1_calibrated','R2_uncalibrated','R2_calibrated','dangerous_improvement']},'improvement':riskall,'bootstrap_generated':len(draw)},allow_nan=False))
if __name__=='__main__':main()
