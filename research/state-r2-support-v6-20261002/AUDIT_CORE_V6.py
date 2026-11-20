"""Read-only independent checker. No MODEL/target/metric candidate imports.

Saved coefficients satisfy independently checked normal equations; never solve.
Bootstrap interval replay consumes stored vectors, never regenerates vectors.
"""
from pathlib import Path
from collections import Counter,defaultdict
from fractions import Fraction
import json,csv,hashlib,math
import numpy as np
import FORENSICS_V5 as a
import AUDIT_RESEARCH_V5 as research_audit
R=Path(__file__).resolve().parent;P=R/'PARENT_V4';C=['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30']
def read(n):return json.loads((R/n).read_text())
def rows(n):return list(csv.DictReader((R/n).open()))
def scalar(s):return None if s in [None,'','None'] else float(s)
def admitted(r):
 x=r['audit_source'];return x['observed'] and x['raw_present'] and x['formal_primary'] is not None and x['numeric_status']=='ACCEPTED' and x['auction']=='CONTINUOUS' and r['tradable_index'] is not None
def label_oracle(stream,i,index):
 anchor=stream[i];src=anchor['audit_source']
 if not admitted(anchor):return False,None,None,'CURRENT_NOT_OBSERVED_CONTINUOUS'
 if src['formal_primary'] not in {'RISE','SHARP_RISE','PULLBACK','RISE_STOP'}:return False,None,None,'ANCHOR_NOT_UP_CONTEXT'
 previous=i;stopped=False
 for offset in range(1,31):
  j=index.get(anchor['tradable_index']+offset)
  if j is None:return False,None,None,'WINDOW_OUTSIDE_SESSION'
  r=stream[j]
  if j!=previous+1 or r['scheduled_t']!=stream[previous]['scheduled_t']+1:return False,None,None,'SCHEDULE_DISCONTINUITY'
  if r['causal_segment_id']!=anchor['causal_segment_id']:return False,None,None,'SEGMENT_BREAK'
  if not admitted(r):return False,None,None,'NULL_GAP_OR_AUCTION'
  p=r['audit_source']['formal_primary'];before=stream[previous]['audit_source']['formal_primary'];changed=p!=before;events=[e for e in r['audit_source']['events'] if e['event_type']=='TRANSITION'];a.check(len(events)==int(changed),'fresh_transition_count',r['row_key'])
  if changed:a.check((events[0]['from_primary_or_null'],events[0]['to_primary_or_null'])==(before,p),'fresh_transition_order',r['row_key'])
  f=r['features']
  if changed and p in {'DROP','SHARP_DROP','REBOUND','DROP_STOP'} and f['context_direction']==-1:return True,'DOWN_REVERSAL',r['bar_end'],None
  if changed and p in {'RISE','SHARP_RISE'} and f['context_direction']==1 and f['local_direction']==1:return True,'UP_CONTINUE',r['bar_end'],None
  stopped=stopped or p in {'RANGE','RISE_STOP','DROP_STOP'};previous=j
 return True,'RANGE_OR_STOP' if stopped else 'NO_DECISION_WITHIN30',stream[previous]['bar_end'],None
def measure(rr,w=None):
 if not rr:return {'N':0,'dates':0,'securities':0,'dangerous_numerator':0,'dangerous_denominator':0,'dangerous_rate':None}
 weight=np.ones(len(rr)) if w is None else np.asarray(w,float);total=weight.sum()
 if total==0:return None
 probs=np.asarray([r['probabilities'] for r in rr]);actual=np.array([C.index(r['actual']) for r in rr]);hard=probs.argmax(1);cm=np.array([[sum(weight[(actual==i)&(hard==j)]) for j in range(4)] for i in range(4)]);sup=cm.sum(1);pred=cm.sum(0);prec=np.array([cm[i,i]/pred[i] if pred[i] else 0 for i in range(4)]);rec=np.array([cm[i,i]/sup[i] if sup[i] else 0 for i in range(4)]);f1=np.array([2*x*y/(x+y) if x+y else 0 for x,y in zip(prec,rec)]);ll=np.array([-math.log(float(probs[i,k])) for i,k in enumerate(actual)]);brier=np.array([sum((p[k]-(y==k))**2 for k in range(4)) for p,y in zip(probs,actual)]);ix=defaultdict(list)
 for i,r in enumerate(rr):ix[r['date']].append(i)
 datew={d:float(weight[ii].mean()) for d,ii in ix.items()};dn=sum(datew.values());ece=0
 for b in range(10):
  mask=np.array([min(int(max(p)*10),9)==b for p in probs]);z=weight[mask].sum()
  if z:ece+=z/total*abs(np.average(probs.max(1)[mask],weights=weight[mask])-np.average((hard==actual)[mask],weights=weight[mask]))
 out={'N':int(total),'dates':sum(x>0 for x in datew.values()),'securities':len({r['security_id'] for i,r in enumerate(rr) if weight[i]>0}),'accuracy':float(np.trace(cm)/total),'balanced_accuracy':float(np.mean(rec[sup>0])),'macro_F1':float(f1.mean()),'row_LL':float(np.average(ll,weights=weight)),'date_equal_LL':sum(datew[d]*ll[ii].mean() for d,ii in ix.items())/dn,'Brier':float(np.average(brier,weights=weight)),'date_equal_Brier':sum(datew[d]*brier[ii].mean() for d,ii in ix.items())/dn,'ECE':float(ece),'dangerous_numerator':int(cm[1,0]),'dangerous_denominator':int(pred[0]),'dangerous_rate':float(cm[1,0]/pred[0]) if pred[0] else None}
 for i,c in enumerate(C):out.update({c+'_support':int(sup[i]),c+'_Precision':float(prec[i]),c+'_Recall':float(rec[i]),c+'_F1':float(f1[i])})
 return out
def quantile(v,informative):
 z=sorted(float(x) for x in v if x is not None and math.isfinite(float(x)))
 def one(q):
  t=(len(z)-1)*q;i=math.floor(t);j=math.ceil(t);return z[i]*(j-t)+z[j]*(t-i) if i!=j else z[i]
 return (one(.025),one(.975),len(z)) if informative and z else (None,None,len(z))
def choose(grid,key,ordering):
 best=min(x[key] for x in grid);return min((r for r in grid if r[key]<=best+1e-12),key=ordering)
def main():
 pre=read('PREDICTIVENESS_V6_PRECOMMIT.json');scope=read('FRESH_SCOPE_V6.json');manifest=read('FRESH_DATA_MANIFEST_V6.json');schema=json.loads((P/'FEATURE_SCHEMA_V4.json').read_text());features={};labels={};fresh=set();ordinals=[];split=read('SPLIT_REALIZED_V6.json')
 for n,h in pre['hashes'].items():a.check(a.sha(R/n)==h,'precommit_hash',n)
 for n,h in read('EVALUATION_CODE_FREEZE_V6.json')['hashes'].items():a.check(a.sha(R/n)==h,'evaluation_code_hash',n)
 V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1'
 for e in read('V5_INHERITANCE_RECEIPT_V6.json')['hash_checks']:a.check(a.sha(V/e['path'])==e['SHA256'],'original_V5_hash_unchanged',e['path'])
 oldpairs=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text())['pairs']+[{**p,'_V5':True} for p in json.loads((V/'FRESH_DATA_MANIFEST_V5.json').read_text())['pairs']]
 for p in oldpairs:
  root=V if p.get('_V5') else P
  ls={l['row_key']:l['REAL']['CONTEXT_REVERSAL'] for l in map(json.loads,(root/p['label_path']).open())}
  for r in map(json.loads,(root/p['feature_path']).open()):
   if ls[r['row_key']]['available']:features[r['row_key']]=r;labels[r['row_key']]=ls[r['row_key']]
 for pair in manifest['pairs']:
  stream=list(map(json.loads,(R/pair['feature_path']).open()));trace=list(map(json.loads,(R/pair['trace_path']).open()));endpoints=list(map(json.loads,(R/pair['path_endpoint_path']).open()));lab=list(map(json.loads,(R/pair['label_path']).open()));index={r['tradable_index']:i for i,r in enumerate(stream) if r['tradable_index'] is not None};a.check(a.sha(R/pair['feature_path'])==pair['feature_SHA256'] and a.sha(R/pair['trace_path'])==pair['state_trace_SHA256'],'fresh_input_hash',pair['pair_id']);a.check(len(stream)==len(trace)==len(lab)==len(endpoints),'fresh_lengths',pair['pair_id'])
  a.check(pair['fresh_pair_eligible_before_retry'] and pair['date'] in scope['fixed_calendar_dates'],'preselected_unexposed_pair',pair['pair_id'])
  for i,(r,t,l,e) in enumerate(zip(stream,trace,lab,endpoints)):
   key=r['row_key'];f=r['features'];a.check(r['feature_created_before_target'] and r['feature_max_timestamp']<=r['bar_end'] and t['as_of']==r['scheduled_t'] and (t['observed_at'] is None or t['observed_at']<=r['scheduled_t']),'fresh_prefix_timestamp',key)
   for analysis in ['range_analysis','fast_analysis']:
    for name in ['window_ids','old_window_ids']:a.check(all(x<=r['scheduled_t'] for x in (t.get(analysis) or {}).get(name,[])),'fresh_analysis_window',key)
   for obj,names in [('stop',['start','recognized_at','progress_at']),('balance',['established_at'])]:
    for name in names:a.check((t.get(obj) or {}).get(name) is None or t[obj][name]<=r['scheduled_t'],'fresh_recognition_prefix',key)
   for name,value in [('local_direction',t['leg_direction']),('context_direction',t['context']),('fast',t['fast_flag']),('formal_primary',e['Primary_or_null'] or '__FORMAL_NULL__')]:a.check(f[name]==value,'State_snapshot_field',key+':'+name)
   a.check(all(ev['scheduled_t']<=r['scheduled_t'] and ev['bar_end']<=r['bar_end'] for ev in r['audit_source']['events']),'fresh_event_time',key)
   expected=label_oracle(stream,i,index);y=l['REAL']['CONTEXT_REVERSAL'];a.check((y['available'],y['target'],y['label_end'],y['reason'])==expected and y['donor_anchor_key']==key,'independent_fresh_target_order',key)
   if y['available']:a.check(key not in features,'old_fresh_partition_disjoint',key);features[key]=r;labels[key]=y;fresh.add(key)
 donor={r['feature_key']:r['donor_key'] for r in rows('PERMUTATION_MAPPING_V6.csv')};by=defaultdict(list)
 for k,r in sorted(features.items()):by[(r['date'],r['security_id'],r['session_id'])].append(k)
 for group,keys in by.items():
  seed=int(hashlib.sha256((str(pre['null_seed_prefix'])+'|CONTEXT_REVERSAL|'+'|'.join(group)).encode()).hexdigest()[:16],16);permutation=np.random.default_rng(seed).permutation(len(keys));a.check([donor[k] for k in keys]==[keys[int(i)] for i in permutation] and set(donor[k] for k in keys)==set(keys),'independent_deterministic_whole_label_bijection',str(group))
 dates=sorted(scope['fixed_calendar_dates']);remaining=dates[5:];q,n=divmod(len(remaining),3);blocks=[];at=0
 for i in range(3):z=q+(i<n);blocks.append(remaining[at:at+z]);at+=z
 a.check([f['test_dates'] for f in split['folds']]==blocks and split['warmup_dates']==dates[:5],'outer_fixed_calendar_blocks')
 oof=list(map(json.loads,(R/'R1_R2_OOF_V6.jsonl').open()));charged=[]
 for fp in sorted((R/'FRESH_FITTED').glob('*.json')):
  art=json.loads(fp.read_text());control=fp.name.split('_R')[0];fold=int(fp.name.split('_F')[-1].split('.')[0]);outer=next(f for f in split['folds'] if f['fold']==fold);labs={k:labels[donor[k] if control=='TRUE_NULL' else k] for k in features};train=[r for k,r in sorted(features.items()) if r['date'] in outer['train_dates'] and labs[k]['label_end']<outer['test_start']];test=[r for k,r in sorted(features.items()) if k in fresh and r['date'] in outer['test_dates']];a.check([r['row_key'] for r in train]==art['train_keys'] and [r['row_key'] for r in test]==art['test_keys'],'outer_exact_purge_train_test_keys',fp.name);a.check(not(set(art['train_keys'])&set(art['test_keys'])) and all(r['date']<min(outer['test_dates']) for r in train),'outer_chronological_no_test_label_selection',fp.name)
  if art['model']=='R2':a.check(art['encoder']['numeric']==schema['numeric_state'] and art['encoder']['categorical']==schema['categorical_state'],'fixed_State_only_allowlist',fp.name)
  raw=research_audit.replay(art,train,test,labs,fp.name);charged.append(art['charged_fit_ordinal']);ds=sorted(outer['train_dates']);left=ds[5:];q,rem=divmod(len(left),4);ib=[];at=0
  for i in range(4):z=q+(i<rem);ib.append(left[at:at+z]);at+=z
  a.check([r['validation_dates'] for r in art['inner_plan']]==ib,'independent_inner_rolling_blocks',fp.name);predictions=defaultdict(list)
  for ix in art['inner_artifacts']:
   block=ib[ix['inner_fold']-1];start=block[0]+'T00:00:00+09:00';itr=[r for r in train if r['date']<block[0] and labs[r['row_key']]['label_end']<start];val=[r for r in train if r['date'] in block];a.check([r['row_key'] for r in itr]==ix['train_keys'] and [r['row_key'] for r in val]==ix['validation_keys'],'independent_inner_purge',fp.name);p=research_audit.replay(ix,itr,val,labs,fp.name+':inner');y=np.array([C.index(labs[r['row_key']]['target']) for r in val]);a.check(np.allclose(p,ix['validation_probabilities'],atol=1e-8) and y.tolist()==ix['validation_actual'],'independent_inner_prediction',fp.name);predictions[ix['alpha']].extend({'date':r['date'],'row_key':r['row_key'],'security_id':r['security_id'],'actual':C[y[j]],'probabilities':p[j].tolist(),'inner_fold':ix['inner_fold']} for j,r in enumerate(val));charged.append(ix['charged_fit_ordinal'])
  grid=[{'alpha':alpha,'loss':measure(rr)['date_equal_LL']} for alpha,rr in predictions.items()];alpha=choose(grid,'loss',lambda x:-(x['alpha'] or 0))['alpha'] if grid else (None if art['model']=='R1' else .1);a.check(alpha==art['alpha'],'independent_alpha_selection',fp.name)
  for g in grid:a.check(any(s['alpha']==g['alpha'] and a.near(s['date_equal_LL'],g['loss']) for s in art['alpha_receipt']),'independent_alpha_receipt_loss',fp.name)
  rr=predictions.get(alpha,[]);fallback=[]
  if len({r['inner_fold'] for r in rr})<2:fallback.append('INNER_EVALUABLE_FOLDS_LT2')
  if len({r['date'] for r in rr})<5:fallback.append('INNER_OOF_DATES_LT5')
  if len(rr)<20:fallback.append('INNER_OOF_ROWS_LT20')
  tg=[]
  for T in [.5,.75,1,1.25,1.5,2]:
   if rr:
    probs=a.temperature(np.asarray([r['probabilities'] for r in rr]),T);testrows=[{**r,'probabilities':probs[j].tolist()} for j,r in enumerate(rr)];tg.append({'T':T,'loss':measure(testrows)['date_equal_LL']})
  T=1 if fallback else choose(tg,'loss',lambda x:(abs(x['T']-1),-x['T']))['T'];a.check(T==art['temperature'] and fallback==art['fallback_reason'],'independent_temperature_selection',fp.name)
  for g in tg:a.check(any(s['temperature']==g['T'] and a.near(s['date_equal_LL'],g['loss']) for s in art['temperature_receipt']),'independent_temperature_receipt_loss',fp.name)
  for calibrated,p in [(False,raw),(True,a.temperature(raw,T))]:
   saved={r['row_key']:r for r in oof if r['fold']==fold and r['model']==art['model'] and r['control']==control and r['calibrated']==calibrated};a.check(set(saved)=={r['row_key'] for r in test},'OOF_complete_matched_keys',fp.name)
   for j,r in enumerate(test):
    s=saved[r['row_key']];l=labs[r['row_key']];a.check(np.allclose(p[j],s['probabilities'],atol=1e-8) and C[int(p[j].argmax())]==s['predicted'],'independent_outer_predictions',r['row_key']);a.check(all(s[k]==l[k] for k in ['label_start','label_end','donor_anchor_key','future_key']) and s['actual']==l['target'],'whole_label_provenance',r['row_key'])
 ledger=list(map(json.loads,(R/'MODEL_EXECUTION_LEDGER_V5.jsonl').open()));caps=read('BUDGET_START_V6.json')['finite_caps'];a.check(sorted(charged)==list(range(1,len(charged)+1)) and len(charged)==len(ledger) and all(l['charged_before_fit'] and l['lane']=='fresh' for l in ledger),'append_before_fit_full_accounting');a.check(len(ledger)<=caps['total_fits'] and len(ledger)<=caps['fresh_fits'],'finite_model_budget')
 runner=read('ACQUISITION/RUNNER_FINAL_RECEIPT.json');a.check(runner['protected_requests']==runner['labels_created']==runner['model_fits']==runner['bootstrap_draws']==runner['secret_values_exported']==0,'provider_boundary_and_no_labels');a.check(runner['actual_provider_HTTP']<=caps['new_provider_HTTP'] and runner['new_steps']<=caps['frozen_current_slot_steps'],'finite_provider_kernel_budget')
 receipt={'status':'PASS' if not a.ERRORS else 'FAIL','mismatch_N':len(a.ERRORS),'errors':a.ERRORS[:100],'assertion_counts':dict(a.CHECKS),'new_fits':0,'new_bootstrap_draws':0,'candidate_helper_imports':0,'new_labels_or_outcomes':0,'fresh_available_anchor_N':len(fresh),'fresh_model_fit_N':len(charged),'provider_HTTP':runner['actual_provider_HTTP'],'kernel_steps':runner['new_steps'],'direct_future_leakage_found':False if not a.ERRORS else None,'V5_result_changes':0,'independent_logic':'V5 independent target/prefix/encoder/coefficient/inner/selection/OOF logic with V6 IO-only adaptation; no candidate imports, solve0'}
 (R/'INDEPENDENT_CORE_AUDIT_V6.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['errors','assertion_counts']}))
 if a.ERRORS:raise RuntimeError('UNRECONCILED_CORE_MISMATCH')
if __name__=='__main__':main()
