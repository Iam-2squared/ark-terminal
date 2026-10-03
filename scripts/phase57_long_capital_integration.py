"""Cash-only event-time research ledger; allocation never receives future paths.

Primary retains all frozen277; pre-existing173 subset is secondary diagnostics only.
Same-close reference marks are not executable fills. Missing positions stay locked.
"""
import argparse
import collections
import copy
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import subprocess

CONTRACT = Path('predict/research/phase57-long-capital-integration-v1.json')
EXIT_BASE = Path('docs/evidence/phase57-long-exit-continuation-v1')
PATHS = Path('docs/evidence/phase57-long-exit-v345-paired/paths.json.gz')
IDENTITIES = Path('docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/historical-enter-identities.json')
PREDICTIONS = Path('docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/frozen-predictions.ndjson.gz')
OUT = Path('docs/evidence/phase57-long-capital-integration-v1')
JST = dt.timezone(dt.timedelta(hours=9))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def iso(value):
    return dt.datetime.fromtimestamp(value, JST).isoformat()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def quantile(values, q):
    if not values:
        return None
    a = sorted(values)
    x = (len(a)-1)*q
    lo, hi = math.floor(x), math.ceil(x)
    return a[lo]*(hi-x)+a[hi]*(x-lo) if hi != lo else a[lo]


def stats(values):
    return {'n': len(values), 'sum': sum(values), 'mean': statistics.mean(values) if values else None,
            'median': statistics.median(values) if values else None, 'p05': quantile(values, .05),
            'min': min(values) if values else None}


def shares(values):
    a = sorted([v for v in values if v > 0], reverse=True)
    total = sum(a)
    return {'top'+str(k): sum(a[:k])/total if total else None for k in [1, 3, 5]} | {
        'hhi': sum((v/total)**2 for v in a) if total else None}


def calendar(date):
    end = 900 if date < '2024-11-05' else 930
    return list(range(545, 691, 5))+list(range(755, end+1, 5))


def minute_stamp(date, minute):
    return stamp(date+'T00:00:00+09:00')+minute*60


def causal_envelopes(events, predictions):
    result = []
    for e in events:
        p = predictions[e['selectorEventId']]
        if p['state'] != 'ENTER' or p['expectedClass'] < 2 or e['direction'] != 'LONG':
            raise ValueError('FROZEN_ENTER_OR_DIRECTION_MISMATCH')
        if p['decisionTimestamp'] != e['decisionTimestamp']:
            raise ValueError('FROZEN_TIMESTAMP_MISMATCH')
        result.append({'eventId': e['selectorEventId'], 'symbol': e['symbol'],
                       'timestamp': iso(stamp(e['decisionTimestamp'])), 'score': p['expectedClass']})
    return result


def weights(envelopes):
    proc = subprocess.run(['node', 'scripts/phase57_long_capital_weights.mjs'],
                          input=json.dumps(envelopes), text=True, capture_output=True)
    if proc.returncode:
        raise ValueError('INVALID_CAUSAL_ALLOCATION_ENVELOPE:'+proc.stderr)
    return json.loads(proc.stdout)


def replay(events, sessions, arm, weight_map, contract, exit_mode='LONG'):
    if arm not in contract['arms'] or exit_mode not in ('LONG', 'FIXED12'):
        raise ValueError('UNKNOWN_ARM')
    runtime = module('predict/long-only/phase57_long_exit_development_final.py', 'long_final')
    fixed = module('predict/long-only/phase57_long_exit_continuation_v1.py', 'fixed_reference')
    initial, lot = contract['initialCashJpy'], contract['lotSize']
    half_fee = contract['roundTripCostPctOfEntryNotional']/200
    cap = contract['maximumConcurrentPositions']
    cash = float(initial)
    realized, fees, turnover, exits_count, reuse_count = 0., 0., 0., 0, 0
    positions, decisions, closed, curve, daily = {}, [], [], [], []
    timeline = collections.defaultdict(lambda: {'entries': [], 'bars': [], 'date': None})
    ids = set()
    by_id = {}
    for e in events:
        eid = e['selectorEventId']
        if eid in ids or e['direction'] != 'LONG' or e['decisionPrice'] <= 0:
            raise ValueError('INVALID_FROZEN_IDENTITY')
        ids.add(eid)
        by_id[eid] = e
        t = stamp(e['decisionTimestamp'])
        remaining = sum(minute_stamp(e['sessionDate'], m) > t for m in calendar(e['sessionDate']))
        if remaining != e['expectedBars']:
            raise ValueError('CALENDAR_CAP_MISMATCH')
        # Only identity/calendar fields reach an entry event; future outcomes do not.
        timeline[t]['entries'].append({k: e[k] for k in
            ['selectorEventId', 'symbol', 'sessionDate', 'decisionTimestamp', 'decisionPrice', 'expectedBars']})
        for b in e['future']:
            timeline[stamp(b['end'])]['bars'].append((eid, b))
    for date in sessions:
        for minute in [540, *calendar(date)]:
            timeline[minute_stamp(date, minute)]['date'] = date
    max_concurrent, first_unknown = 0, None
    balance_error = 0.
    for t, ev in sorted(timeline.items()):
        date = dt.datetime.fromtimestamp(t, JST).date().isoformat()
        exit_at_t = 0
        for eid, b in sorted(ev['bars'], key=lambda row: row[0]):
            if eid not in positions or positions[eid]['unresolved']:
                continue
            pos = positions[eid]
            # Frozen policy consumes this completed bar only, not scheduled exit outcomes.
            out = runtime.on_completed_bar(pos['state'], b) if exit_mode == 'LONG' else fixed.on_completed_bar(pos['state'], b)
            if out['status'] == 'CENSORED':
                pos.update(unresolved=True, mark=None, missingTimestamp=iso(t), missingReason=out['reason'])
                continue
            pos['mark'] = pos['price']*(1+b['c']/100)
            if not math.isfinite(pos['mark']) or pos['mark'] <= 0:
                raise ValueError('INVALID_OBSERVED_PRICE')
            pos['markTime'] = t
            if out['status'] == 'EXIT_REFERENCE':
                gross = (pos['mark']-pos['price'])*pos['qty']
                fee = pos['notional']*half_fee
                cash += pos['mark']*pos['qty']-fee
                realized += gross-fee
                fees += fee
                turnover += pos['mark']*pos['qty']
                pnl = gross-pos['entryFee']-fee
                closed.append({'eventId': eid, 'symbol': pos['symbol'], 'sessionDate': pos['date'],
                               'entryTimestamp': pos['entryTime'], 'exitTimestamp': iso(t), 'quantity': pos['qty'],
                               'entryNotionalJpy': pos['notional'], 'exitPrice': pos['mark'], 'pnlJpy': pnl,
                               'netPct': pnl/pos['notional']*100, 'feesJpy': pos['entryFee']+fee,
                               'exitReason': out['reason'], 'holdingBars': out['exitBar']})
                del positions[eid]
                exits_count += 1
                exit_at_t += 1

        def valuation():
            if any(p['unresolved'] or p['markTime'] != t for p in positions.values()):
                return None, None
            exposure = sum(p['mark']*p['qty'] for p in positions.values())
            return cash+exposure, exposure

        eq_before, _ = valuation()
        open_slots = max(0, cap-len(positions))
        set_budget = eq_before/contract['budgetDivisor']*min(len(ev['entries']), open_slots) if eq_before is not None else None
        for e in sorted(ev['entries'], key=lambda x: (x['symbol'], x['selectorEventId'])):
            eid, price = e['selectorEventId'], e['decisionPrice']
            reason = None
            target = price*lot if arm == 'ONE_LOT_REFERENCE' else (
                set_budget*weight_map[eid] if set_budget is not None else None)
            if e['expectedBars'] == 0:
                reason = 'NO_REMAINING_REGULAR_BAR'
            elif len(positions) >= cap:
                reason = 'MAX_CONCURRENT_POSITIONS'
            elif any(p['symbol'] == e['symbol'] for p in positions.values()):
                reason = 'SYMBOL_ALREADY_OPEN'
            elif target is None:
                reason = 'CURRENT_EQUITY_UNKNOWN'
            cash_qty = math.floor((cash+1e-9)/(price*(1+half_fee))/lot)*lot
            target_qty = math.floor((target+1e-9)/price/lot)*lot if target is not None else 0
            qty = min(cash_qty, target_qty)
            if reason is None and qty < lot:
                reason = 'INSUFFICIENT_CASH' if cash_qty < lot else 'TARGET_BELOW_LOT'
            row = {'eventId': eid, 'symbol': e['symbol'], 'timestamp': iso(t), 'targetJpy': target,
                   'cashBeforeJpy': cash, 'equityAtSetStartJpy': eq_before, 'openPositionsBefore': len(positions),
                   'completedExitCount': exits_count, 'sameTimestampCashRecycling': exit_at_t > 0}
            if reason:
                row.update(status='REJECTED', reason=reason, quantity=0)
            else:
                notional = qty*price
                fee = notional*half_fee
                cash -= notional+fee
                fees += fee
                realized -= fee
                turnover += notional
                state = runtime.new_position(e['expectedBars']) if exit_mode == 'LONG' else fixed.new_state('FIXED12', e['expectedBars'])
                positions[eid] = {'symbol': e['symbol'], 'date': date, 'entryTime': iso(t), 'price': price,
                                  'qty': qty, 'notional': notional, 'entryFee': fee, 'mark': price,
                                  'markTime': t, 'state': state, 'unresolved': False}
                row.update(status='ACCEPTED', reason='CASH_LONG_ONLY', quantity=qty, notionalJpy=notional,
                           feeJpy=fee, cashAfterJpy=cash)
                if exit_at_t:
                    reuse_count += 1
            decisions.append(row)
            assert cash >= -1e-7 and len(positions) <= cap
        # Cash + historical purchase notional reconciles known ledger even if marks unavailable.
        locked = sum(p['notional'] for p in positions.values())
        balance_error = max(balance_error, abs(cash+locked-initial-realized))
        assert balance_error < 1e-5, 'CASH_ACCOUNTING_INVARIANT'
        assert all(p['qty'] % lot == 0 for p in positions.values())
        eq, exposure = valuation()
        if eq is None and first_unknown is None:
            first_unknown = iso(t)
        max_concurrent = max(max_concurrent, len(positions))
        curve.append({'timestamp': iso(t), 'sessionDate': date, 'equityJpy': eq, 'cashJpy': cash,
                      'exposureJpy': exposure, 'lockedPurchaseNotionalJpy': locked,
                      'openPositions': len(positions), 'unresolvedPositions': sum(p['unresolved'] for p in positions.values()),
                      'utilization': exposure/eq if eq is not None and eq > 0 else None})
    # No synthetic session-end liquidation. Incomplete runtime is unresolved too.
    unresolved = [{'eventId': eid, **{k: p[k] for k in ['symbol', 'qty', 'notional', 'entryFee', 'entryTime']},
                   'reason': p.get('missingReason', 'INCOMPLETE_TO_CALENDAR_CAP'),
                   'missingTimestamp': p.get('missingTimestamp')} for eid, p in positions.items()]
    complete = not unresolved and all(r['equityJpy'] is not None for r in curve)
    previous = float(initial)
    for date in sessions:
        rows = [r for r in curve if r['sessionDate'] == date]
        equity = rows[-1]['equityJpy']
        ret = (equity/previous-1)*100 if equity is not None and previous is not None and previous > 0 else None
        daily.append({'sessionDate': date, 'equityJpy': equity, 'returnPct': ret})
        previous = equity
    peak, dd_pct, dd_jpy = float(initial), 0., 0.
    for r in curve:
        if r['equityJpy'] is None:
            continue
        peak = max(peak, r['equityJpy'])
        dd_jpy = max(dd_jpy, peak-r['equityJpy'])
        dd_pct = max(dd_pct, (peak-r['equityJpy'])/peak*100)
    # Trading time only; lunch gap contributes only the following five-minute slot.
    duration = 0.
    weighted_util, weighted_concurrent, weighted_locked = 0., 0., 0.
    all_util_known = True
    for a, b in zip(curve, curve[1:]):
        if a['sessionDate'] != b['sessionDate']:
            continue
        minutes = min(5., (stamp(b['timestamp'])-stamp(a['timestamp']))/60)
        duration += minutes
        weighted_concurrent += a['openPositions']*minutes
        weighted_locked += a['lockedPurchaseNotionalJpy']*minutes
        if a['utilization'] is None:
            all_util_known = False
        else:
            weighted_util += a['utilization']*minutes
    pnls = [r['pnlJpy'] for r in closed]
    profits, losses = sum(max(0, p) for p in pnls), -sum(min(0, p) for p in pnls)
    rejection = dict(collections.Counter(r['reason'] for r in decisions if r['status'] == 'REJECTED'))
    grouped = {}
    for key in ['symbol', 'sessionDate', 'exitReason']:
        sums = collections.defaultdict(float)
        for r in closed:
            sums[r[key]] += r['pnlJpy']
        grouped[key] = dict(sorted(sums.items(), key=lambda x: (-abs(x[1]), x[0])))
    exit_metrics = {}
    for reason in grouped['exitReason']:
        rows = [r for r in closed if r['exitReason'] == reason]
        ps = [r['pnlJpy'] for r in rows]
        gp, gl = sum(max(0, p) for p in ps), -sum(min(0, p) for p in ps)
        exit_metrics[reason] = {'pnlJpy': stats(ps), 'netPct': stats([r['netPct'] for r in rows]),
                                'winRate': sum(p > 0 for p in ps)/len(ps),
                                'profitFactor': gp/gl if gl else ('INF' if gp else None)}
    entry_notionals = [r['notionalJpy'] for r in decisions if r['status'] == 'ACCEPTED']
    net_by_symbol = collections.defaultdict(float)
    for r in decisions:
        if r['status'] == 'ACCEPTED':
            net_by_symbol[r['symbol']] += r['notionalJpy']
    streak = max_streak = 0
    for r in daily:
        streak = streak+1 if r['returnPct'] is not None and r['returnPct'] < 0 else 0
        max_streak = max(streak, max_streak)
    accepted = sum(r['status'] == 'ACCEPTED' for r in decisions)
    assert len(decisions) == len(events) and accepted == len(closed)+len(unresolved)
    assert abs(sum(pnls)-sum(p['entryFee'] for p in positions.values())-realized) < 1e-5
    return {'arm': arm, 'exitMode': exit_mode, 'scope': 'REFERENCE_PRICE_DEVELOPMENT',
            'status': 'COMPLETE_REFERENCE_REPLAY' if complete else 'FULL_PORTFOLIO_UNPRICED_EXPOSURE',
            'initialEquityJpy': initial, 'finalEquityJpy': cash if complete else None,
            'totalReturnPct': (cash/initial-1)*100 if complete else None,
            'cashBalanceJpy': cash, 'realizedLedgerPnlJpy': realized, 'closedTradeNetPnlJpy': sum(pnls),
            'lockedPurchaseNotionalJpy': sum(p['notional'] for p in positions.values()),
            'maxDrawdownPct': dd_pct if complete else None, 'maxDrawdownJpy': dd_jpy if complete else None,
            'knownMarkDrawdownNotFullPortfolio': {'pct': dd_pct, 'jpy': dd_jpy},
            'firstUnknownValuation': first_unknown,
            'sessionReturn': stats([r['returnPct'] for r in daily if r['returnPct'] is not None]),
            'worstSession': min((r for r in daily if r['returnPct'] is not None), key=lambda r: r['returnPct'], default=None),
            'maxConsecutiveLosingSessions': max_streak if complete else None,
            'trade': {'candidates': len(events), 'accepted': accepted, 'closed': len(closed),
                      'unresolved': len(unresolved), 'rejected': len(events)-accepted,
                      'rejectionReasons': rejection, 'closedPnlJpy': stats(pnls),
                      'closedNetPct': stats([r['netPct'] for r in closed]),
                      'winRate': sum(p>0 for p in pnls)/len(pnls) if pnls else None,
                      'profitFactor': profits/losses if losses else ('INF' if profits else None),
                      'largestLossJpy': min(pnls, default=None),
                      'largestLossShareOfTotalLoss': -min(pnls)/losses if losses else None,
                      'tailMinus10Count': sum(r['netPct'] <= -10 for r in closed)},
            'capital': {'averageUtilization': weighted_util/duration if duration and all_util_known else None,
                        'peakUtilization': max((r['utilization'] for r in curve if r['utilization'] is not None), default=None) if complete else None,
                        'idleCashRatio': 1-weighted_util/duration if duration and all_util_known else None,
                        'maxConcurrent': max_concurrent, 'averageConcurrent': weighted_concurrent/duration if duration else None,
                        'averageLockedPurchaseNotionalJpy': weighted_locked/duration if duration else None,
                        'grossTurnoverJpy': turnover, 'grossTurnoverTimesInitial': turnover/initial,
                        'cashReleaseCount': exits_count, 'sameTimestampRecyclingEntries': reuse_count,
                        'feesJpy': fees, 'tradingMinutes': duration},
            'concentration': {'positiveTradeProfitShares': shares(pnls), 'positionNotionalShares': shares(entry_notionals),
                              'symbolNotionalShares': shares(list(net_by_symbol.values())),
                              'symbolPositiveProfitShares': shares(list(grouped['symbol'].values())),
                              'sessionPositiveProfitShares': shares(list(grouped['sessionDate'].values())), 'groupPnlJpy': grouped},
            'ledgerAudit': {'maxCashBalanceErrorJpy': balance_error, 'nonnegativeCash': True, 'hundredShareLots': True,
                            'noShortMarginLeverage': True, 'futureOutcomeInAllocator': False, 'costChargedOnce': True},
            'exitReasonPerformance': exit_metrics,
            'unresolvedPositions': unresolved, 'decisions': decisions, 'closedTrades': closed,
            'equityCurve': curve, 'sessions': daily}


def run(output=OUT):
    c = json.loads(CONTRACT.read_text())
    final = json.loads((EXIT_BASE/'development-final.json').read_text())
    pins = {str(PATHS): '1ffd7e5e3d650a676e06507faf26226ad236ec4de4a0c0446873ee16f7408959',
            str(IDENTITIES): final['upstreamPins'][str(IDENTITIES)],
            str(PREDICTIONS): final['upstreamPins'][str(PREDICTIONS)],
            str(EXIT_BASE/'measurement.json'): final['evidencePins'][str(EXIT_BASE/'measurement.json')],
            **{p: sha for p, sha in final['evidencePins'].items() if p.startswith('predict/')}}
    for p, sha in pins.items():
        assert digest(p) == sha, 'UPSTREAM_HASH_MISMATCH:'+p
    assert digest(EXIT_BASE/'development-final.json') == (EXIT_BASE/'development-final.sha256').read_text().strip()
    events = json.loads(gzip.decompress(PATHS.read_bytes()))['events']
    identities = json.loads(IDENTITIES.read_text())
    by_id = {e['selectorEventId']: e for e in events}
    assert len(by_id) == len(events) == len(identities) == 277
    for row in identities:
        assert all(by_id[row['selectorEventId']][k] == v for k, v in row.items())
    predictions = {p['selectorEventId']: p for p in map(json.loads, gzip.decompress(PREDICTIONS.read_bytes()).decode().splitlines())}
    envelopes = causal_envelopes(events, predictions)
    sessions = json.loads(Path('docs/evidence/phase57-long-exit-v345-paired/contract.json').read_text())['sessionList']
    paired_ids = set(json.loads((EXIT_BASE/'measurement.json').read_text())['pairedIdentities'])
    assert len(paired_ids) == 173 and len(sessions) == 76
    paired = [e for e in events if e['selectorEventId'] in paired_ids]
    all_weights = weights(envelopes)
    paired_weights = weights([r for r in envelopes if r['eventId'] in paired_ids])
    reports = {}
    for scope, es, ws in [('FULL277', events, all_weights), ('EXPOSED_COMMON173_DIAGNOSTIC', paired, paired_weights)]:
        reports[scope] = {arm: replay(es, sessions, arm, ws.get(arm, {}), c) for arm in c['arms']}
    reports['EXPOSED_COMMON173_FIXED_REFERENCE'] = replay(paired, sessions, 'EQUAL_MAX3', paired_weights['EQUAL_MAX3'], c, 'FIXED12')
    # Retrospective opportunity diagnosis only; explicitly after all allocation decisions.
    frozen_runtime = module('predict/long-only/phase57_long_exit_continuation_v1.py', 'evaluator_only')
    outcomes = {e['selectorEventId']: frozen_runtime.replay(e, 'BAR5_TWO_LOWER_CLOSES') for e in events}
    for group in ['FULL277', 'EXPOSED_COMMON173_DIAGNOSTIC']:
        for result in reports[group].values():
            rejected = [r for r in result['decisions'] if r['status'] == 'REJECTED']
            nets = [outcomes[r['eventId']]['netPct'] for r in rejected if outcomes[r['eventId']]['status'] == 'EXIT_REFERENCE']
            result['rejectedOpportunityEvaluatorOnly'] = {'knownOutcomeCount': len(nets), 'unknownOutcomeCount': len(rejected)-len(nets),
                'positiveNetCount': sum(x>0 for x in nets), 'netAtLeast3PctCount': sum(x>=3 for x in nets),
                'netAtLeast5PctCount': sum(x>=5 for x in nets), 'netPct': stats(nets), 'usedForDecision': False}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summary = {'status': 'CAPITAL_INTEGRATION_IMPLEMENTED_FULL277_MEASUREMENT_BLOCKED',
               'exposure': 'HISTORICAL_DEVELOPMENT_IN_SAMPLE_OUTCOME_EXPOSED', 'upstreamPins': pins,
               'contractSHA256': digest(CONTRACT), 'frozenEnterCount': 277, 'sessionCount': 76,
               'primaryFiltering': False, 'secondaryCommonCount': 173, 'secondaryExcludedCount': 104,
               'allocationDevelopmentFinalSelected': False, 'validationReady': False,
               'sourcePathAvailability': dict(collections.Counter(r.get('reason') if r['status'] == 'CENSORED' else 'EXIT_REFERENCE' for r in outcomes.values())),
               'providerRequests': 0, 'freshConsumption': 0, 'oosAccess': 0, 'freshBudgetRemaining': 195,
               'safety': c['safety'], 'reports': reports}
    for name, obj in [('measurement.json', summary), ('causal-entry-envelopes.json', envelopes)]:
        path = output/name
        assert not path.exists(), 'IMMUTABLE_OUTPUT_EXISTS'
        path.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': summary['status'], 'reports': {k: ({a: {'equity': r['finalEquityJpy'], 'accepted': r['trade']['accepted'], 'unresolved': r['trade']['unresolved']} for a,r in v.items()} if k != 'EXPOSED_COMMON173_FIXED_REFERENCE' else {'equity': v['finalEquityJpy']}) for k,v in reports.items()}}))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(OUT))
    run(parser.parse_args().output)
