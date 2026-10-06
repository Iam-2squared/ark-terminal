"""Bounded RNEG cycle IO. All row-level inputs and artifacts remain private."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip, hashlib, json

REPO = Path(__file__).resolve().parents[2]
WORK = REPO.parent
NAME = 'capital-rneg-defense-reuse-20261006-v1'
CODE = Path(__file__).parent
OUT = REPO / 'docs/evidence' / NAME
PRIVATE = WORK / 'capital_rneg_defense_private'
DATA = WORK / 'authority_data'
Q = DATA / 'quality_original' / 'inputs'
HL = DATA / 'hl0' / 'capital_quality_v3_private'
SPECTRUM = DATA / 'spectrum' / 'Ark_Capital_Full_R_Spectrum_Anatomy_20261006_PRIVATE'
RESET = DATA / 'reset20' / 'Ark_Capital_V51_PRIVATE'
V5 = REPO / 'research/capital-v5-max3-slot-intelligence-20261004-v1'
SPLIT_PATH = REPO / 'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json'
ENTRY = REPO / 'research/persistent-watchlist-uptrend-first-entry-20261003-v2'
FREEZE = ENTRY / 'CORRECTED_LINEAGE_FAST_FREEZE_20261003'

def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def read(path): return json.loads(Path(path).read_text())
def rows(path):
    with gzip.open(path, 'rt') as f: return [json.loads(l) for l in f if l.strip()]

def save(path, obj, exclusive=False):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x' if exclusive else 'w') as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False); f.write('\n')

def gzsave(path, rr, exclusive=False):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    b = ('\n'.join(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False) for r in rr)+'\n').encode()
    with p.open('xb' if exclusive else 'wb') as f: f.write(gzip.compress(b, mtime=0))

def checkpoint(event, status, counts, completed, next_step, blockers=()):
    old = read(OUT/'CURRENT_STATE.json')
    s = {**old, 'exact_jst':now(), 'status':status, 'event':event,
         'counts_this_execution':counts, 'completed':completed, 'blockers':list(blockers),
         'next_action':next_step, 'source_exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE',
         'productionReady':False, 'selectedCapitalCandidate':None}
    save(OUT/'CURRENT_STATE.json', s)
    save(OUT/'checkpoints'/f'{event}.json', s, exclusive=True)

PARAMS = dict(loss='log_loss', learning_rate=0.05, max_iter=100,
              max_leaf_nodes=7, max_depth=3, min_samples_leaf=20,
              l2_regularization=1.0, max_bins=255, categorical_features=None,
              early_stopping=False, warm_start=False, class_weight=None, random_state=57)
ZERO_COUNTS = dict(HL0_refits=0, old_State_Entry_EXIT_fits=0, new_R_materialization=0,
                   new_Control_full_replays=0, new_provider_prices=0, protected_openings=0,
                   orders=0, main_merge=0, force_push=0, Claude=0,
                   hyperparameter_feature_seed_searches=0, full_data_final_fits=0)
