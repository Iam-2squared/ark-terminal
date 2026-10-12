"""R37 causal sizing bridge and post-freeze portfolio score primitives.

This module is deliberately performance-free. It joins confirmed EXIT cash
release, fresh NOW marks and the R35 MAX3/4/5 sizing rule around R34 CashBook.
It cannot consume future buckets/outcomes for ranking or sizing. Portfolio
score and >=5% attribution helpers require an explicit SELECT freeze token and
are for use only after the R36 finite selection is frozen.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from decimal import Decimal
from typing import Iterable, Mapping

from scripts import phase57_cash_capital_r34 as cash


INTENT_FIELDS = frozenset((
    'entryId', 'symbol', 'timestamp', 'entryKnownAt', 'effectiveEntryPrice',
    'newEligibleRank', 'savedV1Score', 'rankKnownAt', 'side', 'account'))
CAPACITIES = cash.CAPACITIES
SAFETY = dict(cash.SAFETY)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def _wire(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_wire(v) for v in value]
    return value


def _intent(row: Mapping, now) -> dict:
    require(isinstance(row, Mapping) and set(row) == INTENT_FIELDS,
            'SIZING_INTENT_ALLOWLIST_MISMATCH_NO_OUTCOME_FIELDS')
    out = dict(row)
    require(out['side'] == 'LONG' and out['account'] == 'CASH', 'CASH_LONG_ONLY')
    require(isinstance(out['entryId'], str) and out['entryId'], 'ENTRY_ID_REQUIRED')
    require(isinstance(out['symbol'], str) and out['symbol'], 'SYMBOL_REQUIRED')
    require(cash.stamp(out['timestamp']) == now, 'ENTRY_NOT_AT_BATCH_NOW')
    require(cash.stamp(out['entryKnownAt']) <= now, 'FUTURE_ENTRY_INFORMATION')
    require(cash.stamp(out['rankKnownAt']) <= now, 'FUTURE_RANK_INFORMATION')
    require(type(out['newEligibleRank']) is int and out['newEligibleRank'] > 0,
            'POSITIVE_INTEGER_RANK_REQUIRED')
    out['effectiveEntryPrice'] = cash.number(out['effectiveEntryPrice'], positive=True)
    out['savedV1Score'] = cash.number(out['savedV1Score'])
    return out


class SizedCashPortfolio:
    """Atomic EXIT-release -> fresh-MTM -> ranked Entry sizing bridge."""

    def __init__(self, capacity: int):
        require(type(capacity) is int and capacity in CAPACITIES, 'MAX3_4_5_ONLY')
        self.book = cash.CashBook(capacity)
        self.seen_intents: set[str] = set()

    def step(self, now: str, entry_intents: Iterable[Mapping] = (),
             exits: Iterable[Mapping] = (), marks: Mapping[str, Mapping] | None = None) -> dict:
        when = cash.stamp(now)
        intents = [_intent(x, when) for x in entry_intents]
        ids = [x['entryId'] for x in intents]
        require(len(ids) == len(set(ids)), 'DUPLICATE_ENTRY_IN_BATCH')
        require(not self.seen_intents.intersection(ids), 'ENTRY_ALREADY_PROCESSED')
        intents.sort(key=lambda x: (x['newEligibleRank'], -x['savedV1Score'],
                                    x['symbol'], x['entryId']))
        exits = list(exits)

        # A private copy establishes exactly the confirmed post-EXIT cash/slots.
        # The real ledger is mutated only once after the entire batch is valid.
        preview = copy.deepcopy(self.book)
        preview_exit = preview.step(now, exits=exits)
        marks = {} if marks is None else dict(marks)
        snapshot = preview.snapshot(now, marks)
        equity = snapshot['equityJpy']
        target = (None if equity is None else Decimal(equity) / preview.capacity)
        available = preview.cash
        symbols = {p['symbol'] for p in preview.positions.values()}
        open_count = len(preview.positions)
        accepted, sizing = [], []

        for intent in intents:
            event = {'entryId': intent['entryId'], 'symbol': intent['symbol'],
                     'rank': intent['newEligibleRank'], 'cashBeforeSizingJpy': available,
                     'targetSlotBudgetJpy': target}
            if equity is None:
                reason = 'MISSING_FRESH_MARK_UNRESOLVED_SIZING'
            elif intent['symbol'] in symbols:
                reason = 'SYMBOL_ALREADY_OPEN'
            elif open_count >= preview.capacity:
                reason = 'MAX_CONCURRENT_SYMBOLS'
            else:
                budget = min(target, available)
                quantity = cash.quantity_for_target(budget, intent['effectiveEntryPrice'])
                reason = None if quantity > 0 else 'NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH'
            if reason:
                event.update(status='REJECTED', reason=reason, quantity=0,
                             cashAfterSizingJpy=available)
            else:
                row = dict(intent, quantity=quantity)
                accepted.append(row)
                cost = intent['effectiveEntryPrice'] * quantity
                available -= cost; symbols.add(intent['symbol']); open_count += 1
                event.update(status='SIZED', reason=None, quantity=quantity,
                             costJpy=cost, cashAfterSizingJpy=available)
            sizing.append(event)

        ledger = self.book.step(now, entries=accepted, exits=exits)
        ledger_accepts = [x for x in ledger['events'] if x['kind'] == 'ENTRY']
        require(all(x['status'] == 'ACCEPTED' for x in ledger_accepts),
                'SIZING_PREVIEW_LEDGER_DISAGREEMENT')
        require(Decimal(ledger['cashJpy']) == available, 'SIZING_CASH_DRIFT')
        self.seen_intents.update(ids)
        return _wire({
            'schema': 'phase57-r37-sized-cash-batch-v1', 'timestamp': now,
            'ordering': 'CONFIRMED_EXIT_RELEASE_THEN_FRESH_MTM_THEN_RANKED_ENTRY_SIZING',
            'postExitPreview': preview_exit, 'freshSnapshot': snapshot,
            'sizingResolved': equity is not None, 'portfolioEquityJpy': equity,
            'targetSlotBudgetJpy': target, 'sizing': sizing, 'ledger': ledger,
            'capacity': preview.capacity, 'providerRequests': 0,
            'protectedPartitionsOpened': 0, 'safety': SAFETY,
        })


def require_select_freeze(freeze: Mapping) -> None:
    require(isinstance(freeze, Mapping), 'EXIT_FREEZE_REQUIRED')
    require(freeze.get('outcome') == 'SELECT', 'NO_SELECTION_PORTFOLIO_PERFORMANCE_FORBIDDEN')
    require(isinstance(freeze.get('selectedCandidateId'), str)
            and freeze['selectedCandidateId'].startswith('NEW_EXIT_PRECOMMITTED_'),
            'SELECTED_CANDIDATE_ID_REQUIRED')
    require(isinstance(freeze.get('freezeCommit'), str) and len(freeze['freezeCommit']) == 40,
            'EXIT_FREEZE_COMMIT_REQUIRED')


def portfolio_scorecard(*, freeze: Mapping, snapshots: list[Mapping],
                        closed_trades: list[Mapping], ledger_events: list[Mapping]) -> dict:
    """Post-freeze score only. Inputs are already-realized ledger facts."""
    require_select_freeze(freeze)
    equities = [Decimal(str(x['equityJpy'])) for x in snapshots if x.get('equityJpy') is not None]
    require(equities, 'NO_COMPLETE_PORTFOLIO_EQUITY')
    peak = equities[0]; max_dd = Decimal(0)
    for value in equities:
        peak = max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, (value / peak - 1) * 100)
    pnls = [Decimal(str(x['realizedPnlJpy'])) for x in closed_trades]
    pos, neg = [x for x in pnls if x > 0], [x for x in pnls if x < 0]
    pf = None if not neg else sum(pos, Decimal(0)) / -sum(neg, Decimal(0))
    cash_values = [Decimal(str(x['cashJpy'])) for x in snapshots]
    complete = [(Decimal(str(x['equityJpy'])), Decimal(str(x['grossExposureJpy'])))
                for x in snapshots if x.get('equityJpy') is not None
                and x.get('grossExposureJpy') is not None]
    exposure = [x for _, x in complete]
    position_shares = []
    for snap in snapshots:
        if snap.get('equityJpy') is None or Decimal(str(snap['equityJpy'])) <= 0:
            continue
        for position in (snap.get('positions') or {}).values():
            position_shares.append(Decimal(str(position['cost'])) / Decimal(str(snap['equityJpy'])))
    initial = cash.INITIAL_CASH
    turnover = sum((Decimal(str(x.get('entryNotionalJpy', 0))) +
                    Decimal(str(x.get('exitNotionalJpy', 0))) for x in closed_trades), Decimal(0))
    rejects = collections_counter(x.get('reason') for x in ledger_events
                                  if x.get('status') == 'REJECTED')
    return _wire({
        'schema': 'phase57-r37-portfolio-scorecard-v1',
        'selectedCandidateId': freeze['selectedCandidateId'],
        'portfolioReturnPct': (equities[-1] / initial - 1) * 100,
        'maxDrawdownPct': max_dd, 'profitFactor': pf,
        'winRate': None if not pnls else Decimal(sum(x > 0 for x in pnls)) / len(pnls),
        'capitalLockMeanJpy': (None if not exposure else sum(exposure, Decimal(0)) / len(exposure)),
        'capitalUtilizationMean': (None if not complete else
            sum((x / e for e, x in complete if e > 0), Decimal(0)) / len(complete)),
        'maximumSinglePositionEquityShare': None if not position_shares else max(position_shares),
        'turnoverJpy': turnover, 'minimumCashJpy': min(cash_values),
        'maximumGrossExposureJpy': None if not exposure else max(exposure),
        'insufficientCashRejects': rejects.get('NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH', 0)
                                   + rejects.get('INSUFFICIENT_AVAILABLE_CASH', 0),
        'rejectReasons': rejects, 'safety': SAFETY,
    })


def collections_counter(values) -> dict:
    out = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return out


def evaluator_bucket_attribution(*, freeze: Mapping, opportunities: list[Mapping]) -> dict:
    """>=5% attribution only after sizing; never a rank/sizing input."""
    require_select_freeze(freeze)
    require(all(set(x) == {'opportunity', 'bucket', 'entered', 'entryNotionalJpy',
                           'realizedCapturePct'} for x in opportunities),
            'EVALUATOR_ATTRIBUTION_ALLOWLIST')
    winners = [x for x in opportunities if x['bucket'] == '>=5%']
    reached = [x for x in winners if x['entered']]
    notionals = [Decimal(str(x['entryNotionalJpy'])) for x in reached]
    captures = [Decimal(str(x['realizedCapturePct'])) for x in reached
                if x['realizedCapturePct'] is not None]
    return _wire({
        'evaluatorOnly': True, 'winnerN': len(winners), 'reachedN': len(reached),
        'missedN': len(winners) - len(reached),
        'reachRate': None if not winners else Decimal(len(reached)) / len(winners),
        'missRate': None if not winners else Decimal(len(winners) - len(reached)) / len(winners),
        'capitalJpy': sum(notionals, Decimal(0)),
        'meanRealizedCapturePct': None if not captures else sum(captures, Decimal(0)) / len(captures),
        'fedBackToRankingOrSizing': False,
    })


def reproducibility_hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def assert_reproducible(a, b) -> str:
    left, right = reproducibility_hash(a), reproducibility_hash(b)
    require(left == right, 'PORTFOLIO_RUN_AB_MISMATCH')
    return left
