"""Pure R6 decision-case projection from immutable OFF current snapshots.

No market state evolution, no execution-book reads, no model fitting/inference,
and no candidate replay. Its outputs are cases for the independent auditor.
"""
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
from primary_policy import CandidateView, direct_decision, ranks_from_record, rank_audit

D = Decimal

def build_cases(proposals, intelligence):
    cases = []
    for proposal in proposals:
        by_id = {decision['entry_id']: decision for decision in proposal['gate_decisions']}
        assigned = {item['entry_id']: item for item in proposal['assigned']}
        native_cash = D(proposal['snapshot']['cash'])
        success_N = 0
        success_prior = {}
        for key in proposal['picked_ids']:
            item = assigned[key]
            success_prior[key] = success_N
            if item['quantity'] >= 100 and D(item['debit']) <= native_cash:
                native_cash -= D(item['debit'])
                success_N += 1
        for stable, row in enumerate(proposal['candidates']):
            key = row['entry_id']
            native = by_id.get(key, {})
            allocation = assigned.get(key, {})
            native_admit = native.get('slot_gate_action') == 'ADMIT'
            ranks = ranks_from_record(intelligence.get(key))
            prior = success_prior.get(key, 0)
            planned = proposal['existing_open_N'] + prior + 1 if key in success_prior else None
            quantity = allocation.get('quantity', 0)
            debit = allocation.get('debit', '0')
            if native:
                native_reason = native.get('slot_gate_reason', native.get('reason'))
            elif proposal['minute'] >= 920:
                native_reason = 'CAPITAL_EOD_ENTRY_CUTOFF'
            elif not row['admission']:
                native_reason = 'UPWARD_BELOW_BASELINE'
            elif any(position['symbol'] == row['symbol']
                     for position in proposal['snapshot']['positions'].values()):
                native_reason = 'SYMBOL_ALREADY_OPEN'
            else:
                native_reason = 'SCORE_INPUT_UNKNOWN'
            view = CandidateView(key, row['rank'], native_admit,
                                 native_reason,
                                 native.get('slot_admission_index', 0), planned or 0,
                                 quantity, ranks, stable, native_admit and quantity >= 100)
            action = direct_decision(view)
            cases.append({'entry_id': key, 'session': proposal['session'], 'minute': proposal['minute'],
                          'native_gate_action': native.get('slot_gate_action', 'PRECHECK_REJECT'),
                          'native_reason': view.native_reason,
                          'native_slot_admission_index': native.get('slot_admission_index'),
                          'native_quantity': quantity, 'native_debit': debit,
                          'existing_open_N': proposal['existing_open_N'],
                          'prior_native_successful_BUY_proposal_N': prior if key in success_prior else None,
                          'actual_planned_slot': planned,
                          'intelligence': rank_audit(ranks),
                          'D_veto': action['veto'], 'D_reason': action['reason'],
                          'projection_scope': 'CURRENT_OFF_SNAPSHOT_ONLY_NO_STATE_EVOLUTION'})
    return cases

def materialize(off_proposals_path, current_intelligence_path, output_path):
    def rows(path):
        with gzip.open(path, 'rt') as handle:
            return [json.loads(line) for line in handle if line.strip()]
    proposals = rows(off_proposals_path)
    intelligence = {item['entry_id']: item for item in rows(current_intelligence_path)}
    cases = build_cases(proposals, intelligence)
    raw = b''.join((json.dumps(case, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
                   for case in cases)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('xb') as handle:
        handle.write(gzip.compress(raw, mtime=0))
    return {'candidate_N': len(cases), 'unique_candidate_N': len({case['entry_id'] for case in cases}),
            'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'compressed_sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
            'output': str(output_path), 'market_state_evolution': 0, 'candidate_replay': 0,
            'source': 'immutable OFF native current snapshots plus certified causal intelligence'}
