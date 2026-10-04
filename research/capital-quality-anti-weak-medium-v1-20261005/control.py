"""Quality-only append-only control; no trading, allocation or provider APIs."""
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT.parent / 'quality_work'
OUT = ROOT / 'docs/evidence/capital-quality-anti-weak-medium-v1-20261005'
INPUTS = WORK / 'inputs'
PRIVATE = WORK / 'private'
BASE = 'def427ab1b8fdf464e675d0c8f299059902ff028'
SAFETY = {k: False for k in (
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
    'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
    'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
    'productionReady', 'orders', 'provider', 'claude', 'main_merge',
    'force_push', 'fresh_open', 'capital_replay', 'max3_replay', 'allocator_change')}
ZERO_COUNTS = {k: 0 for k in ('CORE_H2_fits', 'CORE_H3_fits', 'pP_fits',
    'CapitalReplay', 'MAX3Replay', 'allocator_changes', 'threshold_sweep',
    'feature_search', 'hyperparameter_search', 'extra_family', 'within_block_refit',
    'orders', 'main_merge', 'force_push', 'provider', 'Claude',
    'protected_holdout_fresh_validation_OOS_prospective_open')}

def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def rows(p):
    with gzip.open(p, 'rt') as f:
        return [json.loads(s) for s in f]

def save(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')

def gzsave(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n' for r in data).encode()
    with p.open('xb') as f:
        f.write(gzip.compress(raw, mtime=0))

def counts():
    return {**ZERO_COUNTS,
        'MOVE_U2_fits': len(list((PRIVATE/'models').glob('MOVE_U2_BLOCK_*.json'))),
        'MOVE_U3_fits': len(list((PRIVATE/'models').glob('MOVE_U3_BLOCK_*.json'))),
        'total_fits': len(list((PRIVATE/'models').glob('MOVE_U*_BLOCK_*.json')))}

def checkpoint(name, status, completed, result, next_policy):
    state = read(WORK/'latest_basis.json')
    save(OUT/'checkpoints'/f'{name}.json', {
        'checkpoint': name, 'exact_jst': now(), 'branch': state['branch'],
        'basis_HEAD': state['head'], 'basis_tree': state['tree'],
        'fixed_base': BASE, 'status': status, 'completed': completed,
        'result': result, 'next': next_policy, 'fit_counts': counts(),
        'Safety': SAFETY, 'exposure': 'ITERATIVE_DEVELOPMENT_EVIDENCE',
        'fresh_OOS_claim': False, 'productionReady': False})
