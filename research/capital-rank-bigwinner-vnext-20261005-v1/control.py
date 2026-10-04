"""Append-only, Rank-only research control. No execution or replay APIs."""
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT.parent
OUT = ROOT / 'docs/evidence/capital-rank-bigwinner-vnext-20261005-v1'
PRIVATE = WORK / 'rank_work/private'
INPUTS = WORK / 'rank_work/inputs'
SAFETY = {k: False for k in ('executionAllowed', 'brokerWriteAllowed',
    'excelOrderWriteAllowed', 'rssOrderFunctionAllowed', 'liveTradingAllowed',
    'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'transmitted', 'productionReady')}
COUNTS = {k: 0 for k in ('new_fits', 'capital_replay', 'control_replay',
    'MAX3_replay', 'MAX4_MAX5', 'winner_selector_entry_exit_fit', 'provider_request',
    'Claude', 'orders', 'main_merge', 'force_push', 'protected_fresh_holdout_validation_OOS_prospective_open')}

def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')

def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def gzsave(path, data):
    raw = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n' for r in data).encode()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(gzip.compress(raw, mtime=0))

def checkpoint(name, state, completed, results, next_policy, fits=0):
    basis = json.loads((WORK/'rank_work/latest_basis.json').read_text())
    save(OUT/'checkpoints'/f'{name}.json', {
        'checkpoint':name, 'exact_jst':now(), 'basis_HEAD':basis['head'],
        'basis_tree':basis['tree'], 'current_state':state, 'completed':completed,
        'results':results, 'next_policy':next_policy,
        'counts':{**COUNTS,'new_fits':fits}, 'Safety':SAFETY,
        'permanent_freeze':['Selector','Entry','EXIT'],
        'exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE; fresh/OOS claim prohibited'})
