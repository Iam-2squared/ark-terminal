"""Independent V5 current-head reconstruction from raw causal features.

Authority is frozen source preprocessing/staircase contract; no primary adapter,
policy, replay, or metrics module is imported. NumPy float64 matrix multiplication
and stable sigmoid are shared numerical primitives explicitly allowed by contract.
The independent vector assembly is row-major and the monotone projection is a
closed-form three-point equal-weight isotonic solution, not primary PAVA code.
"""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

NUMERIC_FIELDS = ('p2', 'p3', 'p5', 'm2', 'm3', 'm5', 'M', 'B',
                  'ML', 'capital_score', 'base2', 'base3', 'base5')
EXACT_FIELDS = ('rank', 'capacity_band', 'admission')
TOLERANCE = 1e-12
UNKNOWN = '__UNKNOWN__'


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compressed_json_rows(path: Path):
    with gzip.open(path, 'rt', encoding='utf-8') as reader:
        return [json.loads(line) for line in reader if line.strip()]


def vectorize_independently(rows, artifact):
    """Assemble frozen numeric/missing/category columns in one row-major loop."""
    prep = artifact['preprocessing']
    means = prep['numeric_mean']
    scales = prep['numeric_scale']
    keys = prep['numeric_fields']
    assert prep['constant_missing'] == 0 and prep['missing_indicators'] is True
    assert len(means) == len(scales) == 2 * len(keys)
    assert all(math.isfinite(x) and x > 0 for x in scales)
    result = []
    for row in rows:
        values = []
        missing = []
        for key in keys:
            value = row['numeric'][key]
            is_missing = value is None or (isinstance(value, float) and math.isnan(value))
            values.append(0.0 if is_missing else float(value))
            missing.append(float(is_missing))
        assert all(math.isfinite(value) for value in values)
        numeric = values + missing
        encoded = [(value - means[i]) / scales[i] for i, value in enumerate(numeric)]
        for key in prep['categorical_fields']:
            vocabulary = prep['categorical_train_vocab'][key]
            assert UNKNOWN in vocabulary
            observed = row['categorical'][key]
            category = observed if observed in vocabulary else UNKNOWN
            encoded.extend(float(category == item) for item in vocabulary)
        assert len(encoded) == len(artifact['coef'])
        result.append(encoded)
    matrix = np.array(result, dtype=np.float64)
    assert np.isfinite(matrix).all()
    return matrix


def native_probabilities(rows, artifact):
    """Contract primitives: IEEE754 double matrix dot, logaddexp, exp."""
    matrix = vectorize_independently(rows, artifact)
    weights = np.asarray(artifact['coef'], dtype=np.float64)
    logits = matrix @ weights + float(artifact['intercept'])
    result = np.exp(-np.logaddexp(0.0, -logits))
    assert np.isfinite(result).all() and ((result >= 0) & (result <= 1)).all()
    return result.tolist()


def decreasing_three_equal_weights(first, second, third):
    """Independent closed-form least-squares monotone projection for three heads."""
    assert all(math.isfinite(x) and 0 <= x <= 1 for x in (first, second, third))
    if first >= second >= third:
        return [first, second, third]
    if first < second:
        first_pair = (first + second) / 2
        if first_pair >= third:
            return [first_pair, first_pair, third]
    if second < third:
        last_pair = (second + third) / 2
        if first >= last_pair:
            return [first, last_pair, last_pair]
    combined = (first + second + third) / 3
    return [combined, combined, combined]


def native_materialize(raw, artifacts):
    monotone = decreasing_three_equal_weights(*raw)
    bases = [artifact['base_rate'] for artifact in artifacts]
    assert 1 >= bases[0] >= bases[1] >= bases[2] >= 0
    numerator = sum(monotone)
    denominator = sum(bases)
    assert denominator > 0
    relative = numerator / denominator
    if relative < 1:
        rank = 'C'
    elif relative < 1.5:
        rank = 'B'
    elif relative < 2:
        rank = 'A'
    else:
        rank = 'S'
    return {'p2': raw[0], 'p3': raw[1], 'p5': raw[2],
            'm2': monotone[0], 'm3': monotone[1], 'm5': monotone[2],
            'M': numerator, 'B': denominator, 'ML': relative,
            'capital_score': relative, 'base2': bases[0], 'base3': bases[1],
            'base5': bases[2], 'rank': rank, 'capacity_band': rank,
            'admission': relative >= 1}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def reconstruct(inputs, out):
    source_root = inputs / 'capital_staircase_v4_private'
    native_stream_path = source_root / 'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'
    causal_path = inputs / 'inputs/v3/capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz'
    saved = compressed_json_rows(native_stream_path)
    raw = compressed_json_rows(causal_path)
    raw_by_id = {row['entry_id']: row for row in raw}
    assert len(raw_by_id) == len(raw)
    assert len({row['entry_id'] for row in saved}) == len(saved)
    assert len(saved) == 1039
    models = {}
    model_audit = []
    for block in range(1, 9):
        for head in (2, 3, 5):
            model_path = source_root / 'models' / f'H{head}_BLOCK_{block:02d}.json'
            artifact = json.loads(model_path.read_text(encoding='utf-8'))
            assert artifact['head'] == ('CORE_P' if head == 5 else f'H{head}') and artifact['block'] == block
            ids = artifact['train_entry_ids']
            duplicates = len(ids) - len(set(ids))
            absent = [entry_id for entry_id in ids if entry_id not in raw_by_id]
            not_past = [entry_id for entry_id in ids if raw_by_id[entry_id]['session'] >= min(artifact['test_dates'])]
            past_end_bad = [entry_id for entry_id in ids if raw_by_id[entry_id]['session'] > artifact['train_through']]
            assert not duplicates and not absent and not not_past and not past_end_bad
            assert len(ids) == artifact['train_N'] > 0
            assert artifact['base_rate'] == artifact['train_positive_N'] / artifact['train_N']
            identities_sha = hashlib.sha256(json.dumps(ids, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
            record = {'block': block, 'head': f'H{head}', 'sha256': file_sha256(model_path),
                      'training_identity_N': len(ids), 'training_identity_order_sha256': identities_sha,
                      'training_duplicate_N': duplicates, 'training_raw_causal_missing_N': len(absent),
                      'nonpast_training_identity_N': len(not_past), 'training_after_train_through_N': len(past_end_bad),
                      'train_through': artifact['train_through'], 'test_dates': artifact['test_dates'],
                      'base_rate_exact_reconstructed_from_saved_counts': True,
                      'teacher_payload_reads': 0, 'new_fit': 0}
            model_audit.append(record)
            models[(block, head)] = (artifact, record)
    fields = {key: {'N': 0, 'maximum_absolute_error': 0.0, 'mismatch_N': 0, 'argmax_entry_id': None}
              for key in NUMERIC_FIELDS}
    exact = {key: {'N': 0, 'mismatch_N': 0} for key in EXACT_FIELDS}
    errors = []
    reconstructed = {}
    raw_field_mismatch = Counter()
    raw_match_N = 0
    model_stream_hash_mismatch_N = 0
    score_test_date_mismatch_N = 0
    current_raw_missing_N = 0
    for block in range(1, 9):
        members = [row for row in saved if row['block'] == block]
        native_raw = []
        for row in members:
            identity = row['entry_id']
            if identity not in raw_by_id:
                current_raw_missing_N += 1
                raise AssertionError(f'CURRENT_CAUSAL_MISSING:{identity}')
            source = raw_by_id[identity]
            mismatch = [key for key in source if source[key] != row[key]]
            if mismatch:
                for key in mismatch:
                    raw_field_mismatch[key] += 1
                errors.append({'entry_id': identity, 'raw_fields': mismatch})
            else:
                raw_match_N += 1
            assert source['provenance']['max_known_minute'] <= source['entry_minute']
            native_raw.append(source)
        artifacts = [models[(block, head)][0] for head in (2, 3, 5)]
        probabilities = [native_probabilities(native_raw, artifact) for artifact in artifacts]
        for row_index, reference in enumerate(members):
            identity = reference['entry_id']
            prediction = [values[row_index] for values in probabilities]
            result = dict(raw_by_id[identity])
            result.update(native_materialize(prediction, artifacts))
            result['block'] = block
            for head in (2, 3, 5):
                hash_record = models[(block, head)][1]
                result[f'H{head}_hash'] = hash_record['sha256']
                model_stream_hash_mismatch_N += reference[f'H{head}_hash'] != hash_record['sha256']
                score_test_date_mismatch_N += reference['session'] not in models[(block, head)][0]['test_dates']
            for key in NUMERIC_FIELDS:
                assert math.isfinite(float(reference[key])) and math.isfinite(float(result[key]))
                difference = abs(result[key] - reference[key])
                state = fields[key]
                state['N'] += 1
                if difference > state['maximum_absolute_error']:
                    state['maximum_absolute_error'] = difference
                    state['argmax_entry_id'] = identity
                if difference > TOLERANCE:
                    state['mismatch_N'] += 1
                    errors.append({'entry_id': identity, 'field': key, 'reference': reference[key], 'independent': result[key], 'absolute_error': difference})
            for key in EXACT_FIELDS:
                exact[key]['N'] += 1
                if result[key] != reference[key]:
                    exact[key]['mismatch_N'] += 1
                    errors.append({'entry_id': identity, 'field': key, 'reference': reference[key], 'independent': result[key]})
            reconstructed[identity] = result
    out.mkdir(parents=True, exist_ok=True)
    reconstructed_path = out / 'NATIVE_RECONSTRUCTED_CURRENT.jsonl.gz'
    with reconstructed_path.open('wb') as rawfile:
        with gzip.GzipFile(fileobj=rawfile, mode='wb', mtime=0, filename='') as writer:
            for source in saved:
                writer.write((json.dumps(reconstructed[source['entry_id']], sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode())
    code_path = Path(__file__)
    syntax = ast.parse(code_path.read_text())
    imports = []
    for node in ast.walk(syntax):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    forbidden = [name for name in imports if name and any(item in name for item in ('adapter', 'policy', 'replay', 'metrics', 'preprocessing', 'staircase'))]
    numeric_mismatch = sum(record['mismatch_N'] for record in fields.values())
    exact_mismatch = sum(record['mismatch_N'] for record in exact.values())
    mismatch = numeric_mismatch + exact_mismatch + sum(raw_field_mismatch.values()) + model_stream_hash_mismatch_N + score_test_date_mismatch_N + current_raw_missing_N
    report = {'schema': 'ARK_R1_NATIVE_CURRENT_INDEPENDENT_V1', 'status': 'PASS' if mismatch == 0 and not forbidden else 'FAIL',
              'UTC': datetime.now(timezone.utc).isoformat(), 'tolerance': TOLERANCE,
              'current_reference_N': len(saved), 'raw_causal_N': len(raw), 'current_reconstructed_N': len(reconstructed),
              'current_raw_causal_matched_N': raw_match_N, 'current_raw_causal_missing_N': current_raw_missing_N,
              'current_raw_field_mismatch_counts': dict(raw_field_mismatch),
              'score_test_date_mismatch_N': score_test_date_mismatch_N,
              'model_stream_hash_mismatch_N': model_stream_hash_mismatch_N,
              'numeric_fields': fields, 'exact_fields': exact, 'mismatch_N': mismatch,
              'frozen_models': model_audit, 'model_N': len(model_audit),
              'imports': imports, 'primary_adapter_policy_replay_metrics_import_N': len(forbidden),
              'shared_primitives': ['NumPy IEEE754 float64 matrix multiplication', 'NumPy logaddexp and exp stable sigmoid'],
              'independent_implementations': ['row-major causal feature vector assembly', 'closed-form three-point decreasing equal-weight isotonic solution', 'base-rate and native ML/rank/admission materialization'],
              'limitations': ['Base rates validated from frozen artifact count fields; teacher labels were not read.',
                              'Raw causal feature source and frozen model bytes are common evidence dependencies; implementations are separately assembled.'],
              'new_fit': 0, 'market_replay': 0, 'performance_PnL_cross_tab': 0, 'teacher_payload_reads': 0,
              'source_hashes': {'score_stream': file_sha256(native_stream_path), 'raw_causal': file_sha256(causal_path), 'independent_code': file_sha256(code_path)},
              'output_hash': file_sha256(reconstructed_path), 'errors': errors}
    write_json(out / 'NATIVE_INFERENCE_AUDIT.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, default=Path('r1_work/inputs/v5_source'))
    parser.add_argument('--out', type=Path, default=Path('r1_work/independent'))
    arguments = parser.parse_args()
    report = reconstruct(arguments.inputs, arguments.out)
    print(json.dumps({'status': report['status'], 'N': report['current_reconstructed_N'],
                      'mismatch_N': report['mismatch_N'],
                      'maximum_absolute_error': max(record['maximum_absolute_error'] for record in report['numeric_fields'].values()),
                      'primary_import_N': report['primary_adapter_policy_replay_metrics_import_N']}, sort_keys=True))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)
