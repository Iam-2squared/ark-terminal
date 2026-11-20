from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,sys,numpy as np
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_20261002_v1'
sys.path.insert(0,str(V));from BUILD_TARGETS import price_target
TASKS=['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def state_target(rows,i,task):
 a=rows[i];s=a['audit_source'];out={'available':False,'reason':None,'target':None,'label_start':a['bar_end'],'label_end':None,'donor_anchor_key':a['row_key']}
 if not s['observed'] or s['formal_primary'] is None or s['numeric_status']!='ACCEPTED' or s['auction']!='CONTINUOUS' or a['tradable_index'] is None:out['reason']='CURRENT_NOT_OBSERVED_CONTINUOUS';return out
 look={r['tradable_index']:j for j,r in enumerate(rows) if r['tradable_index'] is not None};first=None;firstend=None;last=i
 for step in range(1,2 if task=='NEXT_OBSERVED_PRIMARY' else 31):
  j=look.get(a['tradable_index']+step)
  if j is None:out['reason']='WINDOW_OUTSIDE_SESSION';return out
  b=rows[j];bs=b['audit_source']
  if j!=last+1:out['reason']='SCHEDULE_DISCONTINUITY';return out
  if b['causal_segment_id']!=a['causal_segment_id']:out['reason']='SEGMENT_BREAK';return out
  if not bs['observed'] or bs['formal_primary'] is None or bs['numeric_status']!='ACCEPTED' or bs['auction']!='CONTINUOUS':out['reason']='NULL_GAP_OR_AUCTION';return out
  if task=='NEXT_OBSERVED_PRIMARY':return {**out,'available':True,'target':bs['formal_primary'],'label_end':b['bar_end'],'reason':None,'future_key':b['row_key']}
  trs=[e for e in bs['events'] if e['event_type']=='TRANSITION']
  changed=bs['formal_primary']!=rows[last]['audit_source']['formal_primary']
  assert len(trs)==int(changed),'FROZEN_EVENT_ENDPOINT_MISMATCH'
  if trs and first is None:
   assert trs[0]['from_primary_or_null']==rows[last]['audit_source']['formal_primary'] and trs[0]['to_primary_or_null']==bs['formal_primary']
   first=bs['formal_primary'];firstend=b['bar_end']
   if task=='NEXT_DISTINCT_PRIMARY':return {**out,'available':True,'target':first,'label_end':firstend,'future_key':b['row_key'],'reason':None,'elapsed_slots':step}
  last=j
 if task=='NEXT_DISTINCT_PRIMARY':return {**out,'reason':'NO_TRANSITION_WITHIN30','complete_window_end':rows[last]['bar_end']}
 return {**out,'available':True,'target':'TRANSITION' if first else 'NO_TRANSITION','label_end':rows[last]['bar_end'],'first_destination':first,'first_transition_at':firstend,'reason':None}
def main():
 pre=json.loads((R/'PREDICTIVENESS_V2_PRECOMMIT.json').read_text())
 for n,h in pre['hashes'].items():assert sha(R/n)==h,'V2_PRECOMMIT_CHANGED'
 manifest=json.loads((V/'RECEIVED_DEVELOPMENT/DATASET_MANIFEST.json').read_text());pairs=[]
 for p in manifest['pairs']:pairs.append({**p,'feature_path':str(V/'RECEIVED_DEVELOPMENT/FEATURES'/f"{p['pair_id']}.jsonl"),'trace_path':str(V/'RECEIVED_DEVELOPMENT/STATE9_TRACES'/f"{p['pair_id']}.jsonl"),'exposure':'V1_EXPOSED_DEV','old_labels':str(V/'LABELS'/f"{p['pair_id']}.jsonl")})
 expansion=R/'NEW_DEVELOPMENT'
 if (expansion/'DATASET_MANIFEST.json').exists():
  for p in json.loads((expansion/'DATASET_MANIFEST.json').read_text())['pairs']:pairs.append({**p,'feature_path':str(expansion/'FEATURES'/f"{p['pair_id']}.jsonl"),'trace_path':str(expansion/'STATE9_TRACES'/f"{p['pair_id']}.jsonl"),'exposure':'V2_NEW_DEV_EVAL','old_labels':None})
 assert len(pairs)<=97
 plan=json.loads((R/'SPLIT_PLAN_V2.json').read_text());all_dates=sorted({p['date'] for p in pairs});newdates=sorted({p['date'] for p in pairs if p['exposure']=='V2_NEW_DEV_EVAL'})
 if newdates:
  blocks=[[x['date'] for x in b] for b in plan['fixed_three_blocks']];mode='V2_NEW_DEV_EVAL'
 else:
  rem=all_dates[5:];q,n=divmod(len(rem),3);cursor=0;blocks=[]
  for k in range(3):size=q+(k<n);blocks.append(rem[cursor:cursor+size]);cursor+=size
  mode='V1_EXPOSED_DIAGNOSTIC_LOCAL_FALLBACK'
 folds=[{'fold':k+1,'test_dates':b,'train_dates':[d for d in all_dates if b and d<b[0]],'test_start':b[0]+'T00:00:00+09:00' if b else None} for k,b in enumerate(blocks)]
 assert all(len(f['train_dates'])>=5 for f in folds if f['test_dates'])
 save('SPLIT_REALIZED_V2.json',{'mode':mode,'folds':folds,'input_dates':all_dates,'new_eligible_dates':newdates,'empty_test_dates':[d for b in blocks for d in b if d not in all_dates],'random_row_split':False,'purge_cross_date_label_end':True})
 counts=Counter();keys=set();alllabels=[];features=[];label_files=[]
 for p in pairs:
  path=Path(p['feature_path']);assert sha(path)==p['feature_SHA256'];rows=list(map(json.loads,path.read_text().splitlines()));look={r['tradable_index']:i for i,r in enumerate(rows) if r['tradable_index'] is not None}
  oldlabels={} if not p['old_labels'] else {x['row_key']:x for x in map(json.loads,Path(p['old_labels']).read_text().splitlines())}
  output=R/'LABELS'/f"{p['pair_id']}.jsonl";output.parent.mkdir(exist_ok=True)
  with output.open('x') as writer:
   for i,r in enumerate(rows):
    assert r['row_key'] not in keys;keys.add(r['row_key']);assert r['feature_max_timestamp']<=r['bar_end'] and r['feature_created_before_target']
    r['exposure']=p['exposure'];features.append(r);real={t:state_target(rows,i,t) for t in TASKS};shift={};ti=r['tradable_index'];si=None if ti is None else look.get(ti+60)
    guard=False
    if si is not None:
     through=rows[i:si+1];guard=all(x['causal_segment_id']==r['causal_segment_id'] and x['audit_source']['observed'] and x['audit_source']['numeric_status']=='ACCEPTED' and x['audit_source']['auction']=='CONTINUOUS' for x in through) and all(b['tradable_index']==a['tradable_index']+1 for a,b in zip(through,through[1:]))
    for t in TASKS:shift[t]=state_target(rows,si,t) if guard else {'available':False,'reason':'SHIFT_ANCHOR_OR_BRIDGE_UNAVAILABLE','target':None,'label_end':None}
    prices={str(h):oldlabels[r['row_key']]['real'][str(h)] if oldlabels else price_target(rows,i,h) for h in [5,15,30]}
    l={'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'bar_end':r['bar_end'],'exposure':r['exposure'],'REAL':real,'SHIFT60':shift,'PRICE':prices}
    for c,d in [('REAL',real),('SHIFT60',shift)]:
     for t,v in d.items():counts[(c,t,'AVAILABLE' if v['available'] else v['reason'])]+=1
    alllabels.append(l);writer.write(json.dumps(l,sort_keys=True,separators=(',',':'))+'\n')
  label_files.append({'path':str(output.relative_to(R)),'SHA256':sha(output),'bytes':output.stat().st_size})
 save('DATASET_MANIFEST.json',{'pairs':pairs,'endpoint_N':len(keys),'input_dates':all_dates,'new_eligible_dates':newdates,'reuse_endpoint_N':8050,'new_endpoint_N':len(keys)-8050,'feature_files_verified':True,'future_feature_input':0})
 save('TARGET_FIXATION_RECEIPT.json',{'label_files':label_files,'availability':[{'control':c,'task':t,'status':s,'N':n} for (c,t,s),n in sorted(counts.items())],'created_after_precommit':True,'post_result_changes':0})
 ds=sorted({d for f in folds for d in f['test_dates']});rng=np.random.default_rng(2026100203);draws=rng.integers(0,len(ds),size=(1000,len(ds)))
 save('BOOTSTRAP_GLOBAL_DATE_DRAWS.json',{'seed':2026100203,'dates':ds,'draws':draws.tolist(),'generated_vector_N':1000,'distinct_vector_value_N':len({tuple(x) for x in draws}),'no_per_horizon_generation':True})
 save('BOOTSTRAP_GLOBAL_1000_RECEIPT.json',{'bootstrap_unique_draw_vector_N':1000,'bootstrap_total_generated_draws':1000,'meaning_unique':'1000globally allocated vectorIDs, not necessarily1000distinct vectorvalues','distinct_value_N':len({tuple(x) for x in draws}),'SHA256':sha(R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json'),'independent_checker_new_draws':0})
 print(json.dumps({'endpoints':len(keys),'mode':mode,'newdates':len(newdates),'counts':dict((str(k),n) for k,n in counts.items())}))
if __name__=='__main__':main()
