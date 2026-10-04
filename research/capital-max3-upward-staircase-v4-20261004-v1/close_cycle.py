"""Close once, pin checksums, forbid tuning and additional experimental runs."""
from common import *
def main():
 s=json.loads((OUT/'SELECTION_ANALYSIS.json').read_text());a=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text());can=json.loads((OUT/'CANARY_RESULTS.json').read_text());assert a['mismatch_N']==0 and can['failed_N']==0
 sources=json.loads((OUT/'SOURCE_HASHES.json').read_text());assert all(sha(SRC/k)==v for k,v in sources.items())
 pin=json.loads((OUT/'MODEL_PRECOMMIT_CODE_PIN.json').read_text());assert all(sha(CODE/k)==v for k,v in pin['research_code_hashes'].items())
 closure={'JST':now(),'status':'CLOSED_STOP','selection_status':s['selection_status'],'economic_status':s['economic_status'],'NORTH_STAR_HIT':s['NORTH_STAR_HIT'],'scoreboard':s['scoreboard'],'new_fit_count':8,'H3_H5_new_fit':0,'main_replay_count':1,'independent_replay_count':1,'Control_MAX4_MAX5_rank_replay_count':0,'retune':0,'orders':0,'main_merge':0,'force_push':0,'new_provider_requests':0,'Frozen_change_N':0,'code_hash_pin_unchanged':True,'independent_mismatch_N':0,'canary_failed_N':0,'source_hashes':sources,'model_hashes':json.loads((PRIVATE/'MODEL_HASHES.json').read_text()),'score_hash':sha(PRIVATE/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),'PAVA_config_hash':sha(OUT/'PAVA_CONFIG.json'),'Exposure':EXPOSURE,'protected_holdout_fresh_validation_OOS_prospective_opened':0,'Safety':SAFETY,'next_direction':'STOP; no same-cycle fit/replay/retune or adoption. User decides next cycle.'}
 save(OUT/'CAPITAL_V4_CLOSURE.json',closure);checkpoint('U10_CLOSURE','CAPITAL_V4_CLOSED_STOP',closure,closure['next_direction'])
 print(json.dumps({k:closure[k] for k in ('status','selection_status','economic_status','NORTH_STAR_HIT')}),flush=True)
if __name__=='__main__':main()
