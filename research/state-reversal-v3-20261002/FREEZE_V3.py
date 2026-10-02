from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib
R=Path(__file__).resolve().parent
def save(n,v):(R/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((R/'INHERITED_V2/FEATURE_SCHEMA_V2.json').read_text())
s['version']='V3_PREDICTIVE_LAYER_ONLY'
s['numeric_anatomy']=['anatomy_previous_dwell_'+str(i) for i in range(1,5)]+['anatomy_current_dwell','anatomy_bars_since_transition','anatomy_transition_count_15','anatomy_hold_count_15','anatomy_range_recency','anatomy_stop_recency','anatomy_fast_recency','anatomy_context_flips_15','anatomy_segment_age']
s['categorical_anatomy']=['anatomy_previous_primary_'+str(i) for i in range(1,5)]
s['models']={'R0':[],'R1':['formal_primary'],'R2':'numeric_state+categorical_state','R3':'R2+numeric_path+categorical_path','R4':'R2+numeric_anatomy+categorical_anatomy'}
save('FEATURE_SCHEMA_V3.json',s)
save('REVERSAL_TARGET_SCHEMA.json',{'horizon':30,'max_shift_bridge':60,
 'classes':{'CONTEXT_REVERSAL':['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30'],
 'MOTION_REVERSAL':['UP_MOVE_CONTINUE','DOWN_MOVE_REVERSAL','NON_DIRECTIONAL','NO_DECISION'],
 'NEXT_DISTINCT_PRIMARY':['RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP'],
 'NEXT_OBSERVED_PRIMARY':['RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP']},
 'context_families':{'UP_CONTEXT':['RISE','SHARP_RISE','PULLBACK','RISE_STOP'],'DOWN_CONTEXT':['DROP','SHARP_DROP','REBOUND','DROP_STOP'],'RANGE_CONTEXT':['RANGE']},
 'motion_families':{'UP_MOVE':['RISE','SHARP_RISE','REBOUND'],'DOWN_MOVE':['DROP','SHARP_DROP','PULLBACK'],'NON_DIRECTIONAL_OR_STOP':['RANGE','RISE_STOP','DROP_STOP']},
 'UP_confirm':{'genuine_TRANSITION':True,'destination':['RISE','SHARP_RISE'],'context_direction':1,'local_direction':1},
 'DOWN_confirm':{'genuine_TRANSITION':True,'destination':['DROP','SHARP_DROP','REBOUND','DROP_STOP'],'context_direction':-1},
 'NONE_context_is_NOT_DOWN_structure':True,'early_confirmed_event_available':True,'unavailable_excluded':True})
now=datetime.now(timezone(timedelta(hours=9))).isoformat()
names=['PREDICTIVENESS_V3_REVERSAL_CONTRACT.md','DATA_SCOPE_V3.json','V1_V2_EXPOSED_DEV.json','V3_NEW_DEV_EVAL.json','SPLIT_PLAN_V3.json','FEATURE_SCHEMA_V3.json','REVERSAL_TARGET_SCHEMA.json','BUDGET_START_V3.json','ACQUISITION_COMPLETION_PRECOMMIT.json']
assert not (R/'PREDICTIVENESS_V3_REVERSAL_PRECOMMIT.json').exists(),'PRECOMMIT_ALREADY_FIXED'
save('PREDICTIVENESS_V3_REVERSAL_PRECOMMIT.json',{'JST':now,'hashes':{n:sha(R/n) for n in names},'V3_reversal_labels_before_fix':0,'V3_fits_before_fix':0,'V1_V2_results_exposed':True,'result_driven_changes':0,'status':'V3_PRECOMMITTED'})
save('CHECKPOINTS/C2.json',{'JST':now,'parent_HEAD':None,'current_HEAD':None,'Contract_SHA256':sha(R/names[0]),'data_scope_SHA256':sha(R/'DATA_SCOPE_V3.json'),'status':'V3_CONTRACT_PRE_LABEL_FIXED','next_action':'causal anatomy generation, labels and train-only fit after Development export'})
print(json.dumps({'JST':now,'Contract_SHA256':sha(R/names[0]),'precommit_SHA256':sha(R/'PREDICTIVENESS_V3_REVERSAL_PRECOMMIT.json')}))
