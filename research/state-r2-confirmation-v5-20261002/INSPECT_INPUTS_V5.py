from pathlib import Path
from collections import Counter
import json,csv
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def j(n):return json.loads((P/n).read_text())
def main():
 m=j('DATASET_MANIFEST_PORTABLE_V4.json')
 print('manifest_pair',m['pairs'][0])
 print('schema',j('FEATURE_SCHEMA_V4.json'))
 print('split',j('SPLIT_PLAN_V4.json'))
 print('realized',[{k:v for k,v in f.items() if k not in ['test_dates','train_dates']} for f in j('SPLIT_REALIZED_V4.json')['folds']])
 p=m['pairs'][0]
 for n in ['feature_path','trace_path','original_feature_path']:
  if n in p:
   q=P/p[n];print(n,q, next(iter(q.open())).strip()[:10000])
 print('OOF_sample',next(iter((P/'OOF_ALL.jsonl').open())).strip())
 art=j('FITTED/CONTEXT_REVERSAL_REAL_R3_F2.json')
 print('fit_keys',list(art),'temperature',art['temperature'],'alpha',art['alpha'],'val_grid',art['validation_grid'],'T_grid',art['temperature_grid'])
 with (P/'DEVELOPMENT_COMPLETION_LEDGER_V4.csv').open() as f:rows=list(csv.DictReader(f))
 unavailable=[r for r in rows if r['security_id'] and r['status']!='ACQUIRED']
 print('retry_N',len(unavailable),'status',dict(Counter(r['status'] for r in unavailable)),'days',len({r['date'] for r in unavailable}),'retry_samples',unavailable[:10])
 print('scope_keys',list(j('DATA_SCOPE_V4.json')))
 for k,v in j('DATA_SCOPE_V4.json').items():
  if k not in ['fixed_links','parent_exclusion_pairs','new_unexposed_links']:print('scope',k,str(v)[:2500])
 print('NEW_DEV_FILES',[str(f.relative_to(P)) for f in (P/'NEW_DEVELOPMENT').iterdir()])
 print('budget keys',list(j('BUDGET_FINAL_V4.json')))
 print('exposure',j('EXPOSURE_APPEND_ONLY_DELTA.json'))
if __name__=='__main__':main()
