from pathlib import Path
from collections import Counter
from datetime import datetime,timezone,timedelta
import json,hashlib,csv,shutil,numpy as np,sys
import INHERITED_TARGET_ANATOMY_V3 as frozen
R=Path(__file__).resolve().parent
P=Path('/workspace/scratch/a1e749e0bd6c/state_predictiveness_v3_reversal_20261002_v1')
TASKS=frozen.TASKS
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def csvout(n,rows):
 cols=sorted(set().union(*(r.keys() for r in rows))) if rows else ['status']
 with (R/n).open('w') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def precheck():
 for n,h in json.loads((R/'PREDICTIVENESS_V4_PRECOMMIT.json').read_text())['hashes'].items():assert sha(R/n)==h,'PRECOMMIT_CHANGED'
def prepare():
 precheck();exp=R/'NEW_DEVELOPMENT';old=json.loads((P/'DATASET_MANIFEST.json').read_text())['pairs'];new=json.loads((exp/'DATASET_MANIFEST.json').read_text())['pairs'];pairs=[];keys=set();counts=Counter()
 assert len(old)==90 and len(old)+len(new)<=408,'PAIR_CAP'
 for original in old+new:
  isold=original in old;p=dict(original);pid=p['pair_id']
  source=Path(p['feature_path']) if isold else exp/'FEATURES'/f'{pid}.jsonl'
  trace=Path(p['trace_path']) if isold else exp/'STATE9_TRACES'/f'{pid}.jsonl'
  assert sha(source)==p['feature_SHA256'] and sha(trace)==p['state_trace_SHA256'],'FROZEN_SAVED_TRACE_CHANGED'
  rows=list(map(json.loads,source.read_text().splitlines()))
  if not isold:rows=frozen.anatomy(rows)
  out=R/'FEATURES'/f'{pid}.jsonl';out.parent.mkdir(exist_ok=True)
  exposure='V1_V2_V3_EXPOSED_DEV' if isold else 'V4_NEW_DEV_EVAL'
  with out.open('x') as f:
   for r in rows:
    assert r['row_key'] not in keys,'KEY_DUPLICATE';keys.add(r['row_key'])
    assert r['feature_max_timestamp']<=r['bar_end'] and r['anatomy_source_max_timestamp']<=r['bar_end'],'FEATURE_FUTURE'
    r['exposure']=exposure;f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n');counts['observed' if r['audit_source']['observed'] else 'null']+=1
  tr=R/'STATE9_TRACES'/f'{pid}.jsonl';tr.parent.mkdir(exist_ok=True);shutil.copyfile(trace,tr)
  endpoint_source=(Path(original['original_feature_path']).parent.parent if isold else exp)/'PATH_ENDPOINTS'/f'{pid}.jsonl'
  assert sha(endpoint_source)==p['path_endpoint_SHA256'],'PATH_ENDPOINT_IDENTITY'
  p.update(original_feature_path=str(source),original_feature_SHA256=sha(source),feature_path=str(out),feature_SHA256=sha(out),trace_path=str(tr),path_endpoint_path=str(endpoint_source),exposure=exposure,original_exposure=original.get('exposure','V4_NEW_DEV_EVAL'),old_label_path=str(P/'LABELS'/f'{pid}.jsonl') if isold else None)
  pairs.append(p)
 alldates=sorted({p['date'] for p in pairs});newdates=sorted({p['date'] for p in pairs if p['exposure']=='V4_NEW_DEV_EVAL'});plan=json.loads((R/'SPLIT_PLAN_V4.json').read_text());exposed=set(plan['old_exposed_dates_training_only'])
 assert not exposed.intersection(newdates),'PARTITION_CONTAMINATION'
 folds=[]
 for k,b in enumerate(plan['fixed_three_blocks'],1):
  train=[d for d in alldates if d<b[0]];folds.append({'fold':k,'test_dates':b,'train_dates':train,'test_start':b[0]+'T00:00:00+09:00','initial_train_dates_sufficient':len(train)>=5})
 save('SPLIT_REALIZED_V4.json',{'mode':'V4_NEW_DEV_EVAL','folds':folds,'input_dates':alldates,'new_eligible_dates':newdates,'warmup_new_dates':plan['warmup_new_dates'],'empty_test_dates':[d for b in plan['fixed_three_blocks'] for d in b if d not in newdates],'random_row_split':False,'availability_or_result_refolding':False})
 save('DATASET_MANIFEST_V4.json',{'JST':now(),'pairs':pairs,'endpoint_N':len(keys),'observed_N':counts['observed'],'null_N':counts['null'],'input_dates':alldates,'new_eligible_dates':newdates,'old_saved_endpoint_reuse':29305,'new_frozen_endpoint_N':len(keys)-29305,'feature_anatomy_before_labels':True,'future_classifier_input':0})
 save('C3_DATASET_FIXATION_RECEIPT.json',{'JST':now(),'dataset_SHA256':sha(R/'DATASET_MANIFEST_V4.json'),'split_SHA256':sha(R/'SPLIT_REALIZED_V4.json'),'new_label_N':0,'old_label_reuse_endpoint_N':29305})
 newledger=json.loads((exp/'DEVELOPMENT_COMPLETION_LEDGER.json').read_text());ledger=[]
 for p in old:ledger.append({'pair_id':p['pair_id'],'date':p['date'],'security_id':p['security_id'],'status':'ACQUIRED','reason':'PARENT_SAVED_TRACE_REUSED','exposure':'V1_V2_V3_EXPOSED_DEV','new_request':False,'replacement':0})
 # Preserve all seven original unavailable decisions without new requests or speculative retries.
 v2=P.parent/'state_predictiveness_v2_nextstate_20261002_v1';scope3=json.loads((P/'DATA_SCOPE_V3.json').read_text());have={p['pair_id'] for p in old}
 for i,p in enumerate(scope3['original_proposals'],1):
  pid=f'N{i:03d}'
  if pid in have:continue
  reasons={2:('U_UNAVAILABLE','NO_PREVIOUS_ADJACENT_RETURNS'),17:('RAW_UNAVAILABLE','NO_MINUTE_ROWS'),33:('RAW_UNAVAILABLE','NO_MINUTE_ROWS'),39:('U_UNAVAILABLE','U_UNAVAILABLE'),59:('U_UNAVAILABLE','NO_PREVIOUS_ADJACENT_RETURNS'),63:('U_UNAVAILABLE','NO_PREVIOUS_ADJACENT_RETURNS'),66:('RAW_UNAVAILABLE','NO_MINUTE_ROWS')}
  status,reason=reasons[i];ledger.append({'pair_id':pid,'date':p['date'],'security_id':p['security_id'],'status':status,'reason':reason,'exposure':'V1_V2_V3_EXPOSED_DEV','new_request':False,'replacement':0})
 ledger.extend({**x,'exposure':'V4_NEW_DEV_EVAL','new_request':x.get('request_attempted',False)} for x in newledger)
 csvout('DEVELOPMENT_COMPLETION_LEDGER_V4.csv',ledger)
 unavailable=[x for x in ledger if x['status']!='ACQUIRED']
 unavailable.extend(json.loads((exp/'METADATA_UNAVAILABLE.json').read_text()))
 unavailable.extend({**x,'stage':'DATED_MASTER_OR_FACTOR_UNIVERSE'} for x in json.loads((exp/'METADATA_DATE_LEDGER.json').read_text()) if x['status']!='METADATA_SELECTION_COMPLETE' or x['selected_proposal_N']<3)
 csvout('UNAVAILABLE_INPUTS_V4.csv',unavailable)
 save('DEVELOPMENT_COMPLETION_SUMMARY_V4.json',{'old_acquired_reused_N':90,'old_unavailable_retained_N':7,'new_selected_N':len(newledger),'new_status_counts':dict(Counter(x['status'] for x in newledger)),'new_date_links_N':106,'new_acquired_date_N':len(newdates),'new_unacquired_selected_N':sum(x['status']!='ACQUIRED' for x in newledger),'metadata_unselected_capacity':sum(3-x['selected_proposal_N'] for x in json.loads((exp/'METADATA_DATE_LEDGER.json').read_text())),'remaining_selected_old_and_new_N':sum(x['status']!='ACQUIRED' for x in ledger),'all_link_attempts_recorded':True,'price_or_outcome_refill':0})
 print(json.dumps({'phase':'features','pairs':len(pairs),'endpoints':len(keys),'observed':counts['observed'],'new_dates':len(newdates)}))
def labels():
 precheck();manifest=json.loads((R/'DATASET_MANIFEST_V4.json').read_text());counts=Counter();files=[];reused=0;generated=0
 for p in manifest['pairs']:
  rows=list(map(json.loads,Path(p['feature_path']).read_text().splitlines()));look={r['tradable_index']:i for i,r in enumerate(rows) if r['tradable_index'] is not None};out=R/'LABELS'/f"{p['pair_id']}.jsonl";out.parent.mkdir(exist_ok=True)
  oldlabels=list(map(json.loads,Path(p['old_label_path']).read_text().splitlines())) if p['old_label_path'] else None
  with out.open('x') as f:
   for i,r in enumerate(rows):
    if oldlabels is not None:
     l=oldlabels[i];assert l['row_key']==r['row_key'],'REUSE_LABEL_KEY';l['exposure']=p['exposure'];reused+=1
    else:
     real={t:frozen.target(rows,i,t,look) for t in TASKS};si=look.get(r['tradable_index']+60) if r['tradable_index'] is not None else None;guard=False
     if si is not None:
      chain=rows[i:si+1];guard=all(frozen.admitted(x) and x['causal_segment_id']==r['causal_segment_id'] for x in chain) and all(b['tradable_index']==a['tradable_index']+1 and b['scheduled_t']==a['scheduled_t']+1 for a,b in zip(chain,chain[1:]))
     shift={t:frozen.target(rows,si,t,look) if guard else {'available':False,'target':None,'label_end':None,'reason':'SHIFT_ANCHOR_OR_BRIDGE_UNAVAILABLE'} for t in TASKS}
     l={'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'bar_end':r['bar_end'],'exposure':p['exposure'],'REAL':real,'SHIFT60':shift};generated+=1
    for control in ['REAL','SHIFT60']:
     for task,v in l[control].items():counts[(p['exposure'],control,task,v['target'] if v['available'] else v['reason'])]+=1
    f.write(json.dumps(l,sort_keys=True,separators=(',',':'))+'\n')
  files.append({'path':str(out.relative_to(R)),'SHA256':sha(out),'bytes':out.stat().st_size})
 save('C4_LABEL_FIXATION_RECEIPT.json',{'JST':now(),'files':files,'availability':[{'exposure':e,'control':c,'task':t,'reason_or_class':s,'N':n} for (e,c,t,s),n in sorted(counts.items())],'post_precommit_changes':0,'old_label_endpoint_reuse':reused,'new_label_endpoint_N':generated})
 ds=sorted({d for f in json.loads((R/'SPLIT_REALIZED_V4.json').read_text())['folds'] for d in f['test_dates']})
 assert not (R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').exists(),'NO_DUPLICATE_BOOTSTRAP_GENERATION'
 draws=np.random.default_rng(2026100403).integers(0,len(ds),size=(1000,len(ds)))
 save('BOOTSTRAP_GLOBAL_DATE_DRAWS.json',{'seed':2026100403,'dates':ds,'draws':draws.tolist(),'generated_vector_N':1000,'distinct_value_N':len({tuple(x) for x in draws}),'generation_invocation_N':1})
 save('BOOTSTRAP_GLOBAL_1000_RECEIPT.json',{'bootstrap_unique_draw_vector_N':1000,'bootstrap_total_generated_draws':1000,'distinct_value_N':len({tuple(x) for x in draws}),'independent_checker_new_draws':0,'SHA256':sha(R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json'),'V1_breach_3000_cap1000_preserved':True,'cumulative_known_generated_vectors':6000})
 print(json.dumps({'phase':'labels','old_reused':reused,'new_generated':generated,'new_core':[{'status':s,'N':n} for (e,c,t,s),n in sorted(counts.items()) if e=='V4_NEW_DEV_EVAL' and c=='REAL' and t=='CONTEXT_REVERSAL']}))
if __name__=='__main__':{'features':prepare,'labels':labels}[sys.argv[1]]()
