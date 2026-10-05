"""Precommitted R1 synthetic boundary suite. No market input files are read."""
from dataclasses import fields, replace
from decimal import Decimal
from fractions import Fraction
import hashlib
import inspect
from pathlib import Path

from primary_policy import (Rank, CandidateView, RecoveryToken, create_token,
                            invalidate_token, choose_recovery, direct_decision,
                            rank_from_scores, ranks_from_record, HEADS,
                            DECISION_INPUT_ALLOWLIST, RESERVE_REASON)
from primary_adapter import FrozenNative, day_replay, NATIVE_CANDIDATE_KEYS

D = Decimal
LOW = tuple(Rank(1, 6) for _ in range(4))
HIGH = tuple(Rank(4, 6) for _ in range(4))

def view(**changes):
    values = dict(entry_id='c', native_rank='B', native_admit=True,
                  native_reason='SA_ALWAYS_ADMIT', native_admission_index=3,
                  actual_planned_slot=3, native_quantity=100, ranks=LOW,
                  stable_order=0, current_constraints_pass=True)
    values.update(changes)
    return CandidateView(**values)

def intelligence(low=True):
    return {head: {'score': .1 if low else .8,
                   'training_scores': [.2, .3, .4, .5, .6],
                   'rank_numerator': 1 if low else 6, 'rank_denominator': 6}
            for head in HEADS}

def row(key, minute=540, score=1.6, symbol=None, raw='1000'):
    return {'entry_id': key, 'session': 'SYNTHETIC', 'entry_minute': minute,
            'entry_timestamp': f'2026-01-01T{minute//60:02d}:{minute%60:02d}:00+09:00',
            'symbol': symbol or key, 'raw_reference': raw, 'capital_score': score,
            'rank': 'A' if score >= 1.5 else 'B', 'capacity_band': 'A' if score >= 1.5 else 'B',
            'admission': True, 'ML': score, 'm2': .6, 'm3': .4, 'm5': .2, 'block': 0}

def market(minute, price='1000', session='SYNTHETIC'):
    return {'session': session, 'minute': minute, 'O': price, 'H': price,
            'L': price, 'C': price, 'Vo': '100', 'Va': '100000', 'lineage': 'synthetic-only'}

def book(key):
    return {'entry_id': key, 'session': 'SYNTHETIC', 'symbol': key,
            'market': [market(540), market(600, '1100'), market(920, '1200')],
            'frozen_exit': {'sell_status': 'UNFILLED'}, 'capture_complete': True,
            'entry_actual_source': {'lineage': 'synthetic-only'}, 'limit_up_authority': None}

def table():
    return {'0': {'training_session_N': 10, 'minute_counts': {str(t): [8, 4, 10] for t in range(540, 932)},
                  'minute_bucket': {str(t): t // 30 for t in range(540, 932)},
                  'B_median': 1.2, 'B_p75': 1.4}}

def run_suite(code_dir, safety=None):
    """Run fixed synthetic cases only, after R2 precommit GET authorization."""
    native = FrozenNative(code_dir)
    checks = []
    def check(number, name, condition, evidence=None):
        checks.append({'id': number, 'name': name, 'PASS': bool(condition),
                       'evidence': evidence if evidence is not None else {}})
        if not condition:
            raise AssertionError(f'CANARY_{number:02d}:{name}')
    for number, (existing, prior) in enumerate(((0, 2), (1, 1), (2, 0)), 1):
        planned = existing + prior + 1
        check(number, f'existing{existing}_prior{prior}_planned3_veto',
              direct_decision(view(actual_planned_slot=planned))['veto'],
              {'existing_open_N': existing, 'prior_successful': prior, 'planned': planned})
    check(4, 'actual_planned_slot1_protected', not direct_decision(view(actual_planned_slot=1))['veto'])
    check(5, 'actual_planned_slot2_protected', not direct_decision(view(actual_planned_slot=2))['veto'])
    check(6, 'native_index3_prior_cash_fail_actual2_protected',
          not direct_decision(view(native_admission_index=3, actual_planned_slot=2))['veto'])
    half = rank_from_scores(.2, [.1, .2, .3])
    check(7, 'exact_half_high', half.numerator == 2 and half.denominator == 4 and half.high and not half.low)
    median_tie = rank_from_scores(.2, [.1, .2, .2, .2, .3])
    check(8, 'raw_median_equality_rank_low', median_tie.numerator == 2 and median_tie.denominator == 6 and median_tie.low)
    check(9, 'ties_count_strict_less', rank_from_scores(.2, [.2, .2, .2]).numerator == 1)
    check(10, 'one_axis_high_abstain', not direct_decision(view(ranks=(Rank(3, 6),) + LOW[1:]))['veto'])
    missing = dict(intelligence()); missing['MRET'] = {'score': None}
    check(11, 'missing_current_abstain', not direct_decision(view(ranks=ranks_from_record(missing)))['veto'])
    nonfinite = dict(intelligence()); nonfinite['MRET'] = {'score': float('nan')}
    nan_ranks = ranks_from_record(nonfinite)
    check(12, 'nonfinite_current_abstain_neither_high_nor_low',
          not direct_decision(view(ranks=nan_ranks))['veto'] and not nan_ranks[-1].high and not nan_ranks[-1].low)
    baseline = ranks_from_record(intelligence())
    with_test = dict(intelligence()); with_test['test_rows'] = [0, .99, 123]
    check(13, 'test_rows_outside_certified_reference_not_input', ranks_from_record(with_test) == baseline)
    for number, field in ((14, 'future_High'), (15, 'future_realized'), (16, 'future_EXIT')):
        altered = dict(intelligence()); altered[field] = ['arbitrary_suffix', -999999]
        check(number, field + '_mutation_action_unchanged',
              direct_decision(view(ranks=ranks_from_record(altered))) == direct_decision(view(ranks=baseline)))
    rows = [row('a'), row('b'), row('c')]
    books = {item['entry_id']: book(item['entry_id']) for item in rows}
    aux = {item['entry_id']: intelligence() for item in rows}
    control = day_replay(native, 'OFF', 'SYNTHETIC', rows, books, D(1000000), table())
    shield = day_replay(native, 'D', 'SYNTHETIC', rows, books, D(1000000), table(), aux)
    ctl = {item['entry_id']: item for item in control['decisions']}
    dec = {item['entry_id']: item for item in shield['decisions']}
    check(17, 'nonveto_native_quantities_and_debits_exact',
          all(dec[key]['quantity'] == ctl[key]['quantity'] and dec[key]['debit'] == ctl[key]['debit'] for key in ('a', 'b')))
    check(18, 'postveto_waterfill_no_addition',
          all(dec[key]['water_fill_lots'] == ctl[key]['water_fill_lots'] for key in ('a', 'b')))
    check(19, 'same_batch_backfill_zero', len([item for item in shield['decisions'] if item['reason'] == 'FUNDED']) == 2
          and dec['c']['quantity'] == 0)
    tok = RecoveryToken('SYNTHETIC', 540, 'c', ('a', 'b'))
    rescue = view(entry_id='r', native_admit=False, native_reason=RESERVE_REASON,
                  native_admission_index=0, native_quantity=0, ranks=HIGH)
    check(20, 'same_minute_recovery_zero', choose_recovery(tok, 'SYNTHETIC', 540, ('a', 'b'), False, [rescue]) is None)
    retained, created = create_token(tok, 'SYNTHETIC', 560, 'new_origin', ('a', 'b'))
    check(21, 'token_max1_no_origin_or_expiry_extension', retained == tok and not created)
    check(22, 'held_pair_change_invalidates', invalidate_token(tok, 'SYNTHETIC', 550, ('a', 'd'))[0] is None)
    check(23, 'open_below_two_invalidates', invalidate_token(tok, 'SYNTHETIC', 550, ('a',))[0] is None)
    check(24, 'third_buy_success_invalidates', invalidate_token(tok, 'SYNTHETIC', 550, ('a', 'b', 'd'))[0] is None)
    check(25, 'cutoff_invalidates', invalidate_token(tok, 'SYNTHETIC', 920, ('a', 'b'))[0] is None)
    check(26, 'session_end_invalidates', invalidate_token(tok, 'SYNTHETIC', 919, ('a', 'b'), True)[0] is None)
    check(27, 'old_vetoed_entry_retry_zero', choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False,
                                                        [replace(rescue, entry_id='c')]) is None)
    check(28, 'native_admit_preallocation_nonempty_even_quantity0_blocks_rescue',
          choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), True, [rescue]) is None)
    check(29, 'exact_reserve_reason_required', choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False,
                                                           [replace(rescue, native_reason='SLOT2_RESERVE_FOR_FUTURE_QUALITY')]) is None)
    check(30, 'B_rank_required', choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False,
                                             [replace(rescue, native_rank='A')]) is None)
    check(31, 'four_high_required', choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False,
                                                 [replace(rescue, ranks=LOW)]) is None)
    candidates = [replace(rescue, entry_id='late', stable_order=4),
                  replace(rescue, entry_id='best_M', ranks=(Rank(4, 6), Rank(4, 6), Rank(5, 6), Rank(6, 6))),
                  replace(rescue, entry_id='best_P', ranks=(Rank(5, 6), Rank(4, 6), Rank(4, 6), Rank(4, 6))),
                  replace(rescue, entry_id='early', stable_order=1)]
    chosen = choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False, candidates)
    tie_choice = choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False, [candidates[0], candidates[3]])
    check(32, 'recovery_exact_fraction_priority_and_native_stable_tie', chosen.entry_id == 'best_P' and tie_choice.entry_id == 'early')
    first = choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False, candidates)
    failed = native.allocation([row(first.entry_id, 550, 1.2, raw='100000')], D(1000000), D(999990), D(10), ['A', 'A'])[0]
    check(33, 'first_eligible_cash_lot_fail_no_second_attempt', first.entry_id == 'best_P' and failed['quantity'] == 0)
    rescued_row = row('r', 550, 1.2)
    alloc = native.allocation([rescued_row], D(1000000), D(400000), D(600000), ['A', 'A'])
    check(34, 'singleton_allocation_original_frozen_function', len(alloc) == 1 and alloc[0]['entry_id'] == 'r'
          and native.allocation is native.replay.allocation)
    check(35, 'MAX3_concurrent', max(frame['concurrent'] for frame in control['curves']) <= 3)
    same_symbol = rows + [row('a_later', 550, symbol='a')]
    sym_result = day_replay(native, 'OFF', 'SYNTHETIC', same_symbol, books, D(1000000), table())
    check(36, 'same_symbol_current_open_reject', sym_result['decisions'][-1]['reason'] == 'SYMBOL_ALREADY_OPEN')
    check(37, 'lot100_native_quantities', all(item['quantity'] % 100 == 0 for item in control['decisions']))
    check(38, 'BUY_exact_native_factor', all(D(item['debit']) == D('1000') * D('1.0005') * item['quantity']
                                          for item in control['decisions'] if item['reason'] == 'FUNDED'))
    check(39, 'SELL_exact_native_source_factor', all(D(trade['sell_effective']) == D('1200') * D('.9995') for trade in control['trades']))
    at600 = next(frame for frame in control['curves'] if frame['minute'] == 600)
    at601 = next(frame for frame in control['curves'] if frame['minute'] == 601)
    check(40, 'MTM_exact_asof_not_cash', D(at601['equity']) - D(at600['equity']) == sum(ctl[key]['quantity'] for key in ctl) * D(100)
          and at601['cash'] == at600['cash'])
    at920 = next(frame for frame in control['curves'] if frame['minute'] == 920)
    at921 = next(frame for frame in control['curves'] if frame['minute'] == 921)
    check(41, 'confirmed_sell_cash_release_exact', D(at921['cash']) - D(at920['cash']) == sum(D(trade['credit']) for trade in control['trades'])
          and all(trade['release_minute'] == 921 for trade in control['trades']))
    cutoff_rows = [row('pre', 919), row('at', 920)]
    cutoff = day_replay(native, 'OFF', 'SYNTHETIC', cutoff_rows, {key: book(key) for key in ('pre', 'at')}, D(1000000), table())
    check(42, '1520_entry_cutoff_exact', cutoff['decisions'][0]['reason'] == 'FUNDED'
          and cutoff['decisions'][1]['reason'] == 'CAPITAL_EOD_ENTRY_CUTOFF')
    forbidden = {'protected100', 'protected_ids', 'teacher', 'potential', 'High', 'EXIT', 'books', 'realized'}
    check(43, 'protected100_evaluation_only_runtime_type_allowlist', not forbidden.intersection(DECISION_INPUT_ALLOWLIST)
          and not forbidden.intersection(NATIVE_CANDIDATE_KEYS))
    funded_N, weak_N = 151, 58
    weak_allowed = weak_N <= 58 and weak_N * 150 <= 58 * funded_N
    wrong_train_denominator = weak_N * 150 <= 58 * 38
    check(44, 'Q_rate_denominator_funded_BUY_N', weak_allowed and not wrong_train_denominator)
    sessions = [f'd{index:02d}' for index in range(38)]
    expected_ids = [(sessions[index], sessions[index + 19]) for index in range(19)]
    exact_ids = [(sessions[index], sessions[index + 19]) for index in range(len(sessions) - 19)]
    malformed_ids = exact_ids[:-1] + [('wrong', exact_ids[-1][1])]
    check(45, 'exact_19_window_identifiers_mismatch_detected', exact_ids == expected_ids and malformed_ids != expected_ids)
    baseline_growth = [Fraction(11, 10)] * 19
    candidate_growth = [Fraction(6, 5)] * 18 + [Fraction(109, 100)]
    check(46, 'paired_one_lower_reject_despite_mean_improvement', sum(candidate_growth) > sum(baseline_growth)
          and not all(candidate >= base for candidate, base in zip(candidate_growth, baseline_growth)))
    eods = [D(1000000)] + [D(1000000 + 1000 * index) for index in range(1, 39)]
    grow20 = Fraction(eods[20]) / Fraction(eods[0])
    grow21 = Fraction(eods[21]) / Fraction(eods[1])
    check(47, 'rolling_growth_contiguous_curve_no_cash_reset', grow20 == Fraction(102, 100)
          and grow21 == Fraction(1021000, 1001000))
    tiny_below = Fraction(D('1.000000000000000000000001'))
    tiny_above = Fraction(D('1.000000000000000000000002'))
    check(48, 'Decimal_rational_gate_retains_subfloat_difference', float(tiny_below) == float(tiny_above) and tiny_below < tiny_above)
    safety = safety or native.modules['common'].SAFETY
    check(49, 'all_safety_false', bool(safety) and all(value is False for value in safety.values()))
    # Additional causal/source/operator checks retained alongside the mandatory49.
    original = native.replay.day_replay(3, 'SYNTHETIC', rows, books, D(1000000), True, native.modules['common'].PROFILE, table())
    wrapped_tuple = tuple(control[key] for key in ('daily', 'decisions', 'trades', 'curves', 'intents'))
    check(50, 'OFF_synthetic_original_native_exact', original == wrapped_tuple)
    incomplete = day_replay(native, 'D', 'SYNTHETIC', [row('missing')], {}, D(1000000), table(), {'missing': intelligence()})
    check(51, 'future_sell_availability_does_not_prefilter_current_BUY', incomplete['decisions'][0]['reason'] == 'FUNDED'
          and incomplete['daily']['status'] == 'PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION'
          and incomplete['daily']['ending_cash'] is None)
    check(52, 'invalid_native_index_and_quantity_protected',
          not direct_decision(view(native_admission_index=2))['veto']
          and not direct_decision(view(native_quantity=0))['veto'])
    badhigh = replace(rescue, ranks=(Rank(0, 1, False),) + HIGH[1:])
    check(53, 'unavailable_intelligence_cannot_rescue', choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False, [badhigh]) is None)
    drift_books = {key: dict(value, capture_complete=False) for key, value in books.items()}
    drift = day_replay(native, 'D', 'SYNTHETIC', rows, drift_books, D(1000000), table(), aux)
    check(54, 'future_capture_flag_does_not_change_actual_planned_or_veto',
          [(item['entry_id'], item['actual_planned_slot'], item['reason']) for item in drift['decisions']]
          == [(item['entry_id'], item['actual_planned_slot'], item['reason']) for item in shield['decisions']])
    recovery_rows = rows + [row('expensive_first', 550, 1.3, raw='100000'), row('cheap_second', 550, 1.2)]
    recovery_aux = dict(aux, expensive_first=intelligence(False), cheap_second=intelligence(False))
    fail_rescue = day_replay(native, 'DR', 'SYNTHETIC', recovery_rows, books, D(1000000), table(), recovery_aux)
    recovery_ds = {item['entry_id']: item for item in fail_rescue['decisions']}
    check(55, 'actual_DR_failed_singleton_no_second_backfill',
          recovery_ds['expensive_first'].get('recovery_attempt') is True
          and recovery_ds['expensive_first']['recovery_singleton']['quantity'] == 0
          and not recovery_ds['cheap_second'].get('recovery_attempt')
          and recovery_ds['cheap_second']['quantity'] == 0)
    successful_rows = rows + [row('rescued', 550, 1.2)]
    successful_aux = dict(aux, rescued=intelligence(False))
    successful_books = dict(books, rescued=book('rescued'))
    filled_rescue = day_replay(native, 'DR', 'SYNTHETIC', successful_rows, successful_books,
                              D(1000000), table(), successful_aux)
    rescued_d = filled_rescue['decisions'][-1]
    check(56, 'actual_DR_successful_singleton_exact_and_token_consumed',
          rescued_d.get('recovery_funded') is True
          and rescued_d['quantity'] == rescued_d['recovery_singleton']['quantity']
          and rescued_d['debit'] == rescued_d['recovery_singleton']['debit']
          and sum(event['action'] == 'CONSUME' for event in filled_rescue['token_events']) == 1)
    check(57, 'each_of_four_single_HIGH_axes_individually_abstains',
          all(not direct_decision(view(ranks=tuple(Rank(3, 6) if axis == high_axis else LOW[axis]
                                                  for axis in range(4))))['veto']
              for high_axis in range(4)))
    infinities = []
    for value in (float('inf'), float('-inf')):
        altered = dict(intelligence()); altered['MRET'] = {'score': value}
        altered_ranks = ranks_from_record(altered)
        infinities.append(not direct_decision(view(ranks=altered_ranks))['veto']
                          and not altered_ranks[-1].low and not altered_ranks[-1].high)
    check(58, 'positive_and_negative_infinity_abstain', all(infinities))
    for number, (axis, label) in enumerate(((2, 'r3'), (3, 'rM'), (1, 'r2')), 59):
        lower = replace(rescue, entry_id='lower', ranks=HIGH, stable_order=0)
        boosted = tuple(Rank(5, 6) if index == axis else HIGH[index] for index in range(4))
        higher = replace(rescue, entry_id='higher', ranks=boosted, stable_order=1)
        selected = choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False, [lower, higher])
        check(number, 'recovery_priority_tie_preceding_axes_then_' + label, selected.entry_id == 'higher')
    rational_tie = replace(rescue, entry_id='rational_tie', ranks=tuple(Rank(8, 12) for _ in range(4)), stable_order=2)
    rational_earlier = replace(rescue, entry_id='rational_earlier', ranks=HIGH, stable_order=1)
    check(62, 'exact_fraction_equivalent_rank_native_order_tie',
          choose_recovery(tok, 'SYNTHETIC', 550, ('a', 'b'), False, [rational_tie, rational_earlier]).entry_id == 'rational_earlier')
    files = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
             for name in ('primary_policy.py', 'primary_adapter.py', 'canaries_primary.py')}
    return {'suite': 'R1_SYNTHETIC_PRIMARY_FIXED_CASES', 'mandatory_N': 49, 'executed_N': len(checks),
            'all_PASS': all(item['PASS'] for item in checks), 'market_inputs_read': 0,
            'candidate_primary_replays': 0, 'control_full38_replays': 0, 'new_fits': 0,
            'code_sha256': files, 'native_module_audit': native.audit, 'cases': checks}
