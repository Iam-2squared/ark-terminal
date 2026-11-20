"""R34 offline cash-equity admission/accounting primitives, not a broker router.

Work basis: 87bf068a1dc29a8661c6d60b89141358738cabdd, 2026-09-26 JST.
Current: outcome-free rank ordering and actual MAX3/4/5 capacity enforcement.
Next: connect a precommitted sizing adapter and the final frozen EXIT ledger.
Quantity is an explicit causal input; this module does NOT invent allocation
weights, fit a ranker, replay any historical strategy, or evaluate performance.
"""
from __future__ import annotations

import copy
import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Iterable, Mapping

JST = dt.timezone(dt.timedelta(hours=9))
INITIAL_CASH = Decimal('1000000')
LOT = 100
CAPACITIES = (3, 4, 5)
SELL_COST_PP = Decimal('0.05')
SAFETY = dict.fromkeys((
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
    'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
    'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted'), False)
ENTRY_FIELDS = frozenset((
    'entryId', 'symbol', 'timestamp', 'entryKnownAt', 'effectiveEntryPrice',
    'quantity', 'newEligibleRank', 'savedV1Score', 'rankKnownAt', 'side', 'account'))
EXIT_FIELDS = frozenset(('entryId', 'timestamp', 'knownAt', 'price', 'confirmed'))


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def stamp(value: str) -> dt.datetime:
    require(isinstance(value, str), 'TIMESTAMP_REQUIRED')
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('INVALID_TIMESTAMP') from exc
    require(parsed.tzinfo is not None, 'TIMEZONE_REQUIRED')
    require(parsed.second == parsed.microsecond == 0, 'MINUTE_BOUNDARY_REQUIRED')
    return parsed.astimezone(JST)


def number(value, *, positive: bool = False) -> Decimal:
    require(not isinstance(value, bool) and value is not None, 'INVALID_NUMBER')
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('INVALID_NUMBER') from exc
    require(out.is_finite(), 'NONFINITE_NUMBER')
    require(not positive or out > 0, 'NONPOSITIVE_PRICE')
    return out


def quantity_for_target(target_jpy, effective_entry_price) -> int:
    """Quantize an already-chosen target, without choosing a sizing policy."""
    target, price = number(target_jpy), number(effective_entry_price, positive=True)
    require(target >= 0, 'NEGATIVE_TARGET')
    return int((target / (price * LOT)).to_integral_value(rounding=ROUND_FLOOR)) * LOT


def _entry(row: Mapping, now: dt.datetime) -> dict:
    require(isinstance(row, Mapping) and set(row) == ENTRY_FIELDS,
            'ENTRY_ALLOWLIST_MISMATCH_NO_OUTCOME_FIELDS')
    e = dict(row)
    require(e['side'] == 'LONG' and e['account'] == 'CASH', 'CASH_LONG_ONLY')
    require(isinstance(e['entryId'], str) and bool(e['entryId']), 'ENTRY_ID_REQUIRED')
    require(isinstance(e['symbol'], str) and bool(e['symbol']), 'SYMBOL_REQUIRED')
    require(stamp(e['timestamp']) == now, 'ENTRY_NOT_AT_BATCH_NOW')
    require(stamp(e['entryKnownAt']) <= now, 'FUTURE_ENTRY_INFORMATION')
    require(stamp(e['rankKnownAt']) <= now, 'FUTURE_RANK_INFORMATION')
    require(type(e['quantity']) is int and e['quantity'] > 0
            and e['quantity'] % LOT == 0, 'POSITIVE_100_SHARE_LOT_REQUIRED')
    require(type(e['newEligibleRank']) is int and e['newEligibleRank'] > 0,
            'POSITIVE_INTEGER_RANK_REQUIRED')
    e['effectiveEntryPrice'] = number(e['effectiveEntryPrice'], positive=True)
    e['savedV1Score'] = number(e['savedV1Score'])
    return e


def _exit(row: Mapping, now: dt.datetime) -> dict:
    require(isinstance(row, Mapping) and set(row) == EXIT_FIELDS,
            'EXIT_EVENT_ALLOWLIST_MISMATCH')
    e = dict(row)
    require(isinstance(e['entryId'], str) and bool(e['entryId']), 'ENTRY_ID_REQUIRED')
    require(stamp(e['timestamp']) == now, 'EXIT_NOT_AT_BATCH_NOW')
    require(stamp(e['knownAt']) <= now, 'FUTURE_EXIT_EVENT')
    require(type(e['confirmed']) is bool, 'CONFIRMATION_MUST_BE_BOOLEAN')
    if e['confirmed']:
        e['price'] = number(e['price'], positive=True)
    else:
        require(e['price'] is None, 'UNCONFIRMED_EXIT_CANNOT_HAVE_FILL_PRICE')
    return e


def _wire(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_wire(v) for v in value]
    return value


class CashBook:
    """Single-arm offline ledger with atomic chronological event batches.

    The caller supplies only confirmed fills at their event time, never a future
    EXIT record attached to an Entry. Settlement/broker buying-power rules are
    deliberately NOT claimed by this historical cash-accounting primitive.
    """

    def __init__(self, capacity: int = 3):
        require(type(capacity) is int and capacity in CAPACITIES, 'MAX3_4_5_ONLY')
        self.capacity = capacity
        self.cash = INITIAL_CASH
        self.realized = Decimal(0)
        self.positions: dict[str, dict] = {}
        self.seen_entries: set[str] = set()
        self.last_now: dt.datetime | None = None

    def _invariants(self) -> None:
        require(self.cash >= 0, 'NEGATIVE_CASH_FORBIDDEN')
        require(len(self.positions) <= self.capacity, 'CAPACITY_EXCEEDED')
        require(len({p['symbol'] for p in self.positions.values()}) == len(self.positions),
                'DUPLICATE_SYMBOL_POSITION')
        require(all(p['quantity'] > 0 and p['quantity'] % LOT == 0
                    for p in self.positions.values()), 'POSITION_LOT_VIOLATION')
        purchase_cost = sum((p['cost'] for p in self.positions.values()), Decimal(0))
        require(self.cash + purchase_cost == INITIAL_CASH + self.realized,
                'CASH_COST_REALIZED_RECONCILIATION_FAILED')

    def step(self, now: str, entries: Iterable[Mapping] = (),
             exits: Iterable[Mapping] = ()) -> dict:
        when = stamp(now)
        require(self.last_now is None or when > self.last_now, 'BATCH_NOT_CHRONOLOGICAL')
        if self.last_now is not None and when.date() > self.last_now.date():
            require(not self.positions, 'UNRESOLVED_OVERNIGHT_BOUNDARY')
        # Validate the entire batch before changing anything, including exits.
        incoming = [_entry(e, when) for e in entries]
        outgoing = [_exit(e, when) for e in exits]
        ids = [e['entryId'] for e in incoming]
        require(len(ids) == len(set(ids)), 'DUPLICATE_ENTRY_IN_BATCH')
        require(not self.seen_entries.intersection(ids), 'ENTRY_ALREADY_PROCESSED')
        exit_ids = [e['entryId'] for e in outgoing]
        require(len(exit_ids) == len(set(exit_ids)), 'DUPLICATE_EXIT_IN_BATCH')
        work = copy.deepcopy(self)
        events = []
        # Confirmed cash release always precedes same-time Entry admission.
        for e in sorted(outgoing, key=lambda r: r['entryId']):
            p = work.positions.get(e['entryId'])
            event = {'kind': 'EXIT', 'entryId': e['entryId']}
            if p is None:
                event['status'] = 'NOT_HELD_NO_CASH_RELEASE'
            elif not e['confirmed']:
                event['status'] = 'UNRESOLVED_NO_CASH_RELEASE'
                p['unresolved'] = True
            else:
                # R24 constant pp subtraction is relative to effective Entry.
                # Do not charge its embedded buy-side cost a second time.
                proceeds = e['price'] * p['quantity']
                fee = p['cost'] * SELL_COST_PP / 100
                require(work.cash + proceeds - fee >= 0, 'EXIT_FEE_CANNOT_BORROW')
                pnl = proceeds - fee - p['cost']
                work.cash += proceeds - fee
                work.realized += pnl
                del work.positions[e['entryId']]
                event.update(status='CLOSED', proceedsJpy=proceeds, sellCostJpy=fee,
                             realizedPnlJpy=pnl)
            events.append(event)
        incoming.sort(key=lambda e: (e['newEligibleRank'], -e['savedV1Score'],
                                     e['symbol'], e['entryId']))
        for e in incoming:
            cost = e['effectiveEntryPrice'] * e['quantity']
            event = {'kind': 'ENTRY', 'entryId': e['entryId'], 'symbol': e['symbol'],
                     'requestedQuantity': e['quantity'], 'cashBeforeJpy': work.cash}
            if any(p['symbol'] == e['symbol'] for p in work.positions.values()):
                reason = 'SYMBOL_ALREADY_OPEN'
            elif len(work.positions) == work.capacity:
                reason = 'MAX_CONCURRENT_SYMBOLS'
            elif cost > work.cash:
                reason = 'INSUFFICIENT_AVAILABLE_CASH'
            else:
                reason = None
            if reason:
                event.update(status='REJECTED', reason=reason, quantity=0)
            else:
                work.cash -= cost
                work.positions[e['entryId']] = {
                    'symbol': e['symbol'], 'quantity': e['quantity'], 'cost': cost,
                    'entryTimestamp': when.isoformat(), 'unresolved': False}
                event.update(status='ACCEPTED', quantity=e['quantity'], costJpy=cost)
            event['cashAfterJpy'] = work.cash
            work.seen_entries.add(e['entryId'])
            events.append(event)
        work.last_now = when
        work._invariants()
        self.__dict__.update(work.__dict__)
        return _wire({'timestamp': when.isoformat(), 'events': events,
                      'cashJpy': self.cash, 'openSymbols': len(self.positions),
                      'capacity': self.capacity, 'safety': dict(SAFETY)})

    def snapshot(self, now: str, marks: Mapping[str, Mapping] | None = None) -> dict:
        """Fresh marks only. Unknown valuation is null, never cost or stale fill."""
        when = stamp(now)
        require(self.last_now is None or when >= self.last_now, 'SNAPSHOT_BEFORE_LEDGER')
        marks = {} if marks is None else marks
        require(set(marks) <= set(self.positions), 'MARK_FOR_UNOWNED_POSITION')
        exposure = Decimal(0)
        complete = True
        for eid, p in self.positions.items():
            mark = marks.get(eid)
            if mark is None:
                complete = False
                continue
            require(set(mark) == {'timestamp', 'knownAt', 'price'}, 'MARK_ALLOWLIST_MISMATCH')
            require(stamp(mark['knownAt']) <= when, 'FUTURE_MARK')
            source_time = stamp(mark['timestamp'])
            require(source_time <= when, 'FUTURE_MARK_TIMESTAMP')
            if source_time != when:
                complete = False
                continue
            exposure += number(mark['price'], positive=True) * p['quantity']
        self._invariants()
        equity = self.cash + exposure if complete else None
        return _wire({'cashJpy': self.cash,
                      'lockedPurchaseCostJpy': sum((p['cost'] for p in self.positions.values()), Decimal(0)),
                      'realizedPnlJpy': self.realized, 'positions': self.positions,
                      'grossExposureJpy': exposure if complete else None,
                      'equityJpy': equity,
                      'grossExposureRatio': exposure / equity if equity and equity > 0 else None,
                      'borrowedCashJpy': Decimal(0), 'capacity': self.capacity,
                      'safety': dict(SAFETY)})
