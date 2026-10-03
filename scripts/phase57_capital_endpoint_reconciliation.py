"""Post-result cash-endpoint audit; never changes a trade, mark, rank or Gate.

The original all-event validity test remains authoritative for continuous
intraday statistics. This separate report certifies flat, post-close cash
endpoints and computes endpoint-only metrics. Only pinned result files are read.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

VARIANTS = ('IM_MAX3', 'IM_MAX4', 'IM_MAX5', 'R1_MAX3', 'R1_MAX4', 'R1_MAX5')
SAFETY_KEYS = ('executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
               'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
               'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted')
SPEC_SHA256 = '7859626b18ddd85ea48920d07ba89b79e7e01a34e4960c11fbfb482f16fad456'
INITIAL = Decimal('1000000')
TOLERANCE = Decimal('0.00000001')


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def dec(value: Any) -> Decimal:
    require(not isinstance(value, bool) and value is not None, 'INVALID_MONEY_TYPE')
    result = Decimal(str(value))
    require(result.is_finite(), 'NONFINITE_MONEY')
    return result


def equal(left: Any, right: Any, reason: str) -> None:
    require(abs(dec(left) - dec(right)) <= TOLERANCE, reason)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safety(value: dict) -> None:
    require(set(value) == set(SAFETY_KEYS) and all(x is False for x in value.values()),
            'SAFETY9_NOT_FALSE')


def timestamp(session: str, minute: int) -> str:
    return f'{session}T{minute//60:02}:{minute%60:02}:00+09:00'


def audit_ledger(ledger: dict, sessions: list[str], initial: Decimal = INITIAL) -> dict:
    """Independently reconstruct cash/ownership from stored fills, not a new replay."""
    require(sessions and sorted(set(sessions)) == sessions, 'SESSION_IDENTITY')
    safety(ledger['safety'])
    events, snapshots = ledger['events'], ledger['snapshots']
    require(events and len(events) == len(snapshots), 'EVENT_SNAPSHOT_COUNT')
    require(sorted({x['session'] for x in snapshots}) == sessions, 'SNAPSHOT_SESSIONS')
    require(ledger['capacity'] in (3, 4, 5), 'CAPACITY')
    funded, closed = ledger['funded'], ledger['closed']
    closed_by_id = {x['entryId']: x for x in closed}
    require(len(closed_by_id) == len(closed), 'DUPLICATE_CLOSE')
    cash, realized = initial, Decimal(0)
    active: dict[str, dict] = {}
    entries_seen, exits_seen = set(), set()
    unresolved = set()
    last_stamp = None
    endpoints: dict[str, dict] = {}
    observed_nulls = 0
    for event, snapshot in zip(events, snapshots):
        stamp = timestamp(event['session'], event['minute'])
        require(stamp == snapshot['timestamp'] and event['session'] == snapshot['session']
                and event['minute'] == snapshot['minute'], 'EVENT_TIME_IDENTITY')
        require(last_stamp is None or stamp > last_stamp, 'NONMONOTONE_EVENTS')
        last_stamp = stamp
        for exit_event in event['exitEvents']:
            eid = exit_event['entryId']
            require(eid in active, 'EXIT_WITHOUT_OWNERSHIP')
            if exit_event['status'] == 'CLOSED':
                require(eid not in exits_seen, 'DOUBLE_EXIT')
                trade = closed_by_id[eid]
                require(trade['exitTimestamp'] == stamp, 'EXIT_TIME_MISMATCH')
                require(trade['quantity'] == active[eid]['quantity'], 'EXIT_QUANTITY')
                gross, fee = dec(exit_event['proceedsJpy']), dec(exit_event['sellCostJpy'])
                require(gross > 0 and fee >= 0, 'INVALID_PROCEEDS_FEE')
                pnl = gross - fee - dec(active[eid]['notionalJpy'])
                equal(pnl, exit_event['realizedPnlJpy'], 'EXIT_PNL_MISMATCH')
                equal(pnl, trade['realizedPnlJpy'], 'CLOSED_TABLE_PNL')
                equal(fee, trade['sellCostJpy'], 'CLOSED_TABLE_FEE')
                equal(active[eid]['notionalJpy'], trade['notionalJpy'], 'CLOSED_NOTIONAL')
                cash += gross - fee
                realized += pnl
                del active[eid]
                unresolved.discard(eid)
                exits_seen.add(eid)
            else:
                require(exit_event['status'] == 'UNRESOLVED_NO_CASH_RELEASE', 'UNKNOWN_EXIT_STATUS')
                require(exit_event.get('proceedsJpy') in (None, 0, '0') and
                        exit_event.get('realizedPnlJpy') in (None, 0, '0'),
                        'UNRESOLVED_CREATED_PROCEEDS')
                unresolved.add(eid)
        for size in event['sizing']:
            equal(size['cashBeforeSizingJpy'], cash, 'SIZING_CASH_BEFORE')
            if size['status'] == 'SIZED':
                eid = size['entryId']
                require(eid not in entries_seen, 'DUPLICATE_ENTRY')
                trade = funded[eid]
                quantity = size['quantity']
                require(type(quantity) is int and quantity > 0 and quantity % 100 == 0,
                        'INVALID_LONG_LOT')
                require(quantity == trade['quantity'] and trade['entryTimestamp'] == stamp,
                        'ENTRY_IDENTITY')
                cost = dec(size['costJpy'])
                equal(cost, trade['notionalJpy'], 'ENTRY_NOTIONAL')
                equal(cost, dec(trade['effectiveEntryPrice']) * quantity, 'ENTRY_PRICE_LOT')
                require(cost > 0 and cost <= cash, 'BORROWED_BUYING_POWER')
                cash -= cost
                active[eid] = trade
                entries_seen.add(eid)
                require(len(active) <= ledger['capacity'], 'CAPACITY_OVERFLOW')
                require(len({x['symbol'] for x in active.values()}) == len(active),
                        'SIMULTANEOUS_DUPLICATE_SYMBOL')
            else:
                require(size['status'] == 'REJECTED' and size['quantity'] == 0,
                        'UNKNOWN_SIZING_STATUS')
            equal(size['cashAfterSizingJpy'], cash, 'SIZING_CASH_AFTER')
        require(cash >= 0, 'NEGATIVE_CASH')
        equal(event['cashJpy'], cash, 'EVENT_CASH')
        equal(snapshot['cashJpy'], cash, 'SNAPSHOT_CASH')
        equal(snapshot['realizedPnlJpy'], realized, 'SNAPSHOT_REALIZED')
        positions = snapshot['positions']
        require(len(positions) == snapshot['openCount'] == len(active), 'OPEN_COUNT')
        require({x['entryId'] for x in positions} == set(active), 'OPEN_IDENTITIES')
        require(snapshot['unresolvedCount'] == len(unresolved), 'UNRESOLVED_COUNT')
        marked = Decimal(0)
        unmarkable = 0
        for position in positions:
            eid = position['entryId']
            require(position['quantity'] == active[eid]['quantity'], 'POSITION_QUANTITY')
            equal(position['costBasisJpy'], active[eid]['notionalJpy'], 'POSITION_BASIS')
            require(position['unresolvedExit'] == (eid in unresolved), 'UNRESOLVED_FLAG')
            if position['markPrice'] is None:
                unmarkable += 1
                require(position['markedNotionalJpy'] is None and
                        position['missingReason'] is not None, 'MISSING_MARK_FABRICATION')
            else:
                require(position['markKnownAt'] is not None and
                        dt.datetime.fromisoformat(position['markKnownAt']) <=
                        dt.datetime.fromisoformat(stamp), 'FUTURE_MARK')
                mark = dec(position['markPrice']) * position['quantity']
                require(mark > 0, 'NONPOSITIVE_MARK')
                equal(mark, position['markedNotionalJpy'], 'MARKED_NOTIONAL')
                marked += mark
        if snapshot['equityValid']:
            require(unmarkable == 0, 'VALID_WITH_MISSING_POSITION')
            equal(snapshot['equityJpy'], cash + marked, 'MARK_EQUITY')
            equal(snapshot['grossExposureJpy'], marked, 'GROSS_EXPOSURE')
            equal(snapshot['equityJpy'], initial + realized + dec(snapshot['unrealizedPnlJpy']),
                  'PNL_EQUITY_IDENTITY')
            equal(event['postEventEquityJpy'], snapshot['equityJpy'], 'EVENT_EQUITY')
        else:
            observed_nulls += 1
            require(unmarkable > 0 and snapshot['equityJpy'] is None and
                    event['postEventEquityJpy'] is None, 'NULL_EQUITY_INTEGRITY')
        if event['minute'] == 930:
            require(event['session'] not in endpoints, 'DUPLICATE_EOD')
            flat = not active and not unresolved and snapshot['equityValid']
            endpoints[event['session']] = {
                'session': event['session'], 'timestamp': stamp,
                'certifiedFlatEod': flat, 'cashJpy': str(cash),
                'equityJpy': str(cash) if flat else None,
                'openCount': len(active), 'unresolvedCount': len(unresolved),
                'reason': 'RECONCILED_FLAT_CASH' if flat else 'OPEN_POSITION_NOT_CASH_ENDPOINT'}
    require(entries_seen == set(funded) and exits_seen == set(closed_by_id), 'TRADE_CONSERVATION')
    require(set(active) == set(ledger['endOpenEntryIds']), 'END_OPEN')
    require(unresolved == set(ledger['unresolvedEntryIds']), 'END_UNRESOLVED')
    equal(cash, ledger['finalCashJpy'], 'FINAL_CASH')
    equal(initial + realized, cash + sum((dec(x['notionalJpy']) for x in active.values()),
                                       Decimal(0)), 'CASH_COST_BASIS_IDENTITY')
    return {'status': 'PASS', 'eventsAudited': len(events),
            'fundedAudited': len(funded), 'closedAudited': len(closed),
            'intradayNullEvents': observed_nulls, 'remainingOpen': sorted(active),
            'finalCashJpy': str(cash), 'confirmedRealizedPnlJpy': str(realized),
            'endpoints': [endpoints.get(day, {'session': day, 'timestamp': timestamp(day, 930),
                'certifiedFlatEod': False, 'cashJpy': None, 'equityJpy': None,
                'openCount': None, 'unresolvedCount': None, 'reason': 'MISSING_SCHEDULED_EOD'})
                for day in sessions]}


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    z = (len(ordered) - 1) * q
    low = int(z)
    return ordered[low] + (ordered[min(low+1, len(ordered)-1)]-ordered[low])*(z-low)


def endpoint_metrics(endpoints: list[dict], initial: Decimal = INITIAL) -> dict:
    require(endpoints and initial > 0, 'EMPTY_OR_NONPOSITIVE_INITIAL')
    require([e['session'] for e in endpoints] == sorted({e['session'] for e in endpoints}),
            'ENDPOINT_ORDER')
    previous: Decimal | None = initial
    daily = []
    for endpoint in endpoints:
        end = dec(endpoint['equityJpy']) if endpoint['certifiedFlatEod'] else None
        require(end is None or end > 0, 'NONPOSITIVE_EOD')
        rate = float((end/previous-1)*100) if end is not None and previous is not None else None
        daily.append({**endpoint, 'startEquityJpy': None if previous is None else str(previous),
                      'dailyReturnPct': rate, 'dailyReturnValid': rate is not None})
        previous = end  # Never skip/bridge a missing day; later valid adjacent pairs recover.
    n = len(daily)
    full = all(row['dailyReturnValid'] for row in daily)
    endpoint_return = float((previous/initial-1)*100) if previous is not None else None
    geo = 100 * math.expm1(math.log(float(previous/initial))/n) if previous is not None else None
    rates = [row['dailyReturnPct'] for row in daily]
    stats: dict[str, Any] = {key: None for key in
        ('arithmeticDailyPct','medianDailyPct','stdDailyPct','positiveDayRate','negativeDayRate',
         'bestDayPct','worstDayPct','p05DailyPct','p10DailyPct','maxDrawdownEodPct')}
    high, worst = initial, Decimal(0)
    for row in daily:
        row['drawdownEodPct'] = None
        if full:
            value = dec(row['equityJpy'])
            high = max(high, value)
            dd = (value/high-1)*100
            row['drawdownEodPct'] = float(dd)
            worst = min(worst, dd)
    if full:
        product = math.prod(1+x/100 for x in rates)
        require(math.isclose(product, float(previous/initial), rel_tol=1e-11), 'DAILY_TELESCOPE')
        stats.update(arithmeticDailyPct=statistics.fmean(rates), medianDailyPct=statistics.median(rates),
                     stdDailyPct=statistics.stdev(rates) if n>1 else 0.0,
                     positiveDayRate=sum(x>0 for x in rates)/n, negativeDayRate=sum(x<0 for x in rates)/n,
                     bestDayPct=max(rates), worstDayPct=min(rates),
                     p05DailyPct=percentile(rates,.05), p10DailyPct=percentile(rates,.10),
                     maxDrawdownEodPct=float(worst))
    return {'scheduledSessions': n, 'certifiedEodSessions': sum(e['certifiedFlatEod'] for e in endpoints),
            'validDailyReturns': sum(e['dailyReturnValid'] for e in daily),
            'completeEodSeries': full, 'initialEquityJpy': str(initial),
            'certifiedFinalEquityJpy': None if previous is None else str(previous),
            'endpointReturnPct': endpoint_return, 'geometricPerScheduledSessionPct': geo,
            'simpleTotalDividedBySessionsPct': endpoint_return/n if endpoint_return is not None else None,
            'mechanicalNotForecastPct': {str(m):100*math.expm1(math.log1p(geo/100)*m)
                                       for m in (20,60,120,240)} if geo is not None else None,
            'strictIntradayMaxDrawdownPct': None, 'daily': daily, **stats}


def loose_enrichment_ceiling(total: int, known: int, selected: int) -> float | None:
    require(0 <= known <= total and 0 <= selected <= total, 'INVALID_RANK_COUNTS')
    minimum_known_selected = max(0, selected-(total-known))
    return known/minimum_known_selected if minimum_known_selected > 0 else None


def rank_geometry(report: dict) -> dict:
    require(report['result']['selected'] is None and report['result']['status']=='NO_SELECTION_STOP',
            'UNEXPECTED_SELECTION')
    arms = {}
    rows = []
    for arm, control in report['result']['control'].items():
        total, known, selected = control['totalCandidates'], control['totalKnown'], control['top']['3']['selected']
        bound = loose_enrichment_ceiling(total, known, selected)
        arms[arm] = {'totalCandidates':total,'evaluableCandidates':known,'top3Selected':selected,
                     'top3SelectionFraction':selected/total,'looseTop3EnrichmentCeiling':bound,
                     'unchangedFrozenMinimum':1.15, 'minimumExceedsLooseCeiling':bound is not None and 1.15>bound,
                     'notTradableAndNotASelection':True}
        for name, card in [('EXISTING_CONTROL',control)]+[(name,items[arm]) for name,items in report['result']['candidates'].items()]:
            for k, item in card['top'].items():
                rows.append({'arm':arm,'ranker':name,'k':int(k),'totalCandidates':total,
                             'evaluableCandidates':known,'selected':item['selected'],
                             'knownSelected':item['knownSelected'],'hit':item['hit'],
                             'hitRate':item['hitRate'],'baselineHitRate':control['baselineHitRate'],
                             'enrichment':item['enrichment'],'reach':item['reach']})
    return {'formalSelection':'NO_SELECTION_STOP','gateUnchanged':True,'geometry':arms,'rows':rows}


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(source: Path, spec_path: Path, output: Path) -> dict:
    require(source.resolve()!=output.resolve(), 'OUTPUT_OVERWRITES_SOURCE')
    require(digest(spec_path)==SPEC_SHA256,'SPEC_HASH')
    spec = json.loads(spec_path.read_bytes())
    expected = {'report.json'} | {v+'/ledger.json.gz' for v in VARIANTS}
    require(set(spec['sourceFiles'])==expected,'SOURCE_ALLOWLIST')
    for name, pin in spec['sourceFiles'].items():
        require(digest(source/name)==pin, 'INPUT_HASH:'+name)
    report = json.loads((source/'report.json').read_bytes())
    safety(report['safety'])
    require(report['protocolSha256']==spec['originalProtocolSha256'] and
            report['modelFits']==24, 'ORIGINAL_IDENTITY')
    sessions = report['portfolio']['sessions']
    require(len(sessions)==24 and sessions==report['result']['sessions'],'ORIGINAL_SESSION_WINDOW')
    output.mkdir(parents=True, exist_ok=True)
    variants, summaries, all_daily = {}, [], []
    with localcontext() as context:
        context.prec = 50
        for name in VARIANTS:
            ledger = json.loads(gzip.decompress((source/name/'ledger.json.gz').read_bytes()))
            audit = audit_ledger(ledger, sessions)
            metrics = endpoint_metrics(audit['endpoints'])
            variants[name] = {'audit':audit, 'metrics':metrics}
            summaries.append({'variant':name,**{k:v for k,v in metrics.items()
                                               if k not in ('daily','mechanicalNotForecastPct')},
                              'intradayNullEvents':audit['intradayNullEvents'],
                              'cashAuditEvents':audit['eventsAudited'],
                              'endOpenCount':len(audit['remainingOpen'])})
            all_daily += [{'variant':name,**row} for row in metrics['daily']]
    ranking = rank_geometry(report)
    result = {'schema':'phase57-capital-endpoint-report-v1',
              'status':'POST_RESULT_SUPPLEMENT_NOT_SELECTION', 'specSha256':SPEC_SHA256,
              'basisHead':spec['basisHead'],'originalArtifactSha256':spec['originalArtifactSha256'],
              'originalProtocolAndNoSelectionUnchanged':True,'ranker':'EXISTING_R35_CAUSAL_CONTROL',
              'exit':'TERMINAL_HOLD_BENCHMARK_NOT_FINAL','safety':report['safety'],
              'sessions':sessions,'calendarSpanInclusiveDays':(
                  dt.date.fromisoformat(sessions[-1])-dt.date.fromisoformat(sessions[0])).days+1,
              'variants':variants,'ranking':ranking,
              'newModelFits':0,'newPredictionRefits':0,'newPolicyReplays':0,
              'newProviderRequests':0,'newProtectedOpened':0,
              'priorExposureUnchanged':'R49 and superseded v0 out-of-allowlist decode retained; this report reads only seven pinned result files.'}
    (output/'endpoint-report.json').write_bytes(canonical(result))
    write_csv(output/'endpoint-summary.csv',summaries)
    write_csv(output/'daily-endpoints.csv',all_daily)
    write_csv(output/'rank-scorecard.csv',ranking['rows'])
    manifest = {p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='output-hashes.json'}
    (output/'output-hashes.json').write_bytes(canonical(manifest))
    for name, pin in spec['sourceFiles'].items():
        require(digest(source/name)==pin, 'SOURCE_MODIFIED:'+name)
    return result


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    report=build(args.source,args.spec,args.out)
    print(json.dumps({'status':report['status'],
                      'completeEodVariants':sum(v['metrics']['completeEodSeries'] for v in report['variants'].values()),
                      'rankSelection':'NO_SELECTION_STOP','newFits':0,'newReplays':0},sort_keys=True))


if __name__=='__main__':
    main()
