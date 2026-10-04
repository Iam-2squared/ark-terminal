"""Only completed training score arrivals and historical confirmed tenure."""
from control import *
from runtime import BUCKETS,bucket,active_clock
from collections import defaultdict
def lower_median(x):
 assert x
 return max(1,sorted(x)[(len(x)-1)//2])
def precommit():
 obj={'exact_jst':now(),'arms':ARMS,'B1':{'name':ARMS[0],'rule':'pressure = fraction past training sessions with >= free_slots strictly later admitted candidates whose frozen r is greater than current r','horizon':920,'accept':'pressure < 0.5','exact_0_5':'RESERVE','occupancy_free_slots':{'0':3,'1':2,'2':1,'3':0}},'B2':{'name':ARMS[1],'only_difference':'strictly later admitted candidates before predicted release','group_keys':['Rank-native band','fixed Entry 30-minute bucket'],'buckets':BUCKETS,'teacher_projection':['entry_id','execution_status','release_minute'],'no_U5_U10_PnL_potential_group_or_input':True,'tenure_statistic':'integer active trading minutes; lower-middle empirical median index floor((N-1)/2), min1','minimum_cell_support':10,'backoff':'cell <10 -> same band all time; band <10 -> global admitted completed train','predicted_release':'current Entry active clock + predicted duration; cap15:20; lunch 11:30-12:30 excluded','held_future_release_used':False,'current_actual_future_release_used':False},'same_minute':'pP DESC; occupancy includes earlier picked rows; ACCEPT increments pre-quantity occupancy. At unchanged occupancy a reserved high rank implies reserve of lower ranks.','same_batch_cash_lot_failure':'frozen v7 allocation; no backfill, later topup, replacement','runtime_admission':'exact v7 band map 490; no changes','sizing':'immutable v7 allocation function exact; pP proportional weights','liquidity':'v7 diagnostic-only unchanged','replay_budget':{'B1':1,'B2':1},'new_model_fits':0,'teacher_regeneration':0,'future_test_arrival_used':False,'future_U5_U10_used':False,'integrity_float_tolerance':1e-12,'money_quantity_tolerance':0,'Preservation_gate':{'U5_funded':'>50','U10_funded':'>=26','below2':'<=0.38666667','admission_oracle_recovery':'>50/116','integrity':'0','independent_mismatch':'0'},'Capital_gate':{'Preservation':'PASS','rolling20_median':'>1.1991541915','rolling20_mean':'>1.1906460126','daily_geometric':'>0.01032420041'},'winner_priority':['2x hit N DESC','rolling20 median DESC','rolling20 mean DESC','daily geometric DESC','U5 DESC','U10 DESC','below2 ASC','MaxDD ASC','B1 exact tie'],'diagnostic_arm_priority':['U5 DESC','U10 DESC','below2 ASC','rolling20 median DESC','B1 tie'],'bottleneck':'Preservation PASS Capital FAIL -> CAPITAL_MONETIZATION_OR_SIZING; else max exclusive actionable miss. Exact tie Rank admission > MAX3 online > Capacity reserve > Cash sizing. No post-hoc closeness threshold.','code_sha256':{n:sha(CODE/n) for n in ('runtime.py','tables.py','replay.py','execution_bridge.py')},'immutable_sizing_sha256':sha(ROOT/'research/capital-v7-rank-native-max3-20261005-v1/runtime.py'),'immutable_execution_sha256':sha(ROOT/'research/capital-v5-max3-slot-intelligence-20261004-v1/execution.py'),'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False}
 save(OUT/'POLICY_B1_B2_PRECOMMIT.json',obj);checkpoint('D6_POLICY_B1_B2_PRECOMMIT','EXACT_TWO_POLICIES_PRECOMMITTED',['B1/B2 as instructed','0.5/support10/lower median/buckets','gate / tie / diagnostic / bottleneck rules'],{'arms':ARMS,'new_fits':0},'Build training-only orderstat and tenure tables; no alternative policies',{'primary_pP_diagnostic_solve':1})
def build():
 claim=read(OUT/'POLICY_B1_B2_PRECOMMIT.json')
 for n,v in claim['code_sha256'].items():assert sha(CODE/n)==v
 split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json');train=rows(PIN/'TRAIN_MAPPED_SCORES.jsonl.gz');allteacher=rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')
 # Outcome fields are not passed to the tenure builder.
 release={z['entry_id']:{k:z[k] for k in ('entry_id','execution_status','release_minute')} for z in allteacher};del allteacher
 pressure={};tenures={};summary=[]
 for block in split['blocks']:
  b=block['block'];rr=[r for r in train if r['block']==b];ids=set(r['entry_id'] for r in rr);model=read(INPUT/f'movement/models/MOVE_P_BLOCK_{b:02}.json')
  assert ids==set(model['train_entry_ids']) and len(ids)==len(rr);assert all(r['session'] in block['train'] and r['session']<min(block['test']) and r['entry_minute']<920 for r in rr)
  assert not set(model['test_entry_ids'])&ids if 'test_entry_ids' in model else True
  n=rr[0]['train_N'];sessions={d:[] for d in block['train']};cells=defaultdict(list);bands=defaultdict(list);global_values=[];support_ids=[]
  for r in rr:
   if r['band']=='P_BELOW':continue
   sessions[r['session']].append([r['entry_minute'],r['rank_units']]);z=release[r['entry_id']]
   if z['execution_status']!='COMPLETE' or z['release_minute'] is None:continue
   assert z['release_minute']>r['entry_minute']
   duration=max(1,active_clock(z['release_minute'])-active_clock(r['entry_minute']));cell=bucket(r['entry_minute']);cells[r['band'],cell].append(duration);bands[r['band']].append(duration);global_values.append(duration);support_ids.append(r['entry_id'])
  assert global_values
  table={'cells':{},'training_support_N':len(global_values),'global_median_active_duration':lower_median(global_values),'training_support_entry_ids':sorted(support_ids),'teacher_projection_fields':['entry_id','execution_status','release_minute']}
  for band in ('P_HIGH','P_MID','P_BASE'):
   table['cells'][band]={}
   for low,high in BUCKETS:
    k=f'{low}-{high}';x=cells[band,k];fallback='CELL'
    if len(x)<10:x=bands[band];fallback='BAND'
    if len(x)<10:x=global_values;fallback='GLOBAL'
    table['cells'][band][k]={'cell_support_N':len(cells[band,k]),'band_support_N':len(bands[band]),'used_support_N':len(x),'backoff':fallback,'median_active_duration':lower_median(x)}
  for day in sessions:sessions[day].sort()
  pressure[str(b)]={'train_N':n,'training_sessions':block['train'],'sessions':sessions,'train_entry_ids':sorted(ids),'test_sessions':block['test']};tenures[str(b)]=table
  summary.append({'block':b,'training_N':len(rr),'training_sessions_N':len(sessions),'admitted_training_N':sum(len(v) for v in sessions.values()),'tenure_support_N':len(global_values),'global_median_active_duration':table['global_median_active_duration']})
 save(OUT/'FUTURE_ORDERSTAT_PRESSURE_TABLE.json',pressure);save(OUT/'TENURE_LOOKUP_TABLE.json',tenures)
 save(OUT/'TABLE_SOURCE_LINEAGE.json',{'exact_jst':now(),'training_mapped_scores_sha256':sha(PIN/'TRAIN_MAPPED_SCORES.jsonl.gz'),'runtime_sha256':sha(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz'),'tenure_saved_teacher_source_sha256':sha(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz'),'orderstat_table_sha256':sha(OUT/'FUTURE_ORDERSTAT_PRESSURE_TABLE.json'),'tenure_table_sha256':sha(OUT/'TENURE_LOOKUP_TABLE.json'),'summary':summary,'completed_training_only':True,'test_future_use':0,'U5_U10_PnL_input_to_tenure':0,'fits':0,'teacher_regeneration':0})
 checkpoint('D7_ORDERSTAT_AND_TENURE_TABLE_FREEZE','TRAINING_ONLY_TABLES_FIXED',['exact score arrival lists','fixed lower-middle tenure with support10 backoff','8 past blocks'],summary,'40 causal canaries and independent pre-main policy audit',{'primary_pP_diagnostic_solve':1});print(json.dumps(summary))
if __name__=='__main__':
 import sys
 {'precommit':precommit,'build':build}[sys.argv[1]]()
