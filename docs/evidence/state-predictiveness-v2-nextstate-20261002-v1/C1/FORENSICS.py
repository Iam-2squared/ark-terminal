from pathlib import Path
from collections import Counter, defaultdict
import csv,json,hashlib,datetime,zipfile
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_20261002_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def out(n,rows):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['status']);w.writeheader();w.writerows(rows)
def main():
 assert sha(V/'PREDICTIVENESS_CONTRACT_V1.md')=='393de497cd2218f546ec01d2b0cf24f1d2791332c3f5400069d102ccb5e9fe41'
 checks=[]
 for x in json.loads((V/'FROZEN_IDENTITY_RECEIPT.json').read_text())['checks'][:5]:
  p=Path(x['source_path']);assert sha(p)==x['expected_SHA256'];checks.append({'kind':x['kind'],'SHA256':sha(p),'match':True})
 save('FROZEN_IDENTITY_RECEIPT.json',{'checks':checks,'semantic_changes':0,'V1_status_retained':'BLOCKED_LEAKAGE_OR_SEMANTIC_INTEGRITY','V1_HEAD':'7e3ce89cb2928d46f66d4606e1010ba3a3a1896f'})
 with zipfile.ZipFile(R.parent/'State_Predictiveness_ALL_20261002.zip') as z:assert z.testzip() is None
 names=['00_README.txt','REPORT-ja.md','FINAL_RECEIPT.json','NEXT_STAGE_HANDOFF.md','PREDICTIVENESS_CONTRACT_V1.md','PREDICTIVENESS_PRECOMMIT.json','SPLIT_PLAN.json','SPLIT_REALIZED.json','GATE_ASSESSMENT.json','GATE_ADDITIONAL_FINDINGS_APPEND_ONLY.json','COMPUTE_BUDGET_FINDING.json','NEGATIVE_CONTROL_RESULTS.csv','TARGET_CONTROL_AVAILABILITY.csv','SECONDARY_METRICS.csv','ENTRY_HANDOFF.json','CHECKPOINTS/C5_POST_COMMIT_RECEIPT.json','GITHUB_REQUEST_USAGE_AT_DELIVERY.json','BUDGET_FINAL.json','EXPOSURE_FINAL_APPEND_ONLY_DELTA.json']
 save('V1_INPUT_INDEX.json',{'files':[{'path':str(V/n),'SHA256':sha(V/n),'bytes':(V/n).stat().st_size} for n in names],'all_zip_SHA256':sha(R.parent/'State_Predictiveness_ALL_20261002.zip'),'read_only':True})
 features={};labels={};pairs=[]
 m=json.loads((V/'RECEIVED_DEVELOPMENT/DATASET_MANIFEST.json').read_text())
 for p in m['pairs']:
  f=V/'RECEIVED_DEVELOPMENT/FEATURES'/f"{p['pair_id']}.jsonl";assert sha(f)==p['feature_SHA256']
  rows=[json.loads(l) for l in f.read_text().splitlines()];pairs.append((p,rows))
  features.update({r['row_key']:r for r in rows})
  labels.update({r['row_key']:r for r in map(json.loads,(V/'LABELS'/f"{p['pair_id']}.jsonl").read_text().splitlines())})
 folds=json.loads((V/'SPLIT_REALIZED.json').read_text())['folds'];datefold={d:f['fold'] for f in folds for d in f['test_dates']}
 reasons=Counter();raw=Counter();audit=[];serial=defaultdict(list)
 for p,rows in pairs:
  lookup={r['tradable_index']:r for r in rows if r['tradable_index'] is not None}
  for r in rows:
   l=labels[r['row_key']];raw[(r['date'],r['security_id'],'RAW_PRESENT' if r['audit_source']['raw_present'] else 'RAW_ABSENT')]+=1
   for h in [5,15,30]:
    q=l['real'][str(h)];reasons[(r['date'],r['security_id'],h,'AVAILABLE' if q['available'] else q['unavailable_reason'])]+=1
    s=l['shift60'][str(h)]
    if not s['available']:continue
    start=lookup[r['tradable_index']+60];end=features[s['future_key']]
    violations=[]
    if r['feature_max_timestamp']>r['bar_end']:violations.append('FEATURE_FUTURE')
    if not r['bar_end']<start['bar_end']<end['bar_end']:violations.append('TIMESTAMP_ORDER')
    if start['tradable_index']-r['tradable_index']!=60 or end['tradable_index']-start['tradable_index']!=h:violations.append('EXACT_SLOT')
    between=[x for x in rows if r['scheduled_t']<=x['scheduled_t']<=end['scheduled_t']]
    if any(x['causal_segment_id']!=r['causal_segment_id'] or not x['audit_source']['raw_present'] or x['audit_source']['numeric_status']!='ACCEPTED' or x['audit_source']['auction']!='CONTINUOUS' for x in between):violations.append('BOUNDARY')
    audit.append({'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'horizon':h,'fold':datefold.get(r['date'],0),'feature_max_timestamp':r['feature_max_timestamp'],'feature_t':r['bar_end'],'shift_start':start['bar_end'],'shift_end':end['bar_end'],'segment':r['causal_segment_id'],'violations':';'.join(violations),'current_primary':r['audit_source']['formal_primary'],'shift_primary':start['audit_source']['formal_primary']})
    if q['available']:serial[h].append((float(q['y_token']),float(s['y_token']),r['audit_source']['formal_primary']==start['audit_source']['formal_primary']))
 import numpy as np
 stats={str(h):{'matched_all_N':len(a),'Pearson_real_shift':None if len(a)<2 else float(np.corrcoef(np.array(a)[:,:2].T)[0,1]),'current_shift_primary_equal_fraction':float(np.mean([x[2] for x in a])) if a else None} for h,a in serial.items()}
 out('V1_SHIFT60_TIMESTAMP_AUDIT.csv',audit)
 out('V1_FOLD0TARGET_REASON_COUNTS.csv',[{'date':d,'security_id':s,'horizon':h,'reason':r,'N':n,'fold':datefold.get(d,0)} for (d,s,h,r),n in sorted(reasons.items())])
 out('V1_RAW_COUNTS_BY_SECURITY_DATE.csv',[{'date':d,'security_id':s,'status':r,'N':n} for (d,s,r),n in sorted(raw.items())])
 matched=[]
 for h in [5,15,30]:
  real=list(csv.DictReader((V/f'OOF/REAL_H{h}.csv').open()));shift=list(csv.DictReader((V/f'OOF/SHIFT60_H{h}.csv').open()))
  for model in ['B0','B1','B2','B3']:
   a={r['row_key']:r for r in real if r['model']==model};b={r['row_key']:r for r in shift if r['model']==model};assert set(b)<=set(a)
   assert all(a[k]['fold']==b[k]['fold'] for k in b)
   matched.append({'horizon':h,'model':model,'matched_row_N':len(b),'date_N':len({r['date'] for r in b.values()}),'fold_N':len({r['fold'] for r in b.values()}),'same_keys_and_folds':True,'dates':sorted({r['date'] for r in b.values()})})
 save('V1_SHIFT60_FORENSIC.json',{'timestamp_violation_N':sum(bool(a['violations']) for a in audit),'audited_available_shift_targets_N':len(audit),'matched':matched,'serial_dependence_descriptive':stats,'registered_STOP_retained':True,'actual_leakage_proven':False,'taxonomy_V2':'DEPENDENCE_REGIME_STRESS','concentration_reason':'Need an intact exact 60+h slot window; sparse raw eliminates most sessions. Matching OOF availability leaves two dates in fold1. Pearson/equal-Primary are descriptive, not causal attribution.'})
 draws=json.loads((V/'BOOTSTRAP_DATE_DRAWS.json').read_text());counts={h:len(x['draws']) for h,x in draws['by_horizon'].items()}
 save('V1_BOOTSTRAP_FORENSIC.json',{'registered_cap':1000,'actual':sum(counts.values()),'by_horizon':counts,'excess':sum(counts.values())-1000,'cause':'Separate rng.integers(1000,date_N) within horizon loop','source_SHA256':sha(V/'FIT_WALK_FORWARD.py'),'V1_nonconformance_preserved':True,'V2_solution':'Generate once 1000 global date vectors; reuse stored indices for every task and metric; checker generates0.'})
 focus=[{'date':d,'security_id':s,'horizon':h,'reason':r,'N':n} for (d,s,h,r),n in sorted(reasons.items()) if d in ['2025-04-30','2025-06-02']]
 save('V1_FOLD0TARGET_FORENSIC.json',{'fold':2,'dates':['2025-04-30','2025-06-02'],'reason_counts':focus,'full_denominator_table':'V1_FOLD0TARGET_REASON_COUNTS.csv','not_deleted_or_reselected':True})
 save('C0_INHERITANCE.json',{'JST':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'parent_HEAD':'7e3ce89cb2928d46f66d4606e1010ba3a3a1896f','status':'V1_INHERITED_NO_RESET','old_RC1_FAIL':16,'old_workflow_incident':88,'remote_GET_performed':True})
 print(json.dumps({'features':len(features),'shift_checks':len(audit),'shift_violations':sum(bool(a['violations']) for a in audit),'fold2':focus}))
if __name__=='__main__':main()
