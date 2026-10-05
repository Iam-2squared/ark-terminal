"""Compare every saved-Control candidate proposal without a second OFF replay.

Primary files are read as results only. No Primary implementation is imported.
The causal snapshots were captured during the one authorized OFF verification.
"""

from decimal import Decimal
from pathlib import Path
import argparse
import gzip
import hashlib
import json

from independent_engine import reconstruct_batch, intelligence_state


ROOT = Path('/workspace/scratch/f3d0aa747c89')
OUT = ROOT / 'r1_work/independent'


def rows(path):
    with gzip.open(path, 'rt') as reader:
        return [json.loads(line) for line in reader]


def read(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    with Path(path).open('x') as writer:
        json.dump(data, writer, indent=2, sort_keys=True, allow_nan=False)
        writer.write('\n')


def gzsave(path, data):
    payload = ''.join(json.dumps(row, separators=(',', ':'), sort_keys=True, allow_nan=False) + '\n'
                      for row in data)
    with Path(path).open('xb') as writer:
        writer.write(gzip.compress(payload.encode(), mtime=0))


def load_intelligence():
    current = rows(OUT / 'FOUR_HEAD_CURRENT.jsonl.gz')
    reference = {(r['head'], r['block']): r['scores'] for r in read(OUT / 'FOUR_HEAD_REFERENCES.json')}
    return {r['entry_id']: {head: {'score': r[head]['score'],
                                'training_scores': reference[(head, r['block'])]}
                           for head in ('pP', 'MOVE_U2', 'MOVE_U3', 'MRET')} for r in current}


MONEY = {'debit', 'lot_debit', 'equity_cap', 'desired', 'target_utilization',
         'batch_equity', 'batch_budget', 'budget_unspent', 'native_debit',
         'native_would_fund_debit'}
GATE_KEYS = ('slot_gate_action', 'slot_gate_reason', 'slot_admission_index',
             'pre_decision_occupancy', 'remaining_Aplus_probability',
             'remaining_Aplus_ge2_probability', 'expected_remaining_Aplus',
             'training_B_median', 'training_B_p75', 'arrival_bucket', 'training_block')


def same(key, independent, primary):
    if key in MONEY and independent is not None and primary is not None:
        return Decimal(str(independent)) == Decimal(str(primary))
    return independent == primary


def audit(proposal_path, policy_case_path=None):
    proposals = rows(proposal_path)
    tables = read(ROOT / 'r1_work/inputs/v5/repo/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/ARRIVAL_TABLE.json')
    intelligence = load_intelligence()
    reconstructed, mismatches, ids = [], [], []
    for proposal in proposals:
        snapshot = dict(proposal['snapshot'])
        snapshot.update(session=proposal['session'], minute=proposal['minute'], candidates=proposal['candidates'])
        independent = reconstruct_batch(snapshot, tables, intelligence)
        reconstructed.extend(independent['decisions'])
        ids.extend(d['entry_id'] for d in independent['decisions'])
        expected = {d['entry_id']: d for d in proposal['gate_decisions']}
        assert set(expected) == {d['entry_id'] for d in independent['decisions']}
        for decision in independent['decisions']:
            original = expected[decision['entry_id']]
            for key in GATE_KEYS:
                if not same(key, decision.get(key), original.get(key)):
                    mismatches.append({'entry_id': decision['entry_id'], 'field': key,
                                       'independent': decision.get(key), 'primary': original.get(key)})
            # Pre-gate rejection reasons are frozen V5 too; funded outcomes occur later.
            if decision.get('slot_gate_action') != 'ADMIT' and decision['reason'] != original.get('reason'):
                mismatches.append({'entry_id': decision['entry_id'], 'field': 'native_reject_reason',
                                   'independent': decision['reason'], 'primary': original.get('reason')})
        if independent['picked_ids'] != [a['entry_id'] for a in proposal['assigned']]:
            mismatches.append({'session': proposal['session'], 'minute': proposal['minute'], 'field': 'native_picked_order'})
        assert len(independent['assigned']) == len(proposal['assigned'])
        for assignment, original in zip(independent['assigned'], proposal['assigned']):
            for key in assignment:
                if not same(key, assignment[key], original.get(key)):
                    mismatches.append({'entry_id': assignment['entry_id'], 'field': 'allocation.' + key,
                                       'independent': assignment[key], 'primary': original.get(key)})
    assert len(ids) == len(set(ids)) == 1039
    policy_cases_N = 0
    if policy_case_path:
        cases = rows(policy_case_path)
        expected = {r['entry_id']: r for r in cases}
        assert len(expected) == len(cases) == 1039 and set(expected) == set(ids)
        for decision in reconstructed:
            row = expected[decision['entry_id']]
            if 'intelligence_available' not in decision:
                decision.update(intelligence_state(decision['entry_id'], intelligence))
            audit_keys = ('existing_open_N', 'prior_native_successful_BUY_proposal_N', 'actual_planned_slot',
                          'native_quantity', 'native_debit', 'native_would_fund_quantity',
                          'native_would_fund_debit', 'D_veto', 'intelligence_available')
            rank_keys = tuple(name + suffix for name in ('rP', 'r2', 'r3', 'rM')
                              for suffix in ('', '_numerator', '_denominator'))
            state_keys = tuple(prefix + name for name in ('P', '2', '3', 'M') for prefix in ('LOW_', 'HIGH_'))
            for key in audit_keys + rank_keys + state_keys:
                if key in row and not same(key, decision.get(key), row[key]):
                    mismatches.append({'entry_id': decision['entry_id'], 'field': 'policy.' + key,
                                       'independent': decision.get(key), 'primary': row[key]})
            policy_cases_N += 1
    gzsave(OUT / 'ALL_CANDIDATE_PROPOSALS_RECONSTRUCTED.jsonl.gz', reconstructed)
    report = {'status': 'PASS' if not mismatches else 'FAIL', 'candidate_N': len(ids),
              'snapshot_batch_N': len(proposals), 'policy_candidate_case_N': policy_cases_N,
              'mismatch_N': len(mismatches), 'mismatches': mismatches,
              'native_picked_order_exact': not any(m['field'] == 'native_picked_order' for m in mismatches),
              'money_quantity_domain': 'DECIMAL28_EXACT', 'score_rank_domain': 'STRICT_LESS_INTEGER',
              'primary_implementation_import_N': 0, 'OFF_replay_N': 0, 'candidate_market_replay_N': 0,
              'native_inference_audit': 'NATIVE_INFERENCE_AUDIT.json',
              'four_head_inference_audit': 'FOUR_HEAD_INFERENCE_AUDIT.json',
              'proposal_source_sha256': hashlib.sha256(Path(proposal_path).read_bytes()).hexdigest()}
    save(OUT / 'PRE_MAIN_ALL_CANDIDATE_AUDIT.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'mismatches'}))
    assert not mismatches


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('proposals')
    parser.add_argument('--policy-cases')
    args = parser.parse_args()
    audit(args.proposals, args.policy_cases)
