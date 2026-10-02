"""Apply the already-fixed Path B3-vs-B2 gate; no fit/draw/target changes."""
from pathlib import Path
from collections import defaultdict, Counter
import json,csv,numpy as np
R=Path(__file__).resolve().parent
def write(n,rows):
 with (R/n).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 rows=list(map(json.loads,(R/'OOF_ALL.jsonl').read_text().splitlines()));g=defaultdict(list)
 for r in rows:g[(r['task'],r['control'],r['model'])].append(r)
 states=list(csv.DictReader((R/'PER_STATE_PRECISION_RECALL_F1.csv').open()));metrics=list(csv.DictReader((R/'MODEL_METRICS_AGGREGATE.csv').open()));controls=list(csv.DictReader((R/'NEGATIVE_CONTROL_V2.csv').open()))
 boot=json.loads((R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').read_text());dates=boot['dates'];draws=np.asarray(boot['draws']);classes=json.loads((R/'TARGET_SCHEMA_V2.json').read_text())['class_order'];out=[]
 def precision(rr,state):
  pred=sum(r['predicted']==state for r in rr);correct=sum(r['predicted']==r['actual']==state for r in rr)
  return None if not pred else correct/pred
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']:
  a=g[(task,'REAL','B3')];b=g[(task,'REAL','B2')];bm={r['row_key']:r for r in b}
  am=next(r for r in metrics if (r['task'],r['control'],r['model'])==(task,'REAL','B3'));base=next(r for r in metrics if (r['task'],r['control'],r['model'])==(task,'REAL','B2'))
  calibration=bool(am['date_equal_Brier'] and base['date_equal_Brier']) and float(am['date_equal_Brier'])<=float(base['date_equal_Brier']) and float(am['date_equal_log_loss'])<=float(base['date_equal_log_loss'])
  veto=next(r['warning']=='True' for r in controls if (r['task'],r['control'],r['model'])==(task,'TRUE_NULL','B3'))
  for state in classes:
   support=next(r for r in states if (r['task'],r['control'],r['model'],r['State'])==(task,'REAL','B3',state))
   adequate=int(support['Predicted_N'])>=50 and int(support['Actual_N'])>=50 and int(am['date_N'])>=6 and int(support['predicted_fold_N'])>=2 and int(support['actual_fold_N'])>=2
   bs=[]
   for rr in [a,b]:
    count=np.array([[sum(r['predicted']==state for r in rr if r['date']==d),sum(r['actual']==r['predicted']==state for r in rr if r['date']==d)] for d in dates]);total=count[draws].sum(1);bs.append(np.divide(total[:,1],total[:,0],out=np.full(1000,np.nan),where=total[:,0]>0))
   delta=bs[0]-bs[1];delta=delta[np.isfinite(delta)];lo,hi=(np.quantile(delta,[1/720,719/720]).tolist() if len(delta) else [None,None]);positive=0
   for fold in [1,2,3]:
    af=[r for r in a if r['fold']==fold];bf=[r for r in b if r['fold']==fold];ap=precision(af,state);bp=precision(bf,state)
    positive+=int(ap is not None and bp is not None and ap>bp and any(r['actual']==state for r in af))
   dc=Counter();sc=Counter()
   for r in a:
    old=bm[r['row_key']];gain=int(r['actual']==r['predicted']==state)-int(old['actual']==old['predicted']==state)
    if gain>0:dc[r['date']]+=gain;sc[r['security_id']]+=gain
   total=sum(dc.values());ds=max(dc.values())/total if total else None;ss=max(sc.values())/total if total else None;concentration=ds is not None and ss is not None and max(ds,ss)<=.5
   passed=adequate and positive>=2 and lo is not None and lo>0 and calibration and concentration and not veto
   ap,bp=precision(a,state),precision(b,state)
   out.append({'task':task,'model':'B3','baseline':'B2','State':state,'support_adequate':adequate,'precision_improvement_vs_B2':None if ap is None or bp is None else ap-bp,'adjusted_CI_low':lo,'adjusted_CI_high':hi,'valid_vectors':len(delta),'positive_folds':positive,'global_calibration_not_worse':calibration,'max_date_gross_positive_share':ds,'max_security_gross_positive_share':ss,'true_null_veto':veto,'Path_incremental_evidence':passed,'new_draws':0})
 write('PATH_INCREMENTAL_ASSESSMENT_V2.csv',out)
 print(json.dumps({'Path_qualifying_states':[r['State'] for r in out if r['task']=='NEXT_DISTINCT_PRIMARY' and r['Path_incremental_evidence']],'new_draws':0}))
if __name__=='__main__':main()
