"""Frozen dual Entry/Candidate A -> inherited cash-only reference allocation.

Allocation receives current six-field Entries, current public position state and
cash/equity only. R13 EXIT outcomes are evaluator-only parity checks, never inputs
for acceptance. Unknown positions remain accounting liabilities, not trades.
"""
from __future__ import annotations
import argparse
import collections
import json
import math
import sys
from pathlib import Path
from scripts import phase57_dual_entry_exit_integration_v1 as x

ROOT = x.ROOT
CONTRACT = ROOT / 'docs/evidence/phase57-dual-entry-exit-integration-v1/CAPITAL_CONTRACT_R15.json'
OLD_CONTRACT = 'predict/research/phase57-long-capital-integration-v1.json'
ARCHITECTURES = ('ONE_LOT_REFERENCE', 'EQUAL_MAX3')


def next_open(prefix, opening, cap, candidate):
    """Ask unchanged frozen policy about a known next OPEN and closed prefix.

    The stub carries only the actual OPEN. Neutral h=0/c=2 cannot arm or signal;
    it exists only so an already completed preceding signal can reference OPEN.
    No current-bar HIGH/CLOSE is observed or fed to Candidate A.
    """
    if opening['slot'] != len(prefix) + 1 or opening['slot'] > cap:
        raise ValueError('OPEN_PREFIX_CONTIGUITY')
    stub = {'slot': opening['slot'], 'o': opening['o'], 'h': 0., 'c': 2., 'missing': False}
    out = candidate.policy([*prefix, stub], {'exitBar': cap, 'grossPct': None, 'netPct': None})
    if out['status'] != 'PROTECT_EXIT':
        return None
    if out['exitBar'] != opening['slot'] or out['signalBar'] != len(prefix):
        raise ValueError('MISSED_EARLIER_CAUSAL_EXIT')
    if not prefix or opening['timestamp'] < prefix[-1]['end']:
        raise ValueError('OPEN_PRECEDES_SIGNAL_COMPLETION')
    return dict(out, status='EXIT_REFERENCE', reason='PROTECT_EXIT', exitTimestamp=opening['timestamp'])


def path_events(path):
    events = []
    for b in path['future'][:12]:
        events.append((b['end'], 0, b))
        if not b['missing']:
            events.append((b['openTimestamp'], 1,
                           {'slot': b['slot'], 'o': b['o'], 'timestamp': b['openTimestamp']}))
    return sorted(events, key=lambda r: (r[0], r[1]))


def stream_reference(path, candidate, fixed):
    state = fixed.new_state('FIXED12', path['expectedBars'])
    if not state['cap']:
        return {'status': 'CENSORED', 'netPct': None}
    prefix = []
    for _, kind, item in path_events(path):
        if kind == 0:
            out = fixed.on_completed_bar(state, item)
            if out['status'] != 'HOLD_RESEARCH_STATE':
                return out
            prefix.append(item)
        else:
            out = next_open(prefix, item, state['cap'], candidate)
            if out is not None:
                return out
    return {'status': 'CENSORED', 'netPct': None}


def allocate(entries, public_positions, cash, equity, architecture, c):
    """Pure causal batch sizing; outcomes/paths are not arguments."""
    if architecture not in ARCHITECTURES:
        raise ValueError('UNKNOWN_ALLOCATION')
    lot, cap = c['lotSize'], c['maximumConcurrentPositions']
    fee = c['roundTripCostPctOfEntryNotional'] / 200
    held = [p['symbol'] for p in public_positions]
    slots = max(0, cap - len(held))
    budget = equity / c['budgetDivisor'] * min(len(entries), slots) if equity is not None else None
    rows = []
    for e in sorted(entries, key=lambda e: (e['symbol'], e['entryId'])):
        price = e['price']
        target = price * lot if architecture == 'ONE_LOT_REFERENCE' else (
            budget / len(entries) if budget is not None else None)
        reason = None
        if e['expectedBars'] == 0:
            reason = 'NO_REMAINING_REGULAR_BAR'
        elif len(held) >= cap:
            reason = 'MAX_CONCURRENT_POSITIONS'
        elif e['symbol'] in held:
            reason = 'SYMBOL_ALREADY_OPEN'
        elif target is None:
            reason = 'CURRENT_EQUITY_UNKNOWN'
        cq = math.floor((cash + 1e-9) / (price * (1 + fee)) / lot) * lot
        tq = math.floor((target + 1e-9) / price / lot) * lot if target is not None else 0
        qty = min(cq, tq)
        if reason is None and qty < lot:
            reason = 'INSUFFICIENT_CASH' if cq < lot else 'TARGET_BELOW_LOT'
        row = {'entryId': e['entryId'], 'opportunity': e['opportunity'], 'symbol': e['symbol'],
               'timestamp': x.stamp(e['session'], e['entryMinute']), 'targetJpy': target,
               'cashBeforeJpy': cash, 'equityAtSetStartJpy': equity, 'openPositionsBefore': len(held)}
        if reason is not None:
            row.update(status='REJECTED', reason=reason, quantity=0)
        else:
            notional = qty * price
            entry_fee = notional * fee
            cash -= notional + entry_fee
            held.append(e['symbol'])
            row.update(status='ACCEPTED', reason='CASH_LONG_ONLY', quantity=qty,
                       notionalJpy=notional, feeJpy=entry_fee, cashAfterJpy=cash)
        rows.append(row)
        if cash < -1e-7 or len(held) > cap:
            raise ValueError('CASH_OR_POSITION_CAP_VIOLATION')
    return rows, cash


def replay(rows, sessions, architecture, c, candidate, fixed):
    initial = c['initialCashJpy']
    cash = float(initial)
    half_fee = c['roundTripCostPctOfEntryNotional'] / 200
    positions, decisions, closed, curve = {}, [], [], []
    timeline = collections.defaultdict(lambda: {'entries': [], 'closes': [], 'opens': [], 'calendar': False})
    entry_index = {}
    for row in rows:
        # Deliberately do not access row['candidateA'] or row['fixed12'] here.
        e, path = x.envelope(row['entry']), row['path']
        if e['entryId'] is None:
            continue
        eid = e['entryId']
        if eid in entry_index or path['entry'] != e:
            raise ValueError('FROZEN_IDENTITY_CHANGED')
        expected = len([m for m in range(540, x.calendar_end(e['session']), 5)
                        if m >= ((e['entryMinute'] + 4) // 5) * 5 and x.regular_start(m, x.calendar_end(e['session']))])
        if expected != path['expectedBars']:
            raise ValueError('CALENDAR_CAP_MISMATCH')
        e = dict(e, expectedBars=expected)
        entry_index[eid] = e
        timeline[x.stamp(e['session'], e['entryMinute'])]['entries'].append(e)
        for when, kind, item in path_events(path):
            timeline[when]['closes' if kind == 0 else 'opens'].append((eid, item))
    for day in sessions:
        for minute in [540, *range(545, 695, 5), *range(755, x.calendar_end(day) + 1, 5)]:
            timeline[x.stamp(day, minute)]['calendar'] = True
    realized = fees = turnover = balance_error = 0.
    max_positions = cash_recycling = 0
    first_unknown = None
    for when, ev in sorted(timeline.items()):
        exits_at_t = 0
        def close_position(eid, result):
            nonlocal cash, realized, fees, turnover, exits_at_t
            p = positions[eid]
            price = p['price'] * (1 + result['grossPct'] / 100)
            fee = p['notional'] * half_fee
            gross = (price - p['price']) * p['qty']
            pnl = gross - p['entryFee'] - fee
            cash += price * p['qty'] - fee
            realized += gross - fee
            fees += fee
            turnover += price * p['qty']
            closed.append({'entryId': eid, 'symbol': p['symbol'], 'session': p['session'],
                'entryTimestamp': p['entryTime'], 'entryMinute': p['entryMinute'], 'exitTimestamp': when, 'quantity': p['qty'],
                'entryNotionalJpy': p['notional'], 'exitPrice': price, 'pnlJpy': pnl,
                'netPct': pnl / p['notional'] * 100, 'feesJpy': p['entryFee'] + fee,
                'exitReason': result['reason'], 'holdingClockMinutes': x.elapsed(p['entryTime'], when)})
            del positions[eid]
            exits_at_t += 1
        # Completed observations and terminal CLOSE exits precede OPEN exits;
        # all EXIT cash release precedes the simultaneous Entry batch.
        for eid, bar in sorted(ev['closes'], key=lambda z: z[0]):
            if eid not in positions or positions[eid]['unresolved']:
                continue
            p = positions[eid]
            out = fixed.on_completed_bar(p['fixedState'], bar)
            if out['status'] == 'CENSORED':
                p.update(unresolved=True, mark=None, missingTimestamp=when, missingReason=out['reason'])
                continue
            p['prefix'].append(bar)
            p['mark'], p['markTime'] = p['price'] * (1 + bar['c'] / 100), when
            if out['status'] == 'EXIT_REFERENCE':
                close_position(eid, out)
        for eid, opening in sorted(ev['opens'], key=lambda z: z[0]):
            if eid not in positions or positions[eid]['unresolved']:
                continue
            p = positions[eid]
            out = next_open(p['prefix'], opening, p['fixedState']['cap'], candidate)
            if out is not None:
                close_position(eid, out)
        def valuation():
            if any(p['unresolved'] or p['markTime'] != when for p in positions.values()):
                return None, None
            exposure = sum(p['mark'] * p['qty'] for p in positions.values())
            return cash + exposure, exposure
        eq_before, _ = valuation()
        public = [{'symbol': p['symbol']} for p in positions.values()]
        batch, cash = allocate(ev['entries'], public, cash, eq_before, architecture, c)
        for d in batch:
            if d['status'] == 'ACCEPTED':
                e = entry_index[d['entryId']]
                fees += d['feeJpy']; realized -= d['feeJpy']; turnover += d['notionalJpy']
                positions[e['entryId']] = {'symbol': e['symbol'], 'session': e['session'],
                    'entryTime': when, 'entryMinute': e['entryMinute'], 'price': e['price'], 'qty': d['quantity'],
                    'notional': d['notionalJpy'], 'entryFee': d['feeJpy'],
                    'mark': e['price'], 'markTime': when, 'unresolved': False, 'prefix': [],
                    'fixedState': fixed.new_state('FIXED12', e['expectedBars'])}
                cash_recycling += exits_at_t > 0
            d['sameTimestampCashRecycling'] = exits_at_t > 0
            decisions.append(d)
        locked = sum(p['notional'] for p in positions.values())
        balance_error = max(balance_error, abs(cash + locked - initial - realized))
        if balance_error >= 1e-5 or cash < -1e-7:
            raise ValueError('CASH_RECONCILIATION_FAILURE')
        if any(p['qty'] % c['lotSize'] for p in positions.values()):
            raise ValueError('LOT_INVARIANT_FAILURE')
        max_positions = max(max_positions, len(positions))
        if ev['calendar'] or ev['entries'] or exits_at_t:
            equity, exposure = valuation()
            if equity is None and first_unknown is None:
                first_unknown = when
            curve.append({'timestamp': when, 'session': when[:10], 'cashJpy': cash,
                'equityJpy': equity, 'exposureJpy': exposure, 'lockedPurchaseNotionalJpy': locked,
                'openPositions': len(positions), 'unresolvedPositions': sum(p['unresolved'] for p in positions.values()),
                'utilization': exposure / equity if equity is not None and equity > 0 else None})
    accepted = sum(d['status'] == 'ACCEPTED' for d in decisions)
    if len(decisions) != len(entry_index) or accepted != len(closed) + len(positions):
        raise ValueError('POSITION_COUNT_RECONCILIATION')
    if abs(sum(r['pnlJpy'] for r in closed) - sum(p['entryFee'] for p in positions.values()) - realized) >= 1e-5:
        raise ValueError('REALIZED_PNL_RECONCILIATION_FAILURE')
    complete = not positions and all(r['equityJpy'] is not None for r in curve)
    pnls = [r['pnlJpy'] for r in closed]
    profits, losses = sum(max(0, n) for n in pnls), -sum(min(0, n) for n in pnls)
    peak, drawdown = float(initial), 0.
    for r in curve:
        if r['equityJpy'] is not None:
            peak = max(peak, r['equityJpy'])
            drawdown = max(drawdown, (peak - r['equityJpy']) / peak * 100)
    duration = weighted_lock = weighted_count = weighted_util = 0.
    utilization_known = True
    for a, b in zip(curve, curve[1:]):
        if a['session'] != b['session']:
            continue
        minutes = min(5., x.elapsed(a['timestamp'], b['timestamp']))
        duration += minutes
        weighted_lock += a['lockedPurchaseNotionalJpy'] * minutes
        weighted_count += a['openPositions'] * minutes
        if a['utilization'] is None:
            utilization_known = False
        else:
            weighted_util += a['utilization'] * minutes
    unresolved = [{'entryId': eid, **{k: p[k] for k in ('symbol','qty','notional','entryFee','entryTime')},
                   'reason': p.get('missingReason','INCOMPLETE_TO_CALENDAR_CAP'),
                   'missingTimestamp': p.get('missingTimestamp')} for eid, p in positions.items()]
    summary = {'architecture': architecture, 'status': 'COMPLETE_REFERENCE_REPLAY' if complete else 'FULL_PORTFOLIO_UNPRICED_EXPOSURE',
        'opportunities': len(rows), 'entryFills': len(entry_index), 'noEntry': len(rows) - len(entry_index),
        'accepted': accepted, 'closed': len(closed), 'unresolved': len(positions),
        'rejected': len(decisions) - accepted,
        'rejectionReasons': dict(sorted(collections.Counter(d['reason'] for d in decisions if d['status'] == 'REJECTED').items())),
        'initialCashJpy': initial, 'cashBalanceJpy': cash, 'realizedLedgerPnlJpy': realized,
        'closedTradePnlJpy': sum(pnls), 'lockedPurchaseNotionalJpy': sum(p['notional'] for p in positions.values()),
        'finalEquityJpy': cash if complete else None, 'portfolioReturnPct': (cash / initial - 1) * 100 if complete else None,
        'maxDrawdownPct': drawdown if complete else None, 'knownMarkDrawdownNotFullPortfolioPct': drawdown,
        'firstUnknownValuation': first_unknown,
        'closedTradeProfitFactorNotFullPortfolio': profits / losses if losses else ('INF' if profits else None),
        'closedTradeWinRatePct': 100 * sum(n > 0 for n in pnls) / len(pnls) if pnls else None,
        'feesJpy': fees, 'turnoverJpy': turnover, 'maxConcurrent': max_positions,
        'averageLockedPurchaseNotionalJpy': weighted_lock / duration if duration else None,
        'averageConcurrent': weighted_count / duration if duration else None,
        'averageUtilization': weighted_util / duration if duration and utilization_known else None,
        'cashReleaseCount': len(closed), 'sameTimestampRecyclingEntries': cash_recycling,
        'sessionCount': len(sessions), 'tradingMinutes': duration,
        'maxCashBalanceErrorJpy': balance_error, 'concentration': {}, 'safety': x.SAFETY}
    for field in ('symbol','session','entryMinute','exitReason'):
        sums = collections.defaultdict(float)
        counts = collections.Counter()
        for r in closed:
            sums[r[field]] += r['pnlJpy']; counts[r[field]] += 1
        total_positive = sum(max(0, v) for v in sums.values())
        summary['concentration'][field] = {'closedCounts': dict(sorted(counts.items())),
            'closedPnlJpy': dict(sorted(sums.items())),
            'top5PositivePnlShare': sum(sorted((max(0,v) for v in sums.values()),reverse=True)[:5]) / total_positive if total_positive else None}
    return {'summary': summary, 'decisions': decisions, 'closedTrades': closed,
            'unresolvedPositions': unresolved, 'equityCurve': curve}


def run(ledger_path, outdir, execution_head):
    contract = x.read(CONTRACT)
    if contract['safety'] != x.SAFETY or contract['architectures'] != list(ARCHITECTURES):
        raise ValueError('CAPITAL_CONTRACT_CHANGED')
    for name, sha in contract['inputPins'].items():
        if x.digest(ROOT / name) != sha:
            raise ValueError('INPUT_HASH_MISMATCH:' + name)
    if x.digest(ledger_path) != contract['exitLedgerSHA256']:
        raise ValueError('EXIT_LEDGER_HASH_MISMATCH')
    c = x.read(ROOT / OLD_CONTRACT)
    if (c['initialCashJpy'],c['lotSize'],c['maximumConcurrentPositions'],c['budgetDivisor']) != (1000000,100,10,3):
        raise ValueError('INHERITED_CAPITAL_CONSTANT_CHANGED')
    ledgers = x.read(ledger_path)
    protocol = x.read(ROOT / x.COHORT)
    sessions, expected_ids = protocol['evaluationSessions'], set(protocol['opportunityIds'])
    candidate = x.load_module(x.CANDIDATE, 'capital_frozen_candidate')
    fixed = x.load_module(x.FIXED, 'capital_frozen_fixed12')
    reports, parity_count = {}, 0
    for arm in x.ARMS:
        rows = ledgers[arm]
        if len(rows) != 2155 or {r['entry']['opportunity'] for r in rows} != expected_ids:
            raise ValueError('FULL2155_IDENTITY_MISMATCH')
        reports[arm] = {a: replay(rows,sessions,a,c,candidate,fixed) for a in ARCHITECTURES}
        # Evaluator-only parity, strictly after both allocation replays above.
        outcomes = {}
        for r in rows:
            if r['entry']['entryId'] is None:
                continue
            actual = stream_reference(r['path'],candidate,fixed)
            reference = r['candidateA']
            if actual['status'] != reference['status']:
                raise ValueError('STREAM_VS_R13_STATUS_PARITY')
            if actual['status'] == 'EXIT_REFERENCE' and (
                actual['exitTimestamp'] != reference['exitTimestamp'] or
                not math.isclose(actual['netPct'],reference['netPct'],abs_tol=1e-10)):
                raise ValueError('STREAM_VS_R13_EXIT_PARITY')
            outcomes[r['entry']['entryId']] = reference
            parity_count += 1
        for report in reports[arm].values():
            for trade in report['closedTrades']:
                ref = outcomes[trade['entryId']]
                if trade['exitTimestamp'] != ref['exitTimestamp'] or not math.isclose(trade['netPct'],ref['netPct'],abs_tol=1e-9):
                    raise ValueError('CAPITAL_TRADE_VS_R13_PARITY')
    summary = {'status':'DUAL_ENTRY_CAPITAL_REFERENCE_INTEGRATION_NOT_PROMOTION',
        'scope':'OUTCOME_EXPOSED_DEVELOPMENT_FULL2155_NO_COMPLETE_CASE_FILTER',
        'reports':{arm:{a:r['summary'] for a,r in rs.items()} for arm,rs in reports.items()},
        'streamVsFrozenR13ParityFills':parity_count,'rankRiskAdaptiveArmsNotSubstituted':True,
        'finalEntrySelected':False,'providerRequests':0,'newProtectedPartitionsOpened':0,'safety':x.SAFETY}
    for name, sha in contract['inputPins'].items():
        if x.digest(ROOT / name) != sha:
            raise ValueError('INPUT_MUTATED_DURING_REPLAY:' + name)
    if x.digest(ledger_path) != contract['exitLedgerSHA256']:
        raise ValueError('EXIT_LEDGER_MUTATED_DURING_REPLAY')
    out = Path(outdir);out.mkdir(parents=True,exist_ok=False)
    x.write_new(out/'summary.json',summary)
    x.write_new(out/'ledgers.json.gz',reports)
    x.write_new(out/'manifest.json',{'executionHead':execution_head,'contractSHA256':x.digest(CONTRACT),
        'scriptSHA256':x.digest(__file__),'exitLedgerSHA256':x.digest(ledger_path),
        'inputPins':contract['inputPins'],'outputs':{n:x.digest(out/n) for n in ('summary.json','ledgers.json.gz')},'safety':x.SAFETY})
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exit-ledger',required=True);p.add_argument('--out',required=True);p.add_argument('--execution-head',required=True)
    args=p.parse_args();sys.addaudithook(x.no_network)
    s=run(args.exit_ledger,args.out,args.execution_head)
    print(json.dumps({'status':s['status'],'streamParityFills':s['streamVsFrozenR13ParityFills'],
        'reports':{a:{k:{f:v[f] for f in ('status','accepted','closed','unresolved','portfolioReturnPct')} for k,v in rs.items()} for a,rs in s['reports'].items()}}))


if __name__=='__main__':
    main()
