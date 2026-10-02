"""Precommitted V4 gates applied to fixed OOF, without draws or fits."""
from pathlib import Path
from collections import defaultdict,Counter
import json,csv,hashlib,numpy as np
R=Path(__file__).resolve().parent
def save(n,x):(R/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def csvout(n,rows):
 cols=list(rows[0]) if rows else ['status']
 with (R/n).open('w') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def main(m,groups,controls):
 cl=m.CLASSES['CONTEXT_REVERSAL'];get=lambda model:groups.get(('CONTEXT_REVERSAL','REAL',model,True),[])
 def fdraw(rows,kind):
  a=np.zeros((len(m.DATES),4,4));idx={x:i for i,x in enumerate(cl)}
  for r in rows:a[m.DI[r['date']],idx[r['actual']],idx[r['predicted']]]+=1
  matrices=(m.COUNTS@a.reshape(len(m.DATES),16)).reshape(1000,4,4);truth=matrices.sum(2);pred=matrices.sum(1);tp=np.diagonal(matrices,axis1=1,axis2=2)
  f=np.divide(2*tp,truth+pred,out=np.full((1000,4),np.nan),where=(truth>0)&(pred>0))
  return np.nan_to_num(f,nan=0).mean(1) if kind=='macro_F1' else f[:,cl.index(kind)]
 def concentration(base,test):
  b={r['row_key']:r for r in base};correct=[r for r in test if r['actual']==r['predicted'] and b[r['row_key']]['actual']!=b[r['row_key']]['predicted']]
  risk=[r for r in test if not(r['predicted']=='UP_CONTINUE' and r['actual']=='DOWN_REVERSAL') and b[r['row_key']]['predicted']=='UP_CONTINUE' and b[r['row_key']]['actual']=='DOWN_REVERSAL']
  out={}
  for name,rs in [('correctness',correct),('dangerous_reduction',risk)]:
   ds=Counter(r['date'] for r in rs);ss=Counter(r['security_id'] for r in rs)
   out[name+'_gross_gain_N']=len(rs);out[name+'_max_date_share']=max(ds.values())/len(rs) if rs else None;out[name+'_max_security_share']=max(ss.values())/len(rs) if rs else None
  out['concentration_PASS']=all(out[n+'_'+k] is not None and out[n+'_'+k]<=.5 for n in ['correctness','dangerous_reduction'] for k in ['max_date_share','max_security_share'])
  return out
 primary=get('R2');metric=m.metrics(primary,cl);support=Counter(r['actual'] for r in primary);adequate=metric['date_N']>=8 and metric['fold_N']>=2 and support['DOWN_REVERSAL']>=100 and support['UP_CONTINUE']>=100
 rows=[];promoted=[];gains=[]
 for model in ['R2','R3','R4']:
  test=get(model);mm=m.metrics(test,cl);modelpass=True
  for baseline in ['R1']+(['R2'] if model in ['R3','R4'] else []):
   base=get(baseline);bm=m.metrics(base,cl);con=concentration(base,test);delta=m.danger_draw(base)-m.danger_draw(test);dl,dh,dv=m.interval(delta);point=m.risk(base)['rate'];target=m.risk(test)['rate'];danger=dl is not None and dl>0 and point is not None and target is not None and point>target
   major=[];maingain=[]
   for kind in ['DOWN_REVERSAL','UP_CONTINUE','macro_F1']:
    pc=m.perclass(m.cm(test,cl),cl.index(kind)) if kind!='macro_F1' else None;bc=m.perclass(m.cm(base,cl),cl.index(kind)) if kind!='macro_F1' else None
    v=pc['F1'] if pc else mm['macro_F1'];u=bc['F1'] if bc else bm['macro_F1'];lo,hi,valid=m.interval(fdraw(test,kind)-fdraw(base,kind),.05/(2*6));positive=0
    for fold in [1,2,3]:
     aa=[r for r in test if r['fold']==fold];bb=[r for r in base if r['fold']==fold]
     va=m.perclass(m.cm(aa,cl),cl.index(kind))['F1'] if kind!='macro_F1' else m.metrics(aa,cl)['macro_F1'];vb=m.perclass(m.cm(bb,cl),cl.index(kind))['F1'] if kind!='macro_F1' else m.metrics(bb,cl)['macro_F1']
     positive+=int(va is not None and vb is not None and va>vb)
    predicted_ok=pc is None or pc['Predicted_N']>=100
    ok=predicted_ok and v is not None and u is not None and v>u and lo is not None and lo>0 and positive>=2
    major.append(ok);maingain.append({'metric':kind,'point_improvement':v-u if v is not None and u is not None else None,'adjusted_CI_low':lo,'adjusted_CI_high':hi,'valid_draws':valid,'positive_folds':positive,'predicted_support_gate':predicted_ok,'PASS':bool(ok)})
    gains.append({'model':model,'baseline':baseline,**maingain[-1]})
   dr=m.perclass(m.cm(test,cl),1)['Recall'];bd=m.perclass(m.cm(base,cl),1)['Recall'];recall=dr is not None and bd is not None and dr>=bd-.02
   calibration=mm['date_equal_log_loss'] is not None and bm['date_equal_log_loss'] is not None and mm['date_equal_log_loss']<=1.05*bm['date_equal_log_loss'] and mm['date_equal_Brier']<=1.05*bm['date_equal_Brier']
   nullfail=any(x['task']=='CONTEXT_REVERSAL' and x['control']=='TRUE_NULL' and x['model']==model and x['calibrated'] and x['warning'] for x in controls)
   passed=adequate and danger and any(major) and calibration and recall and con['concentration_PASS'] and not nullfail
   rows.append({'model':model,'baseline':baseline,'OOF_dates':metric['date_N'],'evaluable_folds':metric['fold_N'],'DOWN_actual_N':support['DOWN_REVERSAL'],'UP_actual_N':support['UP_CONTINUE'],'core_support_PASS':bool(adequate),'dangerous_point_improvement':point-target if point is not None and target is not None else None,'dangerous_CI95_low':dl,'dangerous_CI95_high':dh,'dangerous_valid_draws':dv,'dangerous_improvement_PASS':bool(danger),'major_metric_PASS':any(major),'calibration_not_fatally_worse_PASS':bool(calibration),'DOWN_recall_guard_PASS':bool(recall),**con,'TRUE_NULL_equivalent_or_better':nullfail,'comparison_PASS':bool(passed)})
   modelpass &= passed
  if modelpass:promoted.append(model)
 csvout('PROMOTION_GATE_V4.csv',rows);csvout('MAJOR_METRIC_GAIN_GATE_V4.csv',gains)
 nullintegrity=[x for x in controls if x['task']=='CONTEXT_REVERSAL' and x['control']=='TRUE_NULL' and x['model'] in ['R2','R3','R4'] and x['calibrated'] and x['warning']]
 status='BLOCKED_V4_INTEGRITY' if nullintegrity else 'STATE_REVERSAL_INTELLIGENCE_DEV_CANDIDATE_READY_FOR_ENTRY_RESEARCH' if promoted else 'STATE_REVERSAL_INTELLIGENCE_MEASURED_NO_PROMOTABLE_SIGNAL' if adequate else 'STATE_REVERSAL_INTELLIGENCE_LIMITED_SAMPLE'
 save('GATE_ASSESSMENT_V4.json',{'status_pending_independent_audit':status,'integrity_control_PASS':not nullintegrity,'control_integrity_failures':nullintegrity,'core_rows':metric['row_N'],'core_dates':metric['date_N'],'core_folds':metric['fold_N'],'class_support':dict(support),'core_support_adequate':adequate,'comparison_qualifying_before_global_integrity':promoted,'promoted_models':[] if nullintegrity else promoted,'post_result_changes':0,'new_fits':0,'new_draws':0})
 # Required file names and extra ECE/F1 deltas; all derived from identical fixed OOF.
 for src,dst in [('REVERSAL_METRICS_AGGREGATE_V4.csv','REVERSAL_METRICS_V4.csv')]:
  (R/dst).write_bytes((R/src).read_bytes())
 inc=list(csv.DictReader((R/'R0_R1_R2_R3_R4_INCREMENTAL_V4.csv').open()))
 for item in inc:
  cal=item['calibrated']=='True';a=groups.get((item['task'],'REAL',item['baseline'],cal),[]);b=groups.get((item['task'],'REAL',item['model'],cal),[]);am=m.metrics(a,m.CLASSES[item['task']]);bm=m.metrics(b,m.CLASSES[item['task']]);item['top_label_ECE_improvement']=am['top_label_ECE']-bm['top_label_ECE'] if am['top_label_ECE'] is not None and bm['top_label_ECE'] is not None else None
  for c in ['DOWN_REVERSAL','UP_CONTINUE']:
   if item['task']=='CONTEXT_REVERSAL':
    af=m.perclass(m.cm(a,cl),cl.index(c))['F1'];bf=m.perclass(m.cm(b,cl),cl.index(c))['F1'];item[c+'_F1_improvement']=bf-af if af is not None and bf is not None else None
   else:item[c+'_F1_improvement']=None
 csvout('R0_R1_R2_R3_R4_INCREMENTAL_V4.csv',inc)
 # Compare pre-existing path tendencies to new OOF cohorts, without selecting new rules.
 tables=[];baseup=458/597;basedown=98/597;newup=support['UP_CONTINUE']/len(primary) if primary else None;newdown=support['DOWN_REVERSAL']/len(primary) if primary else None
 for length in range(1,5):
  tab=list(csv.DictReader((R/f'PATH_ANATOMY_LENGTH{length}_V4.csv').open()));old={x['sequence']:x for x in csv.DictReader((R/f'INHERITED_V3/REVERSAL_PATH_ANATOMY_LENGTH{length}.csv').open())}
  for name,cond in [('RISE_START',lambda x:x['sequence'].split('>')[0]=='RISE'),('SHARP_RISE_START',lambda x:x['sequence'].split('>')[0]=='SHARP_RISE'),('PULLBACK_INCLUDED',lambda x:'PULLBACK' in x['sequence'].split('>')),('RISE_STOP_INCLUDED',lambda x:'RISE_STOP' in x['sequence'].split('>'))]:
   csvout(f'PATH_{name}_LENGTH{length}_V4.csv',[x for x in tab if cond(x)])
  for x in tab:
   if x['sequence'] not in old:continue
   y=old[x['sequence']];u=float(x['UP_CONTINUE_rate']);d=float(x['DOWN_REVERSAL_rate']);pu=float(y['UP_CONTINUE_rate']);pd=float(y['DOWN_REVERSAL_rate'])
   tables.append({'length':length,'sequence':x['sequence'],'V3_N':int(y['N']),'V4_N':int(x['N']),'V3_dates':int(y['date_N']),'V4_dates':int(x['date_N']),'V3_UP_rate':pu,'V4_UP_rate':u,'V3_DOWN_rate':pd,'V4_DOWN_rate':d,'UP_direction_relative_to_cohort_reproduced':(pu-baseup)*(u-newup)>0 if newup is not None else None,'DOWN_direction_relative_to_cohort_reproduced':(pd-basedown)*(d-newdown)>0 if newdown is not None else None,'V4_supported_descriptive_sequence':x['supported_descriptive_sequence']=='True','cohort_comparison_not_controlled_causal_gain':True})
 csvout('PATH_TENDENCY_V3_V4.csv',tables)
 print(json.dumps({'gate':status,'core_rows':len(primary),'dates':metric['date_N'],'folds':metric['fold_N'],'support':dict(support),'promoted':promoted,'control_integrity_failure_models':[x['model'] for x in nullintegrity]}))
if __name__=='__main__':raise SystemExit('Invoke only from METRICS_V4 fixed OOF aggregation')
