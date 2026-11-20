"""Independent State/Path primitive reconstruction, target scan, model replay and counts.
No V2 candidate helper imported. No model fit/kernel/provider/new bootstrap.
V1 independent feature oracle reused, never candidate FeatureBuilder/PathBuilder.
"""
from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal,Context,localcontext,ROUND_HALF_EVEN
from fractions import Fraction
import json,csv,hashlib,math,statistics,sys,numpy as np
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_20261002_v1';sys.path.insert(0,str(V));import INDEPENDENT_AUDIT as prior_reference
checks=Counter();errors=[]
def check(ok,kind,detail=None):
 checks[kind]+=1
 if not ok:errors.append({'kind':kind,'detail':detail})
def near(a,b):
 if a is None or b is None:return a is None and b is None
 return abs(float(a)-float(b))<=max(1e-8,1e-10*max(abs(float(a)),abs(float(b))))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def number(s):return None if s in ['',None,'None'] else float(s)
def target_ref(stream,index,task):
 r=stream[index];obs=lambda a:a['audit_source']['observed'] and a['audit_source']['formal_primary'] is not None and a['audit_source']['numeric_status']=='ACCEPTED' and a['audit_source']['auction']=='CONTINUOUS'
 if not obs(r) or r['tradable_index'] is None:return False,None,None,'CURRENT_NOT_OBSERVED_CONTINUOUS'
 distinct=None;end=None;last=index;steps=1 if task=='NEXT_OBSERVED_PRIMARY' else 30
 for offset in range(1,steps+1):
  positions=[j for j,x in enumerate(stream) if x['tradable_index']==r['tradable_index']+offset]
  if not positions:return False,None,None,'WINDOW_OUTSIDE_SESSION'
  j=positions[0];x=stream[j]
  if j!=last+1:return False,None,None,'SCHEDULE_DISCONTINUITY'
  if x['causal_segment_id']!=r['causal_segment_id']:return False,None,None,'SEGMENT_BREAK'
  if not obs(x):return False,None,None,'NULL_GAP_OR_AUCTION'
  if task=='NEXT_OBSERVED_PRIMARY':return True,x['audit_source']['formal_primary'],x['bar_end'],None
  changed=x['audit_source']['formal_primary']!=stream[last]['audit_source']['formal_primary']
  if distinct is None and changed:
   distinct=x['audit_source']['formal_primary'];end=x['bar_end']
   if task=='NEXT_DISTINCT_PRIMARY':return True,distinct,end,None
  last=j
 if task=='NEXT_DISTINCT_PRIMARY':return False,None,None,'NO_TRANSITION_WITHIN30'
 return True,'TRANSITION' if distinct is not None else 'NO_TRANSITION',stream[last]['bar_end'],None
def cmref(rows,classes):
 matrix=[[0]*len(classes) for _ in classes]
 for r in rows:matrix[classes.index(r['actual'])][classes.index(r['predicted'])]+=1
 return matrix
def countsref(rows,classes):
 cm=cmref(rows,classes);p=[];rec=[];f=[]
 for i in range(len(classes)):
  true=sum(cm[i]);pred=sum(row[i] for row in cm);tp=cm[i][i];pv=tp/pred if pred else None;rv=tp/true if true else None;fv=None if pv is None or rv is None else 2*pv*rv/(pv+rv) if pv+rv else 0.;p.append(pv);rec.append(rv);f.append(fv)
 correct=sum(cm[i][i] for i in range(len(classes)));ds=defaultdict(list)
 for r in rows:ds[r['date']].append(r)
 def loss(rs):
  ll=statistics.fmean(-math.log(r['probabilities'][classes.index(r['actual'])]) for r in rs);br=statistics.fmean(math.fsum((v-int(i==classes.index(r['actual'])))**2 for i,v in enumerate(r['probabilities'])) for r in rs);return ll,br
 ll,br=loss(rows) if rows else (None,None);dl=[loss(v) for v in ds.values()]
 return {'row_N':len(rows),'date_N':len(ds),'security_N':len({r['security_id'] for r in rows}),'security_session_N':len({(r['security_id'],r['session_id']) for r in rows}),'fold_N':len({r['fold'] for r in rows}),'accuracy':correct/len(rows) if rows else None,'balanced_accuracy':statistics.fmean(x for x in rec if x is not None) if any(x is not None for x in rec) else None,'macro_precision':sum(x or 0 for x in p)/len(p),'macro_recall':sum(x or 0 for x in rec)/len(rec),'macro_F1':sum(x or 0 for x in f)/len(f),'log_loss':ll,'Brier':br,'date_equal_log_loss':statistics.fmean(x[0] for x in dl) if dl else None,'date_equal_Brier':statistics.fmean(x[1] for x in dl) if dl else None},cm,p,rec,f
def main():
 pre=json.loads((R/'PREDICTIVENESS_V2_PRECOMMIT.json').read_text());schema=json.loads((R/'FEATURE_SCHEMA_V2.json').read_text());manifest=json.loads((R/'DATASET_MANIFEST.json').read_text());ts=json.loads((R/'TARGET_SCHEMA_V2.json').read_text());features={};labels={};streams=[]
 for n,h in pre['hashes'].items():check(sha(R/n)==h,'precommit',n)
 for p in manifest['pairs']:
  path=Path(p['feature_path']);check(sha(path)==p['feature_SHA256'],'feature_hash',p['pair_id']);stream=list(map(json.loads,path.read_text().splitlines()));trace=list(map(json.loads,Path(p['trace_path']).read_text().splitlines()));prior_reference.independent_feature_check(stream,trace)
  check(len(stream)==len(trace),'trace_count',p['pair_id']);streams.append(stream)
  ls=list(map(json.loads,(R/'LABELS'/f"{p['pair_id']}.jsonl").read_text().splitlines()))
  for r,l in zip(stream,ls):
   check(r['row_key'] not in features,'key_unique',r['row_key']);features[r['row_key']]=r;labels[r['row_key']]=l
   check((r['audit_source']['formal_primary'] in ts['class_order']) if r['audit_source']['observed'] else r['audit_source']['formal_primary'] is None,'nine_states_or_formal_null',r['row_key'])
  for i,(r,l) in enumerate(zip(stream,ls)):
   for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30']:
    av,t,end,reason=target_ref(stream,i,task);saved=l['REAL'][task];check((saved['available'],saved['target'],saved['label_end'],saved['reason'])==(av,t,end,reason),'target_from_endpoint_tuples',r['row_key']+':'+task)
    si=next((j for j,x in enumerate(stream) if r['tradable_index'] is not None and x['tradable_index']==r['tradable_index']+60),None);good=False
    if si is not None:
     good=True
     for k in range(i,si+1):
      x=stream[k];s=x['audit_source']
      if x['causal_segment_id']!=r['causal_segment_id'] or not s['observed'] or s['numeric_status']!='ACCEPTED' or s['auction']!='CONTINUOUS':good=False
      if k>i and (x['tradable_index'] is None or stream[k-1]['tradable_index'] is None or x['tradable_index']!=stream[k-1]['tradable_index']+1):good=False
    actual=target_ref(stream,si,task) if good else (False,None,None,'SHIFT_ANCHOR_OR_BRIDGE_UNAVAILABLE');s=l['SHIFT60'][task];check((s['available'],s['target'],s['label_end'],s['reason'])==actual,'shift_target_causal_bridge',r['row_key']+':'+task)
   for h in [5,15,30]:
    av,reason,future=prior_reference.independent_price(stream,i,h);s=l['PRICE'][str(h)];check(s['available']==av and s['unavailable_reason']==reason,'price_eligibility',r['row_key'])
    if av:
     exact=(Fraction(future['audit_source']['Close_JPY'])-Fraction(r['audit_source']['Close_JPY']))/Fraction(r['audit_source']['U'])
     with localcontext(Context(prec=80,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999)):token=format((Decimal(future['audit_source']['Close_JPY'])-Decimal(r['audit_source']['Close_JPY']))/Decimal(r['audit_source']['U']),'f')
     check(Fraction(s['y_exact_rational'])==exact and s['y_token']==token and s['label_end']==future['bar_end'],'price_exact_tuple',r['row_key'])
 checks.update(prior_reference.counts);errors.extend(prior_reference.errors)
 split=json.loads((R/'SPLIT_REALIZED_V2.json').read_text());foldmap={d:f['fold'] for f in split['folds'] for d in f['test_dates']};check(not any(set(f['train_dates'])&set(f['test_dates']) for f in split['folds']),'train_test_disjoint')
 donors={}
 for m in csv.DictReader((R/'PERMUTATION_MAPPING_V2.csv').open()):
  a,b=features[m['feature_key']],features[m['donor_key']];check((a['date'],a['security_id'],a['session_id'])==(b['date'],b['security_id'],b['session_id']),'null_within_date_security',m['feature_key']);donors[(m['task'],m['feature_key'])]=m['donor_key']
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30']:
  grouped=defaultdict(list)
  for r in sorted(features.values(),key=lambda x:x['row_key']):
   if labels[r['row_key']]['REAL'][task]['available']:grouped[(r['date'],r['security_id'],r['session_id'])].append(r)
  for group,rs in grouped.items():
   seed=int(hashlib.sha256(('2026100202|'+task+'|'+'|'.join(group)).encode()).hexdigest()[:16],16);per=np.random.default_rng(seed).permutation(len(rs))
   check(all(donors[(task,r['row_key'])]==rs[int(per[i])]['row_key'] for i,r in enumerate(rs)),'null_exact_registered_seed_permutation')
 def target(k,task,control):
  if task.startswith('PRICE'):return labels[k]['PRICE'][task[7:]]
  if control=='TRUE_NULL':return labels[donors[(task,k)]]['REAL'][task]
  return labels[k][control][task]
 oof=list(map(json.loads,(R/'OOF_ALL.jsonl').read_text().splitlines()));price=list(csv.DictReader((R/'PRICE_SECONDARY_OOF.csv').open()));allpred=oof+price;grouped=defaultdict(list)
 for row in allpred:grouped[row['fit_path']].append(row)
 for fp,rows in grouped.items():
  art=json.loads((R/fp).read_text());tr=[features[k] for k in art['train_keys']];te=[features[k] for k in art['test_keys']];task=art['task'];control=art['control'];classes=['NO_TRANSITION','TRANSITION'] if task=='TRANSITION_WITHIN30' else ts['class_order'];isprice=task.startswith('PRICE')
  check(all(r['date']<min(x['date'] for x in te) for r in tr),'chronological_train_test',fp);check(all(target(r['row_key'],task,control)['label_end']<min(x['date'] for x in te)+'T00:00:00+09:00' for r in tr),'exact_label_donor_purge',fp)
  if isprice:Y=np.array([[float(target(r['row_key'],task,control)['y_token'])]+[int(target(r['row_key'],task,control)['direction']==c) for c in [-1,0,1]] for r in tr])
  else:Y=np.array([[int(target(r['row_key'],task,control)['target']==c) for c in classes] for r in tr],float)
  check(hashlib.sha256(Y.astype('<f8').tobytes()).hexdigest()==art['train_target_hash'],'train_matrix_exact',fp)
  sessions=Counter((r['date'],r['security_id'],r['session_id']) for r in tr);dcount=Counter(d for d,s,se in sessions);nd=len({r['date'] for r in tr});w=np.array([1/(nd*dcount[r['date']]*sessions[(r['date'],r['security_id'],r['session_id'])]) for r in tr]);w=w/w.mean()
  if art['model'] in ['B0','B1']:
   prior=[math.fsum(float(Y[j,c])*float(w[j]) for j in range(len(tr)))/math.fsum(map(float,w)) for c in range(Y.shape[1])];check(all(near(a,b) for a,b in zip(prior,art['prior'])),'prior_exact',fp);table={}
   if art['model']=='B1':
    for p in sorted({r['features']['formal_primary'] for r in tr}):
     ids=[j for j,r in enumerate(tr) if r['features']['formal_primary']==p];mass=math.fsum(float(w[j]) for j in ids);table[p]=[(math.fsum(float(w[j])*float(Y[j,c]) for j in ids)+10*prior[c])/(mass+10) for c in range(Y.shape[1])];check(all(near(a,b) for a,b in zip(table[p],art['lookup'][p])),'Markov_lookup',fp)
   raw=np.array([table.get(r['features']['formal_primary'],prior) for r in te])
  else:
   enc=art['encoder'];num=schema['numeric_state']+(schema['numeric_path'] if art['model']=='B3' else []);cat=schema['categorical_state']+(schema['categorical_path'] if art['model']=='B3' else []);check(enc['numeric']==num and enc['categorical']==cat,'train_encoder_allowlist',fp)
   for n in num:
    ids=[i for i,r in enumerate(tr) if r['features'][n] is not None];mass=math.fsum(float(w[i]) for i in ids);mean=math.fsum(float(w[i])*tr[i]['features'][n] for i in ids)/mass if mass else 0.;var=math.fsum(float(w[i])*(tr[i]['features'][n]-mean)**2 for i in ids)/mass if mass else 0.;sd=math.sqrt(var) if var>0 else 1.;check(near(mean,enc['stats'][n][0]) and near(sd,enc['stats'][n][1]),'train_only_numeric_stats',fp+':'+n)
   for n in cat:check(sorted({r['features'][n] for r in tr})==enc['vocab'][n],'train_only_vocabulary',fp+':'+n)
   def encode(rr):
    arr=[]
    for r in rr:
     a=[1.]
     for n in num:
      v=r['features'][n];mu,sd=enc['stats'][n];a.extend([0. if v is None else (v-mu)/sd,float(v is None)])
     for n in cat:a.extend(float(r['features'][n]==v) for v in enc['vocab'][n])
     arr.append(a)
    return np.asarray(arr)
   c=np.asarray(art['coefficients']);X=encode(tr);normal=(X.T*w)@X/w.sum()+np.diag([0.]+[art['alpha']]*(X.shape[1]-1));rhs=(X.T*w)@Y/w.sum();res=normal@c-rhs;check(np.max(np.abs(res))<=1e-8*max(1.,np.max(np.abs(rhs))),'ridge_normal_equation_no_refit',fp);raw=encode(te)@c
   if art['validation_grid']:check(art['alpha']==min(art['validation_grid'],key=lambda r:(r['validation_loss'],-r['alpha']))['alpha'],'saved_inner_selection',fp)
  clipped=np.maximum(raw[:,1:] if isprice else raw,1e-12);q=clipped/clipped.sum(1,keepdims=True);bykey={r['row_key']:r for r in rows}
  for i,r in enumerate(te):
   row=bykey[r['row_key']];t=target(r['row_key'],task,control);check(int(row['fold'])==foldmap[r['date']],'fold_assignment',r['row_key']);check(row['label_end']==t['label_end'],'OOF_target_end',r['row_key'])
   if isprice:check(near(row['prediction'],raw[i,0]) and near(row['y'],float(t['y_token'])),'price_model_replay',r['row_key']);check(all(near(row[k],q[i,j]) for j,k in enumerate(['p_negative','p_zero','p_positive'])),'price_class_scores',r['row_key'])
   else:check(row['actual']==t['target'] and row['predicted']==classes[int(q[i].argmax())],'OOF_truth_argmax',r['row_key']);check(all(near(a,b) for a,b in zip(row['probabilities'],q[i])),'OOF_score_replay',r['row_key'])
 groups=defaultdict(list);foldgroups=defaultdict(list)
 for row in oof:groups[(row['task'],row['control'],row['model'])].append(row);foldgroups[(row['task'],row['control'],row['model'],row['fold'])].append(row)
 for n,fg in [('MODEL_METRICS_AGGREGATE.csv',False),('MODEL_METRICS_BY_FOLD.csv',True)]:
  for row in csv.DictReader((R/n).open()):
   key=(row['task'],row['control'],row['model'])+((int(row['fold']),) if fg else ());rs=(foldgroups if fg else groups).get(key,[]);cl=['NO_TRANSITION','TRANSITION'] if row['task']=='TRANSITION_WITHIN30' else ts['class_order'];m=countsref(rs,cl)[0]
   for k,v in m.items():check(near(number(row[k]),v),'direct_aggregate_'+k,str(key))
 matrices={(r['task'],r['control'],r['model'],r['actual_State'],r['predicted_State']):int(r['N']) for r in csv.DictReader((R/'CONFUSION_MATRIX_9STATE.csv').open())}
 boot=json.loads((R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').read_text());draws=boot['draws'];dates=boot['dates'];check(len(draws)==1000 and len({tuple(x) for x in draws})==boot['distinct_vector_value_N'],'global1000savedvectors');check(all(len(v)==len(dates) and all(0<=i<len(dates) for i in v) for v in draws),'bootstrap_index_bounds');check(sha(R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json')==json.loads((R/'BOOTSTRAP_GLOBAL_1000_RECEIPT.json').read_text())['SHA256'],'bootstrap_identity')
 def percentile(a,q):
  a=sorted(a);p=(len(a)-1)*q;k=math.floor(p);return a[k]+(a[math.ceil(p)]-a[k])*(p-k)
 for row in list(csv.DictReader((R/'PER_STATE_PRECISION_RECALL_F1.csv').open()))+list(csv.DictReader((R/'TRANSITION_BINARY_METRICS.csv').open())):
  key=(row['task'],row['control'],row['model']);rs=groups.get(key,[]);cl=['NO_TRANSITION','TRANSITION'] if row['task']=='TRANSITION_WITHIN30' else ts['class_order'];_,cm,p,rec,f=countsref(rs,cl);i=cl.index(row['State']);pn=sum(x[i] for x in cm);an=sum(cm[i]);tp=cm[i][i]
  for k,v in [('Predicted_N',pn),('Actual_N',an),('Correct_N',tp),('Recalled_N',tp),('Precision',p[i]),('Recall',rec[i]),('F1',f[i])]:check(near(number(row[k]),v),'direct_perState_'+k,str(key)+':'+row['State'])
  if row['task']!='TRANSITION_WITHIN30':
   for j,c in enumerate(cl):check(matrices[(*key,row['State'],c)]==cm[i][j],'direct9x9confusion')
  countdate={d:[sum(r['predicted']==row['State'] for r in rs if r['date']==d),sum(r['actual']==row['State'] for r in rs if r['date']==d),sum(r['actual']==r['predicted']==row['State'] for r in rs if r['date']==d)] for d in dates}
  for col,den in [('precision',0),('recall',1)]:
   vals=[]
   for draw in draws:
    denominator=sum(countdate[dates[x]][den] for x in draw);numerator=sum(countdate[dates[x]][2] for x in draw)
    if denominator:vals.append(numerator/denominator)
   low=percentile(vals,.025) if vals else None;high=percentile(vals,.975) if vals else None;check(near(number(row[col+'_CI95_low']),low) and near(number(row[col+'_CI95_high']),high),'bootstrap_'+col+'_stored_indices',str(key))
 for file,kind in [('MOTION_FAMILY_METRICS.csv','motion'),('TREND_CONTEXT_FAMILY_METRICS.csv','context')]:
  mapping={s:family for family,ss in ts[kind].items() for s in ss}
  expected={'motion':{'UP_MOVE':['RISE','SHARP_RISE','REBOUND'],'DOWN_MOVE':['DROP','SHARP_DROP','PULLBACK'],'NON_DIRECTIONAL_OR_STOP':['RANGE','RISE_STOP','DROP_STOP']},'context':{'UP_CONTEXT':['RISE','SHARP_RISE','PULLBACK','RISE_STOP'],'DOWN_CONTEXT':['DROP','SHARP_DROP','REBOUND','DROP_STOP'],'RANGE_CONTEXT':['RANGE']}}
  check(ts[kind]==expected[kind],'literal_family_mapping')
  for row in csv.DictReader((R/file).open()):
   rs=groups.get((row['task'],row['control'],row['model']),[]);fam=row['family'];pn=sum(mapping[r['predicted']]==fam for r in rs);an=sum(mapping[r['actual']]==fam for r in rs);tp=sum(mapping[r['actual']]==mapping[r['predicted']]==fam for r in rs)
   for col,v in [('Predicted_N',pn),('Actual_N',an),('Correct_N',tp),('Precision',tp/pn if pn else None),('Recall',tp/an if an else None)]:check(near(number(row[col]),v),'direct_family_'+col,fam)
 for row in csv.DictReader((R/'NEGATIVE_CONTROL_V2.csv').open()):
  key=(row['task'],row['control'],row['model']);control=groups.get(key,[]);keys={r['row_key'] for r in control};real=[r for r in groups.get((row['task'],'REAL',row['model']),[]) if r['row_key'] in keys];check(len(keys)==len(real)==int(row['matched_row_N']),'control_exactmatchedkeys');cl=['NO_TRANSITION','TRANSITION'] if row['task']=='TRANSITION_WITHIN30' else ts['class_order'];cm=countsref(control,cl)[0];rm=countsref(real,cl)[0]
  for col,v in [('REAL_accuracy',rm['accuracy']),('control_accuracy',cm['accuracy']),('REAL_log_loss',rm['log_loss']),('control_log_loss',cm['log_loss']),('REAL_date_equal_log_loss',rm['date_equal_log_loss']),('control_date_equal_log_loss',cm['date_equal_log_loss'])]:check(near(number(row[col]),v),'direct_control_'+col)
 for row in csv.DictReader((R/'PRICE_SECONDARY_V2.csv').open()):
  if row['version']!='V2':continue
  rr=[r for r in price if r['horizon']==row['horizon'] and r['model']==row['model']];es=[(float(r['y'])-float(r['prediction']))**2 for r in rr];de=defaultdict(list)
  for r,e in zip(rr,es):de[r['date']].append(e)
  check(near(number(row['MSE']),statistics.fmean(es) if es else None),'direct_price_MSE');check(near(number(row['date_equal_MSE']),statistics.fmean(statistics.fmean(v) for v in de.values()) if de else None),'direct_price_date_MSE')
 # Adjusted candidate precision-difference intervals reuse the same saved indexvectors.
 for row in csv.DictReader((R/'STATE_PROMOTION_ASSESSMENT.csv').open()):
  candidate=groups.get((row['task'],'REAL',row['model']),[]);baseline=groups.get((row['task'],'REAL','B1'),[]);state=row['State'];summaries=[]
  for rr in [candidate,baseline]:
   summaries.append({d:(sum(r['predicted']==state for r in rr if r['date']==d),sum(r['actual']==r['predicted']==state for r in rr if r['date']==d)) for d in dates})
  diffs=[]
  for draw in draws:
   terms=[]
   for summary in summaries:
    den=sum(summary[dates[x]][0] for x in draw);num=sum(summary[dates[x]][1] for x in draw);terms.append(num/den if den else None)
   if all(x is not None for x in terms):diffs.append(terms[0]-terms[1])
  lo=percentile(diffs,1/720) if diffs else None;hi=percentile(diffs,719/720) if diffs else None
  check(near(number(row['adjusted_CI_low']),lo) and near(number(row['adjusted_CI_high']),hi) and int(row['valid_vectors'])==len(diffs),'adjusted_precision_diff_CI_no_new_draws',row['State'])
 result={'status':'PASS' if not errors else 'FAIL','assertion_N':sum(checks.values()),'mismatch_N':len(errors),'counts':dict(checks),'errors':errors,'candidate_helper_imports':0,'independent_feature_oracle':'V1 INDEPENDENT_AUDIT.py primitive oracle only; candidatehelpers0','independent_feature_oracle_SHA256':sha(V/'INDEPENDENT_AUDIT.py'),'kernel_rerun_N':0,'model_refit_N':0,'new_bootstrap_draws':0,'provider_requests':0,'inner_grid_losses_scope':'Selection checked from saved inner losses, independent inner refits0; final normal equations directly checked','raw_page_independent_scope':'Exact derived Close/U and originalresponsehash pointers checked; temporaryproviderpagesnotredownloaded'}
 (R/'INDEPENDENT_AUDIT_V2.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','assertion_N','mismatch_N']}))
if __name__=='__main__':main()
