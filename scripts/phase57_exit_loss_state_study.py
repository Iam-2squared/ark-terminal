"""Bounded Development diagnostic. No candidate policy, fit or runtime mutation."""
from __future__ import annotations

import argparse
import collections
import copy
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

from scripts import phase57_new_long_entry_exit_conditional as cond
from scripts import phase57_new_long_exit_candidate_a as ca

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-exit-loss-state-study-v1'
INITIAL = 'INITIAL_ENTRY_OPPORTUNITY'
DIP = 'DIP_REPRICE_OPPORTUNITY'
COHORTS = (INITIAL, DIP)
HYPOTHESES = ('RECLAIM_REJECTION', 'FAILED_BOUNCE', 'NORMALIZED_ACCELERATION')
TIMES = (5, 10, 15)
SOURCE_HEAD = 'e6b98886a35524c98ae4b6ec5913210de9525c80'
PROTOCOL_COMMIT = '655880937f29aa691fdc44f3d1f445aa93500fc5'


def read(p):
    return cond.read(p)


def encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ratio(a, b):
    return a / b if b else None


def metrics(values):
    return {**cond.dist(values), 'PF': ratio(sum(v for v in values if v > 0), -sum(v for v in values if v < 0)),
            'win': cond.rate(sum(v > 0 for v in values), len(values)),
            'largeLossCountMinus5': sum(v <= -5 for v in values)}


def observation(bars, minute):
    """Only accesses completed prefix, not the next bar's presence or contents."""
    count = minute // 5
    if len(bars) < count:
        return {'status': 'INCOMPLETE_PREFIX'}
    prefix = bars[:count]
    if any(b.get('missing') or not cond.valid(b) for b in prefix):
        return {'status': 'UNKNOWN_MISSING'}
    if any(b['minutes'] != (i + 1) * 5 or b['slot'] != i + 1 for i, b in enumerate(prefix)):
        return {'status': 'SESSION_BOUNDARY'}
    if any(prefix[i]['start'] != prefix[i-1]['end'] for i in range(1, count)):
        return {'status': 'SESSION_BOUNDARY'}
    return {'status': 'COMPLETE', 'prefix': prefix, 'features': features(prefix)}


def features(prefix):
    """No evaluator argument. All geometric features have a fixed formula."""
    b = prefix[-1]
    ranges = [r['h'] - r['l'] for r in prefix]
    closes = [r['c'] for r in prefix]
    changes = [closes[0]] + [y-x for x, y in zip(closes, closes[1:])]
    r = ranges[-1]
    running_lows = [min(x['l'] for x in prefix[:i+1]) for i in range(len(prefix))]
    reclaim = any(closes[i-1] < 0 <= closes[i] for i in range(1, len(closes)))
    normalized = [ratio(-changes[i], ranges[i-1]) for i in range(1, len(prefix))]
    return {
        'close': b['c'], 'closeLocation': ratio(b['c']-b['l'], r),
        'lowerWick': ratio(min(b['o'], b['c'])-b['l'], r),
        'upperWick': ratio(b['h']-max(b['o'], b['c']), r),
        'highToClose': b['h']-b['c'], 'lowToClose': b['c']-b['l'],
        'range': r, 'rangeRatio': ratio(r, ranges[-2]) if len(prefix) > 1 else None,
        'normalizedDisplacement': ratio(b['c'], statistics.mean(ranges)),
        'newLowCount': sum(y < x for x, y in zip(running_lows, running_lows[1:])),
        'lowExtension': running_lows[-2]-running_lows[-1] if len(prefix) > 1 else None,
        'lastCloseChange': changes[-1],
        'acceleration': changes[-1]-changes[-2] if len(prefix) > 1 else None,
        'normalizedAdverseStep': normalized[-1] if normalized else None,
        'normalizedAdverseAcceleration': normalized[-1]-normalized[-2] if len(normalized) > 1 and None not in normalized[-2:] else None,
        'pathEfficiency': ratio(abs(b['c']), sum(abs(x) for x in changes)),
        'bounceFromLowClose': b['c']-min(closes), 'reclaimed': int(reclaim),
        'recoverySlope': (closes[-1]-closes[0]) / (5*(len(closes)-1)) if len(closes) > 1 else None,
    }


def states(prefix):
    if len(prefix) != 3 or any(not cond.valid(b) for b in prefix):
        return dict.fromkeys(HYPOTHESES, None)
    a, b, c = prefix
    r = [x['h']-x['l'] for x in prefix]
    lw = [ratio(min(x['o'], x['c'])-x['l'], y) for x, y in zip(prefix, r)]
    n1, n2 = ratio(a['c']-b['c'], r[0]), ratio(b['c']-c['c'], r[1])
    return {
        HYPOTHESES[0]: a['c'] < 0 <= b['c'] and c['c'] < 0 and c['h'] < b['h'] and c['l'] < b['l'] and c['c'] < (c['h']+c['l'])/2,
        HYPOTHESES[1]: a['c'] < b['c'] < 0 and a['c'] < 0 and c['c'] < a['c'] and c['h'] < b['h'] and c['l'] < a['l'],
        HYPOTHESES[2]: None if None in (n1, n2, lw[1], lw[2]) else
            all(x['c'] < 0 for x in prefix) and c['l'] < b['l'] < a['l'] and r[2] > r[1] > 0 and lw[2] < lw[1] and n2 > n1 > 0,
    }


def preserved(result, bars, level):
    first = next((b['slot'] for b in bars if b['h'] >= level), None)
    if first is None:
        return None
    if result['exitBar'] != first:
        return result['exitBar'] > first
    return result['status'] == 'FIXED12_FALLBACK' or result['grossPct'] >= level


def label_snapshot(bars, minute, result):
    count = minute // 5
    prefix, future = bars[:count], bars[count:]
    if not future:
        return None
    c = prefix[-1]['c']
    return {
        'recovery3': max(b['h'] for b in prefix) < 3 <= max(b['h'] for b in future),
        'recovery5': max(b['h'] for b in prefix) < 5 <= max(b['h'] for b in future),
        'deepFailure': result['netPct'] <= -5,
        'continued2': min(b['l'] for b in future) <= c-2,
        'laterLowMinusClosePP': min(b['l'] for b in future)-c,
        'nextOpenNet': future[0]['o']-.05,
        'oracleRescueVsA': future[0]['o']-.05-result['netPct'],
        'alreadyIncurredClose': c,
    }


def build_rows():
    pins = read(BASE/'input-pins.json')
    for p, expected in pins.items():
        assert sha(ROOT/p) == expected, ('SOURCE_PIN', p)
    for p, expected in cond.PINS.items():
        assert sha(ROOT/p) == expected, p
    for p, expected in cond.PARITY_PINS.items():
        assert sha(cond.BASE/'entry-parity'/p) == expected, p
    study_manifest = read(ROOT/'docs/evidence/phase57-new-long-exit-path-study-v1/manifest.json')
    for p, expected in study_manifest['inputPins'].items():
        assert sha(ROOT/p) == expected, p
    entries = read(cond.BASE/'entry-parity/ledger.ndjson.gz')
    ids = sorted(r['anchorId'] for r in entries)
    assert len(ids) == len(set(ids)) == 2743
    assert hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest() == cond.ANCHOR_SHA
    src = read(ROOT/cond.PATHS)
    assert src['freshAccess'] == src['oosAccess'] == src['providerRequests'] == 0
    paths = {r['selectorEventId']: r for r in src['events']}
    old = read(cond.BASE/'ledger.json.gz')
    study = {(r['anchorId'], r['cohort']): r for r in read(ROOT/'docs/evidence/phase57-new-long-exit-path-study-v1/ledger.json.gz')}
    assert len(study) == len(old) == 3284
    coverage, rows = [], []
    audit = collections.Counter()
    for r in sorted(old, key=lambda r: (r['anchorId'], r['cohort'])):
        key = (r['anchorId'], r['cohort'])
        prior = study[key]
        assert r['opportunity'] == prior['opportunity']
        position = cond.adapt(r['opportunity'], paths[r['anchorId']])
        allbars = position.get('future', [])
        cov = {'anchorId': key[0], 'cohort': key[1], 'observations': {}}
        for t in TIMES:
            obs = observation(allbars, t)
            cov['observations'][str(t)] = obs['status']
            if obs['status'] == 'COMPLETE':
                saved = prior['snapshots'][str(t)]
                assert saved['status'] == 'COMPLETE'
                assert math.isclose(obs['features']['close'], saved['causalPrefix']['currentReturnPct'], abs_tol=1e-12)
                audit['savedPathStudyPrefixMatches'] += 1
        coverage.append(cov)
        fixed = r['fixed']
        if fixed['status'] != 'EXIT_REFERENCE':
            continue
        bars = [b for b in allbars if b['slot'] <= fixed['exitBar']]
        assert len(bars) == fixed['exitBar'] and all(cond.valid(b) for b in bars)
        assert math.isclose(fixed['grossPct'], bars[-1]['c'], abs_tol=1e-12)
        assert math.isclose(fixed['netPct'], fixed['grossPct']-.05, abs_tol=1e-12)
        result = ca.policy(bars, fixed)
        assert math.isclose(result['netPct'], result['grossPct']-.05, abs_tol=1e-12)
        if result['status'] == 'PROTECT_EXIT':
            i, j = result['signalBar']-1, result['exitBar']-1
            arm = next(b['slot'] for b in bars if b['h'] >= 3)
            assert result['signalBar'] > arm and j == i+1
            assert bars[j]['start'] >= bars[i]['end'] and result['grossPct'] == bars[j]['o']
            mutated = copy.deepcopy(bars[:j+1]); mutated[j].update(h=999., l=-999., c=999.)
            assert ca.policy(mutated, fixed) == result
            audit['aFillBarSuffixPerturbations'] += 1
        audit['fixedAndALedgerChecks'] += 1
        record = {'anchorId': key[0], 'cohort': key[1], 'symbol': r['symbol'], 'sessionDate': r['sessionDate'],
                  'block': prior['chronologicalBlock'], 'riskTags': r['riskTags'],
                  'fixed': {k: fixed[k] for k in ('exitBar','grossPct','netPct','exitTimestamp')},
                  'candidateA': result, 'bars': bars, 'observations': {},
                  'preservation': {str(k): preserved(result, bars, k) for k in (3,5)},
                  'mae': min(0., min(b['l'] for b in bars)),
                  'fullUnderlyingMinutes': all(b.get('observedMinutes') == 5 for b in bars)}
        for t in TIMES:
            obs = observation(bars, t)
            if obs['status'] != 'COMPLETE':
                record['observations'][str(t)] = {'status': obs['status']}; continue
            n = t//5
            mutated = copy.deepcopy(bars)
            for b in mutated[n:]:
                b.update(o=999., h=1000., l=-999., c=-500., missing=True)
            assert observation(mutated, t) == obs
            assert observation(bars[:n], t) == obs
            audit['diagnosticPrefixPerturbations'] += 1
            # Eligibility is observable: A has not already signalled or exited.
            active = (result['status'] == 'FIXED12_FALLBACK' and result['exitBar'] > n) or (
                result['status'] != 'FIXED12_FALLBACK' and result['signalBar'] > n)
            label = label_snapshot(bars, t, result)
            record['observations'][str(t)] = {'status':'COMPLETE', 'features':obs['features'],
                'activeA': active, 'adverse': obs['features']['close'] < 0,
                'states': states(obs['prefix']) if t == 15 else None,
                'evaluatorOnly': label}
        rows.append(record)
    assert collections.Counter(r['cohort'] for r in rows) == {INITIAL:1072, DIP:397}
    assert len({(r['anchorId'], r['cohort']) for r in rows}) == 1469
    assert sum('CHEAPER_PRIMARY_D30_2' in r['riskTags'] for r in rows) == 106
    assert sum('CHEAPER_PRIMARY_D30_5' in r['riskTags'] for r in rows) == 21
    return rows, coverage, dict(audit), pins


def baseline(rows):
    result = {arm: metrics([r[arm]['netPct'] for r in rows]) for arm in ('fixed','candidateA')}
    result['meanDeltaAVsFixed'] = statistics.mean(r['candidateA']['netPct']-r['fixed']['netPct'] for r in rows) if rows else None
    result['exitReasons'] = dict(collections.Counter(r['candidateA']['status'] for r in rows))
    result['holdingBars'] = cond.dist([r['candidateA']['exitBar'] for r in rows])
    result['mae'] = cond.dist([r['mae'] for r in rows])
    result['preservation'] = {}
    for level in (3,5):
        ws = [r for r in rows if r['preservation'][str(level)] is not None]
        result['preservation'][str(level)] = cond.rate(sum(r['preservation'][str(level)] for r in ws), len(ws))
        fast = [r for r in ws if any(b['minutes'] <= 5 and b['h'] >= level for b in r['bars'])]
        recovery = [r for r in ws if r['bars'][0]['c'] < 0 and r['bars'][0]['h'] < level]
        result['preservation']['fast'+str(level)] = cond.rate(sum(r['preservation'][str(level)] for r in fast), len(fast))
        result['preservation']['recovery'+str(level)] = cond.rate(sum(r['preservation'][str(level)] for r in recovery), len(recovery))
    return result


def eligible(rows, t):
    return [r for r in rows if (o:=r['observations'][str(t)])['status'] == 'COMPLETE'
            and o['activeA'] and o['adverse'] and o['evaluatorOnly'] is not None]


def rates(rows, t=15):
    return {label:cond.rate(sum(r['observations'][str(t)]['evaluatorOnly'][label] for r in rows),len(rows))
            for label in ('recovery3','recovery5','deepFailure','continued2')}


def top_symbols(rows):
    counts = collections.Counter(r['symbol'] for r in rows)
    return sorted(counts, key=lambda s:(-counts[s],s))[:3]


def separation(base, selected):
    b, s = rates(base), rates(selected)
    gate = {}
    for label in ('continued2','recovery3','recovery5'):
        rb, rs = b[label]['rate'], s[label]['rate']
        gate[label] = (rb is not None and rb > 0 and rs is not None and
                       (rs >= 1.5*rb if label == 'continued2' else rs <= .5*rb))
    return {'baselineN':len(base), 'selectedN':len(selected), 'baseline':b, 'selected':s, 'gates':gate}


def screen(rows, name):
    base = eligible(rows,15)
    selected = [r for r in base if r['observations']['15']['states'][name] is True]
    gates = {'totalSupport30':len(selected)>=30,
             'threeBlocks':len({r['block'] for r in selected})>=3,
             'deepFailures10':sum(r['observations']['15']['evaluatorOnly']['deepFailure'] for r in selected)>=10}
    out = {'name':name,'cohorts':{},'blocks':{},'selectedIdentities':[[r['anchorId'],r['cohort']] for r in selected]}
    for cohort in COHORTS:
        population = [r for r in rows if r['cohort']==cohort]
        b, s = [r for r in base if r['cohort']==cohort], [r for r in selected if r['cohort']==cohort]
        top = top_symbols(population)
        main = separation(b,s)
        exclusion = separation([r for r in b if r['symbol'] not in top], [r for r in s if r['symbol'] not in top])
        out['cohorts'][cohort] = {**main,'excludeTop3':exclusion,'excludedSymbols':top,
            'fullUnderlyingMinuteCoverage':separation([r for r in b if r['fullUnderlyingMinutes']], [r for r in s if r['fullUnderlyingMinutes']])}
        gates[cohort+'_support10'] = len(s)>=10
        gates.update({cohort+'_'+k:v for k,v in main['gates'].items()})
        gates.update({cohort+'_excludeTop3_'+k:v for k,v in exclusion['gates'].items()})
    block_wins = 0
    for block in range(1,5):
        x=separation([r for r in base if r['block']==block],[r for r in selected if r['block']==block])
        b,s=x['baseline']['continued2']['rate'],x['selected']['continued2']['rate']
        better=b is not None and s is not None and s>b
        block_wins += better
        out['blocks'][str(block)]={**x,'deteriorationEnrichment':better}
    gates['threeOfFourBlocksEnriched']=block_wins>=3
    sc=collections.Counter(r['symbol'] for r in selected); dc=collections.Counter(r['sessionDate'] for r in selected)
    out.update(gates=gates,failedGates=[k for k,v in gates.items() if not v],eligible=all(gates.values()),
               selectedN=len(selected),symbolN=len(sc),sessionN=len(dc),
               largestSymbolShare=ratio(max(sc.values(),default=0),len(selected)),
               largestSessionShare=ratio(max(dc.values(),default=0),len(selected)))
    return out


def auc(positive, negative):
    """P(feature(deep failure)>feature(recovery3)); no direction selection."""
    a=[v for v in positive if v is not None];b=[v for v in negative if v is not None]
    return {'deepN':len(a),'recoveryN':len(b),
            'aucHigherDeep':ratio(sum((x>y)+.5*(x==y) for x in a for y in b),len(a)*len(b))}


def feature_diagnostic(rows,t):
    rs=eligible(rows,t)
    deep=[r for r in rs if r['observations'][str(t)]['evaluatorOnly']['deepFailure']]
    recovery=[r for r in rs if r['observations'][str(t)]['evaluatorOnly']['recovery3']]
    overlap={r['anchorId']+'|'+r['cohort'] for r in deep}&{r['anchorId']+'|'+r['cohort'] for r in recovery}
    # Remove overlapping identities only for two-class rank diagnostic, retaining
    # overlap explicitly in rates and labels. Never force conflicting labels.
    d=[r for r in deep if r['anchorId']+'|'+r['cohort'] not in overlap]
    w=[r for r in recovery if r['anchorId']+'|'+r['cohort'] not in overlap]
    out={'n':len(rs),'labels':rates(rs,t),'deepRecoveryOverlap':len(overlap),'features':{},'latency':{}}
    names=next((r['observations'][str(t)]['features'].keys() for r in rs),[])
    for name in names:
        getter=lambda rows:[r['observations'][str(t)]['features'][name] for r in rows]
        out['features'][name]={'deep':cond.dist(getter(d)), 'recovery3':cond.dist(getter(w)),
                               **auc(getter(d),getter(w))}
    for label in ('deepFailure','continued2','recovery3','recovery5'):
        subset=[r['observations'][str(t)]['evaluatorOnly'] for r in rs if r['observations'][str(t)]['evaluatorOnly'][label]]
        out['latency'][label]={k:cond.dist([r[k] for r in subset]) for k in ('alreadyIncurredClose','oracleRescueVsA','laterLowMinusClosePP')}
    return out


def summarize(rows, coverage, audit, pins):
    screens=[screen(rows,name) for name in HYPOTHESES]
    out={'schemaVersion':1,'sourceHead':SOURCE_HEAD,'protocolCommit':PROTOCOL_COMMIT,
         'status':'SEPARATION_EVIDENCE_REQUIRES_CANDIDATE_CONTRACT' if any(s['eligible'] for s in screens) else 'EXIT_ARCHITECTURE_DEVELOPMENT_LIMIT_REACHED',
         'strongCandidate':False,'candidateImplemented':False,'freshOosOpened':False,
         'anchorIdentitySHA256':cond.ANCHOR_SHA,'screens':screens,'overall':baseline(rows),
         'cohorts':{},'adverseSubsets':{},'observations':{},'coverage':{},'audit':audit,'sourcePins':pins,
         'safety':ca.SAFETY,'scope':{k:0 for k in ('selectorChanges','entryChanges','candidateAMutations','candidateCRevival','thresholdSweeps','modelFits','freshAccess','oosAccess','providerRequests','minuteResearch','capitalTuning','portfolioTuning','mainMerge')}}
    for cohort in COHORTS:
        rs=[r for r in rows if r['cohort']==cohort];top=top_symbols(rs)
        symbols=collections.Counter(r['symbol'] for r in rs);sessions=collections.Counter(r['sessionDate'] for r in rs)
        out['cohorts'][cohort]={**baseline(rs),'blocks':{str(b):baseline([r for r in rs if r['block']==b]) for b in range(1,5)},
            'excludeTop3':baseline([r for r in rs if r['symbol'] not in top]),'excludedSymbols':top,
            'symbolN':len(symbols),'sessionN':len(sessions),'symbolHHI':sum((v/len(rs))**2 for v in symbols.values()),
            'largestSessionShare':max(sessions.values())/len(rs),
            'bySession':{day:baseline([r for r in rs if r['sessionDate']==day]) for day in sorted(sessions)}}
        out['observations'][cohort]={str(t):feature_diagnostic(rs,t) for t in TIMES}
        cr=[r for r in coverage if r['cohort']==cohort]
        out['coverage'][cohort]={str(t):dict(collections.Counter(r['observations'][str(t)] for r in cr)) for t in TIMES}
        matched=[r for r in rs if all(r in eligible([r],t) for t in TIMES)]
        out['observations'][cohort]['matchedAllTimesN']=len(matched)
        out['observations'][cohort]['matchedAllTimes']={str(t):feature_diagnostic(matched,t) for t in TIMES}
    tags=sorted({tag for r in rows for tag in r['riskTags']})
    for tag in tags:
        subset=[r for r in rows if tag in r['riskTags']]
        out['adverseSubsets'][tag]=baseline(subset)
    assert out['adverseSubsets']['CHEAPER_PRIMARY_D30_2']['fixed']['n'] == 106
    assert out['adverseSubsets']['CHEAPER_PRIMARY_D30_5']['fixed']['n'] == 21
    for level in (2,5):
        subset=[r for r in rows if r['mae']<=-level]
        out['adverseSubsets']['MAE_MINUS_'+str(level)]=baseline(subset)
    assert all(v is False for v in out['safety'].values())
    return out


def run(outdir):
    outdir=Path(outdir)
    if outdir.exists():
        raise FileExistsError('Immutable output destination already exists: '+str(outdir))
    rows,coverage,audit,pins=build_rows()
    summary=summarize(rows,coverage,audit,pins)
    outdir.mkdir(parents=True,exist_ok=False)
    objects={'summary.json':summary,'ledger.json.gz':rows,'coverage.json.gz':coverage}
    for name,obj in objects.items():
        data=encode(obj)
        (outdir/name).write_bytes(gzip.compress(data,mtime=0) if name.endswith('.gz') else data)
    manifest={'schemaVersion':1,'status':summary['status'],'sourcePins':pins,
              'codePins':{'scripts/phase57_exit_loss_state_study.py':sha(Path(__file__))},
              'outputPins':{name:sha(outdir/name) for name in objects},'safety':ca.SAFETY,
              'protocolCommit':PROTOCOL_COMMIT,'anchorIdentitySHA256':cond.ANCHOR_SHA}
    (outdir/'manifest.json').write_bytes(encode(manifest))
    print(json.dumps({'status':summary['status'],'screens':[{k:s[k] for k in ('name','selectedN','eligible','failedGates')} for s in summary['screens']], 'audit':audit},indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    run(parser.parse_args().out)
