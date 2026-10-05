"""Independent post-main comparison and exact metric certification.

Execution outputs are read from files. Imports are independent modules only.
No market replay is triggered here; each reconstruction is invoked separately
under the parent's durable claim/GET checked harness.
"""

from decimal import Decimal
from pathlib import Path
import argparse
import gzip
import hashlib
import json

from independent_metrics import evaluate, exact


ROOT = Path('/workspace/scratch/f3d0aa747c89')


def rows(path):
    with gzip.open(path, 'rt') as reader:
        return [json.loads(line, parse_float=Decimal) for line in reader]


def json_rows(path):
    with gzip.open(path, 'rt') as reader:
        return [json.loads(line) for line in reader]


def read(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    with Path(path).open('x') as writer:
        json.dump(data, writer, sort_keys=True, indent=2, allow_nan=False)
        writer.write('\n')


def load_run(directory):
    directory = Path(directory)
    return {name: json_rows(directory / (name.upper() + '.jsonl.gz'))
            for name in ('daily', 'decisions', 'trades', 'curves', 'intents', 'token_events', 'native_proposals')}


MONEY_KEYS = {'cash', 'equity', 'exposure', 'starting_cash', 'ending_cash', 'cash_min',
              'recycled_cash_used', 'buy_effective', 'sell_effective', 'debit', 'credit',
              'pnl', 'native_debit', 'native_would_fund_debit', 'lot_debit', 'desired',
              'equity_cap', 'batch_equity', 'batch_budget', 'budget_unspent',
              'target_utilization', 'cash_before', 'actual_debit'}
SCORE_KEYS = {'capital_score', 'ML', 'm2', 'm3', 'm5', 'pP_score', 'MOVE_U2_score',
              'MOVE_U3_score', 'MRET_score', 'net_return', 'daily_return',
              'diagnostic_daily_return', 'utilization'}


def equal(key, a, b):
    if a is None or b is None:
        return a is b
    if key in MONEY_KEYS:
        return Decimal(str(a)) == Decimal(str(b))
    if key in SCORE_KEYS:
        return abs(float(a) - float(b)) <= 1e-12
    return a == b


def compare_lists(kind, a, b, errors):
    if len(a) != len(b):
        errors.append({'artifact': kind, 'field': 'length', 'independent': len(a), 'primary': len(b)})
        return
    for index, (left, right) in enumerate(zip(a, b)):
        for key in set(left) | set(right):
            if not equal(key, left.get(key), right.get(key)):
                errors.append({'artifact': kind, 'index': index, 'entry_id': left.get('entry_id'),
                               'session': left.get('session'), 'minute': left.get('minute'), 'field': key,
                               'independent': left.get(key), 'primary': right.get(key)})


def compare_decisions(a, b, errors):
    assert len({r['entry_id'] for r in a}) == len(a)
    assert len({r['entry_id'] for r in b}) == len(b)
    original = {r['entry_id']: r for r in b}
    if set(original) != {r['entry_id'] for r in a}:
        errors.append({'artifact': 'decisions', 'field': 'candidate_identity_set'})
        return
    keys = ('quantity', 'reason', 'funded_slot', 'slot_gate_action', 'slot_gate_reason',
            'slot_admission_index', 'actual_planned_slot', 'existing_open_N',
            'prior_native_successful_BUY_proposal_N', 'native_quantity', 'native_debit',
            'native_would_fund_quantity', 'native_would_fund_debit', 'cash_before',
            'debit', 'recycled_cash_used',
            'first_pass_quantity', 'water_fill_lots', 'water_fill_rounds', 'budget_unspent',
            'lot_debit', 'equity_cap', 'desired', 'target_utilization', 'batch_equity',
            'batch_budget', 'primary_chain', 'held_before_batch', 'capital_score', 'ML',
            'm2', 'm3', 'm5', 'rank', 'admission', 'capacity_band')
    ranks = tuple(name + suffix for name in ('rP', 'r2', 'r3', 'rM')
                  for suffix in ('', '_numerator', '_denominator'))
    states = tuple(prefix + name for name in ('P', '2', '3', 'M') for prefix in ('LOW_', 'HIGH_'))
    for left in a:
        right = original[left['entry_id']]
        for key in keys:
            # Diagnostic optional fields on rejected/nonproposal cases are
            # compared whenever either implementation supplies their meaning.
            if key not in left and key not in right:
                continue
            if not equal(key, left.get(key), right.get(key)):
                errors.append({'artifact': 'decisions', 'entry_id': left['entry_id'], 'field': key,
                               'independent': left.get(key), 'primary': right.get(key)})
        # Primary serializes exact ranks on native proposals/selected recovery.
        # All rejected candidate scores/ranks already have the all1039 R6 audit.
        if 'intelligence' in right:
            projected = {name: {'numerator': left[name + '_numerator'],
                                'denominator': left[name + '_denominator'],
                                'LOW': left['LOW_' + name[1:]],
                                'HIGH': left['HIGH_' + name[1:]],
                                'available': left['intelligence_available']}
                         for name in ('rP', 'r2', 'r3', 'rM')}
            if projected != right['intelligence']:
                errors.append({'artifact': 'decisions', 'entry_id': left['entry_id'],
                               'field': 'intelligence', 'independent': projected,
                               'primary': right['intelligence']})
        for key in ('D_veto', 'recovery_funded', 'recovery_attempted'):
            right_value = (right.get('reason') == 'V5_SLOT3_UNANIMOUS_LOW_SHIELD_REJECT' if key == 'D_veto'
                           else right.get('recovery_attempt', False) if key == 'recovery_attempted'
                           else right.get(key, False))
            if bool(left.get(key, False)) != bool(right_value):
                errors.append({'artifact': 'decisions', 'entry_id': left['entry_id'], 'field': key,
                               'independent': bool(left.get(key, False)), 'primary': bool(right_value)})
        for key in ('recovery_failure_reason', 'recovery_singleton'):
            if left.get(key) != right.get(key):
                errors.append({'artifact': 'decisions', 'entry_id': left['entry_id'], 'field': key,
                               'independent': left.get(key), 'primary': right.get(key)})


def metrics_projection(result):
    if result['status'] != 'EVALUATED':
        return {'status': 'NOT_EVALUATED', 'eligible': False}
    cap, q = result['capital'], result['quality']
    return {'status': 'EVALUATED', 'session_ids': cap['session_ids'],
            'windows': [{'id': [w['start_session'], w['end_session']],
                         'growth': [exact(w['growth']).numerator, exact(w['growth']).denominator],
                         'maxdd': [exact(w['maxdd']).numerator, exact(w['maxdd']).denominator]}
                        for w in cap['windows']],
            'full_maxdd': [exact(cap['full_maxdd']).numerator, exact(cap['full_maxdd']).denominator],
            'statistics': {k: ([exact(v).numerator, exact(v).denominator] if isinstance(v, dict) else v)
                           for k, v in cap['statistics'].items()},
            'counts': q['count'], 'denominator': q['denominator'],
            'gross_loss': [exact(q['gross_loss']).numerator, exact(q['gross_loss']).denominator],
            'protected': q['protectedSlot12'], 'gates': result['gates'], 'eligible': result['eligible']}


def audit(arm, primary_path, independent_path, v5_path):
    primary, independent, control = load_run(primary_path), load_run(independent_path), load_run(v5_path)
    errors = []
    for name in ('daily', 'trades', 'curves', 'intents'):
        compare_lists(name, independent[name], primary[name], errors)
    compare_decisions(independent['decisions'], primary['decisions'], errors)
    # Token format can be normalized only by an explicit schema adapter. Until
    # the parent records such an adapter, no token differences are discarded.
    compare_lists('token_events', independent['token_events'], primary['token_events'], errors)
    teachers = rows(ROOT / 'r1_work/metrics/evaluation_only/TEACHERS_EVALUATION.jsonl.gz')
    evaluated = evaluate(independent, control, teachers, independent_mismatch=len(errors),
                         causal_canaries_pass=True)
    out = Path(independent_path)
    save(out / 'INDEPENDENT_EXACT_EVALUATION.json', evaluated)
    report = {'status': 'PASS' if not errors else 'FAIL', 'arm': arm,
              'mismatch_N': len(errors), 'mismatches': errors,
              'counts': {key: len(value) for key, value in independent.items()},
              'primary_implementation_import_N': 0, 'market_reconstruction_executed_here_N': 0,
              'money_quantity_comparison': 'DECIMAL_EXACT', 'economic_gates': 'EXACT_RATIONAL',
              'score_float_tolerance': 1e-12,
              'independent_evaluation_status': evaluated['status'],
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    save(out / 'INDEPENDENT_RECONSTRUCTION_AUDIT.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'mismatches'}))
    assert not errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('arm')
    parser.add_argument('primary')
    parser.add_argument('independent')
    parser.add_argument('control')
    args = parser.parse_args()
    audit(args.arm, args.primary, args.independent, args.control)
