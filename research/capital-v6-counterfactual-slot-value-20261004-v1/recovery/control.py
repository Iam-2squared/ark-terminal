"""Append-only recovery records and publication transport. No replay or fitting."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib, json, sys

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT.parent
OUT = ROOT / 'docs/evidence/capital-v6-counterfactual-slot-value-20261004-v1'
STATE = WORK / 'v6_recovery_publication_state.json'
LOG = OUT / 'WORK_STATUS_LOG.jsonl'

def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')

def record(checkpoint, phase, current_state, completed, not_executed,
           result=None, blockers=None, next_policy=None, counts=None):
    remote = json.loads(STATE.read_text())
    original = json.loads((OUT / 'checkpoints/D7_V6_MAIN_REPLAY_START.json').read_text())
    count = dict(original['counts'])
    count['independent_replay'] = 0
    if counts:
        count.update(counts)
    models = json.loads((OUT / 'SLOT_FITS_FREEZE.json').read_text())['models']
    hashes = dict(original['hashes'])
    hashes['slot_models'] = models
    hashes['effective_U5_priority_amendment'] = sha(OUT / 'TEACHER_PRECOMMIT_U5_PRIORITY_AMENDMENT.json')
    hashes['score_action_freeze'] = sha(OUT / 'SCORE_ACTION_FREEZE.json')
    hashes['recovery_code'] = {p.name: sha(p) for p in Path(__file__).parent.glob('*.py')}
    policy = next_policy or ['Resume first incomplete checkpoint only; preserve all frozen artifacts']
    obj = {
        'exact_jst': now(), 'checkpoint': checkpoint, 'phase': phase,
        'repo': remote['repo'], 'branch': remote['branch'],
        'current_head': remote['head'], 'current_tree': remote['tree'],
        'latest_HEAD': remote['head'], 'latest_tree': remote['tree'],
        'recovery_basis_head': remote['initial_head'],
        'recovery_basis_tree': remote['initial_tree'],
        'last_complete_checkpoint': 'D6_SLOT_SCORE_ACTION_FREEZE',
        'first_incomplete_checkpoint': 'D7_V6_MAIN_REPLAY',
        'current_state': current_state,
        'completed': completed, 'not_executed': not_executed,
        'result_so_far': result or {}, 'blockers': blockers or [],
        'next_policy': policy, 'next1_to_3': policy[:3],
        'do_not': original['do_not'] + [
            'No D0-D6 rerun, teacher regeneration or Slot model refit',
            'No duplicated Main replay; retain D3 Block07 failure history',
            'No U5 priority amendment change'],
        'counts': count, 'existing_main_replay_count': count['main_replay'],
        'existing_independent_replay_count': count['independent_replay'],
        'existing_fit_count': count['slot_fit'], 'frozen_hashes': hashes,
        'exposure': original['exposure'], 'safety': original['safety'],
        'actual_result_commit_tree': 'Append-only postcommit actual GET receipt; no future SHA'
    }
    save(OUT / 'checkpoints' / f'{checkpoint}_{phase}.json', obj)
    with LOG.open('a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
    return obj

def payload():
    remote = json.loads(STATE.read_text())
    known = remote['known_sha256']
    prefix = bytes.fromhex(remote['log_prefix_hex'])
    data = LOG.read_bytes()
    assert data.startswith(prefix), 'APPEND_ONLY_STATUS_PREFIX_CHANGED'
    entries = []
    for top in [ROOT / 'research/capital-v6-counterfactual-slot-value-20261004-v1', OUT]:
        for p in sorted(top.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts:
                continue
            path = p.relative_to(ROOT).as_posix()
            digest = sha(p)
            if path in known:
                if known[path] == digest:
                    continue
                assert p == LOG, ('FROZEN_ARTIFACT_CHANGED', path)
                continue
            entries.append({'path': path, 'mode': '100644', 'type': 'blob',
                            'content': p.read_text(encoding='utf-8')})
    result = {'entries': entries, 'append_log': data[len(prefix):].decode(),
              'head': remote['head'], 'tree': remote['tree'],
              'hashes': {e['path']: sha(ROOT / e['path']) for e in entries},
              'status_sha256': hashlib.sha256(data).hexdigest()}
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    assert sys.argv[1] == 'payload'
    payload()
