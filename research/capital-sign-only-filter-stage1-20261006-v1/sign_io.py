"""Sign-only stage1 IO. Public aggregates and private row artifacts are separate."""
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import re
from pathlib import Path

CODE = Path(__file__).resolve().parent
REPO = CODE.parents[1]
WORK = Path(os.environ.get('ARK_SIGN_WORKSPACE', str(REPO.parent)))
OUT = REPO / 'docs/evidence/capital-sign-only-filter-stage1-20261006-v1'
PRIVATE = WORK / 'capital_sign_only_private'
REUSE = WORK / 'reuse_sign'
OLD = REUSE / 'capital_rneg_defense_private'
OLD_OUT = REPO / 'docs/evidence/capital-rneg-defense-reuse-20261006-v1'
SCORE = REUSE / 'score_authority'
SPLIT = REPO / 'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json'
RECIPES = ['SF_A_PRICE', 'SF_B_STATE', 'SF_C_SCORE', 'SF_D_UNION']
ALPHAS = ['0.05', '0.10', '0.20']
SIGN_FIELDS = {'entry_id', 'session', 'sign_status', 'y_neg', 'label_maturity', 'source_hash'}
PARAMS = dict(loss='log_loss', learning_rate=0.05, max_iter=100, max_leaf_nodes=7,
              max_depth=3, min_samples_leaf=20, l2_regularization=1.0, max_bins=255,
              categorical_features=None, early_stopping=False, warm_start=False,
              class_weight=None, random_state=57)

def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='microseconds')

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def rows(path):
    with gzip.open(path, 'rt') as f:
        return [json.loads(line) for line in f]

def save(path, value, exclusive=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w') as f:
        f.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n')

def gzsave(path, values, exclusive=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb' if exclusive else 'wb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', filename='', mtime=0) as z:
            for value in values:
                z.write((canonical(value)+'\n').encode())

def write_csv(path, values):
    fields = list(dict.fromkeys(k for r in values for k in r))
    with Path(path).open('w', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator='\n'); w.writeheader(); w.writerows(values)

def validate_sign(row):
    assert set(row) == SIGN_FIELDS, 'OUTCOME_VIEW_NOT_ALLOWLISTED'
    expected = {'NEGATIVE':1, 'POSITIVE':0, 'EXACT_ZERO':None, 'UNKNOWN':None}
    assert row['sign_status'] in expected and row['y_neg'] == expected[row['sign_status']]
    return row

class SignIndex:
    """Index identities without decoding future sign payloads in the fit driver."""
    def __init__(self, path):
        self.lines = {}; self.read_log = []
        with gzip.open(path, 'rt') as f:
            for line in f:
                key = re.search(r'"entry_id"\s*:\s*"([^"]+)"', line).group(1)
                assert key not in self.lines
                self.lines[key] = line

    def get(self, entry_id, before=None, purpose='evaluation'):
        row = validate_sign(json.loads(self.lines[entry_id]))
        if before is not None:
            assert row['session'] < before, 'CURRENT_OR_FUTURE_SIGN_PAYLOAD_READ'
        self.read_log.append({'entry_id':entry_id, 'before':before, 'purpose':purpose})
        return row

def sufficient(labels):
    return (len(labels)>=100 and len({r['session'] for r in labels})>=10
            and sum(r['y_neg']==0 for r in labels)>=20 and sum(r['y_neg']==1 for r in labels)>=20)

def training_payload(train, labels, nn, cc):
    # source_hash is provenance-only: within-sign magnitude changes alter it,
    # but never the model request. Maturity participates in the training mask.
    return {'numeric_order':nn, 'categorical_order':cc, 'parameters':PARAMS,
            'preprocessing':'native-train-only-0+indicators+standardization+UNKNOWN',
            'sample_weight':None, 'class_weight':None,
            'rows':[{'entry_id':r['entry_id'], 'session':r['session'],
                     'numeric':[r['numeric'][k] for k in nn],
                     'categorical':[r['categorical'][k] for k in cc],
                     'y_neg':labels[r['entry_id']]['y_neg'],
                     'label_maturity':labels[r['entry_id']]['label_maturity']} for r in train]}

def checkpoint(name, status, completed, unexecuted, counts, next_action, blockers=None):
    state = read(OUT/'CURRENT_STATE.json')
    state.update(exact_jst=now(), status=status, completed=completed, unexecuted=unexecuted,
                 counts_this_execution=counts, next_action=next_action, blockers=blockers or [])
    save(OUT/'CURRENT_STATE.json', state)
    event = {k:state[k] for k in ['exact_jst','status','completed','unexecuted','counts_this_execution','next_action','blockers']}
    event.update(checkpoint=name, basis_head=state['execution_basis_head'], basis_tree=state['execution_basis_tree'])
    with (OUT/'WORK_STATUS_LOG.jsonl').open('a') as f:f.write(canonical(event)+'\n')
