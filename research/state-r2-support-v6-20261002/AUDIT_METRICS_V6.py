"""Read-only independent row and cluster-multiplicity checker. Fit/draw0."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,hashlib,math
import numpy as np
from AUDIT_CORE_V6 import measure,quantile,C,scalar
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1';ERRORS=[];CHECKS=Counter();MULT={}
K=['dangerous_rate','DOWN_REVERSAL_Precision','DOWN_REVERSAL_Recall','DOWN_REVERSAL_F1','UP_CONTINUE_Precision','UP_CONTINUE_Recall','UP_CONTINUE_F1','balanced_accuracy','macro_F1','row_LL','date_equal_LL','Brier','ECE']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,name,key=''):
 CHECKS[name]+=1
 if not ok:ERRORS.append({'kind':name,'key':str(key)})
def near(a,b):return a is None and b is None or a is not None and b is not None and abs(float(a)-float(b))<=1e-8*(1+abs(float(a))+abs(float(b)))
def csvrows(n):return list(csv.DictReader((R/n).open()))
def loss(x,y):return -math.log(float(x[y]))
def mult(dates,draws):
 key=id(draws)
 if key not in MULT:
  counters=[Counter(v) for v in draws];MULT[key]=np.array([[c[d] for d in range(len(dates))] for c in counters],float)
 return MULT[key]
def cluster_replicates(rr,dates,draws):
 if not rr:return {}
 # Distinct logic: per-date observation reduction into flat contingency cells.
 lookup={d:i for i,d in enumerate(dates)};cells=np.zeros((len(dates),16));ld=np.zeros((len(dates),3));es=np.zeros((len(dates),20))
 for r in rr:
  d=lookup[r['date']];p=r['probabilities'];y=C.index(r['actual']);j=max(range(4),key=lambda k:p[k]);cells[d,y*4+j]+=1;ld[d,0]+=1;ld[d,1]+=loss(p,y);ld[d,2]+=sum((p[k]-int(k==y))**2 for k in range(4));b=min(int(p[j]*10),9);es[d,b]+=p[j];es[d,10+b]+=int(y==j)
 multipliers=mult(dates,draws);tables=(multipliers@cells).reshape((-1,4,4));support=tables.sum(2);pred=tables.sum(1);tp=np.diagonal(tables,axis1=1,axis2=2);rec=np.divide(tp,support,out=np.zeros_like(tp),where=support>0);prec=np.divide(tp,pred,out=np.zeros_like(tp),where=pred>0);f=np.divide(2*prec*rec,prec+rec,out=np.zeros_like(tp),where=prec+rec>0);s=multipliers@ld;means=np.divide(ld[:,1:],ld[:,0,None],out=np.zeros_like(ld[:,1:]),where=ld[:,0,None]>0);dm=multipliers@means;dn=multipliers@(ld[:,0]>0);bins=multipliers@es
 def div(n,d):return np.divide(n,d,out=np.full(n.shape,np.nan),where=d>0)
 out={'dangerous_rate':div(tables[:,1,0],pred[:,0]),'balanced_accuracy':div(rec.sum(1),(support>0).sum(1)),'macro_F1':f.mean(1),'row_LL':div(s[:,1],s[:,0]),'date_equal_LL':div(dm[:,0],dn),'Brier':div(s[:,2],s[:,0]),'ECE':div(np.abs(bins[:,:10]-bins[:,10:]).sum(1),s[:,0])}
 for k,c in enumerate(C):out.update({c+'_Precision':prec[:,k],c+'_Recall':rec[:,k],c+'_F1':f[:,k]})
 return out
def select(oo,control,model,cal,fold='ALL'):
 return [r for r in oo if r['control']==control and r['model']==model and r['calibrated']==cal and (fold=='ALL' or r['registered_fold']==fold)]
def main():
 core=json.loads((R/'INDEPENDENT_CORE_AUDIT_V6.json').read_text());check(core['status']=='PASS' and core['mismatch_N']==0,'independent_core_PASS')
 scope=json.loads((R/'FRESH_SCOPE_V6.json').read_text());selected=json.loads((R/'ACQUISITION/SELECTED_METADATA_SCOPE_V6.json').read_text());inputmanifest=json.loads((R/'FRESH_DATA_MANIFEST_V6.json').read_text());source=json.loads((R/'ACQUISITION/SOURCE_RECEIPTS.json').read_text());execution=json.loads((R/'ACQUISITION_EXECUTION_FREEZE_V6.json').read_text());exclusions={(p['date'],p['code']) for p in scope['B_exclusion_pairs']};blocked=set(scope['blocked_days']);historical=json.loads((R/'INVENTORY_PROVENANCE_V6.json').read_text());returned={(p['date'],p['code']) for p in historical['historical_current_or_dependency_raw_exclusion_pairs']}
 check(selected['minute_requests_before_selection']==selected['labels_before_selection']==0 and selected['scope_metadata_SHA256']==sha(R/'FRESH_SCOPE_V6.json'),'selection_before_minute_labels')
 check(len(selected['proposals'])<=452 and [p['retry_ordinal'] for p in selected['proposals']]==list(range(1,len(selected['proposals'])+1)),'finite_exact_selection_order')
 check([p['date']+'|'+p['security_id'] for p in selected['proposals'][:136]]==[p['date']+'|'+p['security_id'] for p in scope['A_ordered136']],'original136_order_unchanged')
 B=[p for p in selected['proposals'] if p['lane']=='B_NEW'];group=defaultdict(list)
 for p in B:group[p['date']].append(p)
 for d,pp in group.items():check(len(pp)<=4 and [p['acquisition_metadata_hash'] for p in pp]==sorted(p['acquisition_metadata_hash'] for p in pp),'metadata_first4_order',d)
 for p in inputmanifest['pairs']:
  key=(p['date'],p['code']);check(key not in returned and p['date'] not in blocked and p['previous'] not in blocked and p['date'] in scope['approved_minute_days'] and p['previous'] in scope['approved_minute_days'],'fresh_raw_partition_boundary',p['pair_id'])
  if p['lane']=='B_NEW':check(key not in exclusions and (p['previous'],p['code']) not in exclusions and len(p['factor_sources'])==2,'B_current_previous_fresh_exclusion',p['pair_id'])
  else:check(next(x for x in scope['A_ordered136'] if x['date']==p['date'] and x['security_id']==p['security_id'])['V6_minute_retry_authorized'],'A_fresh_retry_authorized',p['pair_id'])
  featurefile=R/p['feature_path']
  for row in map(json.loads,featurefile.open()):
   ptr=row['source_pointer']
   if ptr is not None:check(any(s['scope']['date']==p['date'] and s['scope'].get('code')==p['code'] and s.get('raw_response_SHA256')==ptr['response_SHA256'] for s in source if s['endpoint'].endswith('/minute')),'feature_response_provenance',row['row_key'])
 for s in source:check(s['scope']['date'] in scope['approved_minute_days'] and s['scope']['date'] not in blocked,'all_provider_requests_authorized',str(s['scope']))
 old=[{**r,'experiment':'V5','registered_fold':'V5:F'+str(r['fold'])} for r in map(json.loads,(V/'R1_R2_FRESH_OOF_V5.jsonl').open())];new=[{**r,'experiment':'V6','registered_fold':'V6:F'+str(r['fold'])} for r in map(json.loads,(R/'R1_R2_OOF_V6.jsonl').open())];sets={'V5_ONLY':old,'V6_ONLY':new,'V5_V6_POOLED':old+new};check(not {r['row_key'] for r in old}&{r['row_key'] for r in new},'pooled_V5_V6_unique_keys')
 pre=json.loads((R/'PREDICTIVENESS_V6_PRECOMMIT.json').read_text());vectors={}
 for pop,filename,seed in [('V6_ONLY','BOOTSTRAP_V6_ONLY_DATE_DRAWS_V6.json',pre['bootstrap_seed']),('V5_V6_POOLED','BOOTSTRAP_POOLED_DATE_DRAWS_V6.json',pre['pooled_bootstrap_seed'])]:
  v=json.loads((R/filename).read_text());ds=sorted({r['date'] for r in sets[pop]}) if new else [];check(v['dates']==ds and v['seed']==seed and len(v['draws'])==(1000 if ds else 0),'saved_bootstrap_identity_shape',pop);check(all(len(draw)==len(ds) and all(isinstance(i,int) and 0<=i<len(ds) for i in draw) for draw in v['draws']),'saved_bootstrap_indices_valid',pop);vectors[pop]=v
 vectors['V5_ONLY']={'dates':sorted({r['date'] for r in old}),'draws':[]};cache={};rep_cache={}
 for row in csvrows('ALL_METRICS_V6.csv'):
  pop=row['population'];rr=select(sets[pop],row['control'],row['model'],row['calibrated']=='True',row['fold']);s=measure(rr);key=(pop,row['control'],row['model'],row['calibrated']=='True',row['fold']);cache[key]=s
  for name,value in s.items():check(near(scalar(row.get(name)),value),'independent_point_'+name,key)
  vec=vectors[pop];rep=cluster_replicates(rr,vec['dates'],vec['draws']) if rr and vec['draws'] else {};rep_cache[key]=rep;info=len({r['date'] for r in rr})>=2 and bool(vec['draws'])
  check((row['CI_informative']=='True')==info,'single_date_CI_not_informative',key)
  for name in K:
   lo,hi,n=quantile(rep.get(name,[]),info);check(near(scalar(row.get(name+'_CI_low')),lo) and near(scalar(row.get(name+'_CI_high')),hi),'independent_metric_shared_vector_CI',str(key)+':'+name)
 allrows=csvrows('ALL_METRICS_V6.csv')
 for filename,predicate in [('R1_R2_HARD_METRICS_V6.csv',lambda r:r['control']=='REAL' and r['calibrated']=='False'),('V5_V6_POOLED_METRICS.csv',lambda r:r['population']=='V5_V6_POOLED'),('V6_ONLY_METRICS.csv',lambda r:r['population']=='V6_ONLY')]:check(csvrows(filename)==[r for r in allrows if predicate(r)],'required_metric_export_consistency',filename)
 allindex={(r['population'],r['control'],r['model'],r['calibrated'],r['fold']):r for r in allrows}
 for r in csvrows('CALIBRATION_METRICS_V6.csv'):
  original=allindex[(r['population'],r['control'],r['model'],r['calibrated'],r['fold'])];check(all(original[k]==v for k,v in r.items()),'probability_export_consistency')
 for row in csvrows('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V6.csv'):
  pop=row['population'];cal=row['calibrated']=='True';r1=select(sets[pop],'REAL','R1',cal);r2map={r['row_key']:r for r in select(sets[pop],'REAL','R2',cal)};kind=row['group_kind'];column={'fold':'registered_fold','date':'date','security':'security_id','current_primary':'current_primary'}.get(kind)
  aa=r1 if kind=='ALL' else [r for r in r1 if str(r[column])==row['group']];bb=[r2map[r['row_key']] for r in aa];a,b=measure(aa),measure(bb);vec=vectors[pop];info=len({r['date'] for r in aa})>=2 and bool(vec['draws']);date_order=vec['dates'];weights=[]
  def dangerous(rr):
   totals=defaultdict(lambda:[0,0])
   for r in rr:
    if r['predicted']=='UP_CONTINUE':totals[r['date']][1]+=1;totals[r['date']][0]+=int(r['actual']=='DOWN_REVERSAL')
   nm=np.array([totals[d][0] for d in date_order]);dn=np.array([totals[d][1] for d in date_order]);m=mult(date_order,vec['draws']);num=m@nm if len(m) else np.array([]);den=m@dn if len(m) else np.array([]);return np.divide(num,den,out=np.full(num.shape,np.nan),where=den>0)
  if row['model']=='R1_MINUS_R2':
   val=100*(a['dangerous_rate']-b['dangerous_rate']) if a['dangerous_rate'] is not None and b['dangerous_rate'] is not None else None;lo,hi,n=quantile(100*(dangerous(aa)-dangerous(bb)),info);check(near(scalar(row['improvement_pp']),val) and near(scalar(row['improvement_CI_low_pp']),lo) and near(scalar(row['improvement_CI_high_pp']),hi) and int(row['finite_bootstrap_N'])==n,'independent_dangerous_improvement_CI',str(row))
  else:
   s=a if row['model']=='R1' else b;rr=aa if row['model']=='R1' else bb;lo,hi,n=quantile(dangerous(rr),info);check(int(row['numerator'])==s['dangerous_numerator'] and int(row['denominator'])==s['dangerous_denominator'] and near(scalar(row['rate']),s['dangerous_rate']) and near(scalar(row['rate_CI_low']),lo) and near(scalar(row['rate_CI_high']),hi) and int(row['finite_bootstrap_N'])==n,'independent_dangerous_num_den_CI',row['group'])
 controls=[]
 for row in csvrows('TRUE_NULL_R2_V6.csv'):
  pop=row['population'];cal=row['calibrated']=='True';m={model:measure(select(sets[pop],control,model,cal)) for model in [] for control in []};real=measure(select(sets[pop],'REAL','R2',cal));null=measure(select(sets[pop],'TRUE_NULL','R2',cal));base=measure(select(sets[pop],'REAL','R1',cal));nb=measure(select(sets[pop],'TRUE_NULL','R1',cal));ready=real['N']>0;gain=base['date_equal_LL']-real['date_equal_LL'] if ready else None;ngain=nb['date_equal_LL']-null['date_equal_LL'] if ready else None;status='FAIL' if ready and (null['date_equal_LL']<=real['date_equal_LL']+1e-12 or gain>1e-12 and ngain>0 and ngain+1e-12>=.9*gain) else 'PASS' if ready else 'NOT_EVALUABLE';check(row['control_status']==status and near(scalar(row['REAL_date_equal_LL']),real.get('date_equal_LL')) and near(scalar(row['TRUE_NULL_date_equal_LL']),null.get('date_equal_LL')) and near(scalar(row['REAL_R1_to_R2_gain']),gain) and near(scalar(row['NULL_R1_to_R2_gain']),ngain),'independent_R2_control',pop);controls.append((pop,status))
 for row in csvrows('CALIBRATION_BUCKETS_V6.csv'):
  rr=select(sets[row['population']],row['control'],row['model'],row['calibrated']=='True');scores=[(max(r['probabilities']),r['predicted']==r['actual']) if row['kind']=='TOP_LABEL' else (r['probabilities'][1],r['actual']=='DOWN_REVERSAL') for r in rr];ii=[i for i,(p,a) in enumerate(scores) if min(int(p*10),9)==int(row['bucket'])];mean=sum(scores[i][0] for i in ii)/len(ii) if ii else None;actual=sum(scores[i][1] for i in ii)/len(ii) if ii else None;check(int(row['N'])==len(ii) and near(scalar(row['mean_predicted_probability']),mean) and near(scalar(row['actual_rate']),actual) and int(row['dates'])==len({rr[i]['date'] for i in ii}) and int(row['securities'])==len({rr[i]['security_id'] for i in ii}),'independent_reliability_buckets')
 positive={};con_pass={pop:True for pop in sets}
 for pop,oo in sets.items():
  r1=select(oo,'REAL','R1',False);r2={r['row_key']:r for r in select(oo,'REAL','R2',False)};positive[pop]={'dangerous_error_reduction':[r for r in r1 if r['actual']=='DOWN_REVERSAL' and r['predicted']=='UP_CONTINUE' and r2[r['row_key']]['predicted']!='UP_CONTINUE'],'class_correctness_gain':[r for r in r1 if r['predicted']!=r['actual'] and r2[r['row_key']]['predicted']==r['actual']]}
 for row in csvrows('STABILITY_AND_CONCENTRATION_V6.csv'):
  rr=positive[row['population']][row['gain']];col={'date':'date','security':'security_id','current_primary':'current_primary','fold':'registered_fold'}[row['group_kind']];counts=Counter(r[col] for r in rr);value=max(counts.values()) if row['group']=='MAXIMUM' and counts else 0 if row['group']=='MAXIMUM' else counts[row['group']];share=value/len(rr) if rr else None;check(int(row['positive_gross_N'])==len(rr) and int(row['group_N'])==value and near(scalar(row['share']),share),'independent_concentration');
  if row['gate_applies']=='True':con_pass[row['population']]=con_pass[row['population']] and share is not None and share<=.5+1e-12;check((row['PASS']=='True')==(share is not None and share<=.5+1e-12),'independent_concentration_gate')
 for row in csvrows('CONFUSION_MATRIX_V6.csv'):
  rr=select(sets[row['population']],'REAL',row['model'],False,row['fold']);check(int(row['N'])==sum(r['actual']==row['actual'] and r['predicted']==row['predicted'] for r in rr),'independent_confusion_matrix')
 gate=json.loads((R/'V6_GATE_MEASUREMENTS.json').read_text());pool=measure(select(sets['V5_V6_POOLED'],'REAL','R2',False));s6=measure(select(new,'REAL','R2',True));raw=measure(select(new,'REAL','R2',False));sample=pool.get('DOWN_REVERSAL_support',0)>=100 and pool.get('UP_CONTINUE_support',0)>=100 and s6['dates']>=1 and s6['N']>0;cal=s6['N']>0 and s6['date_equal_LL']<=1.05*raw['date_equal_LL']+1e-12 and s6['Brier']<=1.05*raw['Brier']+1e-12;direction=gate['dangerous_improvement_by_population']['V6_ONLY']['improvement_pp'];pooled=gate['dangerous_improvement_by_population']['V5_V6_POOLED'];hard=pooled['improvement_pp'] is not None and pooled['improvement_pp']>0 and pooled['improvement_CI_low_pp'] is not None and pooled['improvement_CI_low_pp']>0;control='FAIL' if any(p!='V5_ONLY' and s=='FAIL' for p,s in controls) else 'PASS' if all(s=='PASS' for p,s in controls if p!='V5_ONLY') else 'NOT_EVALUABLE'
 for k,v in [('sample_PASS',bool(sample)),('calibration_PASS',bool(cal)),('V6_only_direction_PASS',direction is not None and direction>=-1e-12),('pooled_dangerous_PASS',bool(hard)),('R2_TRUE_NULL',control),('concentration_PASS',con_pass['V6_ONLY'] and con_pass['V5_V6_POOLED'])]:check(gate[k]==v,'independent_final_measurement_gate',k)
 receipt={'status':'PASS' if not ERRORS else 'FAIL','mismatch_N':len(ERRORS),'errors':ERRORS[:100],'assertion_counts':dict(CHECKS),'core_receipt_SHA256':sha(R/'INDEPENDENT_CORE_AUDIT_V6.json'),'core_mismatch_N':core['mismatch_N'],'new_fits':0,'new_bootstrap_draws':0,'candidate_helper_imports':0,'V5_V6_pooled_duplicate_keys':0,'shared_calendar_date_cluster_audited':True,'V5_immutable_hashes_checked':True,'independent_logic':'separate row measures and per-date flat contingency/binned score reductions; stored-vector replay; no candidate imports, no solve, no bootstrap regeneration','direct_future_leakage_found':core['direct_future_leakage_found']}
 (R/'INDEPENDENT_AUDIT_V6.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['errors','assertion_counts']}))
 if ERRORS:raise RuntimeError('UNRECONCILED_V6_METRIC_MISMATCH')
if __name__=='__main__':main()
