"""Fixed diagnostic anatomy. No feature choice or model/threshold mutation."""
import json,math
from statistics import mean,median,pvariance
from sklearn.metrics import roc_auc_score
from checkpoint import OUT,PRIVATE,save,sha
from io_data import rows
from movement import MOVEMENT,INTERACTIONS,quantile

def describe(values):
 return {'N':len(values),'mean':mean(values) if values else None,'median':median(values) if values else None,
  'p25':quantile(values,.25),'p75':quantile(values,.75)}

def stats(candidates,teacher,key,target):
 pairs=[(float(r['numeric'][key]),teacher[r['entry_id']][target]) for r in candidates
  if r['numeric'][key] is not None and teacher[r['entry_id']][target] is not None]
 pos=[x for x,y in pairs if y==1];neg=[x for x,y in pairs if y==0]
 den=math.sqrt((pvariance(pos)+pvariance(neg))/2) if pos and neg else 0
 diff=(mean(pos)-mean(neg))/den if den else None
 auc=float(roc_auc_score([y for x,y in pairs],[x for x,y in pairs])) if pos and neg else None
 values=[x for x,y in pairs];cuts=sorted(set(quantile(values,q) for q in (.2,.4,.6,.8))) if values else []
 bins=[]
 for index in range(len(cuts)+1):
  pp=[(x,y) for x,y in pairs if sum(x>c for c in cuts)==index]
  bins.append({'bin':index+1,'lower_exclusive':cuts[index-1] if index else None,'upper_inclusive':cuts[index] if index<len(cuts) else None,
   'N':len(pp),'positive_N':sum(y for x,y in pp),'positive_rate':sum(y for x,y in pp)/len(pp) if pp else None,
   'feature_median':median(x for x,y in pp) if pp else None})
 return {'feature':key,'target':target,'positive':describe(pos),'negative':describe(neg),
  'missing_N':len(candidates)-len(pairs),'standardized_difference':diff,'univariate_AUC':auc,
  'monotonic_quantile_bins':bins,'posthoc_sign_flip':False}

def main():
 runtime=rows(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz');teacher={r['entry_id']:r for r in rows(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz')}
 days=sorted({r['session'] for r in runtime});report={}
 for name,rr in [('ALL58',runtime),('OOF38',[r for r in runtime if r['session'] in days[20:]])]:
  report[name]={target:[stats(rr,teacher,'movement/'+k,target) for k in MOVEMENT+INTERACTIONS]
   for target in ('label_bigwinner5','label_bigwinner10')}
 result={'jst_before_fit':__import__('checkpoint').now(),'feature_manifest_hash':sha(OUT/'FEATURE_MANIFEST.json'),
  'design_hash':sha(OUT/'DESIGN_PRECOMMIT.json'),'fits_at_anatomy':0,'diagnostic_only':True,
  'Anatomy_changes_features':False,'feature_search':0,'threshold_search':0,'stats':report}
 save(OUT/'MOVEMENT_ANATOMY.json',result)
 print(json.dumps({'status':'ANATOMY_COMPLETE_MANIFEST_UNCHANGED','feature_N':19,'targets':2,'scopes':2,'fits':0}))

if __name__=='__main__':main()
