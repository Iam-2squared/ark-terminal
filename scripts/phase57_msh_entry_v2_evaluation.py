"""Evaluator-only metrics, frozen gates and inner-calibration threshold selection."""
import collections
import math
import statistics
from predict.research.phase57_msh_entry_long_v2_d30 import timestamp, THRESHOLDS, IntegrityError

LEVELS = (1,2,3,5)


def quantile(values, q):
    if not values:
        return None
    a = sorted(values)
    x = (len(a)-1)*q
    lo,hi = math.floor(x),math.ceil(x)
    return a[lo] if lo == hi else a[lo]*(hi-x)+a[hi]*(x-lo)


def summary(values):
    return {'n':len(values),'mean':statistics.mean(values) if values else None,
            'median':statistics.median(values) if values else None,'p05':quantile(values,.05),
            'worst':min(values) if values else None}


def preservation(rows, selected_ids, labels, paths=None):
    """Shared first-opportunity anchors; same original endpoint, never future filtering."""
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row['symbolSessionId']].append(row)
    result = {str(k):{'anchors':0,'hits':0,'unknownNumerators':0,'rate':None} for k in LEVELS}
    for values in groups.values():
        ordered = sorted(values,key=lambda r:(timestamp(r['decisionTimestamp']),r['selectorEventId']))
        first = ordered[0]
        anchor = labels[first['selectorEventId']]
        if not anchor['labelable']:
            continue
        entries = [r for r in ordered if r['selectorEventId'] in selected_ids]
        if len(entries) > 1:
            raise IntegrityError('REPEATED_SYMBOL_SESSION_ENTER')
        entry = entries[0] if entries else None
        endpoint = timestamp(first['decisionTimestamp'])+1800
        remaining = None
        unknown = False
        if entry and timestamp(entry['decisionTimestamp']) < endpoint:
            eid = entry['selectorEventId']
            if eid == first['selectorEventId']:
                remaining = anchor['mfePct']
            elif paths is None or eid not in paths:
                unknown = True
            else:
                start = timestamp(entry['decisionTimestamp'])
                expected = list(range(int(start),int(endpoint),300))
                by_start = {int(timestamp(b['start'])):b for b in paths[eid]['future']}
                bars = [by_start.get(t) for t in expected]
                if not bars or any(not b or b['missing'] for b in bars):
                    unknown = True
                else:
                    remaining = max(0.,max(b['h'] for b in bars))
        for k in LEVELS:
            if anchor['mfePct'] >= k:
                r = result[str(k)]
                r['anchors'] += 1
                r['unknownNumerators'] += int(unknown)
                r['hits'] += int(remaining is not None and remaining >= k)
    for value in result.values():
        value['rate'] = value['hits']/value['anchors'] if value['anchors'] else None
    return result


def entry_metrics(rows, decisions, labels, sessions, paths=None):
    allowed = {r['selectorEventId'] for r in rows}
    if len(allowed) != len(rows) or len({p['eventId'] for p in decisions}) != len(decisions):
        raise IntegrityError('DUPLICATE_EVALUATION_IDENTITY')
    selected = {p['eventId'] for p in decisions if p['state'] == 'ENTER'}
    if not selected <= allowed:
        raise IntegrityError('ENTRY_OUTSIDE_EVALUATION_SCOPE')
    entries = [r for r in rows if r['selectorEventId'] in selected]
    complete = [r for r in entries if labels[r['selectorEventId']]['labelable']]
    mae = [labels[r['selectorEventId']]['trueMaePct'] for r in complete]
    d30 = [-v for v in mae]
    mfe = [labels[r['selectorEventId']]['mfePct'] for r in complete]
    per_symbol = collections.defaultdict(list)
    for r,d in zip(complete,d30):
        per_symbol[r['symbol']].append(d)
    macro = {s:statistics.mean(v) for s,v in sorted(per_symbol.items())}
    n_tail = max(1,math.ceil(.05*len(d30)))
    return {'candidateRows':len(rows),'sessions':len(sessions),'enterCount':len(entries),
        'enterRate':len(entries)/len(rows) if rows else None,
        'enterPerSession':len(entries)/len(sessions) if sessions else None,
        'uniqueSymbols':len({r['symbol'] for r in entries}),
        'tradesPerSymbol':dict(sorted(collections.Counter(r['symbol'] for r in entries).items())),
        'strict30mCount':len(complete),'unlabelableEnterCount':len(entries)-len(complete),
        'coverageRate':len(complete)/len(entries) if entries else None,
        'censorReasons':dict(collections.Counter(labels[r['selectorEventId']]['reason'] for r in entries if not labels[r['selectorEventId']]['labelable'])),
        'meanD30':statistics.mean(d30) if d30 else None,
        'ES95D30':statistics.mean(sorted(d30,reverse=True)[:n_tail]) if d30 else None,
        'MAE':summary(mae),'MFE':summary(mfe),
        'adverseCounts':{str(k):sum(v <= -k for v in mae) for k in (2,5,10)},
        'adverseRates':{str(k):sum(v <= -k for v in mae)/len(mae) if mae else None for k in (2,5,10)},
        'precision':{str(k):{'hits':sum(v >= k for v in mfe),'n':len(mfe),
                             'rate':sum(v >= k for v in mfe)/len(mfe) if mfe else None} for k in LEVELS},
        'preservation':preservation(rows,selected,labels,paths),
        'symbolMeanD30':macro,'symbolMacroMeanD30':statistics.mean(macro.values()) if macro else None,
        'enterIds':sorted(selected),
        'timeDistribution':dict(sorted(collections.Counter(r['decisionTimestamp'][11:16] for r in entries).items()))}


def ratio_gate(name, baseline, candidate, limit, operator, require_improvement=False):
    ratio = None
    if baseline is None or candidate is None:
        status,reason = 'INCONCLUSIVE','METRIC_UNDEFINED'
    elif baseline == 0:
        if operator == '<=' and not require_improvement:
            status = 'PASS' if candidate == 0 else 'FAIL'
            reason = 'ZERO_BASELINE_NONWORSENING'
        else:
            status,reason = 'INCONCLUSIVE','ZERO_BASELINE_NO_EPSILON_DIVISION'
    else:
        ratio = candidate/baseline
        status = 'PASS' if (ratio <= limit+1e-12 if operator == '<=' else ratio >= limit-1e-12) else 'FAIL'
        reason = 'FROZEN_RELATIVE_GATE'
    return {'name':name,'baseline':baseline,'candidate':candidate,'ratio':ratio,
            'operator':operator,'limit':limit,'status':status,'reason':reason}


def entry_gates(baseline,candidate,c):
    p,g = c['numericGates']['primary'],c['numericGates']['guardrails']
    result = [ratio_gate('adverseMeanRatioMax',baseline['meanD30'],candidate['meanD30'],p['adverseMeanRatioMax'],'<=',True),
              ratio_gate('adverseES95RatioMax',baseline['ES95D30'],candidate['ES95D30'],p['adverseES95RatioMax'],'<='),
              ratio_gate('throughputRatioMin',baseline['enterCount'],candidate['enterCount'],p['throughputRatioMin'],'>=')]
    for k in (3,5):
        result.append(ratio_gate(f'preservation{k}RatioMin',baseline['preservation'][str(k)]['rate'],
                     candidate['preservation'][str(k)]['rate'],p[f'preservation{k}RatioMin'],'>='))
    for k in (1,2):
        result.append(ratio_gate(f'precision{k}RatioMin',baseline['precision'][str(k)]['rate'],
                     candidate['precision'][str(k)]['rate'],g[f'precision{k}RatioMin'],'>='))
    a,b = baseline['coverageRate'],candidate['coverageRate']
    delta = abs(a-b) if a is not None and b is not None else None
    result.append({'name':'absoluteStrictLabelCoverageGapMax','baseline':a,'candidate':b,'absoluteGap':delta,
        'limit':g['absoluteStrictLabelCoverageGapMax'],'operator':'<=',
        'status':'INCONCLUSIVE' if delta is None else ('PASS' if delta <= g['absoluteStrictLabelCoverageGapMax']+1e-12 else 'FAIL'),
        'reason':'METRIC_UNDEFINED' if delta is None else 'FROZEN_COVERAGE_GATE'})
    return result


def choose_threshold(results):
    if set(results) != {str(int(t)) for t in THRESHOLDS}:
        raise IntegrityError('THRESHOLD_CANDIDATES_MISMATCH')
    eligible = [r for r in results.values() if all(g['status'] == 'PASS' for g in r['gates'])]
    if not eligible:
        return {'threshold':None,'status':'SELECTION_INCONCLUSIVE_NO_CANDIDATE',
                'reason':'NO_FIXED_THRESHOLD_PASSES_ALL_FROZEN_INNER_ENTRY_GATES',
                'failedOrUnknownByThreshold':{k:[g['name']+':'+g['status'] for g in r['gates'] if g['status'] != 'PASS'] for k,r in results.items()}}
    best = min(r['metrics']['meanD30'] for r in eligible)
    tied = [r for r in eligible if abs(r['metrics']['meanD30']-best) <= 1e-12]
    def remaining_key(row):
        preserves = [g['ratio'] for g in row['gates'] if g['name'] in ('preservation3RatioMin','preservation5RatioMin')]
        return min(preserves),row['metrics']['enterCount'],row['threshold']
    winner = max(tied,key=remaining_key)
    return {'threshold':winner['threshold'],'status':'SELECTED_INNER_CALIBRATION_ONLY',
            'reason':'FROZEN_MEAN_D30_PRESERVATION_THROUGHPUT_LEAST_RESTRICTIVE_ORDER'}


def concentration(closed_trades):
    totals = collections.defaultdict(float)
    for row in closed_trades:
        totals[row['symbol']] += row['pnlJpy']
    def side(positive):
        a = sorted(((s,v if positive else -v) for s,v in totals.items() if (v > 0 if positive else v < 0)),key=lambda p:(-p[1],p[0]))
        total = sum(v for _,v in a)
        hhi = sum((v/total)**2 for _,v in a) if total else None
        return {'contributors':len(a),'massJpy':total,'HHI':hhi,
                'effectiveContributors':1/hhi if hhi else None,
                'top1Share':sum(v for _,v in a[:1])/total if total else None,
                'top3Share':sum(v for _,v in a[:3])/total if total else None,
                'top5Share':sum(v for _,v in a[:5])/total if total else None,
                'orderedContributions':a}
    values = list(totals.values())
    return {'uniqueSymbols':len(totals),'profitableSymbols':sum(v > 0 for v in values),
            'losingSymbols':sum(v < 0 for v in values),'medianSymbolContributionJpy':statistics.median(values) if values else None,
            'symbolContributionStdJpy':statistics.pstdev(values) if values else None,
            'positive':side(True),'negative':side(False),'symbolContributions':dict(sorted(totals.items()))}
