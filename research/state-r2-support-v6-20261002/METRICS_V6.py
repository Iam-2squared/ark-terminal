"""Registered V6-only and V5+V6 metrics; two frozen global draws, no refits."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,math,hashlib
import numpy as np
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1'
C=['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30']
CI_KEYS=['dangerous_rate','DOWN_REVERSAL_Precision','DOWN_REVERSAL_Recall','DOWN_REVERSAL_F1','UP_CONTINUE_Precision','UP_CONTINUE_Recall','UP_CONTINUE_F1','balanced_accuracy','macro_F1','row_LL','date_equal_LL','Brier','ECE']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;assert not p.exists(),'ALREADY_FIXED:'+n;p.write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def output(n,rows,columns=None):
 cols=columns or (sorted(set().union(*(r.keys() for r in rows))) if rows else ['status'])
 with (R/n).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def ratio(a,b):return np.divide(a,b,out=np.full(np.broadcast_shapes(np.shape(a),np.shape(b)),np.nan),where=b>0)
def aggregate(rows,dates):
 index={d:i for i,d in enumerate(dates)};D=len(dates);cm=np.zeros((D,4,4));n=np.zeros(D);ll=np.zeros(D);br=np.zeros(D);bins=np.zeros((D,10));score=np.zeros((D,10));correct=np.zeros((D,10))
 for r in rows:
  d=index[r['date']];y=C.index(r['actual']);p=np.asarray(r['probabilities']);hard=int(p.argmax());mx=float(p.max());b=min(int(mx*10),9);cm[d,y,hard]+=1;n[d]+=1;ll[d]-=math.log(float(p[y]));br[d]+=float(((p-np.eye(4)[y])**2).sum());bins[d,b]+=1;score[d,b]+=mx;correct[d,b]+=int(y==hard)
 return cm,n,ll,br,bins,score,correct
def calculate(agg,weight):
 cm,n,ll,br,bins,score,correct=agg;cm=np.einsum('bd,dij->bij',weight,cm);N=weight@n;sup=cm.sum(2);pred=cm.sum(1);tp=np.diagonal(cm,axis1=1,axis2=2);prec=np.divide(tp,pred,out=np.zeros_like(tp),where=pred>0);rec=np.divide(tp,sup,out=np.zeros_like(tp),where=sup>0);f1=np.divide(2*prec*rec,prec+rec,out=np.zeros_like(tp),where=prec+rec>0);dw=weight@(n>0).astype(float);dLL=np.divide(ll,n,out=np.zeros_like(ll),where=n>0);dBR=np.divide(br,n,out=np.zeros_like(br),where=n>0)
 out={'N':N,'accuracy':ratio(tp.sum(1),N),'balanced_accuracy':ratio((rec*(sup>0)).sum(1),(sup>0).sum(1)),'macro_F1':f1.mean(1),'row_LL':ratio(weight@ll,N),'date_equal_LL':ratio(weight@dLL,dw),'Brier':ratio(weight@br,N),'date_equal_Brier':ratio(weight@dBR,dw),'ECE':ratio(np.abs(weight@score-weight@correct).sum(1),N),'dangerous_numerator':cm[:,1,0],'dangerous_denominator':pred[:,0],'dangerous_rate':ratio(cm[:,1,0],pred[:,0])}
 for k,c in enumerate(C):out.update({c+'_support':sup[:,k],c+'_Precision':prec[:,k],c+'_Recall':rec[:,k],c+'_F1':f1[:,k]})
 return out,cm
def point_and_reps(rows,dates,weight):
 if not rows:return {'N':0,'dates':0,'securities':0,'dangerous_numerator':0,'dangerous_denominator':0,'dangerous_rate':None},{},np.zeros((4,4))
 agg=aggregate(rows,dates);p,cm=calculate(agg,np.ones((1,len(dates))));rep,_=calculate(agg,weight);out={k:(float(a[0]) if np.isfinite(a[0]) else None) for k,a in p.items()};out.update(dates=len({r['date'] for r in rows}),securities=len({r['security_id'] for r in rows}))
 for k in ['N','dangerous_numerator','dangerous_denominator']+[c+'_support' for c in C]:out[k]=int(round(out[k]))
 return out,rep,cm[0]
def interval(values,informative):
 z=np.asarray(values,float);z=z[np.isfinite(z)];return (float(np.quantile(z,.025)),float(np.quantile(z,.975)),len(z)) if informative and len(z) else (None,None,len(z))
def draw_once(label,dates,seed):
 name='BOOTSTRAP_'+label+'_DATE_DRAWS_V6.json';assert not (R/name).exists(),'BOOTSTRAP_ALREADY_GENERATED'
 draw=np.random.default_rng(seed).integers(0,len(dates),size=(1000,len(dates))).tolist() if dates else []
 save(name,{'seed':seed,'dates':dates,'draws':draw,'generated_vector_N':len(draw),'generation_invocation_N':int(bool(dates)),'same_date_same_cluster_across_periods':True})
 return np.asarray([np.bincount(v,minlength=len(dates)) for v in draw],float) if dates else np.zeros((0,0)),{'path':name,'SHA256':sha(R/name),'seed':seed,'dates':dates,'vector_N':len(draw),'generation_invocation_N':int(bool(dates))}
def main():
 pre=json.loads((R/'PREDICTIVENESS_V6_PRECOMMIT.json').read_text())
 for n,h in pre['hashes'].items():assert sha(R/n)==h,'V6_PRECOMMIT_BREACH:'+n
 for n,h in json.loads((R/'EVALUATION_CODE_FREEZE_V6.json').read_text())['hashes'].items():assert sha(R/n)==h,'V6_CODE_BREACH:'+n
 old=[{**r,'experiment':'V5','registered_fold':'V5:F'+str(r['fold'])} for r in map(json.loads,(V/'R1_R2_FRESH_OOF_V5.jsonl').open())];fresh=[{**r,'experiment':'V6','registered_fold':'V6:F'+str(r['fold'])} for r in map(json.loads,(R/'R1_R2_OOF_V6.jsonl').open())]
 oldkeys={r['row_key'] for r in old};freshkeys={r['row_key'] for r in fresh};assert not oldkeys&freshkeys,'POOLED_PARTITION_DUPLICATE'
 sets={'V5_ONLY':old,'V6_ONLY':fresh,'V5_V6_POOLED':old+fresh};ds6=sorted({r['date'] for r in fresh});dsp=sorted({r['date'] for r in old+fresh}) if fresh else []
 w6,rec6=draw_once('V6_ONLY',ds6,pre['bootstrap_seed']);wp,recp=draw_once('POOLED',dsp,pre['pooled_bootstrap_seed']);save('BOOTSTRAP_GLOBAL_1000_RECEIPT_V6.json',{'V6_ONLY':rec6,'V5_V6_POOLED':recp,'new_generated_vectors':rec6['vector_N']+recp['vector_N'],'independent_new_draws':0,'inherited_known_cumulative_vectors':7000,'cumulative_known_vectors':7000+rec6['vector_N']+recp['vector_N'],'V1_3000_cap1000_breach_preserved':True,'same_index_all_comparisons_within_population':True,'pooled_overlapping_dates_single_cluster':True})
 metrics=[];risk=[];calibration=[];buckets=[];controls=[];concentration=[];confusion=[];cached={};congate={}
 for pop,oo in sets.items():
  dates,weight=(ds6,w6) if pop=='V6_ONLY' else (dsp,wp) if pop=='V5_V6_POOLED' else (sorted({r['date'] for r in old}),np.ones((0,len({r['date'] for r in old}))))
  if not dates and oo:dates=sorted({r['date'] for r in oo});weight=np.ones((0,len(dates)))
  for control in ['REAL','TRUE_NULL']:
   for model in ['R1','R2']:
    for cal in [False,True]:
     rr=[r for r in oo if r['control']==control and r['model']==model and r['calibrated']==cal]
     for fold in ['ALL']+sorted({r['registered_fold'] for r in rr}):
      rs=rr if fold=='ALL' else [r for r in rr if r['registered_fold']==fold];s,rep,cm=point_and_reps(rs,dates,weight);informative=len({r['date'] for r in rs})>=2 and len(weight)>0;record={'population':pop,'control':control,'model':model,'calibrated':cal,'fold':fold,**s,'CI_informative':informative}
      for k in CI_KEYS:
       lo,hi,n=interval(rep.get(k,[]),informative);record.update({k+'_CI_low':lo,k+'_CI_high':hi})
      metrics.append(record);calibration.append({k:v for k,v in record.items() if k in ['population','control','model','calibrated','fold','N','dates','row_LL','date_equal_LL','Brier','date_equal_Brier','ECE','CI_informative'] or k.endswith('_CI_low') and any(k.startswith(m) for m in ['row_LL','date_equal_LL','Brier','ECE']) or k.endswith('_CI_high') and any(k.startswith(m) for m in ['row_LL','date_equal_LL','Brier','ECE'])})
      if fold=='ALL':cached[(pop,control,model,cal)]=s
      if control=='REAL' and not cal:
       for i,a in enumerate(C):
        for j,b in enumerate(C):confusion.append({'population':pop,'model':model,'fold':fold,'actual':a,'predicted':b,'N':int(cm[i,j])})
     for kind in ['TOP_LABEL','DOWN_REVERSAL']:
      cells=defaultdict(list)
      for r in rr:
       p=r['probabilities'];score=max(p) if kind=='TOP_LABEL' else p[1];actual=r['predicted']==r['actual'] if kind=='TOP_LABEL' else r['actual']=='DOWN_REVERSAL';cells[min(int(score*10),9)].append((r,score,actual))
      for b in range(10):
       ix=cells[b];buckets.append({'population':pop,'control':control,'model':model,'calibrated':cal,'kind':kind,'bucket':b,'lower':b/10,'upper':(b+1)/10,'upper_inclusive':b==9,'N':len(ix),'dates':len({r[0]['date'] for r in ix}),'securities':len({r[0]['security_id'] for r in ix}),'mean_predicted_probability':sum(r[1] for r in ix)/len(ix) if ix else None,'actual_rate':sum(r[2] for r in ix)/len(ix) if ix else None})
  for cal in [False,True]:
   r1=[r for r in oo if r['control']=='REAL' and r['model']=='R1' and r['calibrated']==cal];r2={r['row_key']:r for r in oo if r['control']=='REAL' and r['model']=='R2' and r['calibrated']==cal};assert set(r2)=={r['row_key'] for r in r1},'MATCHED_KEYS'
   slices=[('ALL','ALL',r1)]
   for kind,col in [('fold','registered_fold'),('date','date'),('security','security_id'),('current_primary','current_primary')]:slices.extend((kind,str(v),[r for r in r1 if r[col]==v]) for v in sorted({r[col] for r in r1},key=str))
   for kind,value,aa in slices:
    bb=[r2[r['row_key']] for r in aa];st=[];rep=[];informative=len({r['date'] for r in aa})>=2 and len(weight)>0
    for model,rr in [('R1',aa),('R2',bb)]:
     s,r,_=point_and_reps(rr,dates,weight);st.append(s);rep.append(r);lo,hi,n=interval(r.get('dangerous_rate',[]),informative);risk.append({'population':pop,'calibrated':cal,'group_kind':kind,'group':value,'model':model,'N':s['N'],'dates':s['dates'],'numerator':s['dangerous_numerator'],'denominator':s['dangerous_denominator'],'rate':s['dangerous_rate'],'rate_CI_low':lo,'rate_CI_high':hi,'improvement_pp':None,'improvement_CI_low_pp':None,'improvement_CI_high_pp':None,'finite_bootstrap_N':n,'CI_informative':informative})
    diffs=100*(rep[0].get('dangerous_rate',np.array([]))-rep[1].get('dangerous_rate',np.array([])));lo,hi,n=interval(diffs,informative);point=100*(st[0]['dangerous_rate']-st[1]['dangerous_rate']) if all(s['dangerous_rate'] is not None for s in st) else None;risk.append({'population':pop,'calibrated':cal,'group_kind':kind,'group':value,'model':'R1_MINUS_R2','N':st[0]['N'],'dates':st[0]['dates'],'numerator':None,'denominator':None,'rate':None,'rate_CI_low':None,'rate_CI_high':None,'improvement_pp':point,'improvement_CI_low_pp':lo,'improvement_CI_high_pp':hi,'finite_bootstrap_N':n,'CI_informative':informative})
   real=cached[(pop,'REAL','R2',cal)];null=cached[(pop,'TRUE_NULL','R2',cal)];base=cached[(pop,'REAL','R1',cal)];nbase=cached[(pop,'TRUE_NULL','R1',cal)];ready=real['N']>0;gain=base['date_equal_LL']-real['date_equal_LL'] if ready else None;ngain=nbase['date_equal_LL']-null['date_equal_LL'] if ready else None;llfail=null['date_equal_LL']<=real['date_equal_LL']+1e-12 if ready else None;equiv=gain>1e-12 and ngain>0 and ngain+1e-12>=.9*gain if ready else None;controls.append({'population':pop,'model':'R2','calibrated':cal,'N':real['N'],'dates':real['dates'],'REAL_date_equal_LL':real.get('date_equal_LL'),'TRUE_NULL_date_equal_LL':null.get('date_equal_LL'),'REAL_R1_to_R2_gain':gain,'NULL_R1_to_R2_gain':ngain,'NULL_LL_equivalent_or_better':llfail,'positive_gain_equivalence_fail':equiv,'promotion_control_variant':pop!='V5_ONLY','control_status':'FAIL' if ready and (llfail or equiv) else 'PASS' if ready else 'NOT_EVALUABLE'})
  r1=[r for r in oo if r['control']=='REAL' and r['model']=='R1' and not r['calibrated']];r2={r['row_key']:r for r in oo if r['control']=='REAL' and r['model']=='R2' and not r['calibrated']};gain={'dangerous_error_reduction':[r for r in r1 if r['actual']=='DOWN_REVERSAL' and r['predicted']=='UP_CONTINUE' and r2[r['row_key']]['predicted']!='UP_CONTINUE'],'class_correctness_gain':[r for r in r1 if r['predicted']!=r['actual'] and r2[r['row_key']]['predicted']==r['actual']]};passed=True
  for name,rr in gain.items():
   for kind,col in [('date','date'),('security','security_id'),('current_primary','current_primary'),('fold','registered_fold')]:
    cc=Counter(r[col] for r in rr);maximum=max(cc.values())/len(rr) if rr else None;gate=maximum is not None and maximum<=.5+1e-12;applies=kind in ['date','security'];passed=passed and gate if applies else passed;concentration.append({'population':pop,'gain':name,'group_kind':kind,'group':'MAXIMUM','positive_gross_N':len(rr),'group_N':max(cc.values()) if cc else 0,'share':maximum,'gate_applies':applies,'PASS':gate if applies else None});concentration.extend({'population':pop,'gain':name,'group_kind':kind,'group':str(k),'positive_gross_N':len(rr),'group_N':n,'share':n/len(rr),'gate_applies':False,'PASS':None} for k,n in sorted(cc.items(),key=lambda x:str(x[0])))
  congate[pop]=bool(passed)
 riskall={p:next(r for r in risk if r['population']==p and not r['calibrated'] and r['group_kind']=='ALL' and r['model']=='R1_MINUS_R2') for p in sets};v6=cached[('V6_ONLY','REAL','R2',True)];raw6=cached[('V6_ONLY','REAL','R2',False)];pool=cached[('V5_V6_POOLED','REAL','R2',False)];calpass=v6['N']>0 and v6['date_equal_LL']<=1.05*raw6['date_equal_LL']+1e-12 and v6['Brier']<=1.05*raw6['Brier']+1e-12;sample=pool.get('DOWN_REVERSAL_support',0)>=100 and pool.get('UP_CONTINUE_support',0)>=100 and v6['dates']>=1 and v6['N']>0;direction=riskall['V6_ONLY']['improvement_pp'] is not None and riskall['V6_ONLY']['improvement_pp']>=-1e-12;hard=riskall['V5_V6_POOLED']['improvement_pp'] is not None and riskall['V5_V6_POOLED']['improvement_pp']>0 and riskall['V5_V6_POOLED']['improvement_CI_low_pp'] is not None and riskall['V5_V6_POOLED']['improvement_CI_low_pp']>0
 ctl=[r['control_status'] for r in controls if r['population'] in ['V6_ONLY','V5_V6_POOLED']];statusctl='FAIL' if 'FAIL' in ctl else 'PASS' if ctl and all(s=='PASS' for s in ctl) else 'NOT_EVALUABLE';gate={'sample_PASS':bool(sample),'pooled_dangerous_PASS':bool(hard),'V6_only_direction_PASS':bool(direction),'concentration_PASS':congate['V6_ONLY'] and congate['V5_V6_POOLED'],'concentration_by_population':congate,'R2_TRUE_NULL':statusctl,'calibration_PASS':bool(calpass),'V5_support':{'DOWN':75,'UP':354},'V6_only':v6,'V6_raw':raw6,'pooled':pool,'R1_R2_summary':{p:{m:cached[(p,'REAL',m,False)] for m in ['R1','R2']} for p in sets},'dangerous_improvement_by_population':riskall,'result_driven_changes':0,'R3_R4_new_fits':0,'rank_stability':'NOT_EVALUATED_NO_RANK_HANDOFF'}
 output('R1_R2_HARD_METRICS_V6.csv',[r for r in metrics if r['control']=='REAL' and not r['calibrated']]);output('ALL_METRICS_V6.csv',metrics);output('V5_V6_POOLED_METRICS.csv',[r for r in metrics if r['population']=='V5_V6_POOLED']);output('V6_ONLY_METRICS.csv',[r for r in metrics if r['population']=='V6_ONLY']);output('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V6.csv',risk);output('CALIBRATION_METRICS_V6.csv',calibration);output('CALIBRATION_BUCKETS_V6.csv',buckets);output('TRUE_NULL_R2_V6.csv',controls);output('STABILITY_AND_CONCENTRATION_V6.csv',concentration);output('CONFUSION_MATRIX_V6.csv',confusion);save('V6_GATE_MEASUREMENTS.json',gate)
 save('CALIBRATION_STATUS_V6.json',{'method':'ROLLING_INNER_OOF_TEMPERATURE_V1','method_changes':0,'probability_lane':'PASS' if calpass else 'FAIL','V6_only_raw':raw6,'V6_only_calibrated':v6,'gate':'date LL and row Brier each<=1.05 raw','calibration_does_not_block_hard_lane_if_all_H_pass':True,'rank_not_validated':True,'probability_interpretation_authorized':False,'final_handoff_permission_only_in_FINAL_RECEIPT_after_audit':True,'reselect_after_result':0})
 print(json.dumps({'V6_only_N':v6['N'],'V6_only_dates':v6['dates'],'V6_only_DOWN':v6.get('DOWN_REVERSAL_support',0),'pooled_DOWN':pool.get('DOWN_REVERSAL_support',0),'gate':{k:gate[k] for k in ['sample_PASS','pooled_dangerous_PASS','V6_only_direction_PASS','concentration_PASS','R2_TRUE_NULL','calibration_PASS']},'risk':riskall,'new_draws':len(w6)+len(wp)},allow_nan=False))
if __name__=='__main__':main()
