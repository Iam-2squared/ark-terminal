"""Independent primitive reconstruction: no candidate feature/target/metric imports.
Standard Decimal/NumPy libraries are shared dependencies, not shared helpers.
No State9/Path kernel, fitting or provider requests are made.
"""
from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal,Context,localcontext,ROUND_HALF_EVEN
from fractions import Fraction
import csv,hashlib,json,math,statistics,datetime
import numpy as np
R=Path(__file__).resolve().parent
errors=[];counts=Counter()
def check(flag,kind,detail=None):
 counts[kind]+=1
 if not flag:errors.append({'kind':kind,'detail':detail})
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b):
 if a is None or b is None:return a is None and b is None
 if type(a) is bool or type(b) is bool:return a==b
 return abs(float(a)-float(b))<=max(1e-8,1e-10*max(abs(float(a)),abs(float(b))))
def mean(x):return statistics.fmean(x)
def value(x):
 if x is None:return None
 if isinstance(x,bool):return int(x)
 with localcontext(Context(prec=80)):
  if isinstance(x,dict):return float(Decimal(x['num'])/Decimal(x['den']))
  return float(Decimal(str(x)))
def subtract(a,b):
 if a is None or b is None:return None
 with localcontext(Context(prec=80)):return float(Decimal(a)-Decimal(b))
def cat(x):return '__MISSING__' if x is None else str(x)
def csvread(p):return list(csv.DictReader(p.open()))
def parseval(v):return None if v in ('','None') else float(v)
def independent_feature_check(rows,traces):
 accepted=None;pending=set();segment=0;segment_start=None;hist=[];window=[];previous_primary=None;previous_dwell=None;reset_at=None;prior=None;dwell=0;entered=None
 for row,state in zip(rows,traces):
  t=row['scheduled_t'];meta=state['bar_metadata'] or {};reset=[]
  if state['numeric_status']=='ACCEPTED':
   if 'NOT_AVAILABLE' in pending:reset.append('AFTER_UNAVAILABLE')
   if 'REJECTED' in pending:reset.append('AFTER_REJECTED')
   if accepted is not None:
    if t!=accepted['t']+1:reset.append('ORDINAL_GAP')
    if meta['source']!=accepted['source']:reset.append('SOURCE_CHANGE')
    if meta['auction']!=accepted['auction']:reset.append('AUCTION_CHANGE')
   if 'SEGMENT_RESET_NO_GAP_RETURN' in state['events']:reset.append('FROZEN_RESET_EVENT')
   oldseg=segment
   if accepted is None:segment=1
   elif reset:segment+=1
   accepted=dict(meta);pending.clear()
  else:oldseg=segment;pending.add(state['numeric_status'])
  sid=row['pair_id']+f':S{segment:04d}'
  check(row['causal_segment_id']==sid,'causal_segment_reconstruction',row['row_key'])
  if prior is None or oldseg!=segment:
   segment_start=t;hist=[];window=[];previous_primary=None;previous_dwell=None;reset_at=t
  observed=state['current_semantics_observed'];primary=state['primary'] if observed else None
  connected=prior is not None and prior['observed'] and observed and prior['segment']==segment and t==prior['t']+1
  hold=connected and prior['primary']==primary;changed=connected and prior['primary']!=primary
  if prior is not None and (prior['segment']!=segment or t!=prior['t']+1 or prior['observed'] and not observed):reset_at=t
  if changed:
   hist.append((prior['primary'],primary,t));previous_primary=prior['primary'];previous_dwell=dwell
  if observed:
   if hold:dwell+=1
   else:dwell=1;entered=t
  else:dwell=0;entered=None
  window.append((int(hold),int(changed)));window=window[-15:]
  stop=state['stop'] or {};balance=state['balance'] or {};ra=state['range_analysis'] or {};fa=state['fast_analysis'] or {}
  expected={'observed':int(observed),'observed_age':None if state['observed_at'] is None else t-state['observed_at'],'local_direction':value(state['leg_direction']),'context_direction':value(state['context']),'fast':value(state['fast_flag']),'fast_applicable':value(state['fast_applicable_to_primary']),'close_u':value(state['close_u']),'stop_direction':value(stop.get('direction')),'stop_width':subtract(stop.get('high'),stop.get('low')),'stop_center_distance':subtract(state['close_u'],stop.get('center')),'stop_age':None if not stop else t-stop['start'],'stop_recognized_age':None if not stop else t-stop['recognized_at'],'stop_count':value(stop.get('count')),'stop_progress_age':None if not stop else t-stop['progress_at'],'range_width':subtract(balance.get('high'),balance.get('low')),'range_established_age':None if not balance else t-balance['established_at'],'range_exit_low_distance':subtract(state['close_u'],balance.get('exit_low')),'range_exit_high_distance':subtract(balance.get('exit_high'),state['close_u']),'formal_primary':'__FORMAL_NULL__' if primary is None else primary,'display_primary':cat(state['primary']),'activity':cat(state['activity']),'basis':cat(state['basis']),'direction_basis':cat(state['direction_basis']),'numeric_status':cat(state['numeric_status']),'rejection_reason':cat(state['rejection_reason']),'auction':cat(meta.get('auction')),'source':cat(meta.get('source')),'source_events':'|'.join(sorted(state['events'])),'range_reason':cat(balance.get('reason')),'dwell_scheduled_bars':dwell if observed else None,'dwell_observed_bars':dwell if observed else None,'entered_age':None if entered is None else t-entered,'previous_run_dwell':previous_dwell,'bars_since_transition':None if not hist else t-hist[-1][2],'segment_age':t-segment_start,'segment_transition_count':len(hist),'recent_hold_count_15':sum(x[0] for x in window),'recent_transition_count_15':sum(x[1] for x in window),'recent_transition_density_15':sum(x[1] for x in window)/len(window),'reset_recency':None if reset_at is None else t-reset_at,'current_run_primary':cat(primary),'previous_primary':cat(previous_primary),'last_transition_from':cat(hist[-1][0]) if hist else '__MISSING__','last_transition_to':cat(hist[-1][1]) if hist else '__MISSING__'}
  for k in ['net','tv','span','width','eta','turns','guard']:expected['range_analysis_'+k]=value(ra.get(k))
  for k in ['A','B','C','D']:expected['range_'+k]=value((ra.get('conditions') or {}).get(k))
  for k in ['net','tv','eta','directional_net']:expected['fast_analysis_'+k]=value(fa.get(k))
  for k in range(4):expected['transition_seq_'+str(k)]='__MISSING__' if len(hist)<=k else hist[-1-k][0]+'>'+hist[-1-k][1]
  check(set(expected)==set(row['features']),'feature_allowlist',row['row_key'])
  for k,v in expected.items():
   got=row['features'][k];check(got==v if isinstance(v,str) else near(got,v),'feature_value',row['row_key']+':'+k)
  check(row['feature_max_timestamp']<=row['bar_end'] and row['feature_created_before_target'],'feature_timestamp',row['row_key'])
  for analysis in (ra,fa):
   check(all(x<=t for x in analysis.get('window_ids',[])+analysis.get('old_window_ids',[])),'analysis_asof_bound',row['row_key'])
  check(state['as_of']==t and (state['observed_at'] is None or state['observed_at']<=t),'state_timestamp',row['row_key'])
  if row['audit_source']['raw_present'] and state['numeric_status']=='ACCEPTED':check(Fraction(state['close_u'])==Fraction(row['audit_source']['x_C']),'direct_canonical_close',row['row_key'])
  prior={'t':t,'primary':primary,'observed':observed,'segment':segment}
def independent_price(rows,i,h):
 start=rows[i];a=start['audit_source']
 if not a['raw_present'] or a['numeric_status']!='ACCEPTED':return False,'START_UNAVAILABLE',None
 if start['tradable_index'] is None:return False,'START_AUCTION',None
 stop=next((j for j,r in enumerate(rows) if r['tradable_index']==start['tradable_index']+h),None)
 if stop is None:return False,'EXACT_HORIZON_OUTSIDE_SESSION',None
 future=rows[stop];b=future['audit_source']
 if not b['raw_present'] or b['numeric_status']!='ACCEPTED':return False,'EXACT_HORIZON_UNAVAILABLE',future
 for r in rows[i:stop+1]:
  if r['causal_segment_id']!=start['causal_segment_id']:return False,'CAUSAL_SEGMENT_BREAK',future
  if not r['audit_source']['raw_present'] or r['audit_source']['numeric_status']!='ACCEPTED':return False,'INTERVENING_UNKNOWN_OR_REJECTED',future
  if r['audit_source']['auction']!='CONTINUOUS':return False,'AUCTION_OR_OPENING_BOUNDARY',future
 return True,None,future
def rank(xs):
 order=sorted(range(len(xs)),key=lambda i:xs[i]);out=[0.0]*len(xs);start=0
 while start<len(xs):
  end=start+1
  while end<len(xs) and xs[order[end]]==xs[order[start]]:end+=1
  average=(start+1+end)/2
  for k in range(start,end):out[order[k]]=average
  start=end
 return out
def metrics(rows):
 y=[float(r['y']) for r in rows];p=[float(r['prediction']) for r in rows];q=[[float(r[k]) for k in ['p_negative','p_zero','p_positive']] for r in rows];c=[int(r['direction'])+1 for r in rows];pred=[max(range(3),key=lambda k:q[i][k]) for i in range(len(rows))]
 dates=defaultdict(list)
 for i,r in enumerate(rows):dates[r['date']].append(i)
 mse=[(a-b)**2 for a,b in zip(y,p)];mae=[abs(a-b) for a,b in zip(y,p)];ic=None
 if len(set(y))>=2 and len(set(p))>=2:
  a=rank(y);b=rank(p);am=mean(a);bm=mean(b);sa=math.fsum((v-am)**2 for v in a);sb=math.fsum((v-bm)**2 for v in b);ic=math.fsum((a[i]-am)*(b[i]-bm) for i in range(len(a)))/math.sqrt(sa*sb)
 return {'row_N':len(rows),'date_N':len(dates),'security_N':len({r['security_id'] for r in rows}),'security_session_N':len({(r['security_id'],r['session_id']) for r in rows}),'run_N':len({r['run_id'] for r in rows if r['run_id']}),'MAE':mean(mae),'MSE':mean(mse),'date_equal_MAE':mean(mean(mae[i] for i in ids) for ids in dates.values()),'date_equal_MSE':mean(mean(mse[i] for i in ids) for ids in dates.values()),'Spearman_IC':ic,'accuracy':mean(int(pred[i]==c[i]) for i in range(len(c))),'balanced_accuracy':mean(mean(int(pred[i]==v) for i in range(len(c)) if c[i]==v) for v in sorted(set(c))),'regression_sign_accuracy':mean(int((0 if p[i]==0 else 1 if p[i]>0 else -1)==c[i]-1) for i in range(len(c))),'Brier':mean(sum((q[i][k]-int(c[i]==k))**2 for k in range(3)) for i in range(len(c))),'log_loss':mean(-math.log(q[i][c[i]]) for i in range(len(c)))}
def quantile(v,p):
 x=sorted(v);a=(len(x)-1)*p;lo=math.floor(a);hi=math.ceil(a);return x[lo]+(x[hi]-x[lo])*(a-lo)
def main():
 pre=json.loads((R/'PREDICTIVENESS_PRECOMMIT.json').read_text())
 for name,sha in pre['hashes'].items():check(digest(R/name)==sha,'precommit_hash',name)
 manifest=json.loads((R/'RECEIVED_DEVELOPMENT/DATASET_MANIFEST.json').read_text());featuremap={};labelmap={};all_rows=[]
 for item in manifest['pairs']:
  pid=item['pair_id'];features=[json.loads(l) for l in (R/'RECEIVED_DEVELOPMENT/FEATURES'/f'{pid}.jsonl').read_text().splitlines()];traces=[json.loads(l) for l in (R/'RECEIVED_DEVELOPMENT/STATE9_TRACES'/f'{pid}.jsonl').read_text().splitlines()];labels=[json.loads(l) for l in (R/'LABELS'/f'{pid}.jsonl').read_text().splitlines()]
  check(len(features)==len(traces)==len(labels)==item['scheduled_endpoints_N'],'pair_rows',pid)
  independent_feature_check(features,traces)
  # Dated calendar reconstructed from the inherited source interval contract,
  # with its original auction buckets; no candidate calendar helper import.
  day=item['date'];last=925 if day>='2024-11-05' else 900;minutes=list(range(541,691))+[691]+list(range(751,last+1))+[931 if last==925 else 901]
  trade=[m for m in minutes if m not in (691,931 if last==925 else 901)];indices={m-540:k for k,m in enumerate(trade)}
  check([r['scheduled_t'] for r in features]==[m-540 for m in minutes],'dated_calendar',pid)
  for i,(row,label) in enumerate(zip(features,labels)):
   check(row['tradable_index']==indices.get(row['scheduled_t']),'tradable_index',row['row_key'])
   check(row['row_key'] not in featuremap,'duplicate_key',row['row_key']);featuremap[row['row_key']]=row;labelmap[row['row_key']]=label;all_rows.append(row)
   for h in [5,15,30]:
    available,reason,future=independent_price(features,i,h);target=label['real'][str(h)]
    check(target['available']==available and target['unavailable_reason']==reason,'target_eligibility',row['row_key']+':'+str(h))
    if available:
     source=row['audit_source'];end=future['audit_source']
     with localcontext(Context(prec=80,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999)):
      expected=format((Decimal(end['Close_JPY'])-Decimal(source['Close_JPY']))/Decimal(source['U']),'f');delta=format(Decimal(end['x_C'])-Decimal(source['x_C']),'f')
     direction=0 if Decimal(end['Close_JPY'])==Decimal(source['Close_JPY']) else 1 if Decimal(end['Close_JPY'])>Decimal(source['Close_JPY']) else -1
     exact=(Fraction(end['Close_JPY'])-Fraction(source['Close_JPY']))/Fraction(source['U'])
     check(target['y_token']==expected and target['delta_x_token']==delta and Fraction(target['y_exact_rational'])==exact,'target_value_exact',row['row_key']+':'+str(h))
     check(target['direction']==direction and target['future_key']==future['row_key'] and target['label_end']==future['bar_end'],'target_endpoint_exact',row['row_key']+':'+str(h))
     check(target['label_segment']==row['causal_segment_id']==future['causal_segment_id'],'target_segment',row['row_key']+':'+str(h))
    ti=row['tradable_index'];si=None if ti is None else next((j for j,r in enumerate(features) if r['tradable_index']==ti+60),None);shift=label['shift60'][str(h)]
    if si is None:ok=False
    else:ok=independent_price(features,i,60+h)[0] and independent_price(features,si,h)[0]
    check(shift['available']==ok,'shift_eligibility',row['row_key']+':'+str(h))
    if ok:
     future=independent_price(features,si,h)[2];start=features[si]
     with localcontext(Context(prec=80,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999)):expected=format((Decimal(future['audit_source']['Close_JPY'])-Decimal(start['audit_source']['Close_JPY']))/Decimal(start['audit_source']['U']),'f')
     check(shift['y_token']==expected and shift['label_start']==start['bar_end'] and shift['label_end']==future['bar_end'],'shift_target_exact',row['row_key']+':'+str(h))
   # Structural targets independently from adjacent tuples, not saved event list.
   s=label['structural'];next_row=features[i+1] if i+1<len(features) else None
   can_next=row['tradable_index'] is not None and row['audit_source']['observed'] and next_row is not None and next_row['tradable_index']==row['tradable_index']+1 and next_row['audit_source']['observed'] and next_row['causal_segment_id']==row['causal_segment_id'] and next_row['audit_source']['auction']=='CONTINUOUS'
   check(s['next_primary_available']==can_next,'structural_next_eligibility',row['row_key'])
   if can_next:check(s['next_primary']==next_row['audit_source']['formal_primary'],'structural_next_primary',row['row_key'])
   can_window=row['audit_source']['observed'] and row['tradable_index'] is not None and independent_price(features,i,30)[0]
   check(s['transition_window_available']==can_window,'structural_window',row['row_key'])
   if can_window:
    end=independent_price(features,i,30)[2];found=None
    for k in range(i+1,features.index(end)+1):
     a,b=features[k-1],features[k]
     if a['audit_source']['observed'] and b['audit_source']['observed'] and a['causal_segment_id']==b['causal_segment_id'] and b['scheduled_t']==a['scheduled_t']+1 and a['audit_source']['formal_primary']!=b['audit_source']['formal_primary']:found=(a,b);break
    check(s['transition_within30']==int(found is not None),'structural_transition_occurrence',row['row_key'])
    if found:
     a,b=found;check(s['next_transition_from']==a['audit_source']['formal_primary'] and s['next_transition_to']==b['audit_source']['formal_primary'] and s['next_transition_at']==b['bar_end'] and s['time_to_next_transition']==b['tradable_index']-row['tradable_index'],'structural_boundary_duration',row['row_key'])
   
 split=json.loads((R/'SPLIT_REALIZED.json').read_text());dates=sorted({p['date'] for p in manifest['pairs']});remaining=dates[3:];q,rem=divmod(len(remaining),3);expected_folds={};cursor=0
 for f in range(1,4):
  n=q+int(f<=rem);test=remaining[cursor:cursor+n];cursor+=n
  for d in test:expected_folds[d]=f
 check(split['dates']==dates,'split_date_order')
 oof=[]
 for p in sorted((R/'OOF').glob('*.csv')):oof.extend(csvread(p))
 perm=csvread(R/'PERMUTATION_MAPPING.csv');donors={}
 for p in perm:
  key=(int(p['horizon']),p['feature_key']);end=p['label_donor_future_key'];date=p['date']
  choices=[k for k,l in labelmap.items() if l['date']==date and l['real'][p['horizon']]['available'] and l['real'][p['horizon']]['future_key']==end]
  check(len(choices)==1,'permutation_donor_unique',key)
  if choices:donors[key]=labelmap[choices[0]]['real'][p['horizon']]
 groups=defaultdict(list);foldgroups=defaultdict(list);keyset=set();session_folds={};fitcache={};prediction_checks=0
 for row in oof:
  c,h,m,f=row['control'],int(row['horizon']),row['model'],int(row['fold']);k=row['row_key'];identity=(c,h,m,k)
  check(identity not in keyset,'OOF_duplicate',identity);keyset.add(identity)
  check(expected_folds.get(row['date'])==f,'OOF_fold',k)
  group=(row['security_id'],row['session_id']);old=session_folds.setdefault(group,f);check(old==f,'security_session_single_fold',group)
  target=donors[(h,k)] if c=='PERMUTATION' else labelmap[k]['shift60' if c=='SHIFT60' else 'real'][str(h)]
  check(target['available'] and row['y_token']==target['y_token'] and int(row['direction'])==target['direction'] and row['label_end']==target['label_end'],'OOF_truth',identity)
  path=row['fit_path']
  if path not in fitcache:fitcache[path]=json.loads((R/path).read_text())
  fit=fitcache[path];check(all(d<min(fit['test_dates']) for d in fit['train_dates']) and row['date'] in fit['test_dates'],'fitting_time_order',identity)
  features=featuremap[k]['features']
  if m in ['B0','B1']:raw_prediction=fit['lookup'].get(features['formal_primary'],fit['mean'])
  else:
   enc=fit['encoder'];x=[1.0]
   for name in enc['numeric']:
    v=features[name];mu,sd=enc['stats'][name];x.extend([0.0 if v is None else (v-mu)/sd,float(v is None)])
   for name in enc['categorical']:x.extend(float(features[name]==v) for v in enc['vocab'][name])
   coef=fit['coefficients'];raw_prediction=[math.fsum(x[j]*coef[j][col] for j in range(len(x))) for col in range(4)]
  probabilities=[max(1e-12,v) for v in raw_prediction[1:]];den=sum(probabilities);probabilities=[v/den for v in probabilities]
  check(near(row['prediction'],raw_prediction[0]) and all(near(row[name],p) for name,p in zip(['p_negative','p_zero','p_positive'],probabilities)),'fitted_artifact_prediction_replay',identity);prediction_checks+=1
  groups[(c,h,m)].append(row);foldgroups[(c,h,m,f)].append(row)
 for filename,grouper,withfold in [('METRICS_AGGREGATE.csv',groups,False),('METRICS_BY_FOLD.csv',foldgroups,True)]:
  table=csvread(R/filename);calculated={key:metrics(rows) for key,rows in grouper.items()}
  for r in table:
   key=(r['control'],int(r['horizon']),r['model'])+((int(r['fold']),) if withfold else ())
   actual=calculated[key];basekey=(r['control'],int(r['horizon']),'B0')+((int(r['fold']),) if withfold else ());base=calculated[basekey]
   actual['R2_vs_saved_B0']=None if base['MSE']==0 else 1-actual['MSE']/base['MSE'];actual['date_equal_R2_vs_B0']=None if base['date_equal_MSE']==0 else 1-actual['date_equal_MSE']/base['date_equal_MSE']
   for name,v in actual.items():check(near(parseval(r[name]),v),'independent_metric',str(key)+':'+name)
 bootstrap=json.loads((R/'BOOTSTRAP_DATE_DRAWS.json').read_text());incremental=csvread(R/'INCREMENTAL_VALUE.csv')
 date_errors={}
 for (c,h,m),rows in groups.items():
  if c!='REAL':continue
  date_errors[(h,m)]={d:mean((float(r['y'])-float(r['prediction']))**2 for r in rows if r['date']==d) for d in sorted({r['date'] for r in rows})}
 for r in incremental:
  h=int(r['horizon']);a=r['candidate'];b=r['comparator'];info=bootstrap['by_horizon'][str(h)];ds=info['dates'];av=[date_errors[(h,a)][d] for d in ds];bv=[date_errors[(h,b)][d] for d in ds];samples=[]
  for draw in info['draws']:
   den=mean(bv[i] for i in draw)
   if den:samples.append(mean(bv[i]-av[i] for i in draw)/den)
  point=None if mean(bv)==0 else 1-mean(av)/mean(bv);lower=None if not samples else quantile(samples,1/240);upper=None if not samples else quantile(samples,239/240)
  check(near(point,parseval(r['relative_reduction'])) and near(mean(bv)-mean(av),parseval(r['date_equal_MSE_reduction'])),'independent_increment',str((h,a,b)))
  check(near(lower,parseval(r['CI_low'])) and near(upper,parseval(r['CI_high'])) and len(samples)==int(r['bootstrap_replicates']),'independent_cluster_bootstrap',str((h,a,b)))
 negative=csvread(R/'NEGATIVE_CONTROL_RESULTS.csv')
 for r in negative:
  if r['status']=='UNAVAILABLE':continue
  c,h,m=r['control'],int(r['horizon']),r['model'];rows=groups[(c,h,m)];base=groups[(c,h,'B0')];keys={x['row_key'] for x in rows};matched=[x for x in groups[('REAL',h,m)] if x['row_key'] in keys];matchedbase=[x for x in groups[('REAL',h,'B0')] if x['row_key'] in keys]
  cm,cb=metrics(rows),metrics(base);rm,rb=metrics(matched),metrics(matchedbase);nc=None if cb['date_equal_MSE']==0 else 1-cm['date_equal_MSE']/cb['date_equal_MSE'];actual=None if rb['date_equal_MSE']==0 else 1-rm['date_equal_MSE']/rb['date_equal_MSE'];flag=actual is not None and actual>0 and nc is not None and nc>0 and nc>=0.9*actual
  check(near(nc,parseval(r['control_relative_improvement'])) and near(actual,parseval(r['real_matched_relative_improvement'])) and flag==(r['comparably_good']=='True'),'independent_negative_control',str((c,h,m)))
 # Recompute B0/B1 training priors/lookups from saved labels, not saved mean alone.
 for path,fit in fitcache.items():
  if fit['family'] not in ('B0','B1'):continue
  task=fit['task'];parts=task.split('_H');control=parts[0];h=int(parts[1]);training=[];ys=[]
  for row in all_rows:
   if row['date'] not in fit['train_dates']:continue
   target=donors.get((h,row['row_key'])) if control=='PERMUTATION' else labelmap[row['row_key']]['shift60' if control=='SHIFT60' else 'real'][str(h)]
   if not target or not target['available']:continue
   training.append(row);ys.append([float(target['y_token'])]+[int(target['direction']==c) for c in [-1,0,1]])
  datesN=len({r['date'] for r in training});paircounts=Counter((r['date'],r['security_id'],r['session_id']) for r in training);perdate=Counter(d for d,s,x in paircounts);ww=[1/(datesN*perdate[r['date']]*paircounts[(r['date'],r['security_id'],r['session_id'])]) for r in training];wm=mean(ww);ww=[w/wm for w in ww];sw=math.fsum(ww);prior=[math.fsum(ww[i]*ys[i][j] for i in range(len(training)))/sw for j in range(4)]
  check(all(near(v,fit['mean'][j]) for j,v in enumerate(prior)),'independent_baseline_prior',path)
  for category,values in fit['lookup'].items():
   ids=[i for i,r in enumerate(training) if r['features']['formal_primary']==category];mass=math.fsum(ww[i] for i in ids);expected=[(math.fsum(ww[i]*ys[i][j] for i in ids)+10*prior[j])/(mass+10) for j in range(4)]
   check(all(near(v,values[j]) for j,v in enumerate(expected)),'independent_Primary_shrinkage',path+':'+category)
 report={'created_at_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'status':'PASS' if not errors else 'MISMATCH_LOCALIZATION_REQUIRED','pass':not errors,'checks':dict(counts),'assertion_N':sum(counts.values()),'error_N':len(errors),'errors':errors,'feature_endpoint_N':len(featuremap),'OOF_record_N':len(oof),'prediction_replay_N':prediction_checks,'saved_float_tolerance':{'abs':1e-8,'rel':1e-10},'independence':'No import from candidate feature builder, target builder, fitter, Path builder or State9 engine. Separate tuple/clock/segment/target/fold/rank/metric/bootstrap/baseline reconstruction. NumPy/Decimal are declared shared libraries.','full_kernel_reruns':0,'fits_rerun':0,'provider_requests':0,'protected_exposure':0,'limits':['Underlying raw provider pages remain runner-temporary; exact Close/U/source tokens in approved derived tables checked against runner raw/hash binding, not re-downloaded independently.','Finite M0 precision and historical bar-end availability limitations are inherited.','Date-cluster intervals have only the realized small Development date population.']}
 (R/'INDEPENDENT_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'assertion_N':report['assertion_N'],'error_N':len(errors),'first_errors':errors[:10],'kernel_reruns':0}))
if __name__=='__main__':main()
