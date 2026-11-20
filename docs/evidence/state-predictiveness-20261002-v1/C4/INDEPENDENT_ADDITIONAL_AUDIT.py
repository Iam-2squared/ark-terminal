"""Separate direct audit of saved secondary, aggregate and train-only artifacts.
No imports from any candidate or first independent audit script. No fitting,
State9/Path execution, new bootstrap or provider operation.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,datetime,hashlib,json,math,statistics
import numpy as np
R=Path(__file__).resolve().parent
counts=Counter();errors=[]
def test(ok,kind,detail=None):
 counts[kind]+=1
 if not ok:errors.append({'kind':kind,'detail':detail})
def read(p):return list(csv.DictReader(p.open()))
def close(a,b):
 if a is None or b is None:return a is None and b is None
 return abs(float(a)-float(b))<=max(1e-8,1e-10*max(abs(float(a)),abs(float(b))))
def scalar(v):return None if v in ('','None') else float(v)
def avg(v):return statistics.fmean(v)
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalized_mass(rows):
 pairs=Counter((r['date'],r['security_id'],r['session_id']) for r in rows);daypairs=Counter(k[0] for k in pairs);dayN=len(daypairs)
 raw=[1/(dayN*daypairs[r['date']]*pairs[(r['date'],r['security_id'],r['session_id'])]) for r in rows];norm=avg(raw)
 return [x/norm for x in raw]
def date_mse(rows):
 by=defaultdict(list)
 for r in rows:by[r['date']].append((float(r['y'])-float(r['prediction']))**2)
 return avg(avg(v) for v in by.values())
def saved_prediction(row,fit):
 f=row['features']
 if fit['family'] in ('B0','B1'):return fit['lookup'].get(f['formal_primary'],fit['mean'])
 e=fit['encoder'];vector=[1.0]
 for n in e['numeric']:
  v=f[n];mu,sd=e['stats'][n];vector.extend([0.0 if v is None else (v-mu)/sd,float(v is None)])
 for n in e['categorical']:vector.extend(float(f[n]==c) for c in e['vocab'][n])
 coef=fit['coefficients'];return [math.fsum(vector[j]*coef[j][k] for j in range(len(vector))) for k in range(len(coef[0]))]
def probabilities(values):
 p=[max(1e-12,float(v)) for v in values];den=math.fsum(p);return [v/den for v in p]
def main():
 manifest=json.loads((R/'RECEIVED_DEVELOPMENT/DATASET_MANIFEST.json').read_text());schema=json.loads((R/'FEATURE_SCHEMA.json').read_text());fm={};lm={}
 for pair in manifest['pairs']:
  p=pair['pair_id'];fs=R/'RECEIVED_DEVELOPMENT/FEATURES'/f'{p}.jsonl';ls=R/'LABELS'/f'{p}.jsonl'
  test(sh(fs)==pair['feature_SHA256'],'received_feature_hash',p)
  for line in fs.read_text().splitlines():
   row=json.loads(line);fm[row['row_key']]=row
  for line in ls.read_text().splitlines():
   row=json.loads(line);lm[row['row_key']]=row
 sorted_features=sorted(fm.values(),key=lambda r:r['row_key']);dates=sorted({p['date'] for p in manifest['pairs']})
 mapping=read(R/'PERMUTATION_MAPPING.csv');donors={};mappings={(int(r['horizon']),r['feature_key']):r for r in mapping};generator=np.random.default_rng(2026100202)
 for h in [5,15,30]:
  for d in dates:
   rows=[r for r in sorted_features if r['date']==d and lm[r['row_key']]['real'][str(h)]['available']];order=generator.permutation(len(rows));seen=set()
   for i,row in enumerate(rows):
    donor=lm[rows[int(order[i])]['row_key']]['real'][str(h)];actual=mappings[(h,row['row_key'])]
    test(int(actual['permutation_index'])==int(order[i]) and actual['label_donor_future_key']==donor['future_key'] and actual['date']==d,'permutation_seed_and_tuple_mapping',(h,row['row_key']))
    donors[(h,row['row_key'])]=donor;seen.add(donor['future_key'])
   test(len(seen)==len(rows),'permutation_within_date_bijection',(h,d))
 fitted={};secondary_classes={'NEXT_PRIMARY':['RISE','SHARP_RISE','RISE_STOP','PULLBACK','RANGE','REBOUND','DROP','SHARP_DROP','DROP_STOP'],'TRANSITION_WITHIN30':[0,1]}
 primary_map=defaultdict(list)
 for p in sorted((R/'OOF').glob('*.csv')):
  for row in read(p):primary_map[(row['control'],int(row['horizon']),row['model'])].append(row)
 # Train-only encoder/target/hash/purge checks for every fitted artifact.
 for path in sorted((R/'FITTED').glob('*.json')):
  fit=json.loads(path.read_text());fitted[str(path.relative_to(R))]=fit;task=fit['task'];secondary=task in secondary_classes
  if secondary:
   classes=secondary_classes[task];available='next_primary_available' if task=='NEXT_PRIMARY' else 'transition_window_available';field='next_primary' if task=='NEXT_PRIMARY' else 'transition_within30'
   usable=[r for r in sorted_features if lm[r['row_key']]['structural'][available]]
   label_for=lambda r:lm[r['row_key']]['structural'][field]
  else:
   control,hh=task.split('_H');h=int(hh);part='shift60' if control=='SHIFT60' else 'real'
   usable=[r for r in sorted_features if lm[r['row_key']][part][str(h)]['available']]
   label_for=lambda r:donors[(h,r['row_key'])] if control=='PERMUTATION' else lm[r['row_key']][part][str(h)]
  train=[r for r in usable if r['date'] in fit['train_dates']];testrows=[r for r in usable if r['date'] in fit['test_dates']]
  test(set(fit['train_dates']).isdisjoint(fit['test_dates']) and max(fit['train_dates'])<min(fit['test_dates']),'train_test_date_and_session_separation',path.name)
  expected_key_sha=hashlib.sha256('\n'.join(r['row_key'] for r in train).encode()).hexdigest()
  test(fit['train_key_SHA256']==expected_key_sha,'fit_train_keys',path.name)
  for rows,name in [(train,'train_feature_SHA256'),(testrows,'test_feature_SHA256')]:
   hsh=hashlib.sha256(json.dumps([[r['row_key'],r['features']] for r in rows],sort_keys=True,separators=(',',':')).encode()).hexdigest();test(fit[name]==hsh,'fit_feature_input_identity',path.name+':'+name)
  if secondary:Y=[[int(label_for(r)==c) for c in classes] for r in train]
  else:
   targets=[label_for(r) for r in train];Y=[[float(t['y_token'])]+[int(t['direction']==c) for c in [-1,0,1]] for t in targets]
   boundary=datetime.datetime.fromisoformat(min(fit['test_dates'])+'T00:00:00+09:00')
   for target in targets:
    end=datetime.datetime.fromisoformat(target['label_end']);test(end<boundary and (boundary-end).total_seconds()>=1800,'purge_embargo_label_bound',path.name)
  test(fit['train_target_matrix_SHA256']==hashlib.sha256(np.asarray(Y,dtype='<f8').tobytes()).hexdigest() and fit['model_plan_SHA256']==sh(R/'MODEL_PLAN.json'),'fit_target_and_plan_identity',path.name)
  w=normalized_mass(train);sw=math.fsum(w)
  if fit['family'] in ('B0','B1'):
   prior=[math.fsum(w[i]*Y[i][k] for i in range(len(train)))/sw for k in range(len(Y[0]))]
   test(all(close(x,fit['mean'][k]) for k,x in enumerate(prior)),'all_task_baseline_prior',path.name)
   for cat,lookup in fit['lookup'].items():
    ids=[i for i,r in enumerate(train) if r['features']['formal_primary']==cat];mass=math.fsum(w[i] for i in ids)
    expected=[(math.fsum(w[i]*Y[i][k] for i in ids)+10*prior[k])/(mass+10) for k in range(len(Y[0]))]
    test(all(close(x,lookup[k]) for k,x in enumerate(expected)),'all_task_Primary_lookup',path.name+':'+cat)
  else:
   e=fit['encoder'];num=schema['numeric_state']+(schema['numeric_path'] if fit['family']=='B3' else []);cats=schema['categorical_state']+(schema['categorical_path'] if fit['family']=='B3' else [])
   test(e['numeric']==num and e['categorical']==cats,'closed_feature_family',path.name)
   for n in num:
    ids=[i for i,r in enumerate(train) if r['features'][n] is not None];mass=math.fsum(w[i] for i in ids);mu=math.fsum(w[i]*train[i]['features'][n] for i in ids)/mass if ids else 0.0;var=math.fsum(w[i]*(train[i]['features'][n]-mu)**2 for i in ids)/mass if ids else 0.0;sd=math.sqrt(var) if var>0 else 1.0
    test(close(mu,e['stats'][n][0]) and close(sd,e['stats'][n][1]),'train_only_numeric_preprocessing',path.name+':'+n)
   for n in cats:test(e['vocab'][n]==sorted({r['features'][n] for r in train}),'train_only_categorical_vocabulary',path.name+':'+n)
   if secondary:test(fit['alpha']==0.1 and not fit['validation_grid'],'fixed_secondary_regularization',path.name)
   else:
    grid=fit['validation_grid'];best=min(grid,key=lambda x:(x['continuous_validation_MSE'],-x['alpha']))['alpha']
    test([x['alpha'] for x in grid]==[0.01,0.1,1.0] and fit['alpha']==best,'finite_grid_selection_from_saved_inner_losses',path.name)
 # Secondary truth, probability replay, fold membership and aggregate metrics.
 secondary=read(R/'SECONDARY_OOF.csv');sg=defaultdict(list);keys=set();split=json.loads((R/'SPLIT_REALIZED.json').read_text());fold_for={d:f['fold'] for f in split['folds'] for d in f['test_dates']}
 for r in secondary:
  task=r['task'];model=r['model'];key=(task,model,r['row_key']);test(key not in keys,'secondary_duplicate_key',key);keys.add(key)
  row=fm[r['row_key']];s=lm[r['row_key']]['structural'];truth=s['next_primary'] if task=='NEXT_PRIMARY' else s['transition_within30'];classes=secondary_classes[task];fit=fitted[r['fit_path']];q=probabilities(saved_prediction(row,fit));actualq=json.loads(r['probabilities_json']);actualtruth=r['truth'] if task=='NEXT_PRIMARY' else int(r['truth']);pred=classes[max(range(len(q)),key=lambda k:q[k])]
  test(actualtruth==truth and json.loads(r['classes_json'])==classes,'secondary_saved_truth',key)
  test(int(r['fold'])==fold_for[r['date']] and r['date'] in fit['test_dates'],'secondary_fold',key)
  test(all(close(a,b) for a,b in zip(actualq,q)) and (r['prediction'] if task=='NEXT_PRIMARY' else int(r['prediction']))==pred,'secondary_probability_replay',key)
  sg[(task,model)].append(r)
 for r in read(R/'SECONDARY_METRICS.csv'):
  rows=sg[(r['task'],r['model'])];classes=secondary_classes[r['task']];qs=[json.loads(x['probabilities_json']) for x in rows];truth=[classes.index(x['truth'] if r['task']=='NEXT_PRIMARY' else int(x['truth'])) for x in rows];pred=[max(range(len(classes)),key=lambda k:q[k]) for q in qs]
  expected={'row_N':len(rows),'date_N':len({x['date'] for x in rows}),'accuracy':avg(int(a==b) for a,b in zip(truth,pred)),'balanced_accuracy':avg(avg(int(pred[i]==k) for i in range(len(rows)) if truth[i]==k) for k in sorted(set(truth))),'Brier':avg(math.fsum((q[k]-int(c==k))**2 for k in range(len(classes))) for q,c in zip(qs,truth)),'log_loss':avg(-math.log(q[c]) for q,c in zip(qs,truth))}
  for n,v in expected.items():test(close(v,scalar(r[n])),'independent_secondary_metric',(r['task'],r['model'],n))
 # Five buckets, calibrated direction bins and cluster concentration directly.
 for r in read(R/'PREDICTION_BUCKETS.csv'):
  h=int(r['horizon']);m=r['model'];k=int(r['bucket'])-1;rows=sorted(primary_map[('REAL',h,m)],key=lambda x:(float(x['prediction']),x['row_key']));cell=rows[k*len(rows)//5:(k+1)*len(rows)//5]
  expected={'N':len(cell),'predicted_mean':avg(float(x['prediction']) for x in cell),'realized_mean':avg(float(x['y']) for x in cell),'realized_median':statistics.median(float(x['y']) for x in cell),'date_N':len({x['date'] for x in cell}),'security_session_N':len({(x['security_id'],x['session_id']) for x in cell})}
  for n,v in expected.items():test(close(v,scalar(r[n])),'independent_prediction_bucket',(h,m,k+1,n))
 for r in read(R/'DIRECTION_CALIBRATION.csv'):
  h=int(r['horizon']);m=r['model'];binN=int(r['confidence_bin']);cell=[]
  for x in primary_map[('REAL',h,m)]:
   q=[float(x[n]) for n in ['p_negative','p_zero','p_positive']];confidence=max(q);category=q.index(confidence)-1
   if min(9,int(confidence*10))==binN:cell.append((confidence,int(category==int(x['direction']))))
  test(len(cell)==int(r['N']) and close(avg(c for c,a in cell),float(r['mean_confidence'])) and close(avg(a for c,a in cell),float(r['observed_accuracy'])),'independent_calibration',(h,m,binN))
 for r in read(R/'CONCENTRATION_LEAVE_ONE.csv'):
  h=int(r['horizon']);m=r['candidate'];b=r['comparator'];unit=r['cluster_unit'];mm={x['row_key']:x for x in primary_map[('REAL',h,m)]};bb={x['row_key']:x for x in primary_map[('REAL',h,b)]};keys=sorted(set(mm)&set(bb));dn=Counter(mm[k]['date'] for k in keys);net=defaultdict(list);gross=defaultdict(list)
  def group(x):return x['date'] if unit=='date' else x['security_id'] if unit=='security_id' else x['security_id']+'|'+x['session_id']
  for k in keys:
   v=((float(bb[k]['y'])-float(bb[k]['prediction']))**2-(float(mm[k]['y'])-float(mm[k]['prediction']))**2)/dn[mm[k]['date']];g=group(mm[k]);net[g].append(v);gross[g].append(max(0,v))
  contributions={g:math.fsum(v) for g,v in net.items()};positive={g:math.fsum(v) for g,v in gross.items()};total=math.fsum(positive.values());share=max(positive.values())/total if total else None;leave=[]
  for g in net:
   keep=[k for k in keys if group(mm[k])!=g]
   if keep:leave.append(date_mse([bb[k] for k in keep])-date_mse([mm[k] for k in keep]))
  test(len(net)==int(r['cluster_N']) and close(share,scalar(r['maximum_gross_positive_share'])) and close(min(leave) if leave else None,scalar(r['minimum_leave_one_MSE_improvement'])) and close(math.fsum(contributions.values())/len(dn),scalar(r['net_date_weighted_improvement'])),'independent_concentration_leave_one',(h,m,b,unit))
  actual=json.loads(r['contributions_json']);test(set(actual)==set(contributions) and all(close(actual[g],contributions[g]) for g in actual),'independent_contribution_table',(h,m,b,unit))
 # Source and failed-run raw-purge receipts are metadata only; never reopen raw.
 for folder in ['REPAIR_01_PARTIAL','RECEIVED_DEVELOPMENT']:
  for n in ['PURGE_RECEIPT.json','WORKFLOW_PURGE_RECEIPT.json']:test((R/folder/n).exists(),'raw_purge_receipt_present',folder+'/'+n)
 report={'created_at_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'status':'PASS' if not errors else 'MISMATCH_LOCALIZATION_REQUIRED','pass':not errors,'assertion_N':sum(counts.values()),'checks':dict(counts),'error_N':len(errors),'errors':errors,'secondary_OOF_record_N':len(secondary),'fitted_artifact_N':len(fitted),'candidate_imports':0,'kernel_reruns':0,'fits_rerun':0,'bootstrap_draws_created':0,'provider_requests':0,'independence':'Separate primitive arithmetic, training-set reconstruction, saved-artifact probability replay and table logic. Shared standard dependencies only.','limits':['The saved inner grid selection is checked but its regressions are not re-fitted.','No actual receive chronology can be inferred from historical bar-end assumption.']}
 (R/'INDEPENDENT_ADDITIONAL_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'assertion_N':report['assertion_N'],'error_N':len(errors),'first_errors':errors[:12]}))
if __name__=='__main__':main()
