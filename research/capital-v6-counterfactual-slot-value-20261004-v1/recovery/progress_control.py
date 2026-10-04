"""Current progress records; initial recovery anchors remain explicit provenance."""
import json
from pathlib import Path
from control import ROOT, WORK, OUT, STATE, LOG, now, save, sha

def record(checkpoint, phase, current_state, completed, not_executed, result=None,
           blockers=None, next_policy=None, counts=None, last_complete='D9_ECONOMIC_ASSET_CURVE',
           first_incomplete='D10_INDEPENDENT_AUDIT'):
    remote=json.loads(STATE.read_text())
    original=json.loads((OUT/'checkpoints/D7_V6_MAIN_REPLAY_START.json').read_text())
    count=dict(original['counts']);count.update(main_replay=1,independent_replay=0)
    if counts:
        count.update(counts)
    policy=next_policy or ['Continue first incomplete checkpoint under frozen contract']
    hashes=dict(original['hashes'])
    hashes['slot_models']=json.loads((OUT/'SLOT_FITS_FREEZE.json').read_text())['models']
    hashes['effective_U5_priority_amendment']=sha(OUT/'TEACHER_PRECOMMIT_U5_PRIORITY_AMENDMENT.json')
    hashes['recovery_code']={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')}
    obj={'exact_jst':now(),'checkpoint':checkpoint,'phase':phase,'repo':remote['repo'],'branch':remote['branch'],
        'current_head':remote['head'],'current_tree':remote['tree'],'latest_HEAD':remote['head'],'latest_tree':remote['tree'],
        'recovery_basis_head':remote['initial_head'],'recovery_basis_tree':remote['initial_tree'],
        'recovery_last_complete_checkpoint':'D6_SLOT_SCORE_ACTION_FREEZE',
        'recovery_first_incomplete_checkpoint':'D7_V6_MAIN_REPLAY',
        'last_complete_checkpoint':last_complete,'first_incomplete_checkpoint':first_incomplete,
        'current_state':current_state,'completed':completed,'not_executed':not_executed,'result_so_far':result or {},
        'blockers':blockers or [],'next_policy':policy,'next1_to_3':policy[:3],
        'next1':policy[0] if policy else None,'next2':policy[1] if len(policy)>1 else None,
        'next3':policy[2] if len(policy)>2 else None,'do_not':original['do_not']+[
            'No D0-D6 rerun, teacher regeneration or additional Slot fitting',
            'No second Main invocation, no U5 amendment change'],
        'counts':count,'existing_main_replay_count':count['main_replay'],
        'existing_independent_replay_count':count['independent_replay'],'existing_fit_count':count['slot_fit'],
        'frozen_hashes':hashes,'exposure':original['exposure'],'safety':original['safety'],
        'actual_result_commit_tree':'Append-only postcommit actual GET receipt; no future SHA'}
    save(OUT/'checkpoints'/f'{checkpoint}_{phase}.json',obj)
    with LOG.open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
    return obj
