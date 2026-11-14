"""Lane A independent read-only V4 forensic. No fitted helper, solve or kernel."""
from pathlib import Path
from collections import Counter,defaultdict,deque
from datetime import datetime,timezone,timedelta
import json,csv,math,hashlib,statistics
import numpy as np
R=Path(__file__).resolve().parent;P=R/'PARENT_V4';C=['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30']
CHECKS=Counter();ERRORS=[];features={};labels={};mapping={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((P/n).read_text())
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def output(n,rows):
 with (R/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['status']);w.writeheader();w.writerows(rows)
def check(ok,kind,detail=''):
 CHECKS[kind]+=1
 if not ok:ERRORS.append({'kind':kind,'detail':str(detail)})
def near(x,y):return x is None and y is None if x is None or y is None else math.isclose(float(x),float(y),abs_tol=1e-8,rel_tol=1e-8)
def weights(rows):
 groups=Counter((r['date'],r['security_id'],r['session_id']) for r in rows);d=Counter(t[0] for t in groups)
 w=np.array([1/(len(d)*d[r['date']]*groups[(r['date'],r['security_id'],r['session_id'])]) for r in rows]);return w/w.mean()
def transform(a,rows):
 e=a['encoder'];x=[np.ones(len(rows))]
 for n in e['numeric']:
  m,s=e['stats'][n];v=np.array([np.nan if r['features'][n] is None else r['features'][n] for r in rows]);bad=~np.isfinite(v)
  x.extend([np.where(bad,0,(v-m)/s),bad.astype(float)])
 for n in e['categorical']:
  for v in e['vocab'][n]:x.append(np.array([r['features'][n]==v for r in rows],float))
 return np.column_stack(x)
def temperature(p,t):
 z=np.log(p)/t;z-=z.max(axis=1,keepdims=True);x=np.exp(z);return x/x.sum(axis=1,keepdims=True)
def replay(a,tr,te,Y,detail):
 w=weights(tr);e=a['encoder']
 for n in e['numeric']:
  v=np.array([np.nan if r['features'][n] is None else r['features'][n] for r in tr]);ok=np.isfinite(v);m=float(np.average(v[ok],weights=w[ok])) if ok.any() else 0.;var=float(np.average((v[ok]-m)**2,weights=w[ok])) if ok.any() else 0.;s=math.sqrt(var) if var>0 else 1.
  check(near(m,e['stats'][n][0]) and near(s,e['stats'][n][1]),'encoder_train_only_stats',detail+':'+n)
 for n in e['categorical']:check(e['vocab'][n]==sorted({r['features'][n] for r in tr}),'encoder_train_only_vocab',detail+':'+n)
 z=transform(a,tr);coef=np.asarray(a['coefficients']);A=(z.T*w)@z/w.sum()+np.diag([0.]+[a['alpha']]*(z.shape[1]-1));B=(z.T*w)@Y/w.sum()
 check(np.max(np.abs(A@coef-B))<1e-8,'saved_normal_equation_no_refit',detail)
 raw=transform(a,te)@coef;p=np.maximum(raw,1e-12);p/=p.sum(1,keepdims=True);return p
def rowll(r):return -math.log(max(r['probabilities'][C.index(r['actual'])],1e-300))
def ll(rr):
 g=defaultdict(list)
 for r in rr:g[r['date']].append(rowll(r))
 return statistics.fmean(statistics.fmean(x) for x in g.values()) if g else None
def stats(rr):
 p=np.array([r['probabilities'] for r in rr]);y=np.array([C.index(r['actual']) for r in rr]);pred=p.argmax(1);mx=p.max(1);ent=-(p*np.log(np.maximum(p,1e-300))).sum(1)
 ece=0.
 for b in range(10):
  ix=np.minimum((mx*10).astype(int),9)==b
  if ix.any():ece+=ix.mean()*abs(mx[ix].mean()-(pred[ix]==y[ix]).mean())
 down=p[:,1];de=0.
 for b in range(10):
  ix=np.minimum((down*10).astype(int),9)==b
  if ix.any():de+=ix.mean()*abs(down[ix].mean()-(y[ix]==1).mean())
 result={'N':len(rr),'date_N':len({r['date'] for r in rr}),'date_equal_LL':ll(rr),'row_LL':statistics.fmean(rowll(r) for r in rr),'entropy_mean_nats':float(ent.mean()),'max_probability_mean':float(mx.mean()),'max_probability_P95':float(np.quantile(mx,.95)),'top_label_ECE':float(ece),'DOWN_probability_ECE':float(de),'DOWN_actual_rate':float((y==1).mean())}
 for k,c in enumerate(C):
  for n,v in [('mean',p[:,k].mean()),('P01',np.quantile(p[:,k],.01)),('P95',np.quantile(p[:,k],.95)),('P99',np.quantile(p[:,k],.99)),('floor_N',sum(p[:,k]<1e-8))]:result[c+'_'+n]=float(v)
 return result
def target(k,control):return labels[mapping[k] if control=='TRUE_NULL' else k]
def main():
 manifest=read('DATASET_MANIFEST_PORTABLE_V4.json');schema=read('FEATURE_SCHEMA_V4.json');prefix_family=Counter()
 for pair in manifest['pairs']:
  fp=P/pair['feature_path'];check(sha(fp)==pair['feature_SHA256'],'feature_hash',pair['pair_id'])
  stream=list(map(json.loads,fp.open()));ep=list(map(json.loads,(P/pair['path_endpoint_path']).open()));traces=list(map(json.loads,(P/pair['trace_path']).open()));ls=list(map(json.loads,(P/pair['label_path']).open()))
  check(len(stream)==len(ep)==len(traces)==len(ls),'pair_lengths',pair['pair_id'])
  segment=None;start=None;history=[];window=deque(maxlen=15);previous=None;dwell=None;reset=None;last_ep=None;chain=[];last_row=None
  for row,end,trace,label in zip(stream,ep,traces,ls):
   t=row['scheduled_t'];f=row['features'];src=row['audit_source'];seg=row['causal_segment_id'];events=src['events'];types=[x['event_type'] for x in events]
   check(row['feature_max_timestamp']<=row['bar_end'] and row['anatomy_source_max_timestamp']<=row['bar_end'] and row['feature_created_before_target'],'prefix_timestamp',row['row_key'])
   check(trace['as_of']==t and (trace['observed_at'] is None or trace['observed_at']<=t),'state_source_asof',row['row_key'])
   for name in ['range_analysis','fast_analysis']:
    for key in ['window_ids','old_window_ids']:check(all(i<=t for i in (trace.get(name) or {}).get(key,[])),'analysis_prefix_window',name)
   for name,keys in [('stop',['start','recognized_at','progress_at']),('balance',['established_at'])]:
    for key in keys:check((trace.get(name) or {}).get(key) is None or trace[name][key]<=t,'recognition_not_future',name+key)
   check(all(e['scheduled_t']<=t and e['bar_end']<=row['bar_end'] for e in events),'event_timestamp',row['row_key'])
   if seg!=segment:segment=seg;start=t;history=[];window.clear();previous=None;dwell=None;reset=t
   if any(e in types for e in ['SEGMENT_BREAK','OBSERVATION_LOST']):reset=t
   transition=[e for e in events if e['event_type']=='TRANSITION']
   if transition:
    check(len(transition)==1,'single_current_transition',row['row_key']);history.extend(transition);previous=transition[0]['from_primary_or_null'];dwell=last_ep['dwell_observed_bars'] if last_ep else None
   window.append((int('HOLD' in types),int(bool(transition))))
   expected={'dwell_scheduled_bars':end['dwell_scheduled_bars'],'dwell_observed_bars':end['dwell_observed_bars'],'entered_age':None if end['entered_at'] is None else t-end['entered_at'],'previous_run_dwell':dwell,'bars_since_transition':None if not history else t-history[-1]['scheduled_t'],'segment_age':t-start,'segment_transition_count':len(history),'recent_hold_count_15':sum(x[0] for x in window),'recent_transition_count_15':sum(x[1] for x in window),'recent_transition_density_15':sum(x[1] for x in window)/len(window),'reset_recency':None if reset is None else t-reset,'current_run_primary':end['Primary_or_null'] or '__MISSING__','previous_primary':previous or '__MISSING__','last_transition_from':history[-1]['from_primary_or_null'] if history else '__MISSING__','last_transition_to':history[-1]['to_primary_or_null'] if history else '__MISSING__'}
   for k in range(4):expected['transition_seq_'+str(k)]=history[-1-k]['from_primary_or_null']+'>'+history[-1-k]['to_primary_or_null'] if len(history)>k else '__MISSING__'
   for k,v in expected.items():check(near(v,f[k]) if isinstance(v,(float,int)) or v is None else v==f[k],'standard_Path_prefix_'+k,row['row_key']);prefix_family[k]+=1
   observed=src['observed']
   if not (observed and last_row and last_row['audit_source']['observed'] and last_row['causal_segment_id']==seg and last_row['scheduled_t']+1==t):chain=[]
   if observed:chain.append(row)
   for kind in ['range','stop','fast']:
    match=[x['scheduled_t'] for x in chain if (x['audit_source']['formal_primary']=='RANGE' if kind=='range' else x['audit_source']['formal_primary'] in ['RISE_STOP','DROP_STOP'] if kind=='stop' else x['features']['fast']==1)]
    check(near(f['anatomy_'+kind+'_recency'],t-max(match) if match else None),'fixed_anatomy_'+kind+'_prefix',row['row_key'])
   last_ep=end;last_row=row
   if label['REAL']['CONTEXT_REVERSAL']['available']:
    features[row['row_key']]=row;labels[row['row_key']]=label['REAL']['CONTEXT_REVERSAL']
 with (P/'PERMUTATION_MAPPING_V4.csv').open() as fi:
  for row in csv.DictReader(fi):
   if row['task']=='CONTEXT_REVERSAL':mapping[row['feature_key']]=row['donor_key']
 by=defaultdict(list)
 for k,r in sorted(features.items()):by[(r['date'],r['security_id'],r['session_id'])].append(k)
 for group,keys in sorted(by.items()):
  seed=int(hashlib.sha256(('2026100402|CONTEXT_REVERSAL|'+'|'.join(group)).encode()).hexdigest()[:16],16);perm=np.random.default_rng(seed).permutation(len(keys))
  check([mapping[k] for k in keys]==[keys[int(i)] for i in perm],'whole_label_deterministic_permutation',str(group))
  check(set(mapping[k] for k in keys)==set(keys),'whole_label_group_bijection',str(group))
 with (P/'CONTEXT_REVERSAL_OOF_PREDICTIONS.csv').open() as fi:
  allrows=[]
  for r in csv.DictReader(fi):
   r['probabilities']=json.loads(r['probabilities']);r['calibrated']=r['calibrated']=='True';r['fold']=int(r['fold']);allrows.append(r)
 groups=defaultdict(list)
 for r in allrows:groups[(r['model'],r['control'],r['calibrated'])].append(r)
 comparisons=[];selection=[];distribution=[];decomp=[];cf=[];instability=[]
 for model in ['R2','R3','R4']:
  for cal in [False,True]:
   rr=groups[(model,'REAL',cal)];nn=groups[(model,'TRUE_NULL',cal)];keys={r['row_key'] for r in rr};check(keys=={r['row_key'] for r in nn},'matched_control_keys',model)
   comparisons.append({'model':model,'calibrated':cal,'matched_N':len(keys),'dates':len({r['date'] for r in rr}),'REAL_date_equal_LL':ll(rr),'TRUE_NULL_date_equal_LL':ll(nn),'REAL_minus_TRUE_NULL_LL':ll(rr)-ll(nn),'REAL_better':ll(rr)<ll(nn)})
 for model in ['R2','R3','R4']:
  for fold in [2,3]:
   for control in ['REAL','TRUE_NULL']:
    name=f'FITTED/CONTEXT_REVERSAL_{control}_{model}_F{fold}.json';a=read(name);tr=[features[k] for k in a['train_keys']];te=[features[k] for k in a['test_keys']];Y=np.eye(4)[[C.index(target(k,control)['target']) for k in a['train_keys']]]
    suffix='path' if model=='R3' else 'anatomy' if model=='R4' else None
    check(a['encoder']['numeric']==schema['numeric_state']+(schema['numeric_'+suffix] if suffix else []),'feature_allowlist_no_target',name)
    check(a['encoder']['categorical']==schema['categorical_state']+(schema['categorical_'+suffix] if suffix else []),'category_allowlist_no_target',name)
    start=min(a['test_dates'])+'T00:00:00+09:00'
    check(all(r['date']<min(a['test_dates']) and target(r['row_key'],control)['label_end']<start for r in tr),'fold_partition_and_donor_purge',name)
    check(not(set(a['train_keys'])&set(a['test_keys'])),'no_outer_label_selection',name)
    p=replay(a,tr,te,Y,name);yv=np.array([C.index(target(k,control)['target']) for k in a['test_keys']]);last=max(r['date'] for r in tr)
    innerloss=[]
    for inner in a['inner_artifacts']:
     itr=[features[k] for k in inner['train_keys']];ival=[features[k] for k in inner['validation_keys']];IY=np.eye(4)[[C.index(target(k,control)['target']) for k in inner['train_keys']]]
     check(all(r['date']<last for r in itr) and all(r['date']==last for r in ival),'inner_chronological_train_only',name)
     ip=replay(inner,itr,ival,IY,name+':inner');iy=np.array([C.index(target(k,control)['target']) for k in inner['validation_keys']]);check(np.allclose(ip,inner['validation_probabilities'],atol=1e-8),'inner_prediction_replay',name)
     loss=float(np.average(-np.log(ip[np.arange(len(ip)),iy]),weights=weights(ival)));innerloss.append(loss)
    pick=min(range(len(innerloss)),key=lambda k:(innerloss[k],-a['validation_grid'][k]['alpha']))
    check(a['alpha']==a['validation_grid'][pick]['alpha'],'alpha_choice_replay',name)
    ig=a['inner_artifacts'][pick];ip=np.asarray(ig['validation_probabilities']);iy=np.asarray(ig['validation_actual']);ival=[features[k] for k in ig['validation_keys']]
    tg=[(float(np.average(-np.log(temperature(ip,t)[np.arange(len(ip)),iy]),weights=weights(ival))),abs(t-1),-t,t) for t in [.5,.75,1,1.25,1.5,2]]
    check(a['temperature']==min(tg)[3],'temperature_choice_replay',name)
    selection.append({'model':model,'fold':fold,'control':control,'alpha':a['alpha'],'temperature':a['temperature'],'validation_date':last,'validation_N':len(ival),'validation_usable_dates':1,'validation_classes':json.dumps(dict(Counter(C[i] for i in iy)))})
    for cal,q in [(False,p),(True,temperature(p,a['temperature']))]:
     saved={r['row_key']:r for r in groups[(model,control,cal)] if r['fold']==fold}
     for i,k in enumerate(a['test_keys']):
      s=saved[k];t=target(k,control);check(s['actual']==t['target'] and s['label_start']==t.get('label_start') and s['label_end']==t['label_end'],'whole_label_provenance_preserved',k);check(np.allclose(s['probabilities'],q[i],atol=1e-8) and s['predicted']==C[int(q[i].argmax())],'outer_saved_prediction_replay',k)
     if model=='R3':distribution.append({'model':model,'fold':fold,'control':control,'calibrated':cal,'alpha':a['alpha'],'temperature':a['temperature'],**stats(list(saved.values()))})
    if model=='R3':
     other=read(f'FITTED/CONTEXT_REVERSAL_{"TRUE_NULL" if control=="REAL" else "REAL"}_R3_F{fold}.json')
     for label,t in [('own_T',a['temperature']),('other_control_T',other['temperature']),('T1',1)]:
      q=temperature(p,t);rows=[{**saved[k],'probabilities':q[i].tolist()} for i,k in enumerate(a['test_keys'])]
      cf.append({'fold':fold,'control':control,'alpha_fixed':a['alpha'],'transform':label,'T':t,'date_equal_LL':ll(rows),'fit_operations':0})
     for n in schema['numeric_path']+schema['categorical_path']:
      if n in schema['numeric_path']:
       m,sd=a['encoder']['stats'][n];tv=[float(r['features'][n]) for r in te if r['features'][n] is not None];z=[abs((v-m)/sd) for v in tv]
       record={'kind':'numeric','train_mean':m,'train_sd':sd,'test_mean':statistics.fmean(tv) if tv else None,'test_nonmissing_N':len(tv),'test_above_train_3SD_share':sum(x>3 for x in z)/len(z) if z else None,'test_unseen_category_share':None}
      else:record={'kind':'categorical','train_mean':None,'train_sd':None,'test_mean':None,'test_nonmissing_N':len(te),'test_above_train_3SD_share':None,'test_unseen_category_share':sum(r['features'][n] not in a['encoder']['vocab'][n] for r in te)/len(te)}
      instability.append({'fold':fold,'control':control,'feature':n,**record})
 for cal in [False,True]:
  rr=groups[('R3','REAL',cal)];nn=groups[('R3','TRUE_NULL',cal)]
  for kind,column in [('fold','fold'),('date','date'),('security','security_id')]:
   for value in sorted({r[column] for r in rr},key=str):
    a=[r for r in rr if r[column]==value];b=[r for r in nn if r[column]==value];weight=len({r['date'] for r in a})/len({r['date'] for r in rr})
    decomp.append({'calibrated':cal,'group_type':kind,'group':value,'N':len(a),'date_N':len({r['date'] for r in a}),'REAL_date_equal_LL':ll(a),'TRUE_NULL_date_equal_LL':ll(b),'REAL_minus_TRUE_NULL_LL':ll(a)-ll(b),'additive_global_LL_contribution':weight*(ll(a)-ll(b)) if kind in ['fold','date'] else None,'CI_informative':len({r['date'] for r in a})>1})
 output('V4_R3_REAL_TRUE_NULL_DECOMPOSITION.csv',comparisons);output('V4_R3_CALIBRATION_DECOMPOSITION.csv',distribution);output('V4_R3_FOLD_DATE_SECURITY_CONTROL.csv',decomp);output('V4_ALPHA_T_SELECTION_REPLAY_V5.csv',selection);output('V4_R3_TEMPERATURE_COUNTERFACTUAL_V5.csv',cf);output('V4_R3_PATH_DISTRIBUTION_V5.csv',instability)
 raw=next(x for x in comparisons if x['model']=='R3' and not x['calibrated']);cal=next(x for x in comparisons if x['model']=='R3' and x['calibrated'])
 classification='F6_UNRESOLVED' if ERRORS else 'F3_CALIBRATION_INSTABILITY' if raw['REAL_better'] and not cal['REAL_better'] else 'F5_STATISTICAL_CONTROL_FAILURE_WITHOUT_DIRECT_LEAKAGE'
 audit={'status':'PASS' if not ERRORS else 'FAIL','direct_future_leakage_found':False if not ERRORS else None,'mismatch_N':len(ERRORS),'assertions':dict(CHECKS),'errors':ERRORS[:100],'scope':'saved feature/Path prefix, encoder, final and inner coefficients, label donor provenance, split and timestamps; no full State/Path semantic kernel rerun','new_fits':0,'new_labels':0,'new_bootstrap_draws':0,'kernel_reruns':0,'candidate_helper_imports':0,'saved_prefix_rows':sum(p['scheduled_endpoints_N'] for p in manifest['pairs'])}
 save('V4_R3_FEATURE_TIMESTAMP_AUDIT.json',audit)
 receipt={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'classification':classification,'secondary_observation':'R3 Path score distribution instability may amplify calibration sensitivity; no causal alpha attribution without forbidden refits','new_fits':0,'new_labels':0,'new_bootstrap_draws':0,'kernel_reruns':0,'V4_status_unchanged':'BLOCKED_V4_INTEGRITY','audit_status':audit['status'],'mismatch_N':len(ERRORS),'comparisons':comparisons,'selection':selection,'counterfactual_saved_scores_only':cf,'R3_candidate_scope':'diagnostic-only, excluded from V5 promotion','R4_candidate_scope':'descriptive challenger, excluded from V5 promotion','parent_OOF_SHA256':sha(P/'OOF_ALL.jsonl')}
 save('V4_CONTROL_FORENSICS_RECEIPT.json',receipt)
 print(json.dumps({'classification':classification,'mismatch_N':len(ERRORS),'errors':ERRORS[:10],'comparisons':comparisons,'R3_selection':[s for s in selection if s['model']=='R3'],'counterfactual':cf},ensure_ascii=False),flush=True)
 if ERRORS:raise RuntimeError('FORENSIC_UNRECONCILED_MISMATCH')
if __name__=='__main__':main()
