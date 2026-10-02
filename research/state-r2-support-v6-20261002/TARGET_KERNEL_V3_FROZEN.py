from pathlib import Path
from collections import Counter
from datetime import datetime, timezone, timedelta
import json,hashlib,csv,numpy as np,sys
R=Path(__file__).resolve().parent
TASKS=['CONTEXT_REVERSAL','MOTION_REVERSAL','NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']
UP={'RISE','SHARP_RISE','PULLBACK','RISE_STOP'};DOWN={'DROP','SHARP_DROP','REBOUND','DROP_STOP'}
UM={'RISE','SHARP_RISE','REBOUND'};DM={'DROP','SHARP_DROP','PULLBACK'};ST={'RISE_STOP','DROP_STOP'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def save(n,v):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def csvout(n,rows,columns=None):
 with (R/n).open('w') as f:
  w=csv.DictWriter(f,fieldnames=columns or list(rows[0]) if rows else columns or ['status']);w.writeheader();w.writerows(rows)
def precheck():
 for n,h in json.loads((R/'PREDICTIVENESS_V3_REVERSAL_PRECOMMIT.json').read_text())['hashes'].items():assert sha(R/n)==h,'V3_PRECOMMIT_CHANGED'
def admitted(r):
 s=r['audit_source'];return s['observed'] and s['formal_primary'] is not None and s['numeric_status']=='ACCEPTED' and s['auction']=='CONTINUOUS' and r['tradable_index'] is not None
def target(rows,i,task,look):
 a=rows[i];out={'available':False,'target':None,'reason':None,'label_start':a['bar_end'],'label_end':None,'donor_anchor_key':a['row_key']}
 if not admitted(a):return {**out,'reason':'CURRENT_NOT_OBSERVED_CONTINUOUS'}
 primary=a['audit_source']['formal_primary']
 if task=='CONTEXT_REVERSAL' and primary not in UP:return {**out,'reason':'ANCHOR_NOT_UP_CONTEXT'}
 if task=='MOTION_REVERSAL' and primary not in UM:return {**out,'reason':'ANCHOR_NOT_UP_MOVE'}
 last=i;provisional=False
 for step in range(1,2 if task=='NEXT_OBSERVED_PRIMARY' else 31):
  j=look.get(a['tradable_index']+step)
  if j is None:return {**out,'reason':'WINDOW_OUTSIDE_SESSION'}
  b=rows[j]
  if j!=last+1 or b['scheduled_t']!=rows[last]['scheduled_t']+1:return {**out,'reason':'SCHEDULE_DISCONTINUITY'}
  if b['causal_segment_id']!=a['causal_segment_id']:return {**out,'reason':'SEGMENT_BREAK'}
  if not admitted(b):return {**out,'reason':'NULL_GAP_OR_AUCTION'}
  bp=b['audit_source']['formal_primary'];prev=rows[last]['audit_source']['formal_primary']
  trs=[e for e in b['audit_source']['events'] if e['event_type']=='TRANSITION'];changed=bp!=prev
  assert len(trs)==int(changed),'FROZEN_EVENT_ENDPOINT_MISMATCH'
  if changed:assert (trs[0]['from_primary_or_null'],trs[0]['to_primary_or_null'])==(prev,bp),'FROZEN_TRANSITION_MISMATCH'
  label=None
  if task=='NEXT_OBSERVED_PRIMARY':label=bp
  elif task=='NEXT_DISTINCT_PRIMARY' and changed:label=bp
  elif task=='MOTION_REVERSAL' and changed:label='UP_MOVE_CONTINUE' if bp in UM else 'DOWN_MOVE_REVERSAL' if bp in DM else 'NON_DIRECTIONAL'
  elif task=='CONTEXT_REVERSAL':
   if changed and bp in DOWN and b['features']['context_direction']==-1:label='DOWN_REVERSAL'
   elif changed and bp in {'RISE','SHARP_RISE'} and b['features']['context_direction']==1 and b['features']['local_direction']==1:label='UP_CONTINUE'
   if bp=='RANGE' or bp in ST:provisional=True
  if label is not None:
   return {**out,'available':True,'target':label,'label_end':b['bar_end'],'future_key':b['row_key'],'elapsed_slots':step,'context_direction':b['features']['context_direction'],'local_direction':b['features']['local_direction'],'reason':None}
  last=j
 if task=='NEXT_DISTINCT_PRIMARY':return {**out,'reason':'NO_TRANSITION_WITHIN30','complete_window_end':rows[last]['bar_end']}
 label=('RANGE_OR_STOP' if provisional else 'NO_DECISION_WITHIN30') if task=='CONTEXT_REVERSAL' else 'NO_DECISION'
 return {**out,'available':True,'target':label,'label_end':rows[last]['bar_end'],'future_key':rows[last]['row_key'],'elapsed_slots':30,'reason':None}
def anatomy(rows):
 hist=[];run=None;previous=None;recent=[];lastseen={'range':None,'stop':None,'fast':None};outputs=[]
 for r in rows:
  p=r['audit_source']['formal_primary'];obs=r['audit_source']['observed'];t=r['scheduled_t']
  connected=previous is not None and previous['audit_source']['observed'] and obs and previous['causal_segment_id']==r['causal_segment_id'] and previous['scheduled_t']+1==t
  if not connected:hist=[];run=None;recent=[];lastseen={'range':None,'stop':None,'fast':None}
  changed=connected and previous['audit_source']['formal_primary']!=p
  contextflip=connected and previous['features']['context_direction']!=r['features']['context_direction']
  if obs:
   if run is None or changed:
    if run is not None:hist.append(dict(run));hist=hist[-4:]
    run={'primary':p,'entered':t,'dwell':1,'stop_seen':False,'range_seen':False,'fast_seen':False,'context_flips':0}
   else:run['dwell']+=1
   run['stop_seen']|=p in ST;run['range_seen']|=p=='RANGE';run['fast_seen']|=r['features']['fast']==1;run['context_flips']+=int(contextflip)
   recent.append({'t':t,'transition':int(changed),'hold':int(connected and not changed),'flip':int(contextflip)});recent=recent[-15:]
   for k,flag in [('range',p=='RANGE'),('stop',p in ST),('fast',r['features']['fast']==1)]:
    if flag:lastseen[k]=t
  f={}
  for k in range(1,5):
   f['anatomy_previous_primary_'+str(k)]=hist[-k]['primary'] if len(hist)>=k else 'NULL'
   f['anatomy_previous_dwell_'+str(k)]=hist[-k]['dwell'] if len(hist)>=k else None
  f.update(anatomy_current_dwell=run['dwell'] if run else None,anatomy_bars_since_transition=t-run['entered'] if run and hist else None,
   anatomy_transition_count_15=sum(x['transition'] for x in recent),anatomy_hold_count_15=sum(x['hold'] for x in recent),
   anatomy_context_flips_15=sum(x['flip'] for x in recent),anatomy_segment_age=r['features']['segment_age'])
  for k in ['range','stop','fast']:f['anatomy_'+k+'_recency']=None if lastseen[k] is None else t-lastseen[k]
  history=hist+([dict(run)] if run else [])
  outputs.append({**r,'features':{**r['features'],**f},'anatomy_history':history,'anatomy_source_max_timestamp':r['bar_end'],'anatomy_derived_before_labels':True})
  previous=r
 return outputs
def prepare():
 precheck();v2=R.parent/'state_predictiveness_v2_nextstate_20261002_v1';pairs=[]
 for p in json.loads((v2/'DATASET_MANIFEST.json').read_text())['pairs']:
  pairs.append({**p,'exposure':'V1_V2_EXPOSED_DEV','original_exposure':p['exposure']})
 exp=R/'NEW_DEVELOPMENT'
 if (exp/'DATASET_MANIFEST.json').exists():
  for p in json.loads((exp/'DATASET_MANIFEST.json').read_text())['pairs']:
   pairs.append({**p,'feature_path':str(exp/'FEATURES'/f"{p['pair_id']}.jsonl"),'trace_path':str(exp/'STATE9_TRACES'/f"{p['pair_id']}.jsonl"),'exposure':'V3_NEW_DEV_EVAL','original_exposure':'V3_NEW_DEV_EVAL'})
 assert len(pairs)<=93,'PAIR_CAP'
 alldates=sorted({p['date'] for p in pairs});newdates=sorted({p['date'] for p in pairs if p['exposure']=='V3_NEW_DEV_EVAL'})
 plan=json.loads((R/'SPLIT_PLAN_V3.json').read_text())
 if newdates:blocks=plan['fixed_three_blocks'];mode='V3_NEW_DEV_EVAL'
 else:
  rem=alldates[5:];q,n=divmod(len(rem),3);c=0;blocks=[]
  for k in range(3):m=q+(k<n);blocks.append(rem[c:c+m]);c+=m
  mode='V1_V2_EXPOSED_DIAGNOSTIC_FALLBACK'
 folds=[{'fold':k+1,'test_dates':b,'train_dates':[d for d in alldates if b and d<b[0]],'test_start':b[0]+'T00:00:00+09:00' if b else None} for k,b in enumerate(blocks)]
 assert all(len(f['train_dates'])>=5 for f in folds if f['test_dates']),'INITIAL_TRAIN_SUPPORT'
 save('SPLIT_REALIZED_V3.json',{'mode':mode,'folds':folds,'input_dates':alldates,'new_eligible_dates':newdates,'empty_test_dates':[d for b in blocks for d in b if d not in alldates],'random_row_split':False})
 keys=set();counts=Counter()
 for p in pairs:
  original=Path(p['feature_path']);trace=Path(p['trace_path']);assert sha(original)==p['feature_SHA256'] and sha(trace)==p['state_trace_SHA256'],'FROZEN_SAVED_TRACE_CHANGED'
  rows=anatomy(list(map(json.loads,original.read_text().splitlines())));output=R/'FEATURES'/f"{p['pair_id']}.jsonl";output.parent.mkdir(exist_ok=True)
  with output.open('x') as f:
   for r in rows:
    assert r['row_key'] not in keys,'KEY_DUPLICATE';keys.add(r['row_key']);assert r['feature_max_timestamp']<=r['bar_end'] and r['anatomy_source_max_timestamp']<=r['bar_end'],'FEATURE_FUTURE'
    r['exposure']=p['exposure'];f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n');counts['observed' if r['audit_source']['observed'] else 'null']+=1
  p['original_feature_path']=p['feature_path'];p['original_feature_SHA256']=p['feature_SHA256'];p['feature_path']=str(output);p['feature_SHA256']=sha(output)
 save('DATASET_MANIFEST.json',{'JST':now(),'pairs':pairs,'endpoint_N':len(keys),'observed_N':counts['observed'],'null_N':counts['null'],'input_dates':alldates,'new_eligible_dates':newdates,'old_saved_endpoint_reuse':19495,'new_frozen_endpoint_N':len(keys)-19495,'feature_anatomy_before_labels':True,'future_classifier_input':0})
 save('C3_DATASET_FIXATION_RECEIPT.json',{'JST':now(),'dataset_SHA256':sha(R/'DATASET_MANIFEST.json'),'split_SHA256':sha(R/'SPLIT_REALIZED_V3.json'),'label_N':0})
 print(json.dumps({'phase':'features','pairs':len(pairs),'endpoints':len(keys),'observed':counts['observed'],'new_dates':len(newdates)}))
def labels():
 precheck();manifest=json.loads((R/'DATASET_MANIFEST.json').read_text());counts=Counter();files=[]
 for p in manifest['pairs']:
  rows=list(map(json.loads,Path(p['feature_path']).read_text().splitlines()));look={r['tradable_index']:i for i,r in enumerate(rows) if r['tradable_index'] is not None};out=R/'LABELS'/f"{p['pair_id']}.jsonl";out.parent.mkdir(exist_ok=True)
  with out.open('x') as f:
   for i,r in enumerate(rows):
    real={t:target(rows,i,t,look) for t in TASKS};si=look.get(r['tradable_index']+60) if r['tradable_index'] is not None else None;guard=False
    if si is not None:
     chain=rows[i:si+1];guard=all(admitted(x) and x['causal_segment_id']==r['causal_segment_id'] for x in chain) and all(b['tradable_index']==a['tradable_index']+1 and b['scheduled_t']==a['scheduled_t']+1 for a,b in zip(chain,chain[1:]))
    shift={t:target(rows,si,t,look) if guard else {'available':False,'target':None,'label_end':None,'reason':'SHIFT_ANCHOR_OR_BRIDGE_UNAVAILABLE'} for t in TASKS}
    l={'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'bar_end':r['bar_end'],'exposure':p['exposure'],'REAL':real,'SHIFT60':shift}
    for control,data in [('REAL',real),('SHIFT60',shift)]:
     for task,v in data.items():counts[(p['exposure'],control,task,v['target'] if v['available'] else v['reason'])]+=1
    f.write(json.dumps(l,sort_keys=True,separators=(',',':'))+'\n')
  files.append({'path':str(out.relative_to(R)),'SHA256':sha(out),'bytes':out.stat().st_size})
 save('C4_LABEL_FIXATION_RECEIPT.json',{'JST':now(),'files':files,'availability':[{'exposure':e,'control':c,'task':t,'reason_or_class':s,'N':n} for (e,c,t,s),n in sorted(counts.items())],'post_precommit_changes':0})
 ds=sorted({d for f in json.loads((R/'SPLIT_REALIZED_V3.json').read_text())['folds'] for d in f['test_dates']})
 assert not (R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').exists(),'NO_DUPLICATE_BOOTSTRAP_GENERATION'
 draws=np.random.default_rng(2026100303).integers(0,len(ds),size=(1000,len(ds)))
 save('BOOTSTRAP_GLOBAL_DATE_DRAWS.json',{'seed':2026100303,'dates':ds,'draws':draws.tolist(),'generated_vector_N':1000,'distinct_value_N':len({tuple(x) for x in draws}),'generation_invocation_N':1})
 save('BOOTSTRAP_GLOBAL_1000_RECEIPT.json',{'bootstrap_unique_draw_vector_N':1000,'bootstrap_total_generated_draws':1000,'distinct_value_N':len({tuple(x) for x in draws}),'independent_checker_new_draws':0,'SHA256':sha(R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json')})
 print(json.dumps({'phase':'labels','availability':[{'exposure':e,'control':c,'task':t,'status':s,'N':n} for (e,c,t,s),n in sorted(counts.items()) if c=='REAL' and e=='V3_NEW_DEV_EVAL']}))
if __name__=='__main__':
 {'features':prepare,'labels':labels}[sys.argv[1]]()
