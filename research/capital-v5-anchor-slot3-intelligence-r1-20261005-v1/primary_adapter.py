"""R1 V5-native adapter. Definitions only: importing this module never replays."""
import builtins
from collections import defaultdict
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import hashlib
from pathlib import Path
import sys
import types

from primary_policy import (ARMS, CandidateView, create_token, invalidate_token,
                            choose_recovery, direct_decision, ranks_from_record,
                            rank_audit, VETO_REASON)

D = Decimal
V5_PROFILE = 'CAPITAL_MAX3_SLOT_RESERVE_V1'
ARM_PROFILE = {'OFF': V5_PROFILE, 'D': 'V5_SLOT3_UNANIMOUS_LOW_SHIELD_V1',
               'DR': 'V5_SLOT3_UNANIMOUS_LOW_SHIELD_WITH_GUARDED_RECOVERY_V1'}
FROZEN_HASHES = {
    'common': 'd0550b6d82d3289367e5f6766d7c63bb39a0262c4292bc8b9ceb992ee7229144',
    'execution': '7f084415ed92344fb99ef26e27ac48f2beeb868e643fba720bb61355339a8bc8',
    'allocation': 'bbb0f6446cb2c7edd859a2ab97edde03276bda592262c94dacbaa7900ad6b147',
    'staircase': '96d3b01749b30de17d3bce811fea771a990a15ee17508f4462c50e35e4650f70',
    'slot_policy': '7088999ffad385051522228f46c97b28ff96d0d34fcdfbb12021e098d31f3a32',
    'replay': '42e229f3816427ca16e6d44acc218d7b044e1a04f74cfd3154ff4aa6da11bb88',
}
NATIVE_CANDIDATE_KEYS = ('entry_id', 'session', 'entry_minute', 'entry_timestamp',
                         'symbol', 'raw_reference', 'capital_score', 'rank',
                         'capacity_band', 'admission', 'ML', 'm2', 'm3', 'm5', 'block')

def encoded(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {key: encoded(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encoded(item) for item in value]
    return value

class FrozenNative:
    """Runs original bytes with a private import resolver, no sys.path mutation.

    Each original module's __file__, original byte hash and resolved local imports
    are audited. The compiled code is the original source, without AST rewrites.
    """
    def __init__(self, code_dir):
        self.code_dir = Path(code_dir).resolve()
        self.namespace = '_r1_frozen_v5_' + hashlib.sha256(str(self.code_dir).encode()).hexdigest()[:16]
        self.modules = {}
        self.audit = {}
        for name in FROZEN_HASHES:
            self._load(name)
        self.execution = self.modules['execution']
        self.allocation = self.modules['allocation'].allocation
        self.band = self.modules['allocation'].band
        self.gate = self.modules['slot_policy'].gate
        self.candidate_order = self.modules['staircase'].candidate_order
        self.replay = self.modules['replay']
        assert self.replay.allocation is self.allocation
        assert self.replay.gate is self.gate
        assert self.replay.candidate_order is self.candidate_order
        assert self.modules['allocation'].BUY == self.execution.BUY

    def _load(self, name):
        if name in self.modules:
            return self.modules[name]
        source = self.code_dir / (name + '.py')
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != FROZEN_HASHES[name]:
            raise ValueError('FROZEN_V5_MODULE_HASH_MISMATCH:' + name)
        module = types.ModuleType(self.namespace + '.' + name)
        module.__file__ = str(source)
        module.__package__ = self.namespace
        self.modules[name] = module
        sys.modules[module.__name__] = module
        standard_import = builtins.__import__
        def private_import(target, globals=None, locals=None, fromlist=(), level=0):
            if level == 0 and target in FROZEN_HASHES:
                return self._load(target)
            return standard_import(target, globals, locals, fromlist, level)
        private_builtins = dict(vars(builtins))
        private_builtins['__import__'] = private_import
        module.__dict__['__builtins__'] = private_builtins
        exec(compile(payload, str(source), 'exec'), module.__dict__)
        if Path(module.__file__).resolve() != source:
            raise ValueError('FROZEN_V5_FILE_RESOLUTION_MISMATCH')
        self.audit[name] = {'__file__': str(source), 'sha256': digest,
                            'namespace': module.__name__, 'original_bytes_executed': True}
        return module

def day_replay(native, arm, day, candidates, books, starting_cash, tables,
               intelligence=None, primary_chain=True):
    """Frozen native event order plus one proposal pass and pure intervention.

    SELL/MTM suffixes are accessed only after BUY funding is fixed. Auxiliary
    policy receives CandidateView, never rows, books or teacher/evaluation IDs.
    """
    if arm not in ARMS:
        raise ValueError('FIXED_TWO_CANDIDATE_ARMS_ONLY')
    profile = ARM_PROFILE[arm]
    cash = D(str(starting_cash))
    positions, fills, events = {}, defaultdict(list), defaultdict(list)
    for raw in candidates:
        row = {key: raw[key] for key in NATIVE_CANDIDATE_KEYS}
        events[row['entry_minute']].append(row)
    decisions, trades, frames, intents, blockers = [], [], [], [], []
    token_events, native_proposals = [], []
    token = None
    original_pool, recycled_pool, recycled_used = cash, D(0), D(0)
    peak, cash_min = 0, cash
    x = native.execution
    def equity():
        return cash + sum(position['quantity'] * position['mark'] for position in positions.values())
    def token_log(action, minute, prior=None, reason=None):
        token_events.append({'session': day, 'minute': minute, 'action': action,
                             'reason': reason, 'token': prior.audit() if prior else None})
    for minute in range(540, 932):
        for key, position in positions.items():
            if key in books:
                assert books[key]['session'] == day
            while (position['mark_index'] < len(position['mark_updates'])
                   and position['mark_updates'][position['mark_index']][0] <= minute):
                known, price = position['mark_updates'][position['mark_index']]
                position['mark'] = price
                position['mark_known_minute'] = known
                position['mark_index'] += 1
        for key, source in sorted(fills.pop(minute, []), key=lambda pair: pair[0]):
            assert key in positions, 'DUPLICATE_SELL_OR_RELEASE'
            if source.get('blocked'):
                blockers.append({'entry_id': key, 'minute': minute, 'reason': source['blocked']})
                continue
            position = positions.pop(key)
            credit = D(source['price']) * position['quantity']
            cash += credit
            recycled_pool += credit
            debit = position['buy'] * position['quantity']
            trades.append({'entry_id': key, 'session': day, 'quantity': position['quantity'],
                           'entry_minute': position['entry_minute'], 'release_minute': minute,
                           'source_minute': source['source_minute'], 'exit_kind': source['kind'],
                           'buy_effective': str(position['buy']), 'sell_effective': source['price'],
                           'debit': str(debit), 'credit': str(credit), 'pnl': str(credit - debit),
                           'net_return': float(credit / debit - 1), 'lineage': source['lineage'],
                           'commission': 0})
        # Canonical invalidation point: after confirmed SELL, before Entry.
        if arm == 'DR':
            before = token
            token, why = invalidate_token(token, day, minute, positions)
            if why:
                token_log('INVALIDATE', minute, before, why)
        batch = sorted(events.get(minute, []), key=native.candidate_order)
        eligible = []
        for row in batch:
            decision = {'entry_id': row['entry_id'], 'session': day, 'minute': minute,
                        'capital_score': row['capital_score'], 'capacity_band': row['capacity_band'],
                        'rank': row['rank'], 'admission': row['admission'], 'ML': row['ML'],
                        'm2': row['m2'], 'm3': row['m3'], 'm5': row['m5'],
                        'held_before_batch': sorted(positions), 'profile': profile,
                        'quantity': 0, 'reason': None, 'primary_chain': primary_chain}
            decisions.append(decision)
            if minute >= 920:
                decision['reason'] = 'CAPITAL_EOD_ENTRY_CUTOFF'; continue
            if not row['admission']:
                decision['reason'] = 'UPWARD_BELOW_BASELINE'; continue
            if native.band(row['capital_score']) is None:
                decision['reason'] = 'SCORE_INPUT_UNKNOWN'; continue
            if any(position['symbol'] == row['symbol'] for position in positions.values()):
                decision['reason'] = 'SYMBOL_ALREADY_OPEN'; continue
            eligible.append((row, decision))
        picked = []
        for row, decision in eligible:
            occupancy = len(positions) + len(picked)
            allowed, why, audit = native.gate(row, occupancy, minute, tables[str(row['block'])])
            decision.update(audit, slot_gate_reason=why,
                            slot_gate_action='ADMIT' if allowed else 'REJECT')
            if not allowed:
                decision['reason'] = ('SLOT_RESERVE_REJECT'
                                      if why.startswith(('SLOT2_RESERVE', 'SLOT3_RESERVE')) else why)
                continue
            decision['slot_admission_index'] = occupancy + 1
            picked.append((row, decision))
        existing_N = len(positions)
        assigned = []
        snapshot = {'cash': str(cash), 'equity': str(equity()), 'exposure': str(equity() - cash),
                    'positions': encoded({key: {field: position[field]
                                                for field in ('symbol', 'quantity', 'mark', 'band')}
                                          for key, position in positions.items()})}
        if picked:
            eq = equity()
            assigned = native.allocation([row for row, decision in picked], eq, eq - cash, cash,
                                         [position['band'] for position in positions.values()])
        if batch:
            native_proposals.append({'session': day, 'minute': minute, 'snapshot': snapshot,
                                     'candidates': batch, 'existing_open_N': existing_N,
                                     'gate_decisions': encoded([dict(decision) for row, decision in eligible]),
                                     'picked_ids': [row['entry_id'] for row, decision in picked],
                                     'assigned': encoded(assigned)})
        vetoed = []
        # Successful native proposals are counted on the unmodified snapshot.
        prior_successful, proposed_cash = 0, cash
        for stable, ((row, decision), allocation) in enumerate(zip(picked, assigned)):
            decision.update({key: encoded(value) for key, value in allocation.items() if key != 'entry_id'})
            quantity = allocation['quantity']
            buy = D(row['raw_reference']) * x.BUY
            native_debit = quantity * buy
            current_pass = (quantity >= 100 and native_debit == allocation['debit']
                            and native_debit <= proposed_cash and buy.is_finite() and buy > 0)
            planned_slot = existing_N + prior_successful + 1
            view = None
            if arm != 'OFF':
                ranks = ranks_from_record((intelligence or {}).get(row['entry_id']))
                view = CandidateView(row['entry_id'], row['rank'], True, decision['slot_gate_reason'],
                                     decision['slot_admission_index'], planned_slot, quantity, ranks,
                                     stable, current_pass)
                decision.update(native_quantity=quantity, native_debit=str(native_debit),
                                native_would_fund_quantity=quantity,
                                native_would_fund_debit=str(native_debit), actual_planned_slot=planned_slot,
                                existing_open_N=existing_N,
                                prior_native_successful_BUY_proposal_N=prior_successful,
                                intelligence=rank_audit(ranks))
                action = direct_decision(view)
                decision['intelligence_action'] = action['reason']
            if current_pass:
                proposed_cash -= native_debit
                prior_successful += 1
            decision['cash_before'] = str(cash)
            if quantity < 100:
                decision['reason'] = 'CASH_OR_LOT_CONSTRAINED'; continue
            assert native_debit == allocation['debit'] and native_debit <= cash
            if arm != 'OFF' and action['veto']:
                decision.update(quantity=0, debit='0', reason=VETO_REASON)
                vetoed.append(row['entry_id'])
                continue
            # Native quantity/debit are frozen. No reallocation or backfill here.
            cash -= native_debit
            cash_min = min(cash_min, cash)
            used = min(original_pool, native_debit)
            original_pool -= used
            recycled = native_debit - used
            recycled_pool -= recycled
            recycled_used += recycled
            assert recycled_pool >= 0 and cash >= 0
            decision.update(quantity=quantity, reason='FUNDED', debit=str(native_debit),
                            recycled_cash_used=str(recycled), funded_slot=len(positions) + 1)
            key, raw = row['entry_id'], D(row['raw_reference'])
            positions[key] = {'symbol': row['symbol'], 'entry_minute': minute, 'raw_reference': str(raw),
                              'buy': buy, 'quantity': quantity, 'mark': raw, 'mark_known_minute': minute,
                              'band': row['capacity_band'], 'side': 'LONG', 'margin': False,
                              'intent_issued': False}
            peak = max(peak, len(positions))
            assert len(positions) <= 3 and quantity % 100 == 0
            # Only now inspect future execution/MTM book, never as policy input.
            book = books.get(key)
            if book is None:
                book = {'market': [], 'capture_complete': False, 'entry_actual_source': None,
                        'limit_up_authority': None}
            positions[key]['mark_updates'] = sorted([(market['minute'] + 1, D(market['C']))
                                                    for market in book['market']
                                                    if market.get('session') == day
                                                    and market['minute'] >= minute and x.valid_market(market)])
            positions[key]['mark_index'] = 0
            if not book['capture_complete'] or not book.get('entry_actual_source'):
                blockers.append({'entry_id': key, 'minute': minute, 'reason': 'MTM_SOURCE_LINEAGE_BLOCKED'})
            prior = x.frozen_execution(book) if 'frozen_exit' in book else None
            if prior:
                assert prior['release_minute'] > minute
                fills[prior['release_minute']].append((key, prior))
            if arm == 'DR' and token is not None and len(positions) == 3:
                token_log('INVALIDATE', minute, token, 'THIRD_BUY_SUCCESS')
                token = None
        # Token uses completed actual batch holdings; rejected proposals never hold.
        if arm == 'DR' and vetoed:
            token, created = create_token(token, day, minute, vetoed[0], positions)
            if created:
                token_log('CREATE', minute, token)
        if arm == 'DR' and token is not None:
            recovery_views = []
            rows_by_id = {}
            decisions_by_id = {}
            for stable, (row, decision) in enumerate(eligible):
                ranks = ranks_from_record((intelligence or {}).get(row['entry_id']))
                recovery_views.append(CandidateView(row['entry_id'], row['rank'],
                                     decision.get('slot_gate_action') == 'ADMIT',
                                     decision.get('slot_gate_reason', ''),
                                     decision.get('slot_admission_index', 0), 0, 0, ranks,
                                     stable, True))
                rows_by_id[row['entry_id']] = row
                decisions_by_id[row['entry_id']] = decision
            selected = choose_recovery(token, day, minute, positions, bool(picked), recovery_views)
            if selected is not None:
                row, decision = rows_by_id[selected.entry_id], decisions_by_id[selected.entry_id]
                eq = equity()
                singleton = native.allocation([row], eq, eq - cash, cash,
                                               [position['band'] for position in positions.values()])[0]
                quantity = singleton['quantity']
                buy = D(row['raw_reference']) * x.BUY
                debit = buy * quantity
                token_log('RECOVERY_ATTEMPT', minute, token, selected.entry_id)
                decision.update(recovery_attempt=True, recovery_singleton=encoded(singleton),
                                intelligence=rank_audit(selected.ranks))
                if quantity >= 100:
                    assert debit == singleton['debit'] and debit <= cash
                    cash -= debit
                    cash_min = min(cash_min, cash)
                    used = min(original_pool, debit)
                    original_pool -= used
                    recycled = debit - used
                    recycled_pool -= recycled
                    recycled_used += recycled
                    assert recycled_pool >= 0 and cash >= 0
                    decision.update({key: encoded(value) for key, value in singleton.items() if key != 'entry_id'})
                    decision.update(quantity=quantity, reason='FUNDED', debit=str(debit), cash_before=str(cash + debit),
                                    recycled_cash_used=str(recycled), funded_slot=len(positions) + 1,
                                    recovery_funded=True)
                    key, raw = row['entry_id'], D(row['raw_reference'])
                    positions[key] = {'symbol': row['symbol'], 'entry_minute': minute,
                                      'raw_reference': str(raw), 'buy': buy, 'quantity': quantity,
                                      'mark': raw, 'mark_known_minute': minute, 'band': row['capacity_band'],
                                      'side': 'LONG', 'margin': False, 'intent_issued': False}
                    peak = max(peak, len(positions))
                    assert len(positions) <= 3 and quantity % 100 == 0
                    book = books.get(key) or {'market': [], 'capture_complete': False,
                                              'entry_actual_source': None, 'limit_up_authority': None}
                    positions[key]['mark_updates'] = sorted([(market['minute'] + 1, D(market['C']))
                                                             for market in book['market']
                                                             if market.get('session') == day
                                                             and market['minute'] >= minute and x.valid_market(market)])
                    positions[key]['mark_index'] = 0
                    if not book['capture_complete'] or not book.get('entry_actual_source'):
                        blockers.append({'entry_id': key, 'minute': minute, 'reason': 'MTM_SOURCE_LINEAGE_BLOCKED'})
                    prior = x.frozen_execution(book) if 'frozen_exit' in book else None
                    if prior:
                        assert prior['release_minute'] > minute
                        fills[prior['release_minute']].append((key, prior))
                    token_log('CONSUME', minute, token, 'RECOVERY_THIRD_BUY_SUCCESS')
                    token = None
                else:
                    decision['recovery_failure_reason'] = 'CASH_OR_LOT_CONSTRAINED'
                    # No second candidate is attempted. Native rejection retained.
        if minute == 920:
            for key, position in sorted(positions.items()):
                intent = x.eod_intent(position)
                assert intent is not None
                position['intent_issued'] = True
                book = books.get(key) or {'market': [], 'limit_up_authority': None}
                intent.update(entry_id=key, session=day,
                              limit_up_status=('LIMIT_UP_CONFIRMED'
                                               if x.limit_up_confirmed(book.get('limit_up_authority'), day, minute)
                                               else 'LIMIT_UP_UNKNOWN'))
                intents.append(intent)
                source = x.eod_source(book['market'], day)
                if source:
                    fills[source['release_minute']].append((key, source))
                else:
                    blockers.append({'entry_id': key, 'minute': 931,
                                     'reason': ('LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED'
                                                if intent['limit_up_status'] == 'LIMIT_UP_CONFIRMED'
                                                else 'EOD_UNEXECUTED_FAIL_CLOSED')})
        eq = equity()
        assert cash >= 0 and eq > 0
        frames.append({'session': day, 'minute': minute, 'equity': str(eq), 'cash': str(cash),
                       'exposure': str(eq - cash), 'utilization': float((eq - cash) / eq),
                       'concurrent': len(positions), 'primary_chain': primary_chain,
                       'known_marks': {key: position['mark_known_minute'] for key, position in positions.items()}})
    if token is not None:
        token_log('INVALIDATE', 931, token, 'SESSION_END')
    if positions:
        known = {blocker['entry_id'] for blocker in blockers}
        for key in positions:
            if key not in known:
                blockers.append({'entry_id': key, 'minute': 931, 'reason': 'EOD_UNEXECUTED_FAIL_CLOSED'})
    valid = not blockers and not positions
    daily = {'session': day, 'status': 'COMPLETE' if valid else 'PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION',
             'starting_cash': str(starting_cash), 'ending_cash': str(cash) if valid else None,
             'daily_return': float(cash / D(str(starting_cash)) - 1) if valid and primary_chain else None,
             'diagnostic_daily_return': float(cash / D(str(starting_cash)) - 1) if valid else None,
             'primary_chain': primary_chain, 'blockers': blockers, 'open_obligations': list(positions),
             'cash_min': str(cash_min), 'max_concurrent': peak, 'recycled_cash_used': str(recycled_used)}
    return {'daily': daily, 'decisions': decisions, 'trades': trades, 'curves': frames,
            'intents': intents, 'token_events': token_events, 'native_proposals': native_proposals}

def run_profile(arm, stream, books, tables, intelligence=None, *, native=None, code_dir=None):
    """One claimed chain. Caller must hold durable claim; no retries in here."""
    if native is None:
        if code_dir is None:
            raise ValueError('EXPLICIT_FROZEN_NATIVE_CODE_DIR_REQUIRED')
        native = FrozenNative(code_dir)
    if arm not in ARMS:
        raise ValueError('FIXED_TWO_CANDIDATE_ARMS_ONLY')
    days = sorted({row['session'] for row in stream})
    cash, chain = D(1000000), True
    output = {key: [] for key in ('daily', 'decisions', 'trades', 'curves', 'intents',
                                  'token_events', 'native_proposals')}
    with localcontext() as context:
        context.prec, context.rounding = 28, ROUND_HALF_EVEN
        for day in days:
            current = day_replay(native, arm, day, [row for row in stream if row['session'] == day],
                                 books, cash if chain else D(1000000), tables, intelligence, chain)
            output['daily'].append(current['daily'])
            for key in output:
                if key != 'daily':
                    output[key].extend(current[key])
            if chain and current['daily']['status'] == 'COMPLETE':
                cash = D(current['daily']['ending_cash'])
            elif chain:
                if arm != 'OFF':
                    # Fail closed on the first unresolved execution. No reset
                    # diagnostic chain and no synthetic full-window completion.
                    break
                chain = False
        result = native.replay.summary(3, output['daily'], output['decisions'], output['trades'],
                                       output['curves'], output['intents'])
        result.update(arm=ARM_PROFILE[arm], profile=ARM_PROFILE[arm],
                      water_fill_lots_N=sum(decision.get('water_fill_lots', 0) for decision in output['decisions']),
                      water_fill_funded_N=sum(decision['reason'] == 'FUNDED'
                                             and decision.get('water_fill_lots', 0) > 0
                                             for decision in output['decisions']))
    output['result'], output['native_module_audit'] = result, native.audit
    return output
