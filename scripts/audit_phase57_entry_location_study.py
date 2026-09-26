"""Evaluator-only denominator, missingness and window-attribution audit.

Reads only the pinned Development projection and saved location ledger. No new
timing rule, threshold search, model prediction, provider, EXIT or minute input.
"""
import collections
import csv
import gzip
import json
import math

from scripts import phase57_entry_location_study as s


def touch(value, level):
    return value is not None and (value >= level or math.isclose(value, level, rel_tol=0, abs_tol=1e-10))


def outcome(window, level):
    """Observed touch is known; incomplete no-touch is UNKNOWN, never failure."""
    value = window.get('observedUpsideLowerBound', window.get('upside'))
    if touch(value, level):
        return True
    if window['status'] == 'COMPLETE':
        return False
    return None


def preservation(rows, original, horizon, policy, level):
    winners = [r for r in rows if outcome(original[r['eventId']], level) is True]
    counts = collections.Counter()
    for r in winners:
        e = r['policies'][policy]
        if e['status'] == 'EXPIRED_BOUNDARY':
            counts['boundaryNoReferenceEntry'] += 1
        else:
            value = outcome(e[horizon], level)
            counts[{True: 'preserved', False: 'knownLost', None: 'unknown'}[value]] += 1
    n = len(winners)
    result = {k: counts[k] for k in ['preserved', 'knownLost', 'unknown', 'boundaryNoReferenceEntry']}
    result.update(originalKnownWinners=n, originalUnknown=sum(outcome(original[r['eventId']], level) is None for r in rows),
                  preservationLower=result['preserved']/n if n else None,
                  preservationUpper=(result['preserved']+result['unknown'])/n if n else None)
    assert sum(result[k] for k in ['preserved','knownLost','unknown','boundaryNoReferenceEntry']) == n
    return result


def diagnostics(ledger, paths):
    primary = [r for r in ledger if r['primary60']]
    session_paired = [r for r in ledger if all(r['policies'][p]['savedSession']['status']=='COMPLETE' for p in s.POLICIES)]
    original_session = {r['eventId']: r['censusSavedSession'] for r in ledger}
    original60 = {}
    exclusions = collections.Counter()
    window_effect = {p: [] for p in s.POLICIES}
    for r in ledger:
        source = paths[r['eventId']]
        bars = s.absolute_path(source)
        start = source['entryMinute']
        end = s.segment_end(start, source['sessionEndMinute'])
        if end is None:
            reason = 'DECISION_OUTSIDE_CONTINUOUS_SESSION'
        elif start+60 > end:
            reason = 'SIXTY_MINUTE_WINDOW_CROSSES_SESSION_BOUNDARY'
        elif not r['primary60']:
            reason = 'MISSING_OR_INVALID_FIVE_MINUTE_BAR'
        else:
            reason = 'PRIMARY_COMPLETE'
        exclusions[reason] += 1
        if not r['primary60']:
            continue
        original60[r['eventId']] = s.window(bars, start, start+60, r['decisionPrice'])
        immediate = r['policies']['IMMEDIATE']
        for p in s.POLICIES:
            e = r['policies'][p]
            # Same subsequent market path, two purchase prices. This separates
            # dropping the first interval from the effect of a cheaper buy.
            same = s.window(bars, start+e['delay'], start+e['delay']+30, immediate['price'])
            d0 = immediate['windows']['30']['downside']
            dd = e['windows']['30']['downside']
            window_effect[p].append({
                'eventId': r['eventId'], 'firstClosedDip': r['firstClosedDip'],
                'windowShiftImprovementPP': d0-same['downside'],
                'buyPriceEffectImprovementPP': same['downside']-dd,
                'totalD30ImprovementPP': d0-dd,
                'samePostEntryWindowAtImmediatePriceD30': same['downside'],
            })
    panels = {
        'PRIMARY_COMMON60_DECISION_PRICE': (primary, original60, 'common60'),
        'PRIMARY_SAVED_SESSION_OBSERVED_DECISION_PRICE': (primary, original_session, 'savedSession'),
        'FULL_SAVED_SESSION_OBSERVED_DECISION_PRICE': (ledger, original_session, 'savedSession'),
        'COMPLETE_SAVED_SESSION_PAIRED_DECISION_PRICE': (session_paired, original_session, 'savedSession'),
    }
    captures = []
    for panel_name, (rows, original, horizon) in panels.items():
        for cohort in ['ALL', 'FIRST_CLOSED_DIP', 'NO_FIRST_CLOSED_DIP']:
            selected = rows if cohort == 'ALL' else [r for r in rows if r['firstClosedDip'] is (cohort == 'FIRST_CLOSED_DIP')]
            for p in s.POLICIES:
                for k in s.LEVELS:
                    captures.append({'panel':panel_name, 'cohort':cohort, 'N':len(selected), 'policy':p, 'levelPct':k,
                                     **preservation(selected, original, horizon, p, k)})
    window_summary = {}
    for cohort in ['ALL', 'FIRST_CLOSED_DIP', 'NO_FIRST_CLOSED_DIP']:
        window_summary[cohort] = {}
        for p, records in window_effect.items():
            subset = records if cohort == 'ALL' else [r for r in records if r['firstClosedDip'] is (cohort == 'FIRST_CLOSED_DIP')]
            window_summary[cohort][p] = {key:s.distribution([r[key] for r in subset]) for key in [
                'windowShiftImprovementPP','buyPriceEffectImprovementPP','totalD30ImprovementPP','samePostEntryWindowAtImmediatePriceD30']}
    coverage = []
    for field in ['firstClosedDip','timeOfDay','segment']:
        for value in sorted({str(r[field]) for r in ledger}):
            group = [r for r in ledger if str(r[field]) == value]
            n = sum(r['primary60'] for r in group)
            coverage.append({'field':field,'value':value,'full':len(group),'primary':n,'excluded':len(group)-n,'primaryRate':n/len(group)})
    original_cohorts = {}
    for name, condition in [('DECISION_COMMON60_WINNER3',lambda v:touch(v,3)),
                            ('DECISION_COMMON60_WINNER5',lambda v:touch(v,5)),
                            ('DECISION_COMMON60_NON1_OBSERVED',lambda v:not touch(v,1))]:
        original_cohorts[name] = s.summarize([r for r in primary if condition(original60[r['eventId']]['upside'])])
    return {'purpose':'EVALUATOR_ONLY_NO_NEW_RULES', 'baseline':'Decision Price -> future HIGH; distinct from immediate reference OPEN winners',
            'missingPolicy':'Known touch retained under gaps; incomplete no-touch remains UNKNOWN; boundary no-entry separate',
            'primaryExclusionReasons':dict(exclusions),'coverageByGroup':coverage,
            'originalOpportunityPreservation':captures,'originalDecisionPriceCohorts':original_cohorts,
            'windowAttribution':window_summary,'windowAttributionLedger':window_effect,
            'thresholdTolerancePct':1e-10,'thresholdToleranceNotTradingParameter':True}


def write_json(path, value):
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',',':'))+'\n').encode()
    path.write_bytes(gzip.compress(data,mtime=0) if path.suffix == '.gz' else data)


def write_csv(path, rows):
    with path.open('w',newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def run():
    protocol = s.read(s.BASE/'protocol.json')
    for path, digest in protocol['sourcePins'].items():
        assert s.sha(path) == digest, path
    ledger = s.read(s.BASE/'ledger.json.gz')
    paths = {r['selectorEventId']:r for r in s.read(s.PATHS)['events']}
    report = diagnostics(ledger, paths)
    write_json(s.BASE/'denominator-and-window-audit.json.gz', report)
    write_csv(s.BASE/'original-opportunity-preservation.csv',report['originalOpportunityPreservation'])
    write_csv(s.BASE/'coverage-audit.csv',report['coverageByGroup'])
    result = s.read(s.BASE/'result.json.gz')
    distributions = []
    for cohort, group in result['cohorts'].items():
        for p, v in group['policies'].items():
            for n in [5,10,15,30,60]:
                for metric in ['upside','downside']:
                    distributions.append({'cohort':cohort,'policy':p,'horizonMinutes':n,'metric':metric,**v['windows'][str(n)][metric]})
    write_csv(s.BASE/'horizon-distributions.csv',distributions)
    rows = []
    for name, group in result['cohorts'].items():
        for p in s.POLICIES:
            for cell, n in sorted(group['policies'][p]['efficiency30Joint'].items()):
                rows.append({'cohort':name,'policy':p,'upsideBin':cell.split('_')[0], 'downsideBin':cell.split('_')[1], 'count':n})
    write_csv(s.BASE/'entry-efficiency-2d.csv',rows)
    deep = {}
    for cohort in ['PRIMARY','FIRST_CLOSED_DIP','NO_FIRST_CLOSED_DIP']:
        group = [r for r in ledger if r['primary60'] and (cohort=='PRIMARY' or r['firstClosedDip'] is (cohort=='FIRST_CLOSED_DIP'))]
        deep[cohort] = {}
        for p in s.POLICIES:
            deep[cohort][p] = {}
            for n in [5,10,15,30]:
                values = [r['policies'][p]['windows'][str(n)]['downside'] for r in group]
                values = [v for v in values if v is not None]
                deep[cohort][p][str(n)] = {'observed':len(values),'atLeastPct':{str(k):sum(v>=k for v in values) for k in [1,2,5,10]}}
    (s.BASE/'deep-adverse-counts.json').write_text(json.dumps(deep,indent=2)+'\n')
    print(json.dumps({'status':'PASS','captureRows':len(report['originalOpportunityPreservation']),
                      'primaryExclusions':report['primaryExclusionReasons'],'distributionRows':len(distributions)}))


if __name__ == '__main__':
    run()
