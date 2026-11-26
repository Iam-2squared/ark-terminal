"""Observed execution balances -> unchanged original Capital V5 / EXIT.

This adapter performs calculations only. The former synthetic bridge remains
synthetic. Its upstream validator is reused with ZERO fictional cash solely to
check the existing R0 contract; actual balances are passed directly to the
byte-pinned original allocation and slot functions, never relabelled synthetic.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import ModuleType

import no11_h235_capital_v5_shadow as hcap
import no11_capital_v5_crlf_safe_synthetic as source_loader
import no11_h235_asof_forward_shadow as h
import no11_original_exit_shadow as exits
from no11_broker_fill_attribution import instant, digest
from no11_broker_execution_ledger import INTENT_SCHEMA, ACCOUNTS, TERMINAL


def need(ok, code):
    if not ok:
        raise ValueError('NO11_BROKER_DECISION_' + code)


def money(value):
    need(type(value) in (str, int, float) and type(value) is not bool, 'MONEY')
    try:
        v = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('NO11_BROKER_DECISION_MONEY') from None
    need(v.is_finite() and 0 <= v <= Decimal('1000000000000'), 'MONEY')
    return v


def quantity(value, *, allow_zero=False):
    # A partial broker fill can leave an odd quantity. It still occupies its
    # original slot; only an outgoing order must obey the 100-share contract.
    need(type(value) is int and (0 if allow_zero else 1) <= value <= 1_000_000_000,
         'POSITION_QUANTITY')
    return value


def original_functions():
    bridge = source_loader.load_original_bridge()
    original = bridge.git_blob_sha
    bridge.git_blob_sha = lambda data: source_loader.canonical_git_blob(data)
    try:
        allocator, slots = bridge.load_frozen()
    finally:
        bridge.git_blob_sha = original
    need(Path(allocator.__file__).resolve() == (bridge.SOURCE / 'allocation.py').resolve()
         and Path(slots.__file__).resolve() == (bridge.SOURCE / 'slot_policy.py').resolve(),
         'ORIGINAL_MODULE_IDENTITY')
    return allocator, slots


def original_execution():
    bridge = source_loader.load_original_bridge()
    source = h.pin_public(bridge.SOURCE / 'execution.py', bridge.CAPITAL_BLOBS['execution.py'])
    execution = ModuleType('_no11_broker_pinned_capital_execution')
    execution.__file__ = str(bridge.SOURCE / 'execution.py')
    exec(compile(source, str(bridge.SOURCE / 'execution.py'), 'exec'), execution.__dict__)
    return execution, {'execution.py': bridge.CAPITAL_BLOBS['execution.py']}


def original_eod(position, *, session, at):
    """Invoke the pinned EOD function without inventing a position fill clock."""
    execution, pins = original_execution()
    native = execution.eod_intent({'quantity': position['quantity'], 'side': 'LONG', 'margin': False})
    need(native is not None and native['quantity'] == position['quantity']
         and native['side'] == 'SELL' and native['transmitted'] is False,
         'NATIVE_EOD_IDENTITY')
    return {'intent': dict(native, reason='EOD_1520', timestamp=session + 'T15:20:00+09:00',
                           sourceKnownAtJst=at),
            'sourceBlobPins': pins,
            'originalEodExecuted': True, 'fillTimeUnknown': True}


def calculate_capital(batch, account, arrival):
    """Run the original gate and allocator on a bounded, current account view."""
    need(type(account) is dict and account.get('schemaId') == 'ARK_NO11_BROKER_CAPITAL_INPUT_V1', 'ACCOUNT')
    session, at = account['sessionDate'], account['decisionAtJst']
    instant(at, session)
    # No real account values enter a SYNTHETIC scenario. Reuse its exact source
    # and causal checks as a zero-cash validation pass, with no funding call.
    validation = {'schemaId': hcap.SCENARIO, 'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',
        'sessionDate': session, 'decisionAtJst': at,
        'arkCapitalInputs': {'cash': '0', 'equity': '0', 'exposure': '0'},
        'externalSymbols': [], 'arkManagedSymbols': [], 'existingBands': [],
        'afterFirstLegalSellFill': False, 'pendingBrokerOrders': False,
        'syntheticAccountOnly': True, 'productionReady': False, 'orderTransmission': False}
    validated = hcap.build_request(batch, validation, arrival)
    candidates = validated['preorderedCandidates']
    # Preserve the scorer's received-data boundary when its R0 crosses into the
    # execution adapter. Never accept an edited future receipt or stale mark.
    rows = batch['results']
    need(len({r['symbol'] for r in rows}) == len(rows), 'R0_SYMBOL_DUPLICATE')
    for row in rows:
        decision = instant(row['decisionAtJst'], session)
        reference = instant(row['asofReferenceBarEndJst'], session)
        received = instant(row['referenceKnownAtJst'], session)
        end = h.timestamp(row['asofReferenceBarEndJst'], session)
        need(instant(row['entry_timestamp'], session) <= reference <= received <= decision
             and decision - reference <= 90_000_000_000
             and end.second == 0 and end.microsecond == 0
             and h.minute(end) < 920 and h.eligible_closed_minute(h.minute(end)),
             'R0_REFERENCE_NOT_RECEIVED_OR_STALE')
    need(account.get('account') in ACCOUNTS, 'ACCOUNT_TYPE')
    need(type(account.get('entryBlocked')) is bool and type(account.get('pendingOrders')) is bool, 'ACCOUNT_GATES')
    positions = account.get('positions')
    need(type(positions) is list and len(positions) <= 3
         and all(type(p) is dict for p in positions), 'POSITIONS')
    for position in positions:
        quantity(position.get('quantity'))
        need(position.get('account', account['account']) == account['account'], 'POSITION_ACCOUNT')
    managed = [p.get('symbol') for p in positions]
    bands = [p.get('band') for p in positions]
    need(len(set(managed)) == len(managed) and all(type(s) is str and h.SYMBOL.fullmatch(s) for s in managed)
         and all(b in ('S', 'A', 'B') for b in bands), 'POSITION_IDENTITY')
    external = account.get('externalSymbols')
    need(type(external) is list and len(external) <= 5000
         and all(type(s) is str and h.SYMBOL.fullmatch(s) for s in external), 'EXTERNAL_SYMBOLS')
    need(len(set(external)) == len(external), 'EXTERNAL_SYMBOLS_DUPLICATE')
    need(not set(managed).intersection(external), 'PERSONAL_AND_ARK_OVERLAP')
    cash, exposure = money(account['availableCashJpy']), money(account['exposureJpy'])
    equity = money(account['equityJpy'])
    need(equity == cash + exposure, 'EQUITY')
    need(bool(positions) == (exposure > 0), 'POSITION_MARKS')
    allocator, slots = original_functions()
    admitted, rejected = [], []
    blocked = account['entryBlocked'] or account['pendingOrders']
    for row in candidates:
        code = row['brokerSymbol']
        if blocked:
            reason = 'ENTRY_BLOCKED_OR_PENDING'
        elif code in managed or code in external:
            reason = 'ALREADY_OWNED_OR_PERSONAL'
        elif len(managed) + len(admitted) >= 3:
            reason = 'MAX_POSITION_CAP'
        else:
            accepted, reason, _ = slots.gate(row, len(managed) + len(admitted),
                                             validated['minute'], arrival[row['block']])
            if accepted:
                admitted.append(row)
                continue
        rejected.append({'entry_id': row['entry_id'], 'reason': reason})
    assigned = allocator.allocation(admitted, str(equity), str(exposure), str(cash), bands) if admitted else []
    need(len(assigned) == len(admitted), 'ALLOCATION_COUNT')
    by_id = {r['candidateId']: r for r in batch['results']}
    intents, allocations = [], []
    spent = Decimal(0)
    for row, output in zip(admitted, assigned):
        qty, debit = output['quantity'], output['debit']
        need(type(qty) is int and 0 <= qty <= 1_000_000_000 and qty % 100 == 0
             and output['entry_id'] == row['entry_id'], 'ALLOCATION_IDENTITY')
        unit = money(row['raw_reference']) * Decimal('1.0005')
        need(debit == unit * qty and debit <= output['equity_cap'], 'NATIVE_DEBIT')
        spent += debit
        allocation = {'entry_id': row['entry_id'], 'quantity': qty, 'band': output['band'],
                      'debitJpy': str(debit), 'batchBudgetJpy': str(output['batch_budget']),
                      'firstPassQuantity': output['first_pass_quantity'], 'waterFillLots': output['water_fill_lots']}
        allocations.append(allocation)
        if qty:
            intent = {'schemaId': INTENT_SCHEMA, 'sessionDate': session,
                'intentId': h.digest([session, row['entry_id'], 'BUY']),
                'entryId': row['entry_id'], 'symbol': row['brokerSymbol'], 'side': 'BUY',
                'account': account['account'], 'quantity': qty, 'band': output['band'],
                'createdAtJst': at, 'sourceDecisionSha256': h.digest(by_id[row['entry_id']]),
                'sourceKind': 'ORIGINAL_CAPITAL_V5', 'reservePriceJpy': str(unit),
                'reserveChargesJpy': str(money(account.get('reserveChargesJpy', '0')))}
            intents.append(intent)
    need(spent <= cash and len(managed) + sum(a['quantity'] > 0 for a in allocations) <= 3, 'NATIVE_LIMIT')
    return {'schemaId': 'ARK_NO11_BROKER_CAPITAL_CALCULATION_V1', 'intents': intents,
        'allocations': allocations, 'rejected': rejected, 'allocatedDebitJpy': str(spent),
        'originalAllocatorExecuted': True, 'originalSlotPolicyExecuted': True,
        'strategyFreezeCommit': hcap.FROZEN, 'sourceR0Sha256': h.digest(batch),
        'sourceAccountSha256': digest(account), 'orderTransmission': False, 'productionReady': False}


def calculate_exits(positions, traces, *, session, at, order_history):
    """Confirmed managed quantities only; cash/ownership stay in the ledger."""
    now = instant(at, session)
    need(type(positions) is list and type(traces) is dict and type(order_history) is dict
         and all(type(p) is dict for p in positions)
         and all(type(o) is dict for o in order_history.values()), 'EXIT_INPUTS')
    intents, unresolved, odd_lots = [], [], []
    entries, symbols = set(), set()
    for position in positions:
        qty = quantity(position.get('quantity'), allow_zero=True)
        if qty == 0:
            continue
        entry_id = position.get('entryId')
        code = position.get('symbol')
        need(type(entry_id) is str and 0 < len(entry_id) <= 256 and entry_id not in entries
             and type(code) is str and h.SYMBOL.fullmatch(code) and code not in symbols
             and position.get('account') in ACCOUNTS and position.get('band') in ('S', 'A', 'B'),
             'EXIT_POSITION_IDENTITY')
        entries.add(entry_id)
        symbols.add(code)
        sells = [o for o in order_history.values() if o.get('entryId') == entry_id and o.get('side') == 'SELL']
        # Only a terminal observed order permits a new generation. Unknown or
        # newly introduced phases cannot accidentally authorize a duplicate.
        if any(o.get('phase') not in TERMINAL for o in sells):
            continue
        if qty % 100:
            odd_lots.append({'entryId': entry_id, 'symbol': code, 'quantity': qty,
                             'reason': 'OWNED_QUANTITY_NOT_100_SHARE_LOT'})
            continue
        need(type(position.get('fillTimeVerified', False)) is bool, 'POSITION_FILL_PROOF')
        fill_time = position.get('filledAtJst') if position.get('fillTimeVerified') is True else None
        if fill_time is None:
            if now < instant(session + 'T15:20:00+09:00', session):
                unresolved.append(position['symbol'])
                continue
            result = original_eod(position, session=session, at=at)
        else:
            need(instant(fill_time, session) <= now, 'FUTURE_POSITION_FILL')
            result = exits.decide_received_exit(session=session, entry_at=fill_time,
                trace=traces.get(position['symbol'], []), evaluated_at=at)
        if result['intent'] is None:
            continue
        generation = len(sells)
        intents.append({'schemaId': INTENT_SCHEMA, 'sessionDate': session,
            'intentId': h.digest([session, entry_id, 'SELL', generation]),
            'entryId': entry_id, 'symbol': position['symbol'], 'side': 'SELL',
            'account': position['account'], 'quantity': position['quantity'], 'band': position['band'],
            'createdAtJst': at, 'sourceDecisionSha256': h.digest(result),
            'sourceKind': 'ORIGINAL_EXIT', 'reservePriceJpy': '0', 'reserveChargesJpy': '0',
            'exitReason': result['intent']['reason']})
    return {'intents': intents, 'unknownFillTimeSymbols': unresolved,
            'unresolvedExitPositions': odd_lots,
            'originalExitPins': exits.PINS, 'orderTransmission': False, 'productionReady': False}
