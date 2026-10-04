"""Only completed training score arrivals and historical confirmed tenure."""
from control import *
from runtime import BUCKETS,bucket,active_clock
from collections import defaultdict
def lower_median(x):
 assert x
 return max(1,sorted(x)[(len(x)-1)//2])
def build():
 claim=read(OUT/'B1_B2_SEMANTIC_FREEZE.json')['frozen_policy']
 assert sha(CODE/'runtime.py')==claim['code_sha256']['runtime.py']
 assert sha(ROOT/'research/capital-v8-capacity-aware-online-max3-20261005-v1/tables.py')==claim['code_sha256']['tables.py']
 split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json');train=rows(PIN/'TRAIN_MAPPED_SCORES.jsonl.gz');allteacher=rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')
 # Outcome fields are not passed to the tenure builder.
 release={z['entry_id']:{k:z.get(k) for k in ('entry_id','execution_status','release_minute')} for z in allteacher};del allteacher
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
 save(OUT/'B1_CAPACITY_PRESSURE_TABLE.json',pressure);save(OUT/'B2_TENURE_LOOKUP_TABLE.json',tenures)
 save(OUT/'B2_CAPACITY_PRESSURE_TABLE.json',{'pressure_source_sha256':sha(OUT/'B1_CAPACITY_PRESSURE_TABLE.json'),'tenure_source_sha256':sha(OUT/'B2_TENURE_LOOKUP_TABLE.json'),'sessions':pressure,'horizon':'Frozen B2 predicted release; counts strictly later < horizon, rank_units greater'})
 save(OUT/'TABLE_IDENTITY_AUDIT.json',{'exact_jst':now(),'training_mapped_scores_sha256':sha(PIN/'TRAIN_MAPPED_SCORES.jsonl.gz'),'runtime_sha256':sha(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz'),'tenure_saved_teacher_source_sha256':sha(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz'),'orderstat_table_sha256':sha(OUT/'B1_CAPACITY_PRESSURE_TABLE.json'),'tenure_table_sha256':sha(OUT/'B2_TENURE_LOOKUP_TABLE.json'),'summary':summary,'completed_training_only':True,'test_future_use':0,'U5_U10_PnL_input_to_tenure':0,'fits':0,'teacher_regeneration':0})
 checkpoint('R6_B1_B2_TABLE_BUILD','TRAINING_ONLY_TABLES_FIXED',['exact score arrival lists','fixed lower-middle tenure with support10 backoff','8 past blocks'],summary,'40 causal canaries and independent pre-main policy audit',{'primary_pP_diagnostic_solve':1});print(json.dumps(summary))
if __name__=='__main__':
 import sys
 build()
