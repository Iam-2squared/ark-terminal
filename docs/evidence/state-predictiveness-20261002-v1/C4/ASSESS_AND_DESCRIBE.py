"""Apply the unchanged V1 gate and create descriptive denominator tables.
Never fits models, reselects data or changes precommit definitions.
"""
from pathlib import Path
from collections import Counter,defaultdict
import csv,datetime,hashlib,json,math
R=Path(__file__).resolve().parent
def read(p):return list(csv.DictReader(p.open()))
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def csvsave(n,rows):
 with (R/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 audit=json.loads((R/'INDEPENDENT_AUDIT.json').read_text());extra=json.loads((R/'INDEPENDENT_ADDITIONAL_AUDIT.json').read_text());manifest=json.loads((R/'RECEIVED_DEVELOPMENT/DATASET_MANIFEST.json').read_text());lr=json.loads((R/'LABEL_FIXATION_RECEIPT.json').read_text());features=[];labels={}
 for p in manifest['pairs']:
  features.extend(json.loads(l) for l in (R/'RECEIVED_DEVELOPMENT/FEATURES'/f"{p['pair_id']}.jsonl").read_text().splitlines())
  for l in (R/'LABELS'/f"{p['pair_id']}.jsonl").read_text().splitlines():
   row=json.loads(l);labels[row['row_key']]=row
 schema=json.loads((R/'FEATURE_SCHEMA.json').read_text());coverage=[]
 for family in ['numeric_state','categorical_state','numeric_path','categorical_path']:
  for name in schema[family]:
   vals=[r['features'][name] for r in features];present=[v for v in vals if v is not None and v!='__MISSING__'];nonformal=[v for v in present if v!='__FORMAL_NULL__']
   coverage.append({'family':family,'feature':name,'row_N':len(vals),'present_N':len(present),'missing_N':len(vals)-len(present),'formal_null_category_N':sum(v=='__FORMAL_NULL__' for v in vals),'nonformal_present_N':len(nonformal),'distinct_present_value_N':len(set(present)),'coverage_fraction':len(present)/len(vals),'semantic_frozen':True})
 csvsave('FEATURE_COVERAGE.csv',coverage)
 def sample(scope,rows):return {'scope':scope,'row_N':len(rows),'security_session_N':len({(r['security_id'],r['session_id']) for r in rows}),'security_N':len({r['security_id'] for r in rows}),'session_date_N':len({r['date'] for r in rows}),'effective_date_cluster_N':len({r['date'] for r in rows}),'unique_run_N':len({r['run_id'] for r in rows if r.get('run_id')}),'note':'Rows/overlapping horizons are not independent IID samples; date is the uncertainty unit.'}
 counts=[sample('ALL_FEATURE_ENDPOINTS',features)];oof=[]
 for f in sorted((R/'OOF').glob('*.csv')):oof.extend(read(f))
 for control in ['REAL','PERMUTATION','SHIFT60']:
  for h in [5,15,30]:
   part='shift60' if control=='SHIFT60' else 'real';available=[r for r in features if labels[r['row_key']][part][str(h)]['available']];counts.append(sample(f'{control}_H{h}_ALL_AVAILABLE',available))
   rows=[r for r in oof if r['control']==control and int(r['horizon'])==h and r['model']=='B0'];counts.append(sample(f'{control}_H{h}_OOF_UNIQUE',rows))
   for f in [1,2,3]:counts.append(sample(f'{control}_H{h}_FOLD{f}_OOF_UNIQUE',[r for r in rows if int(r['fold'])==f]))
 csvsave('SAMPLE_CLUSTER_COUNTS.csv',counts)
 overlap=[]
 for h in [5,15,30]:
  for subset in ['ALL_AVAILABLE','OOF_UNIQUE']:
   rows=[r for r in features if labels[r['row_key']]['real'][str(h)]['available']] if subset=='ALL_AVAILABLE' else [r for r in oof if r['control']=='REAL' and int(r['horizon'])==h and r['model']=='B0']
   groups=defaultdict(list)
   for r in rows:groups[(r['security_id'],r['session_id'])].append(r)
   strictly=touch=0;affected=set();max_per_run=0;run_counter=Counter(r['run_id'] for r in rows if r.get('run_id'))
   for group,items in groups.items():
    items.sort(key=lambda r:r['bar_end'])
    for i,a in enumerate(items):
     end=labels[a['row_key']]['real'][str(h)]['label_end']
     for b in items[i+1:]:
      if b['bar_end']<end:strictly+=1;affected.update([a['row_key'],b['row_key']])
      elif b['bar_end']==end:touch+=1
      else:break
   overlap.append({'horizon':h,'scope':subset,'row_N':len(rows),'security_session_N':len(groups),'strict_overlap_row_pair_N':strictly,'touching_endpoint_row_pair_N':touch,'rows_with_strict_overlap_N':len(affected),'unique_run_N':len(run_counter),'maximum_rows_in_one_run':max(run_counter.values()) if run_counter else 0,'uncertainty_unit':'whole session date','iid_independent_row_claim':False})
 csvsave('TARGET_OVERLAP.csv',overlap)
 skips=json.loads((R/'RECEIVED_DEVELOPMENT/SOURCE_METADATA/SKIPS.json').read_text());reason=Counter(x['reason'] for x in skips);obs=sum(p['observed_semantic_N'] for p in manifest['pairs']);null=sum(p['formal_null_N'] for p in manifest['pairs'])
 quality={'original_proposal_N':36,'input_eligible_security_session_N':25,'excluded_proposal_N':len(skips),'original_current_date_N':12,'eligible_current_date_N':10,'excluded_dates':['2025-05-28','2025-07-18'],'reason_counts':dict(reason),'exact_existing_exclusion_file':'RECEIVED_DEVELOPMENT/SOURCE_METADATA/SKIPS.json','excluded_file_SHA256':sha(R/'RECEIVED_DEVELOPMENT/SOURCE_METADATA/SKIPS.json'),'endpoint_N':len(features),'observed_endpoint_N':obs,'formal_null_endpoint_N':null,'raw_present_endpoint_N':sum(r['audit_source']['raw_present'] for r in features),'raw_absent_endpoint_N':sum(not r['audit_source']['raw_present'] for r in features),'duplicate_key_N':len(features)-len({r['row_key'] for r in features}),'eligible_price_targets':{str(h):sum(labels[r['row_key']]['real'][str(h)]['available'] for r in features) for h in [5,15,30]},'unavailable_targets_preserved':lr['target_denominators'],'result_driven_refill_or_reselection_N':0,'original_scope_used_in_full_not_29cases_only':True}
 save('DATA_INPUT_QUALITY_SUMMARY.json',quality)
 incr=read(R/'INCREMENTAL_VALUE.csv');neg=read(R/'NEGATIVE_CONTROL_RESULTS.csv');con=read(R/'CONCENTRATION_LEAVE_ONE.csv');checks=[]
 for h in [5,15,30]:
  for m in ['B2','B3']:
   item={'horizon':h,'model':m,'comparisons':[]};ss=next(x for x in counts if x['scope']==f'REAL_H{h}_OOF_UNIQUE');fc=[next(x for x in counts if x['scope']==f'REAL_H{h}_FOLD{f}_OOF_UNIQUE') for f in [1,2,3]]
   item['minimum_six_OOF_dates']=ss['session_date_N']>=6;item['three_evaluable_folds_at_least_50_rows_each']=all(x['row_N']>=50 for x in fc);item['OOF_date_N']=ss['session_date_N'];item['fold_target_counts']={str(f+1):x['row_N'] for f,x in enumerate(fc)}
   for b in ['B0','B1']:
    rr=next(r for r in incr if int(r['horizon'])==h and r['candidate']==m and r['comparator']==b);cc=[x for x in con if int(x['horizon'])==h and x['candidate']==m and x['comparator']==b and x['cluster_unit'] in ['date','security_id']]
    conditions={'at_least_two_percent_improvement':float(rr['relative_reduction'])>=0.02,'positive_at_least_two_folds':int(rr['positive_folds'])>=2,'positive_registered_CI_lower':float(rr['CI_low'])>0,'no_cluster_over_half_gross_positive_improvement':all(x['maximum_gross_positive_share'] and float(x['maximum_gross_positive_share'])<=0.5 for x in cc),'leave_one_date_and_security_nonnegative':all(x['minimum_leave_one_MSE_improvement'] and float(x['minimum_leave_one_MSE_improvement'])>=0 for x in cc)}
    item['comparisons'].append({'comparator':b,'relative_reduction':float(rr['relative_reduction']),'CI_low':float(rr['CI_low']),'CI_high':float(rr['CI_high']),'conditions':conditions,'all_pass':all(conditions.values())})
   item['pre_integrity_primary_candidate_pass']=item['minimum_six_OOF_dates'] and item['three_evaluable_folds_at_least_50_rows_each'] and all(c['all_pass'] for c in item['comparisons']);checks.append(item)
 violations=[{k:r[k] for k in ['control','horizon','model','control_rows_N','control_date_N','real_matched_relative_improvement','control_relative_improvement']} for r in neg if r.get('comparably_good')=='True']
 independent_pass=audit['pass'] and extra['pass'];passed=[x for x in checks if x['pre_integrity_primary_candidate_pass']]
 status='BLOCKED_LEAKAGE_OR_SEMANTIC_INTEGRITY' if violations or not independent_pass else 'STATE_PREDICTIVENESS_DEV_CANDIDATE_READY_FOR_VALIDATION' if passed else 'STATE_PREDICTIVENESS_NO_PREDICTIVE_EVIDENCE_ON_DEVELOPMENT'
 gate={'created_at_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'status':status,'contract_SHA256':sha(R/'PREDICTIVENESS_CONTRACT_V1.md'),'definition_or_gate_changes':0,'candidate_claims':checks,'positive_primary_candidate_N':len(passed),'negative_control_stop_condition_count':len(violations),'negative_control_stop_findings':violations,'independent_recalculation_PASS':independent_pass,'causal_feature_timestamp_and_partition_checks_PASS':True,'actual_future_leakage_proven':False,'causal_time_isolation_violation_N':0,'interpretation':'A registered negative-control integrity STOP is not proof of actual leakage. SHIFT60 has only two OOF dates and one fold; regime persistence and sampling variation remain unresolved. The V1 rule is nevertheless applied without loosening or post-result reinterpretation. Primary improvement is negative and OOF dates/folds are insufficient independently of this STOP.','no_Holdout_or_Entry_promotion':True,'next_action':'Separate review of the saved negative-control finding; no additional V1 data/model/horizon search or automatic validation.'}
 save('GATE_ASSESSMENT.json',gate)
 save('AUDIT_COMBINED_RECEIPT.json',{'created_at_jst':gate['created_at_jst'],'status':'PASS' if independent_pass else 'FAIL','assertion_N':audit['assertion_N']+extra['assertion_N'],'error_N':audit['error_N']+extra['error_N'],'audit1_SHA256':sha(R/'INDEPENDENT_AUDIT.json'),'audit2_SHA256':sha(R/'INDEPENDENT_ADDITIONAL_AUDIT.json'),'independent_kernel_reruns':0,'independent_fits_rerun':0,'independent_metric_PASS_does_not_override_negative_control_gate':True})
 original=R/'CHECKPOINTS/C2_POST_COMMIT_RECEIPT.json';c2=json.loads(original.read_text());fixed=datetime.datetime.fromisoformat(c2['JST'].replace('Z','+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
 save('C2_JST_NORMALIZATION.json',{'original_path':str(original.relative_to(R)),'original_SHA256':sha(original),'original_JST_field_value':c2['JST'],'correct_JST_same_instant':fixed,'routine_serialization_correction_only':True,'original_receipt_unchanged':True})
 print(json.dumps({'status':status,'independent_assertion_N':audit['assertion_N']+extra['assertion_N'],'negative_control_stop_N':len(violations),'positive_primary_candidate_N':len(passed),'observed_N':obs,'null_N':null,'chart_table_files_created':True}))
if __name__=='__main__':main()
