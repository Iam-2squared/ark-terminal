"""Independent four-head current inference and original T_h reconstruction.

Raw model/reference/feature bytes are shared frozen inputs. NumPy float64 matrix
multiply and stable exp(-logaddexp(0,-logit)) are explicitly shared
contract-defined primitives. Feature mapping, training identity selection,
original reference lookup, causal checks and strict-less ranks are implemented
here without importing any Primary or score-certification implementation.
"""

from pathlib import Path
import gzip
import hashlib
import json
import math
import numpy as np

ROOT = Path('/workspace/scratch/f3d0aa747c89')
INPUT = ROOT / 'r1_work/inputs'
OUT = ROOT / 'r1_work/independent'
HEADS = ('pP', 'MOVE_U2', 'MOVE_U3', 'MRET')


def rows(path):
    with gzip.open(path, 'rt') as reader:
        return [json.loads(line) for line in reader]


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open('x') as writer:
        json.dump(data, writer, indent=2, sort_keys=True, allow_nan=False)
        writer.write('\n')


def gzsave(path, data):
    payload = ''.join(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'
                      for row in data)
    with Path(path).open('xb') as writer:
        writer.write(gzip.compress(payload.encode(), mtime=0))


def probability(raw_rows, model):
    """Independent row mapper, same explicitly permitted NumPy primitive."""
    prep = model['preprocessing']
    feature_rows = []
    n = len(prep['numeric_fields'])
    means, scales = prep['numeric_mean'], prep['numeric_scale']
    for row in raw_rows:
        raw = [row['numeric'][key] for key in prep['numeric_fields']]
        vector = [(0. if value is None else float(value)) for value in raw]
        vector.extend(float(value is None) for value in raw)
        assert len(vector) == 2 * n == len(means) == len(scales)
        vector = [(value - mean) / scale for value, mean, scale in zip(vector, means, scales)]
        for field in prep['categorical_fields']:
            vocabulary = prep['categorical_train_vocab'][field]
            value = row['categorical'][field]
            if value not in vocabulary:
                value = '__UNKNOWN__'
            vector.extend(1. if value == category else 0. for category in vocabulary)
        assert len(vector) == len(model['coef'])
        assert all(math.isfinite(v) for v in vector)
        feature_rows.append(vector)
    matrix = np.asarray(feature_rows, dtype=np.float64)
    coefficients = np.asarray(model['coef'], dtype=np.float64)
    logits = matrix @ coefficients + model['intercept']
    probabilities = np.exp(-np.logaddexp(0, -logits))
    assert np.isfinite(probabilities).all()
    return [float(p) for p in probabilities]


def rank(score, scores):
    assert math.isfinite(score) and scores and all(math.isfinite(v) for v in scores)
    less = sum(v < score for v in scores)
    numerator, denominator = 1 + less, len(scores) + 1
    return {'score': score, 'rank_numerator': numerator, 'rank_denominator': denominator,
            'less_count': less, 'reference_N': len(scores),
            'LOW': 2 * numerator < denominator, 'HIGH': 2 * numerator >= denominator}


def model_files(block):
    return {
        'pP': INPUT / 'v8r1/inputs/movement/models' / f'MOVE_P_BLOCK_{block:02d}.json',
        'MOVE_U2': INPUT / 'quality/private/models' / f'MOVE_U2_BLOCK_{block:02d}.json',
        'MOVE_U3': INPUT / 'quality/private/models' / f'MOVE_U3_BLOCK_{block:02d}.json',
        'MRET': INPUT / 'mret/private/models' / f'MRET_BLOCK_{block:02d}.json',
    }


def certify():
    OUT.mkdir(parents=True, exist_ok=True)
    assert (ROOT / 'r1_work/R2_ACTUAL_GET_RECEIPT.json').exists()
    save(OUT / 'FOUR_HEAD_INFERENCE_CLAIM.json', {
        'purpose': 'INDEPENDENT_PRE_MAIN_CAUSAL_INFERENCE',
        'new_fit': 0, 'market_replays': 0, 'score_pnl_joins': 0,
        'primary_implementation_import_N': 0,
        'code_sha256': sha(__file__),
        'shared_primitives': ['NumPy float64 matrix @ vector', 'NumPy exp(-logaddexp(0,-logit))'],
    })
    raw_path = INPUT / 'v8r1/inputs/movement/RUNTIME_CAUSAL.jsonl.gz'
    raw_rows = rows(raw_path)
    raw = {row['entry_id']: row for row in raw_rows}
    assert len(raw) == len(raw_rows)
    native = rows(INPUT / 'v5_source/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
    expected_current = {row['entry_id']: row for row in rows(
        ROOT / 'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz')}
    expected_refs = {(r['head'], r['block']): r for r in read(
        ROOT / 'r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json')}
    split = read(INPUT / 'v5_source/repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')
    ref_sources = {
        'pP': (rows(INPUT / 'v8r1/private/TRAIN_MAPPED_SCORES.jsonl.gz'), 'pP'),
        'MOVE_U2': (rows(INPUT / 'v9/private/QUALITY_TRAIN_SCORE_TABLE.jsonl.gz'), 'q2'),
        'MOVE_U3': (rows(INPUT / 'v9/private/QUALITY_TRAIN_SCORE_TABLE.jsonl.gz'), 'q3'),
        'MRET': (rows(INPUT / 'mret/private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz'), 'mP'),
    }
    for row in raw_rows:
        minute = row['entry_minute']
        known = row['provenance']['max_known_minute']
        assert known is None or known <= minute
        known = row['movement_provenance']['current_max_source_minute']
        assert known is None or known < minute
        for field in ('prior5_calendar_dates', 'prior20_calendar_dates'):
            assert all(date < row['session'] for date in row['movement_provenance'][field])
    independent = {row['entry_id']: {'entry_id': row['entry_id'], 'block': row['block'],
                    'session': row['session'], 'entry_minute': row['entry_minute']} for row in native}
    refs, audits = [], []
    max_score_error, rank_mismatch = 0., 0
    for block in split['blocks']:
        number, train_dates, test_dates = block['block'], block['train'], block['test']
        assert max(train_dates) < min(test_dates) and not set(train_dates) & set(test_dates)
        test = [r for r in raw_rows if r['session'] in test_dates]
        for head, model_path in model_files(number).items():
            model = read(model_path)
            ids = model['train_entry_ids']
            assert len(ids) == len(set(ids)) == model['train_N'] > 0
            assert model['train_through'] == max(train_dates) and model['test_dates'] == test_dates
            train = [raw[entry_id] for entry_id in ids]
            assert all(row['session'] in train_dates and row['session'] < min(test_dates) for row in train)
            source_rows, score_field = ref_sources[head]
            originals = [r for r in source_rows if r['block'] == number]
            original_map = {r['entry_id']: r for r in originals}
            assert len(original_map) == len(originals) == len(ids)
            assert set(original_map) == set(ids)
            original_scores = [original_map[entry_id][score_field] for entry_id in ids]
            train_inferred = probability(train, model)
            train_error = max(abs(a - b) for a, b in zip(train_inferred, original_scores))
            assert train_error <= 1e-12
            expected_ref = expected_refs[(head, number)]
            assert ids == expected_ref['train_identity_order']
            assert original_scores == expected_ref['scores']
            assert sha(model_path) == expected_ref['model_sha256']
            current_error = 0.
            predictions = probability(test, model)
            for row, score in zip(test, predictions):
                key = row['entry_id']
                state = rank(score, original_scores)
                expected = expected_current[key][head]
                error = abs(score - expected['score'])
                assert error <= 1e-12
                current_error = max(current_error, error)
                if any(state[k] != expected[k] for k in (
                        'rank_numerator', 'rank_denominator', 'less_count', 'reference_N', 'LOW', 'HIGH')):
                    rank_mismatch += 1
                independent[key][head] = state | {'model_sha256': sha(model_path)}
            ref = {'head': head, 'block': number, 'model_sha256': sha(model_path),
                   'train_identity_order': ids, 'scores': original_scores, 'reference_N': len(ids),
                   'ordered_reference': [{'entry_id': r['entry_id'], 'session': r['session'], 'score': score}
                                         for r, score in zip(train, original_scores)]}
            refs.append(ref)
            audits.append({'head': head, 'block': number, 'current_N': len(test),
                           'reference_N': len(ids), 'model_sha256': sha(model_path),
                           'train_score_max_delta': train_error, 'current_score_max_delta': current_error,
                           'train_identity_match': True, 'original_T_exact': True,
                           'strict_completed_past': True, 'duplicate_N': 0, 'denominator_change_N': 0})
            max_score_error = max(max_score_error, train_error, current_error)
    assert rank_mismatch == 0
    assert set(independent) == set(expected_current)
    current_rows = [independent[row['entry_id']] for row in native]
    gzsave(OUT / 'FOUR_HEAD_CURRENT.jsonl.gz', current_rows)
    save(OUT / 'FOUR_HEAD_REFERENCES.json', refs)
    audit = {
        'status': 'PASS', 'independent_current_N': len(current_rows), 'head_block_N': len(refs),
        'current_raw_features_sha256': sha(raw_path), 'strict_rank_mismatch_N': rank_mismatch,
        'max_score_delta': max_score_error, 'score_tolerance': 1e-12,
        'primary_implementation_import_N': 0, 'new_fit': 0, 'market_replays': 0, 'score_pnl_joins': 0,
        'saved_original_T_h_reconstructed': True,
        'shared_primitives': ['NumPy float64 matrix @ vector', 'NumPy exp(-logaddexp(0,-logit))'],
        'head_blocks': audits,
    }
    save(OUT / 'FOUR_HEAD_INFERENCE_AUDIT.json', audit)
    print(json.dumps({k: v for k, v in audit.items() if k != 'head_blocks'}))


if __name__ == '__main__':
    certify()
