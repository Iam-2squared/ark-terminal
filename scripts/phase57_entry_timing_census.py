"""Fixed-population timing study. Full paths exist ONLY in this evaluator."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts import phase57_entry_timing_signals as s

e = s.legacy
read, write, sha = e.read, e.write, e.sha
dist = e.ext.distribution
SOURCE = e.BASE / 'ci-result'
ARMS = ('A', 'B', 'C', 'D', 'E', 'F')


def future_rows(day, a, start):
    """Endpoint-stamped auction bars at the decision are already closed, not future.

    15:00 is a regular bar after the November 2024 session extension.
    """
    close = 900 if day < '2024-11-05' else 930
    return a[(a[:, 0] >= start) & ~((a[:, 0] == start) & np.isin(a[:, 0], [690, close]))]


def ordered_oracle(a, start):
    rows = a[a[:, 0] >= start]
    if len(rows) < 2:
        return {'status': 'INSUFFICIENT_ORDERED_ROWS'}
    best = None
    low = rows[0]
    for high in rows[1:]:
        value = s.pct(high[2], low[3])
        if best is None or value > best['rangePct']:
            best = {'status': 'OBSERVED_ORDERED_ORACLE', 'lowMinute': int(low[0]),
                    'highMinute': int(high[0]), 'low': float(low[3]),
                    'high': float(high[2]), 'rangePct': value}
        if high[3] < low[3]:
            low = high
    return best


def retention(oracle, entry, price, full_available, a):
    out = {'valuePct': None, 'alternativeHighPct': None, 'status': None}
    if entry is None:
        out['status'] = 'NO_FILL'
    elif not full_available:
        out['status'] = 'FULL_SESSION_OBSERVATION_INSUFFICIENT'
    elif oracle['status'] != 'OBSERVED_ORDERED_ORACLE':
        out['status'] = 'INSUFFICIENT_ORDERED_ROWS'
    elif oracle['rangePct'] <= 0:
        out['status'] = 'NONPOSITIVE_DENOMINATOR'
    elif oracle['highMinute'] <= entry:
        out['status'] = 'ORACLE_HIGH_AT_OR_BEFORE_ENTRY'
    else:
        out['status'] = 'ENTRY_BEFORE_ORACLE_LOW' if entry < oracle['lowMinute'] else 'ENTRY_AT_OR_AFTER_ORACLE_LOW'
        out['valuePct'] = 100 * s.pct(oracle['high'], price) / oracle['rangePct']
    later = a[a[:, 0] > entry] if entry is not None else []
    if len(later) and full_available and oracle.get('rangePct', 0) > 0:
        out['alternativeHighPct'] = 100 * s.pct(max(later[:, 2]), price) / oracle['rangePct']
    return out


def direct_path(a, start, price, available):
    if not available:
        return 'UNKNOWN'
    x = a[a[:, 0] >= start]
    hit = x[x[:, 2] >= price*1.03]
    dip = x[x[:, 3] <= price*.995]
    if not len(hit):
        return 'NO_3_HIT'
    if len(dip) and dip[0, 0] == hit[0, 0]:
        return 'SAME_BAR_ORDER_AMBIGUOUS'
    if not len(dip) or hit[0, 0] < dip[0, 0]:
        return 'DIRECT_CONTINUATION'
    return 'PULLBACK_BEFORE_3_HIT'


def strict_coverage(day, t, a, h):
    if t is None:
        return {'status': 'NO_FILL', 'observed': 0, 'expected': h}
    ms = [m for m in e.minutes(day) if m >= t][:h]
    observed = set(a[:, 0])
    n = sum(m in observed for m in ms)
    return {'status': 'CENSORED' if len(ms) < h else 'ALL_1M_OBSERVED' if n == h else 'PARTIAL_1M',
            'observed': n, 'expected': h}


def first_summary(rows, family, grid, day, start):
    ans = {}
    for name, xx in [('fullCensus', rows), ('comparisonWindow', [r for r in rows if r['minute'] in grid])]:
        values = [r['signals'][family]['trigger'] for r in xx]
        first = next((r for r in xx if r['signals'][family]['trigger'] is True), None)
        ans[name] = {'trueBars': sum(v is True for v in values), 'falseBars': sum(v is False for v in values),
                     'unknownBars': sum(v is None for v in values), 'scheduledBars': len(xx),
                     'firstMinute': first['minute'] if first else None,
                     'firstTimestampJst': day+'T'+first['barClosedAtJst']+':00+09:00' if first else None,
                     'delay': e.elapsed(day, start, first['minute']) if first else None,
                     'absenceStatus': 'SIGNAL_PRESENT' if first else 'OBSERVATION_INSUFFICIENT' if not xx or any(v is None for v in values) else 'CONFIRMED_NO_SIGNAL',
                     'firstActivity': first['activity'] if first else None,
                     'firstContext': first['context'] if first else None}
    return ans


def arm_summary(opps, ts, labs):
    filled = [t for t in ts if t['entryId']]
    out = {'opportunities': len(opps), 'fills': len(filled), 'fillThroughputPct': 100*len(filled)/len(opps) if opps else None,
           'BUYIntentOpportunities': sum(t['intentMinute'] is not None for t in ts),
           'BUYAttemptCount': sum(t['buyAttemptCount'] for t in ts),
           'retryCount': sum(t['retryCount'] for t in ts),
           'fallbackIntentCount': sum(t['intentReason'] == 'FALLBACK' for t in ts),
           'reasons': dict(collections.Counter(t['unfilledReason'] for t in ts if not t['entryId'])),
           'attemptResults': dict(collections.Counter(a.get('result', a['state']) for t in ts for a in t['attempts'])),
           'delay': dist(t['delay'] for t in ts), 'price': dist(t['price'] for t in ts),
           'capture': e.ext.capture(opps, ts, labs),
           'rangeRetention': dist(t['rangeRetention']['valuePct'] for t in ts),
           'rangeRetentionReasons': dict(collections.Counter(t['rangeRetention']['status'] for t in ts)),
           'waitMaxRiseVsImmediatePct': dist(t['waitMaxRiseVsImmediatePct'] for t in ts)}
    for h in ('30', '60'):
        ll = [labs[t['entryId']]['labels'][h] for t in filled]
        out[h] = {'coverage': dict(collections.Counter(z['status'] for z in ll)), 'hits': e.ext.hit_rates(ll),
                  'strict1mCoverage': dict(collections.Counter(t['strictCoverage'][h]['status'] for t in ts))}
        for k in ('MFE', 'MAE', 'MaxDD', 'MaxDDAdverseBound', 'returnNet'):
            out[h][k] = dist(z.get(k) for z in ll)
    for k in ('mfeEnd', 'maeEnd', 'returnEnd'):
        out[k] = dist(labs[t['entryId']]['labels'][k] for t in filled)
    out['endHits'] = {}
    for level in range(1, 6):
        values = [labs[t['entryId']]['labels']['mfeEnd'] for t in filled]
        hits = sum(v is not None and v >= level for v in values)
        unknown = sum(v is None for v in values)
        out['endHits'][str(level)] = {'hits': hits, 'fillDenominator': len(filled), 'populationDenominator': len(opps),
                                    'unknownFilled': unknown, 'unfilled': len(opps)-len(filled),
                                    'populationObservedHitPct': 100*hits/len(opps) if opps else None,
                                    'conditionalFillHitPct': 100*hits/len(filled) if filled else None}
    return out


def paired_record(base, candidate, labs, selector):
    both = bool(base['entryId'] and candidate['entryId'])
    z = {'opportunity': base['opportunity'], 'session': base['session'],
         'status': 'BOTH_FILLED' if both else 'BASE_ONLY' if base['entryId'] else 'CANDIDATE_ONLY' if candidate['entryId'] else 'NEITHER_FILLED',
         'priceImprovementPct': 100*(1-candidate['price']/base['price']) if both else None,
         'delayDelta': candidate['delay']-base['delay'] if both else None,
         'rangeRetentionDeltaPp': None, 'captureDelta': {}}
    ra, rb = base['rangeRetention']['valuePct'], candidate['rangeRetention']['valuePct']
    if ra is not None and rb is not None:
        z['rangeRetentionDeltaPp'] = rb-ra
    for h in ('30', '60'):
        z[h] = {}
        for k in ('MFE', 'MAE', 'MaxDD', 'returnNet'):
            a = labs[base['entryId']]['labels'][h][k] if base['entryId'] else None
            b = labs[candidate['entryId']]['labels'][h][k] if candidate['entryId'] else None
            z[h][k] = b-a if a is not None and b is not None else None
    for level in range(1, 6):
        value = selector['mfeEnd']
        if value is None or value < level:
            z['captureDelta'][str(level)] = None
        else:
            def hit(t):
                v = labs[t['entryId']]['labels']['mfeEnd'] if t['entryId'] else None
                return int(v is not None and v >= level)
            z['captureDelta'][str(level)] = hit(candidate)-hit(base)
    return z


def paired_summary(rows):
    out = {'population': len(rows), 'pairStatus': dict(collections.Counter(x['status'] for x in rows))}
    for k in ('priceImprovementPct', 'delayDelta', 'rangeRetentionDeltaPp'):
        out[k] = dist(x[k] for x in rows)
    for h in ('30', '60'):
        out[h] = {k: dist(x[h][k] for x in rows) for k in ('MFE', 'MAE', 'MaxDD', 'returnNet')}
    groups = collections.defaultdict(list)
    for x in rows:
        if x['priceImprovementPct'] is not None:
            groups[x['session']].append(x['priceImprovementPct'])
    means = np.array([np.mean(v) for k,v in sorted(groups.items())])
    ci = None
    if len(means):
        rng = np.random.default_rng(570921)
        boot = rng.choice(means, (2000, len(means)), replace=True).mean(axis=1)
        ci = {'sessionCount': len(means), 'mean': float(means.mean()), 'percentile95': np.percentile(boot, [2.5,97.5]).tolist(), 'descriptiveNotConfirmatory': True}
    out['sessionEqualPriceBootstrap'] = ci
    return out


def volume_bin(x):
    return 'UNKNOWN' if x is None else 'LT_0.8' if x < .8 else '0.8_TO_1.2' if x < 1.2 else 'GE_1.2'


def signal_summary(records, labs):
    out, volume = {}, []
    for family in s.FAMILIES:
        out[family] = {}
        for scope in ('fullCensus', 'comparisonWindow'):
            items = [(r, r['signalSummary'][family][scope]) for r in records]
            zz = {'opportunities': len(items), 'occurrenceCount': sum(v['firstMinute'] is not None for r,v in items),
                  'absenceStatus': dict(collections.Counter(v['absenceStatus'] for r,v in items)),
                  'firstDelay': dist(v['delay'] for r,v in items),
                  'trueBars': sum(v['trueBars'] for r,v in items), 'unknownBars': sum(v['unknownBars'] for r,v in items),
                  'scheduledBars': sum(v['scheduledBars'] for r,v in items), 'contingencies': {}}
            zz['occurrenceRatePct'] = 100*zz['occurrenceCount']/len(items)
            for level in range(1, 6):
                c = collections.Counter()
                for r, v in items:
                    value = r['selectorOutcome']['mfeEnd']
                    outcome = 'UNKNOWN_OUTCOME' if value is None else 'SUCCESS' if value >= level else 'FAILURE'
                    # A no-observed-signal/partial case is retained, never certified absence.
                    state = 'SIGNAL' if v['firstMinute'] is not None else 'NO_OBSERVED_SIGNAL'
                    c[state+'_'+outcome] += 1
                zz['contingencies'][str(level)] = dict(c)
                assert sum(c.values()) == 2155
            out[family][scope] = zz
        # Fixed volume context strata, first observed comparison signal only.
        for field in ('3/volumeAcceleration', '3/valueAcceleration', '3/volumeRelativePreviousDay', '3/valueRelativePreviousDay'):
            by = collections.defaultdict(list)
            for r in records:
                z = r['signalSummary'][family]['comparisonWindow']
                if z['firstMinute'] is None:
                    continue
                by[volume_bin(z['firstActivity'][field])].append((r,z))
            for bucket in ('LT_0.8', '0.8_TO_1.2', 'GE_1.2', 'UNKNOWN'):
                values = by[bucket]
                returns = []
                for r,z in values:
                    lab = labs.get(r['opportunity']+'|'+str(z['firstMinute']))
                    returns.append(lab['labels']['30']['returnNet'] if lab and lab['labels'] else None)
                volume.append({'family':family,'field':field,'bucket':bucket,'n':len(values),
                               'firstSignal30Return':dist(returns),
                               'warning':'Conditional first-signal hypothetical fill label; no quality gate, no independent causal effect.'})
    return out, volume


def run(output, census_cache=None):
    p = s.verify()
    src = SOURCE/'substrate'
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    cached_by_opp = {}
    if census_cache:
        cache = Path(census_cache)
        cached_manifest = read(cache/'manifest.json')
        for name, digest in cached_manifest.items():
            assert sha(cache/name) == digest, ('CACHE_HASH_MISMATCH', name)
        assert read(cache/'cohort.json')['protocolSHA256'] == sha(s.BASE/'protocol.json')
        # Evaluator-only correction reuse; detectors already regenerated twice.
        assert read(cache/'cohort.json')['definitionsSHA256'] == sha(s.BASE/'PROTOCOL.md')
    cohort_ids = set(p['opportunityIds'])
    opps = [o for o in read(src/'opportunities.json.gz') if o['id'] in cohort_ids]
    opps.sort(key=lambda o:o['id'])
    assert [o['id'] for o in opps] == p['opportunityIds']
    # Minimal causal identity payload excludes WHO, future outcome, score and rank.
    paths = read(src/'raw-paths-evaluator-only.json.gz')
    rows = [r for r in read(src/'rows.json.gz') if r['opportunity'] in cohort_ids and r['eligible1']]
    byrow = {r['id']:r for r in rows}
    all_labs = read(src/'outcomes.json.gz')
    labs = {r['id']:all_labs[r['id']] for r in rows}
    del all_labs
    old_a = {t['opportunity']:t for t in read(SOURCE/'measurement/trades.json.gz')['B0_RETRY_1m']}
    calendar = e.f.s.calendar()
    records, trades, paired = [], {k:[] for k in ARMS}, {k:[] for k in ARMS}
    minute_rows, current_day = [], None
    co = np.zeros((6,6), dtype=int)
    co_any = np.zeros((6,6), dtype=int)
    co_first = np.zeros((6,6), dtype=int)
    for number, o in enumerate(opps):
        oid, day = o['id'], o['session']
        if current_day is not None and current_day != day:
            write(out/'minute-census'/(current_day+'.json.gz'), minute_rows)
            print(json.dumps({'session':current_day,'censusRows':len(minute_rows),'processed':number}), flush=True)
            minute_rows = []
        if census_cache and current_day != day:
            assert not cached_by_opp, 'UNCONSUMED_CACHE_OPPORTUNITY'
            for row in read(cache/'minute-census'/(day+'.json.gz')):
                cached_by_opp.setdefault(row['opportunity'], []).append(row)
        current_day = day
        path = paths.pop(oid)
        a = np.asarray(path['today'], float).reshape(-1,7)
        prev = np.asarray(path['previous'], float).reshape(-1,7)
        previous_day = path['previousSession']
        if len(prev):
            assert previous_day == calendar[calendar.index(day)-1], 'NOT_ACTUAL_PREVIOUS_SESSION'
            assert previous_day in p['developmentSessions'], 'UNAUTHORIZED_PREVIOUS_SOURCE'
        start = e.old.minute(o['origin']['decisionTimestamp'])
        grid = s.comparison_grid(day,start)
        obs = cached_by_opp.pop(oid) if census_cache else []
        if not census_cache:
            for t in s.census_grid(day, start):
                z = s.detect(day,t,o['origin']['decisionPrice'],e.closed(a,t),prev,previous_day)
                z.update(opportunity=oid,session=day,delay=e.elapsed(day,start,t),comparisonEligible=t in grid)
                obs.append(z)
        assert [z['minute'] for z in obs] == s.census_grid(day,start)
        for z in obs:
            t = z['minute']
            if t in grid:
                fires = np.array([z['signals'][f]['trigger'] is True for f in s.FAMILIES], int)
                co += np.outer(fires,fires)
        bytime = {z['minute']:z for z in obs}
        summary = {f:first_summary(obs,f,grid,day,start) for f in s.FAMILIES}
        fires = np.array([summary[f]['comparisonWindow']['firstMinute'] is not None for f in s.FAMILIES], int)
        co_any += np.outer(fires,fires)
        for i,f in enumerate(s.FAMILIES):
            for j,g in enumerate(s.FAMILIES):
                ft,gt = summary[f]['comparisonWindow']['firstMinute'],summary[g]['comparisonWindow']['firstMinute']
                co_first[i,j] += ft is not None and ft == gt
        quotes = {t:byrow[oid+'|'+str(t)]['quoteAvailable'] for t in grid}
        fills = {t:labs[oid+'|'+str(t)]['price'] for t in grid}
        tt = s.replay(oid,day,start,bytime,quotes,fills,p['arms'])
        assert tt['A']['entryId'] == old_a[oid]['entryId'], ('BASELINE_CHANGED',oid)
        full = o['selectorOutcome']['mfeEnd'] is not None
        future = future_rows(day,a,start)
        oracle = ordered_oracle(future,start)
        oracle.update(fullSessionEvaluable=full)
        path_class = direct_path(future,start,o['origin']['decisionPrice'],full)
        for arm,tr in tt.items():
            t,price = tr['entryMinute'],tr['price']
            tr['strictCoverage'] = {str(h):strict_coverage(day,t,a,h) for h in (30,60)}
            tr['rangeRetention'] = retention(oracle,t,price,full,a)
            waiting = a[(a[:,0] >= tt['A']['entryMinute']) & (a[:,0] < t)] if t is not None and tt['A']['entryMinute'] is not None else []
            tr['waitMaxRiseVsImmediatePct'] = max(0.,s.pct(max(waiting[:,2]),tt['A']['price'])) if len(waiting) else 0. if t is not None and t == tt['A']['entryMinute'] else None
            tr['waitCloseRiseVsImmediatePct'] = s.pct(bytime[t]['context']['close'],tt['A']['price']) if t is not None and tt['A']['price'] is not None else None
            tr['waitCoverage'] = {'observedBars':len(waiting),'expectedActiveMinutes':max(0,e.elapsed(day,tt['A']['entryMinute'],t)) if t is not None and tt['A']['entryMinute'] is not None else None}
            trades[arm].append(tr)
        for arm in ARMS:
            paired[arm].append(paired_record(tt['A'],tt[arm],labs,o['selectorOutcome']))
        record = {'opportunity':oid,'session':day,'symbol':o['symbol'],'selectorMinute':start,
                  'selectorPrice':o['origin']['decisionPrice'],'selectorOutcome':o['selectorOutcome'],
                  'orderedOracle':oracle,'pathClassEvaluatorOnly':path_class,
                  'inheritedPathOrderEvaluatorOnly':o['selectorOutcome']['order'],
                  'sourceHash':path['sourceHash'],'signalSummary':summary,
                  'previousSession':previous_day,'dictionaryUsed':False}
        records.append(record)
        minute_rows.extend(obs)
    if current_day is not None:
        write(out/'minute-census'/(current_day+'.json.gz'),minute_rows)
    del paths
    signals,volume = signal_summary(records,labs)
    metrics = {arm:arm_summary(opps,ts,labs) for arm,ts in trades.items()}
    oldm = read(SOURCE/'measurement/metrics.json')['B0_RETRY_1m']
    assert metrics['A']['fills'] == oldm['BUY'] == 1963
    for level in range(1,6):
        assert e.ext.same(metrics['A']['capture'][str(level)]['rate'],oldm['capture'][str(level)]['rate'])
    sessions, times, path_results = [], [], []
    for key, bucket_fn, target in [
        ('session',lambda o:o['session'],sessions),
        ('timeOfDay',lambda o:'AM_09' if e.old.minute(o['origin']['decisionTimestamp'])<600 else 'AM_10' if e.old.minute(o['origin']['decisionTimestamp'])<660 else 'AM_11' if e.old.minute(o['origin']['decisionTimestamp'])<=690 else 'PM_12_13' if e.old.minute(o['origin']['decisionTimestamp'])<840 else 'PM_14_PLUS',times),
        ('path',lambda o:next(r['pathClassEvaluatorOnly'] for r in records if r['opportunity']==o['id']),path_results)]:
        groups = collections.defaultdict(list)
        for o in opps:
            groups[bucket_fn(o)].append(o)
        # Explicitly keep zero-opportunity days in the 59-session manifest.
        if key=='session':
            for day in p['evaluationSessions']:
                groups[day]
        for name,oo in sorted(groups.items()):
            ids = {o['id'] for o in oo}
            for arm in ARMS:
                target.append({'bucket':name,'arm':arm,**arm_summary(oo,[t for t in trades[arm] if t['opportunity'] in ids],labs),
                               'paired':paired_summary([x for x in paired[arm] if x['opportunity'] in ids])})
    jac = [[int(co_any[i,j])/int(co_any[i,i]+co_any[j,j]-co_any[i,j]) if co_any[i,i]+co_any[j,j]-co_any[i,j] else None for j in range(6)] for i in range(6)]
    anatomy = {'population':2155,'fullSessionAvailable':sum(r['orderedOracle']['fullSessionEvaluable'] for r in records),
               'selectorBelow1':sum(r['selectorOutcome']['mfeEnd'] is not None and r['selectorOutcome']['mfeEnd']<1 for r in records),
               'unknownFullSession':sum(r['selectorOutcome']['mfeEnd'] is None for r in records),
               'pathClass':dict(collections.Counter(r['pathClassEvaluatorOnly'] for r in records)),
               'oracleRange':dist(r['orderedOracle'].get('rangePct') for r in records if r['orderedOracle']['fullSessionEvaluable']),
               'thresholds':{str(level):{'selectorToHigh':sum(r['selectorOutcome']['mfeEnd'] is not None and r['selectorOutcome']['mfeEnd']>=level for r in records),
                                         'orderedLowLaterHigh':sum(r['orderedOracle']['fullSessionEvaluable'] and r['orderedOracle'].get('rangePct',-1)>=level for r in records)} for level in (1,2,3,4,5,10)}}
    cohort = {'population':2155,'inputDevelopmentSessions':144,'evaluationManifestSessions':len(p['evaluationSessions']),
              'evaluationSessionsWithOpportunities':len(set(o['session'] for o in opps)),
              'opportunityIdsSHA256':hashlib.sha256(json.dumps(p['opportunityIds'],separators=(',',':')).encode()).hexdigest(),
              'protocolSHA256':sha(s.BASE/'protocol.json'),'definitionsSHA256':sha(s.BASE/'PROTOCOL.md'),
              'noTraining':True,'noDictionary':True,'holdoutOpened':0,'safety':p['safety'],
              'baselineFillTimestampParity':True,'baselineCaptureParity':True,
              'studyStatus':'DESCRIPTIVE_DEVELOPMENT_CENSUS_COMPLETE_NO_PROMOTION',
              'causalityLimitations':['Observed historical bars, not independently certified knownAt','Frozen upstream same-day metadata limitation inherited','No liquidity guarantee; next-open +5bps historical fill proxy','Missing source is not certified halt/no-trade','Legacy COMPLETE30/60 is five-minute-slot observation; strict1m masks saved']}
    for name,data in [('cohort.json',cohort),('opportunity-records.json.gz',records),('trades.json.gz',trades),
                      ('paired.json.gz',paired),('metrics.json',metrics),('paired-summary.json',{k:paired_summary(v) for k,v in paired.items()}),
                      ('signal-summary.json',signals),('volume-context.json',volume),('session-stability.json',sessions),
                      ('time-stability.json',times),('path-stability.json',path_results),('oracle-anatomy.json',anatomy),
                      ('cooccurrence.json',{'families':s.FAMILIES,'sameDecisionCounts':co.tolist(),'anyComparisonSignalCounts':co_any.tolist(),'firstTimestampAgreementCounts':co_first.tolist(),'opportunityJaccard':jac})]:
        write(out/name,data)
    write(out/'manifest.json',{str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file()})
    print(json.dumps({'status':cohort['studyStatus'],'fills':{k:v['fills'] for k,v in metrics.items()}}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--census-cache',help='Hash-verified v1 census for evaluator-only correction; optional')
    args = parser.parse_args()
    run(args.output, args.census_cache)
