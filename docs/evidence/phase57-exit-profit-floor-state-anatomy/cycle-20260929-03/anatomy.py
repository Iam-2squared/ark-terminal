"""One finite descriptive Anatomy, no EXIT decision, replay, fit or provider call."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import statistics
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MILESTONES = (0.5, 1, 2, 3, 5, 7, 10)
PAIRS = {1: (2, 3, 5, 10), 2: (3, 5, 10), 3: (5, 7, 10),
         5: (7, 10), 7: (10,)}
FLOORS = {1: 0, 2: 1.5, 3: 2.5}
WORLD = {'IM': 'IMMEDIATE', 'R1': 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    p = HERE / name
    if p.exists():
        raise FileExistsError(p)
    p.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False,
                            allow_nan=False, separators=(',', ':')) + '\n')


def gzwrite(name, rows):
    p = HERE / name
    if p.exists():
        raise FileExistsError(p)
    with p.open('wb') as f, gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as g:
        for r in rows:
            g.write((json.dumps(r, sort_keys=True, ensure_ascii=False,
                                allow_nan=False, separators=(',', ':')) + '\n').encode())


def guard(ok, reason):
    if not ok:
        raise ValueError(reason)


def skip_value(text, i):
    quote = escape = False
    stack = []
    while i < len(text):
        c = text[i]
        if quote:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                quote = False
        elif c == '"':
            quote = True
        elif c in '[{':
            stack.append(c)
        elif c in ']}':
            if not stack:
                break
            guard((stack.pop(), c) in (('[', ']'), ('{', '}')), 'RAW_UNBALANCED')
        elif c == ',' and not stack:
            break
        i += 1
    guard(not quote and not stack, 'RAW_UNTERMINATED')
    return i


def project_raw(path, allowed):
    """Only parse exact allowlisted top-level payloads; skip other values structurally."""
    text = gzip.decompress(path.read_bytes()).decode()
    decoder = json.JSONDecoder()
    n = len(text)
    def ws(i):
        while i < n and text[i].isspace():
            i += 1
        return i
    i = ws(0)
    guard(text[i] == '{', 'RAW_NOT_OBJECT')
    i += 1
    seen, projected, skipped = set(), {}, 0
    while True:
        i = ws(i)
        if text[i] == '}':
            guard(ws(i + 1) == n, 'TRAILING_DATA')
            break
        key, i = decoder.raw_decode(text, i)
        guard(isinstance(key, str) and key not in seen, 'BAD_RAW_KEY')
        seen.add(key)
        i = ws(i)
        guard(text[i] == ':', 'BAD_RAW_COLON')
        i = ws(i + 1)
        if key in allowed:
            value, i = decoder.raw_decode(text, i)
            guard(isinstance(value, dict) and isinstance(value.get('today'), list),
                  'RAW_SCHEMA')
            projected[key] = value['today']
        else:
            i = skip_value(text, i)
            skipped += 1
        i = ws(i)
        guard(text[i] in ',}', 'BAD_RAW_SEPARATOR')
        if text[i] == ',':
            i += 1
    guard(set(projected) == allowed, 'RAW_SCOPE_INCOMPLETE')
    return projected, skipped


def minutes():
    return tuple(range(540, 690)) + tuple(range(750, 925))


def valid(row, minute, auction=False):
    if not isinstance(row, list) or len(row) != 7 or row[0] != minute:
        return False
    if any(isinstance(x, bool) or not isinstance(x, (float, int)) or
           not math.isfinite(x) for x in row):
        return False
    _, o, h, l, c, v, a = row
    return o > 0 and l > 0 and l <= min(o, c) <= max(o, c) <= h and v >= 0 and a >= 0 and (
        not auction or o == h == l == c)


def canonical_minute(row):
    """Producer casts clock HH:MM to numeric minutes in a float ndarray."""
    if not isinstance(row, list) or not row:
        return None, 'ROW_SHAPE'
    value = row[0]
    if type(value) not in (int, float):
        return None, 'TIMESTAMP_TYPE'
    if not math.isfinite(value):
        return None, 'TIMESTAMP_NONFINITE'
    if not float(value).is_integer():
        return None, 'TIMESTAMP_FRACTIONAL'
    minute = int(value)
    if minute not in minutes() and minute not in (690, 930):
        return None, 'TIMESTAMP_OUTSIDE_SESSION'
    return minute, None


def ret(price, entry):
    return 100 * (price / entry - 1)


def active(entry_minute, minute):
    return sum(entry_minute <= m < minute for m in minutes())


def delta_active(m1, m2):
    return sum(m1 <= m < m2 for m in minutes())


def quant(values, adverse='high'):
    v = [float(x) for x in values if x is not None]
    if not v:
        return {'n': 0, 'p10': None, 'p25': None, 'median': None,
                'p75': None, 'p90': None, 'worst': None}
    a = np.asarray(v)
    q = np.quantile(a, [.1, .25, .5, .75, .9])
    return dict(zip(('p10', 'p25', 'median', 'p75', 'p90'), map(float, q))) | {
        'n': len(v), 'worst': max(v) if adverse == 'high' else min(v)}


def focus(rows):
    if not rows:
        return {'sessions': 0, 'symbols': 0, 'topSession': None,
                'topSessionN': 0, 'topSymbol': None, 'topSymbolN': 0}
    sessions = Counter(r['session'] for r in rows)
    symbols = Counter(r['symbol'] for r in rows)
    s = sorted(sessions.items(), key=lambda x: (-x[1], x[0]))[0]
    y = sorted(symbols.items(), key=lambda x: (-x[1], x[0]))[0]
    return {'sessions': len(sessions), 'symbols': len(symbols),
            'topSession': s[0], 'topSessionN': s[1],
            'topSessionShare': s[1] / len(rows), 'topSymbol': y[0],
            'topSymbolN': y[1], 'topSymbolShare': y[1] / len(rows)}


def load():
    pre = HERE / 'ANATOMY_PRECOMMIT.json'
    spec = json.loads(pre.read_text())
    guard(spec['sourceManifestSha256'] == digest(HERE / 'SOURCE_MANIFEST.json'), 'PRECOMMIT_DRIFT')
    source = json.loads((HERE / 'SOURCE_MANIFEST.json').read_text())
    for name, pin in source['pins'].items():
        p = ROOT / pin['path']
        guard(digest(p) == pin['sha256'] and p.stat().st_size == pin['bytes'],
              'SOURCE_DRIFT:' + name)
    allow = json.loads((ROOT / source['pins']['entryAllowlist']['path']).read_text())
    entries = {arm: {} for arm in WORLD}
    with gzip.open(ROOT / source['pins']['phaseAAccounting']['path'], 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r['world'] == 'ALL_100':
                a, key = r['arm'], r['entryId']
                guard(a in WORLD and key not in entries[a] and
                      key == f"{r['session']}|{r['symbol']}|{r['entryMinute']}", 'ENTRY_ID')
                entries[a][key] = r
    guard(all(set(entries[a]) == set(allow[a]) for a in WORLD), 'ENTRY_SCOPE')
    with zipfile.ZipFile(ROOT / source['pins']['integrationZip']['path']) as z:
        manifest = json.loads(z.read('manifest.json'))
        for name, expected in manifest['filesSha256'].items():
            guard(hashlib.sha256(z.read(name)).hexdigest() == expected, 'ZIP_MEMBER_HASH')
        funded = {a: json.loads(gzip.decompress(z.read(f'{a}_V3_B_R50_A_ledger.json.gz')))['funded']
                  for a in WORLD}
    guard({a: len(funded[a]) for a in WORLD} == {'IM': 79, 'R1': 32}, 'FUNDED_SCOPE')
    for a in WORLD:
        for eid, f in funded[a].items():
            guard(eid in entries[a] and f['entryMinute'] == entries[a][eid]['entryMinute'] and
                  abs(float(f['effectiveEntryPrice']) - entries[a][eid]['entryPrice']) < 1e-7,
                  'FUNDED_IDENTITY')
    opportunity_ids = {e['opportunityId'] for a in WORLD for e in entries[a].values()}
    raw, skipped = project_raw(ROOT / source['pins']['rawPath']['path'], opportunity_ids)
    guard(skipped == 5375 - len(opportunity_ids), 'RAW_PROJECT_COUNT')
    return entries, funded, raw, skipped


def events(path, entry, mode):
    result = {}
    for m in MILESTONES:
        result[str(m)] = next((i for i, b in enumerate(path)
                               if (mode == 'HIGH' or b['kind'] == 'CONTINUOUS') and
                               b['highReturn' if mode == 'HIGH' else 'closeReturn'] >= m), None)
    return result


def build_path(entry, rows):
    em, day, cp = entry['entryMinute'], entry['session'], entry['entryPrice']
    grid = tuple(m for m in minutes() if m >= em)
    by_minute, dup, rejected = {}, [], Counter()
    for r in rows:
        minute, reason = canonical_minute(r)
        if reason:
            rejected[reason] += 1
            continue
        if minute in by_minute:
            dup.append(minute)
        by_minute[minute] = r
    invalid = [m for m in grid if m in by_minute and not valid(by_minute[m], m)]
    auction = by_minute.get(930)
    auction_good = 930 not in dup and valid(auction, 930, True)
    observed = [m for m in grid if m in by_minute and m not in dup and valid(by_minute[m], m)]
    price_known = isinstance(cp, (int, float)) and math.isfinite(cp) and cp > 0 and bool(observed)
    contiguous = price_known and len(observed) == len(grid) and not any(m in dup for m in grid)
    path_known = contiguous and auction_good
    bars = []
    if price_known:
        for m in observed:
            b = by_minute[m]
            bars.append({'minute': m, 'kind': 'CONTINUOUS',
                         'highReturn': ret(b[2], cp), 'lowReturn': ret(b[3], cp),
                         'closeReturn': ret(b[4], cp)})
        if auction_good:
            bars.append({'minute': 930, 'kind': 'AUCTION',
                         'highReturn': ret(auction[2], cp), 'lowReturn': ret(auction[3], cp),
                         'closeReturn': ret(auction[4], cp)})
    bars.sort(key=lambda x: x['minute'])
    return bars, {'priceKnown': price_known, 'continuousPathKnown': contiguous,
                  'pathKnown': path_known, 'stateKnown': False,
                  'expectedContinuousN': len(grid), 'observedContinuousN': len(observed),
                  'invalidContinuousN': len(invalid), 'missingContinuousN': len(grid) - len(observed),
                  'auctionKnown': auction_good, 'duplicateMinuteN': len(dup),
                  'rejectedBarReasons': dict(sorted(rejected.items()))}


def entry_row(arm, entry, funded, bars, mask):
    cp, em = entry['entryPrice'], entry['entryMinute']
    continuous = [b for b in bars if b['kind'] == 'CONTINUOUS']
    hi = max(bars, key=lambda b: (b['highReturn'], b['minute'])) if bars else None
    close = max(continuous, key=lambda b: (b['closeReturn'], b['minute'])) if continuous else None
    low = min(bars, key=lambda b: b['lowReturn']) if bars else None
    h_events, c_events = events(bars, cp, 'HIGH'), events(bars, cp, 'CLOSE')
    summary = {'arm': arm, 'entryId': entry['entryId'], 'session': entry['session'],
               'symbol': entry['symbol'], 'entryMinute': em, 'effectiveEntryPrice': cp,
               'entryCost100Jpy': entry['entryCostJpy'], 'funded': funded,
               **mask,
               'observedEntryHighPct': hi['highReturn'] if hi else None,
               'entryHighPct': hi['highReturn'] if mask['pathKnown'] and hi else None,
               'maxFinalizedContinuousClosePct': close['closeReturn'] if mask['pathKnown'] and close else None,
               'auctionReturnPct': bars[-1]['closeReturn'] if mask['auctionKnown'] and bars else None,
               'MFEHighPct': hi['highReturn'] if mask['pathKnown'] and hi else None,
               'MFEClosePct': close['closeReturn'] if mask['pathKnown'] and close else None,
               'MAEPct': low['lowReturn'] if mask['pathKnown'] and low else None,
               'timeToHighActiveMinutes': active(em, hi['minute']) if mask['pathKnown'] and hi else None,
               'highMinute': hi['minute'] if mask['pathKnown'] and hi else None,
               'highAtAuction': hi['kind'] == 'AUCTION' if mask['pathKnown'] and hi else None,
               'highEventIndex': h_events if mask['pathKnown'] else None,
               'closeEventIndex': c_events if mask['pathKnown'] else None,
               'observedHighTouch': {k: v is not None for k, v in h_events.items()},
               'timeToFirstHighActiveMinutes': {k: active(em, bars[v]['minute']) if v is not None else None
                                                for k, v in h_events.items()} if mask['pathKnown'] else None,
               'timeToFirstCloseActiveMinutes': {k: active(em, bars[v]['minute']) if v is not None else None
                                                 for k, v in c_events.items()} if mask['pathKnown'] else None,
               'hypotheticalMaxCloseNetMarkPct': close['closeReturn'] - 0.05 if mask['pathKnown'] and close else None,
               'hypotheticalAuctionNetMarkPct': bars[-1]['closeReturn'] - 0.05 if mask['pathKnown'] else None,
               'markCaveat': 'finalized Close hypothetical cost mark, no next OPEN fill'}
    return summary


def pullback_row(base, bars, m, target, anchor):
    floor = FLOORS.get(m)
    simultaneous = bars[anchor]['highReturn'] >= target
    first_target = None if simultaneous else next((j for j in range(anchor + 1, len(bars))
        if bars[j]['highReturn'] >= target), None)
    end = first_target if first_target is not None else len(bars)
    prior_peak, peak_minute = bars[anchor]['highReturn'], bars[anchor]['minute']
    drawdown, giveback_fraction, trough, trough_peak, trough_peak_minute = None, None, None, None, None
    for i in range(anchor + 1, end):
        b = bars[i]
        dd = prior_peak - b['lowReturn']
        if drawdown is None or dd > drawdown:
            drawdown, trough, trough_peak, trough_peak_minute = dd, i, prior_peak, peak_minute
            giveback_fraction = 100 * dd / prior_peak if prior_peak > 0 else None
        if b['highReturn'] >= prior_peak:
            prior_peak, peak_minute = b['highReturn'], b['minute']
    first_floor = (next((i for i in range(anchor + 1, len(bars))
                         if bars[i]['lowReturn'] <= floor), None) if floor is not None else None)
    first_strict_floor = (next((i for i in range(anchor + 1, len(bars))
                         if bars[i]['lowReturn'] < floor), None) if floor is not None else None)
    if simultaneous:
        cross = 'SAME_ANCHOR_BAR_HIGHER'
    elif first_target is None:
        cross = 'NO_LATER_HIGHER'
    elif first_floor is None or first_floor > first_target:
        cross = 'NO_CROSS'
    elif first_floor == first_target:
        cross = 'SAME_BAR_AMBIGUOUS'
    else:
        cross = 'DEFINITE_CROSS'
    if trough is None:
        recovery = former = new = None
        duration = None
    else:
        t = bars[trough]
        recovery = next((delta_active(t['minute'], b['minute']) for b in bars[trough + 1:]
                         if b['kind'] == 'CONTINUOUS' and b['closeReturn'] > t['closeReturn']), None)
        former = next((delta_active(t['minute'], b['minute']) for b in bars[trough + 1:]
                       if b['highReturn'] >= trough_peak), None)
        new = next((delta_active(t['minute'], b['minute']) for b in bars[trough + 1:]
                    if b['highReturn'] > trough_peak), None)
        duration = delta_active(trough_peak_minute, t['minute'])
    pretarget_min = min((bars[i]['lowReturn'] for i in range(anchor + 1, end)), default=None)
    return {'arm': base['arm'], 'entryId': base['entryId'], 'session': base['session'],
            'symbol': base['symbol'], 'funded': base['funded'], 'anchorPct': m,
            'targetPct': target, 'anchorMinute': bars[anchor]['minute'],
            'targetMinute': bars[first_target]['minute'] if first_target is not None else None,
            'higherSimultaneousAnchor': simultaneous, 'laterHigherReached': first_target is not None,
            'minimumReturnBeforeTargetPct': pretarget_min,
            'maxGivebackPp': drawdown, 'givebackFractionPct': giveback_fraction,
            'pullbackDurationActiveMinutes': duration, 'recoveryStartActiveMinutes': recovery,
            'formerHighRetouchActiveMinutes': former, 'newHighRefreshActiveMinutes': new,
            'floorPct': floor, 'floorCross': cross, 'floorStrictBreachBeforeTarget':
                first_strict_floor is not None and first_target is not None and
                first_strict_floor < first_target if floor is not None else None,
            'floorExactEqualityFirst': first_floor is not None and
                bars[first_floor]['lowReturn'] == floor if floor is not None else None,
            'sameTargetBarFloorTouch': first_target is not None and floor is not None and
                bars[first_target]['lowReturn'] <= floor if floor is not None else None,
            'anchorBarHighThenCloseAtOrBelowFloor':
                bars[anchor]['kind']=='CONTINUOUS' and bars[anchor]['closeReturn'] <= floor
                if floor is not None else None}


def weakness_row(base, bars, threshold):
    adverse = next((i for i, b in enumerate(bars) if b['lowReturn'] <= threshold), None)
    plus1 = next((i for i, b in enumerate(bars) if b['highReturn'] >= 1), None)
    before = adverse is not None and (plus1 is None or adverse < plus1)
    same = adverse is not None and adverse == plus1
    later, ambiguity = {}, {}
    for t in (1, 2, 3, 5, 7, 10):
        if adverse is None or not before:
            later[str(t)] = ambiguity[str(t)] = False
        else:
            ambiguity[str(t)] = bars[adverse]['highReturn'] >= t
            later[str(t)] = not ambiguity[str(t)] and any(
                b['highReturn'] >= t for b in bars[adverse + 1:])
    break_even = (next((delta_active(bars[adverse]['minute'], b['minute'])
                 for b in bars[adverse + 1:] if b['highReturn'] >= 0), None)
                  if adverse is not None and before else None)
    plus1_delay = (next((delta_active(bars[adverse]['minute'], b['minute'])
                    for b in bars[adverse + 1:] if b['highReturn'] >= 1), None)
                   if adverse is not None and before and not ambiguity['1'] else None)
    return {'arm': base['arm'], 'entryId': base['entryId'], 'session': base['session'],
            'symbol': base['symbol'], 'funded': base['funded'], 'thresholdPct': threshold,
            'reached': adverse is not None, 'beforePlus1': before, 'sameBarPlus1Ambiguous': same,
            'laterHigh': later, 'sameAdverseBarHighAmbiguous': ambiguity,
            'recoveryToEntryActiveMinutes': break_even,
            'recoveryToPlus1ActiveMinutes': plus1_delay,
            'worstFullPathMAEPct': min(b['lowReturn'] for b in bars)}


def prewinner_row(base, bars, target):
    """Strict earlier-bar lows; same target bar has unknown High/Low order."""
    first = base['highEventIndex'][str(target)]
    if first is None:
        return None
    earlier = [b['lowReturn'] for b in bars[:first]]
    same = bars[first]['lowReturn']
    return {'arm':base['arm'],'entryId':base['entryId'],'session':base['session'],
            'symbol':base['symbol'],'funded':base['funded'],'targetPct':target,
            'strictEarlierMinimumReturnPct':min(earlier) if earlier else None,
            'noStrictEarlierBar':not earlier,
            'crossBeforeTarget':{str(x):any(y<=x for y in earlier) for x in (-.5,-1,-2)},
            'sameTargetBarAmbiguous':{str(x):same<=x for x in (-.5,-1,-2)}}


def close_pullback_row(base,bars,m,target):
    """Finalized continuous 1m Close only; auction cannot trigger a Close milestone."""
    cont=[b for b in bars if b['kind']=='CONTINUOUS']
    anchor=base['closeEventIndex'][str(m)]
    if anchor is None:return None
    same=cont[anchor]['closeReturn']>=target
    first=next((j for j in range(anchor+1,len(cont)) if cont[j]['closeReturn']>=target),None) if not same else None
    end=first if first is not None else len(cont)
    peak=cont[anchor]['closeReturn'];peak_minute=cont[anchor]['minute']
    dd=trough=trough_peak=trough_peak_minute=None
    for j in range(anchor+1,end):
        b=cont[j];gap=peak-b['closeReturn']
        if dd is None or gap>dd:
            dd=gap;trough=j;trough_peak=peak;trough_peak_minute=peak_minute
        if b['closeReturn']>=peak:peak=b['closeReturn'];peak_minute=b['minute']
    if trough is None:recovery=former=new=duration=None
    else:
        z=cont[trough]
        recovery=next((delta_active(z['minute'],b['minute']) for b in cont[trough+1:]
                       if b['closeReturn']>z['closeReturn']),None)
        former=next((delta_active(z['minute'],b['minute']) for b in cont[trough+1:]
                     if b['closeReturn']>=trough_peak),None)
        new=next((delta_active(z['minute'],b['minute']) for b in cont[trough+1:]
                  if b['closeReturn']>trough_peak),None)
        duration=delta_active(trough_peak_minute,z['minute'])
    return {'arm':base['arm'],'entryId':base['entryId'],'session':base['session'],
            'symbol':base['symbol'],'funded':base['funded'],'anchorPct':m,'targetPct':target,
            'sameAnchorBarHigher':same,'laterHigherReached':first is not None,
            'minimumCloseBeforeTargetPct':min((cont[j]['closeReturn'] for j in range(anchor+1,end)),default=None),
            'maxCloseGivebackPp':dd,'pullbackDurationActiveMinutes':duration,
            'recoveryStartActiveMinutes':recovery,'formerHighRetouchActiveMinutes':former,
            'newHighRefreshActiveMinutes':new}


def summarize_prewinner(entries,rows):
    out={}
    for arm in WORLD:
        for subset in ('ALL','FUNDED'):
            cohort=[r for r in entries if r['arm']==arm and (subset=='ALL' or r['funded'])]
            known=sum(r['pathKnown'] for r in cohort)
            d={'totalN':len(cohort),'pathKnownN':known,'priceKnownN':sum(r['priceKnown'] for r in cohort),
               'stateKnownN':0,'unknownN':len(cohort)-known,'targets':{}}
            for target in (1,2,3,5,7,10):
                chosen=[r for r in rows if r['arm']==arm and r['targetPct']==target and
                        (subset=='ALL' or r['funded'])]
                d['targets'][str(target)]={'winnerN':len(chosen),
                    'noStrictEarlierBarN':sum(r['noStrictEarlierBar'] for r in chosen),
                    'strictEarlierCrossN':{str(t):sum(r['crossBeforeTarget'][str(t)] for r in chosen)
                                           for t in (-.5,-1,-2)},
                    'sameTargetBarAmbiguousN':{str(t):sum(r['sameTargetBarAmbiguous'][str(t)] for r in chosen)
                                               for t in (-.5,-1,-2)},
                    'preWinnerMinimumReturn':quant([r['strictEarlierMinimumReturnPct'] for r in chosen],'low'),
                    'concentration':focus(chosen)}
            out[arm+':'+subset]=d
    return out


def summarize_close_pairs(entries,rows):
    out={}
    for arm in WORLD:
        for subset in ('ALL','FUNDED'):
            cohort=[r for r in entries if r['arm']==arm and (subset=='ALL' or r['funded'])]
            d={'totalN':len(cohort),'pathKnownN':sum(r['pathKnown'] for r in cohort),
               'priceKnownN':sum(r['priceKnown'] for r in cohort),'stateKnownN':0,
               'unknownN':sum(not r['pathKnown'] for r in cohort),'pairs':{}}
            for m,targets in PAIRS.items():
                d['pairs'][str(m)]={}
                for t in targets:
                    selected=[r for r in rows if r['arm']==arm and r['anchorPct']==m and r['targetPct']==t
                              and (subset=='ALL' or r['funded'])]
                    wins=[r for r in selected if r['laterHigherReached']]
                    d['pairs'][str(m)][str(t)]={'anchorReachedN':len(selected),'laterHigherReachedN':len(wins),
                        'sameAnchorBarHigherN':sum(r['sameAnchorBarHigher'] for r in selected),
                        'minimumCloseBeforeTarget':quant([r['minimumCloseBeforeTargetPct'] for r in wins],'low'),
                        'maxCloseGivebackPp':quant([r['maxCloseGivebackPp'] for r in wins]),
                        'pullbackDurationActive':quant([r['pullbackDurationActiveMinutes'] for r in wins]),
                        'recoveryStartActive':quant([r['recoveryStartActiveMinutes'] for r in wins]),
                        'formerHighRetouchActive':quant([r['formerHighRetouchActiveMinutes'] for r in wins]),
                        'newHighRefreshActive':quant([r['newHighRefreshActiveMinutes'] for r in wins])}
            out[arm+':'+subset]=d
    return out


def state_row(base, bars):
    one = next((i for i, b in enumerate(bars) if b['highReturn'] >= 1), None)
    if one is None:
        return None
    checkpoint = next((j for j in range(one + 1, len(bars))
                       if bars[j]['kind'] == 'CONTINUOUS' and bars[j]['closeReturn'] <= .5), None)
    if checkpoint is None:
        return None
    prior = bars[:checkpoint]
    if any(b['highReturn'] >= 5 for b in bars[:checkpoint + 1]):
        return {'excludedPriorOrSameBarPlus5': True, 'arm': base['arm'], 'entryId': base['entryId']}
    current = bars[checkpoint]
    prefix = bars[:checkpoint + 1]
    closes = [b['closeReturn'] for b in prefix if b['kind'] == 'CONTINUOUS']
    prev_high = max(b['highReturn'] for b in prior)
    last_peak = max(i for i, b in enumerate(prior) if b['highReturn'] == prev_high)
    down = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            down += 1
        else:
            break
    recent = [b for b in prefix if b['kind'] == 'CONTINUOUS']
    diffs = [recent[i]['closeReturn'] - recent[i - 1]['closeReturn']
             for i in range(max(1, len(recent) - 5), len(recent))]
    low_since_peak = min((b['closeReturn'] for b in prefix[last_peak + 1:] if
                          b['kind'] == 'CONTINUOUS'), default=None)
    denom = prev_high - low_since_peak if low_since_peak is not None else None
    return {'excludedPriorOrSameBarPlus5': False, 'arm': base['arm'],
            'entryId': base['entryId'], 'session': base['session'], 'symbol': base['symbol'],
            'checkpointMinute': current['minute'], 'priorPeakPct': prev_high,
            'currentClosePct': current['closeReturn'], 'givebackPp': prev_high-current['closeReturn'],
            'laterPlus5': any(b['highReturn'] >= 5 for b in bars[checkpoint + 1:]),
            'consecutiveDownCloses': down,
            'lowerHighCount3': sum(recent[i]['highReturn'] < recent[i-1]['highReturn']
                                  for i in range(max(1,len(recent)-3),len(recent))),
            'lowerLowCount3': sum(recent[i]['lowReturn'] < recent[i-1]['lowReturn']
                                 for i in range(max(1,len(recent)-3),len(recent))),
            'drawdownFromPriorPeakPp': prev_high-current['closeReturn'],
            'last3CloseSlopePp': closes[-1]-closes[-4] if len(closes)>=4 else None,
            'last5ClosePathEfficiency': abs(sum(diffs))/sum(abs(d) for d in diffs)
                 if len(diffs)==5 and sum(abs(d) for d in diffs)>0 else None,
            'reboundToPriorDrawdownRatio': (current['closeReturn']-low_since_peak)/denom
                 if denom is not None and denom>0 else None,
            'barsSinceNewHigh': checkpoint-last_peak,
            'peakBinHalfPp': math.floor(prev_high*2)/2,
            'closeBinHalfPp': math.floor(current['closeReturn']*2)/2,
            'returnPath': [{'minute': b['minute'], 'highPct': b['highReturn'],
                            'lowPct': b['lowReturn'], 'closePct': b['closeReturn']}
                           for b in bars if b['kind']=='CONTINUOUS']}


def summarize(entries, pairs, weakness, states):
    opp, initial, pull, floors, state_out = {}, {}, {}, {}, {}
    for a in WORLD:
        for subset, subset_rows in [('ALL', [r for r in entries if r['arm']==a]),
                                    ('FUNDED', [r for r in entries if r['arm']==a and r['funded']])]:
            key = a+':'+subset
            known = [r for r in subset_rows if r['pathKnown']]
            opp[key] = {'totalN': len(subset_rows), 'pathKnownN': len(known),
                        'priceKnownN': sum(r['priceKnown'] for r in subset_rows),
                        'continuousPathKnownN': sum(r['continuousPathKnown'] for r in subset_rows),
                        'stateKnownN': 0, 'unknownN': len(subset_rows)-len(known),
                        'auctionMissingOrInvalidN': sum(not r['auctionKnown'] for r in subset_rows),
                        'missingContinuousEntryN': sum(r['missingContinuousN']>0 for r in subset_rows),
                        'entryHighMeanPct': statistics.mean(r['entryHighPct'] for r in known) if known else None,
                        'entryHighMedianPct': statistics.median(r['entryHighPct'] for r in known) if known else None,
                        'entryHighDistribution': quant([r['entryHighPct'] for r in known], 'high'),
                        'MAEDistribution': quant([r['MAEPct'] for r in known], 'low'),
                        'maxCloseDistribution': quant([r['maxFinalizedContinuousClosePct'] for r in known]),
                        'timeToHigh': quant([r['timeToHighActiveMinutes'] for r in known]),
                        'highMilestoneReached': {str(m): sum(r['highEventIndex'][str(m)] is not None
                                                      for r in known) for m in MILESTONES},
                        'closeMilestoneReached': {str(m): sum(r['closeEventIndex'][str(m)] is not None
                                                       for r in known) for m in MILESTONES},
                        'observedHighTouchOnIncompletePath': {str(m): sum(r['observedHighTouch'][str(m)]
                            for r in subset_rows if not r['pathKnown']) for m in MILESTONES},
                        'timeToFirstHigh': {str(m): quant([r['timeToFirstHighActiveMinutes'][str(m)]
                            for r in known]) for m in MILESTONES},
                        'timeToFirstClose': {str(m): quant([r['timeToFirstCloseActiveMinutes'][str(m)]
                            for r in known]) for m in MILESTONES},
                        'concentration': focus(known)}
            initial[key] = {}
            for t in (-.5, -1):
                rows = [r for r in weakness if r['arm']==a and r['thresholdPct']==t and
                        (subset=='ALL' or r['funded'])]
                before = [r for r in rows if r['beforePlus1']]
                initial[key][str(t)] = {'totalN': len(subset_rows), 'pathKnownN': len(rows),
                    'priceKnownN': opp[key]['priceKnownN'], 'stateKnownN': 0,
                    'unknownN': len(subset_rows)-len(rows), 'reachedN': sum(r['reached'] for r in rows),
                    'beforePlus1N': len(before), 'sameBarPlus1AmbiguousN':
                        sum(r['sameBarPlus1Ambiguous'] for r in rows),
                    'laterWinnerN': {str(z): sum(r['laterHigh'][str(z)] for r in before)
                                     for z in (1,2,3,5,7,10)},
                    'sameAdverseBarAmbiguousN': {str(z): sum(r['sameAdverseBarHighAmbiguous'][str(z)]
                        for r in before) for z in (1,2,3,5,7,10)},
                    'recoveryToEntryActive': quant([r['recoveryToEntryActiveMinutes'] for r in before]),
                    'recoveryToPlus1Active': quant([r['recoveryToPlus1ActiveMinutes'] for r in before]),
                    'worstMAE': quant([r['worstFullPathMAEPct'] for r in before], 'low'),
                    'concentration': focus(before)}
            pull[key], floors[key] = {}, {}
            for anchor, targets in PAIRS.items():
                ar = [r for r in pairs if r['arm']==a and r['anchorPct']==anchor and
                      (subset=='ALL' or r['funded'])]
                pull[key][str(anchor)] = {}
                for t in targets:
                    rr = [r for r in ar if r['targetPct']==t]
                    progressed = [r for r in rr if r['laterHigherReached']]
                    pull[key][str(anchor)][str(t)] = {
                        'totalN': len(subset_rows), 'pathKnownN': opp[key]['pathKnownN'],
                        'priceKnownN': opp[key]['priceKnownN'], 'stateKnownN': 0,
                        'unknownN': opp[key]['unknownN'], 'anchorReachedN': len(rr),
                        'laterHigherReachedN': len(progressed),
                        'laterHigherNotReachedN': sum(not r['laterHigherReached'] and
                                                       not r['higherSimultaneousAnchor'] for r in rr),
                        'sameAnchorBarHigherN': sum(r['higherSimultaneousAnchor'] for r in rr),
                        'minimumReturnBeforeTarget': quant([r['minimumReturnBeforeTargetPct']
                                                             for r in progressed], 'low'),
                        'minimumReturnIfNotReached': quant([r['minimumReturnBeforeTargetPct']
                          for r in rr if not r['laterHigherReached'] and not r['higherSimultaneousAnchor']], 'low'),
                        'maxGivebackPp': quant([r['maxGivebackPp'] for r in progressed]),
                        'givebackFractionPct': quant([r['givebackFractionPct'] for r in progressed]),
                        'pullbackDurationActive': quant([r['pullbackDurationActiveMinutes']
                                                         for r in progressed]),
                        'recoveryStartActive': quant([r['recoveryStartActiveMinutes'] for r in progressed]),
                        'formerHighRetouchActive': quant([r['formerHighRetouchActiveMinutes'] for r in progressed]),
                        'newHighRefreshActive': quant([r['newHighRefreshActiveMinutes'] for r in progressed]),
                        'progressedConcentration': focus(progressed)}
                if anchor in FLOORS:
                    floors[key][str(anchor)] = {'floorPct': FLOORS[anchor], 'anchorReachedN': len(ar)//len(targets),
                      'targets': {str(t): {'laterWinnerN': sum(r['laterHigherReached'] for r in ar if r['targetPct']==t),
                          'definiteCrossBeforeWinnerN': sum(r['floorCross']=='DEFINITE_CROSS'
                              for r in ar if r['targetPct']==t),
                          'sameBarOrderAmbiguousN': sum(r['floorCross']=='SAME_BAR_AMBIGUOUS'
                              for r in ar if r['targetPct']==t),
                          'noCrossN': sum(r['floorCross']=='NO_CROSS' for r in ar if r['targetPct']==t),
                          'sameAnchorBarHigherN': sum(r['floorCross']=='SAME_ANCHOR_BAR_HIGHER'
                              for r in ar if r['targetPct']==t),
                          'strictBreachBeforeWinnerN': sum(r['floorStrictBreachBeforeTarget'] is True
                              for r in ar if r['targetPct']==t),
                          'exactEqualityFirstN': sum(r['floorExactEqualityFirst'] is True
                              for r in ar if r['targetPct']==t),
                          'sameAnchorBarHighThenCloseAtOrBelowFloorN':
                              sum(r['anchorBarHighThenCloseAtOrBelowFloor'] is True
                                  for r in ar if r['targetPct']==t)} for t in targets},
                      'pathKnownN': opp[key]['pathKnownN'], 'priceKnownN': opp[key]['priceKnownN'],
                      'stateKnownN': 0, 'unknownN': opp[key]['unknownN']}
            ss = [r for r in states if r['arm']==a and (subset=='ALL' or r.get('funded'))]
            state_out[key] = {'totalN': len(subset_rows), 'pathKnownN': len(known),
                'priceKnownN': opp[key]['priceKnownN'], 'stateKnownN': 0,
                'unknownN': opp[key]['unknownN'], 'checkpointCandidatesN': len(ss),
                'priorOrSameBarPlus5ExcludedN': sum(r['excludedPriorOrSameBarPlus5'] for r in ss),
                'diagnosticN': sum(not r['excludedPriorOrSameBarPlus5'] for r in ss),
                'snapshotStatus': 'BLOCKED_EXACT_STATE_SIGNAL_SNAPSHOT',
                'causalPrimitiveStatus': 'HISTORICAL_BAR_END_PROXY_ONLY'}
    return opp, initial, pull, floors, state_out


def main():
    gate=json.loads((HERE/'PRE_MAIN_INPUT_CONTRACT_GATE.json').read_text())
    guard(gate['status']=='PASS' and gate['allPass'], 'PRE_MAIN_GATE')
    guard(not (HERE / 'RUN_INVALID_POSTPROCESS.json').exists(), 'MAIN_BUDGET_EXHAUSTED')
    marker = HERE / 'ANATOMY_RUN_STARTED.json'
    resuming_pre_path_failure = (marker.exists() and
        (HERE / 'RUN_INVALID_PREFLIGHT.json').exists())
    guard(not marker.exists() or resuming_pre_path_failure, 'MAIN_BUDGET_USED')
    guard(not (HERE / 'ENTRY_HIGH_ANATOMY.json').exists(), 'RESULT_EXISTS')
    guard(json.loads((HERE/'START_AUDIT.json').read_text())['basisHead'] ==
          json.loads((HERE/'ANATOMY_PRECOMMIT.json').read_text())['basisHead'], 'BASIS')
    if not resuming_pre_path_failure:
        write('ANATOMY_RUN_STARTED.json', {'atJst': datetime.now(timezone(timedelta(hours=9))).isoformat(),
            'path_anatomy_main': 1, 'new_policy_replays': 0, 'new_provider_requests': 0})
    else:
        write('ANATOMY_PREFLIGHT_RESUME.json', {'atJst': datetime.now(timezone(timedelta(hours=9))).isoformat(),
            'priorError': 'funded effective Entry numeric string conversion before any raw path projection',
            'newPathOutcomesPreviouslyComputed': 0, 'path_anatomy_main_finalBudget': 1})
    entries, funded, raw, skipped = load()
    entry_rows, pair_rows, weak_rows, state_rows, prewinner_rows, close_pair_rows = [], [], [], [], [], []
    state_paths = {}
    for arm in WORLD:
        for eid in sorted(entries[arm]):
            entry = entries[arm][eid]
            bars, mask = build_path(entry, raw[entry['opportunityId']])
            base = entry_row(arm, entry, eid in funded[arm], bars, mask)
            entry_rows.append(base)
            if not mask['pathKnown']:
                continue
            for m, targets in PAIRS.items():
                anchor = base['highEventIndex'][str(m)]
                if anchor is not None:
                    for t in targets:
                        pair_rows.append(pullback_row(base, bars, m, t, anchor))
                if base['closeEventIndex'][str(m)] is not None:
                    for t in targets:
                        close_pair_rows.append(close_pullback_row(base,bars,m,t))
            for t in (1,2,3,5,7,10):
                r=prewinner_row(base,bars,t)
                if r is not None:prewinner_rows.append(r)
            for t in (-.5, -1):
                weak_rows.append(weakness_row(base, bars, t))
            state = state_row(base, bars)
            if state:
                state['funded'] = base['funded']
                path = state.pop('returnPath', None)
                if path is not None:
                    state_paths[(arm,eid)] = path
                state_rows.append(state)
    opp, initial, pull, floors, state_summary = summarize(entry_rows,pair_rows,weak_rows,state_rows)
    gzwrite('ENTRY_PATH_ROWS.jsonl.gz', entry_rows)
    gzwrite('MILESTONE_PAIR_ROWS.jsonl.gz', pair_rows)
    gzwrite('INITIAL_WEAKNESS_ROWS.jsonl.gz', weak_rows)
    gzwrite('PATH_STATE_CHECKPOINT_ROWS.jsonl.gz', state_rows)
    gzwrite('PRE_WINNER_DOWNSIDE_ROWS.jsonl.gz',prewinner_rows)
    gzwrite('CLOSE_MILESTONE_PAIR_ROWS.jsonl.gz',close_pair_rows)
    write('ENTRY_HIGH_ANATOMY.json', opp)
    write('INITIAL_WEAKNESS_ANATOMY.json', initial)
    write('MILESTONE_PULLBACK_ANATOMY.json', pull)
    write('OPERATOR_FLOOR_DIAGNOSTIC.json', floors)
    write('PRE_WINNER_DOWNSIDE_ANATOMY.json',summarize_prewinner(entry_rows,prewinner_rows))
    write('CLOSE_MILESTONE_PULLBACK_ANATOMY.json',summarize_close_pairs(entry_rows,close_pair_rows))
    write('PATH_STATE_AVAILABILITY.json', {
        'allEntries':len(entry_rows), 'rawAllowlistPayloadsDecoded':len(raw),
        'outOfScopeRawPayloadsSkippedBeforeDecode':skipped,
        'stateKnownN':0, 'signalKnownN':0,
        'historicalBarEndProxyAvailable':True,'providerPublicationKnownAtVerified':False,
        'primitiveSources':'owned valid completed 1m OHLC only; no future High in features',
        'existingExactSnapshot':'BLOCKED; previous target availability reports zero exact joined State/Signal rows',
        'vwap':'BLOCKED exact producer/snapshot provenance; not used',
        'volume':'raw exists but unit/producer partially unknown; not used',
        'missingNoTradeHalt':'UNKNOWN; absent bars never imputed',
        'auction':'single-price 15:30 separate endpoint; not a 1m State checkpoint',
        'byWorld':state_summary})
    make_state_summary(state_rows, state_paths, state_summary)
    figures(entry_rows,pair_rows,weak_rows,state_rows,state_paths,opp,initial,pull,floors)
    print(json.dumps({'status':'MAIN_DONE', 'rows':len(entry_rows),
                      'pairs':len(pair_rows),'weak':len(weak_rows),
                      'pathKnown':{k:v['pathKnownN'] for k,v in opp.items()}},ensure_ascii=False))


def make_state_summary(rows, paths, availability):
    out = {'byWorld':{}, 'conclusion':'STATE_INCREMENT_NOT_DEMONSTRATED',
           'reason':'descriptive, correlated Development observations; exact State/Signal snapshot unavailable; no fit or held-out test',
           'classifierFits':0, 'thresholdSelected':False}
    fields = ['consecutiveDownCloses','lowerHighCount3','lowerLowCount3',
              'drawdownFromPriorPeakPp','last3CloseSlopePp','last5ClosePathEfficiency',
              'reboundToPriorDrawdownRatio','barsSinceNewHigh']
    for a in WORLD:
        rr = [r for r in rows if r['arm']==a and not r['excludedPriorOrSameBarPlus5']]
        groups = {}
        for flag in (True,False):
            group = [r for r in rr if r['laterPlus5']==flag]
            groups['RECOVERY' if flag else 'NO_LATER_PLUS5'] = {
                'n':len(group), 'concentration':focus(group),
                'primitive':{f:quant([r[f] for r in group], 'low' if f=='last3CloseSlopePp' else 'high')
                             for f in fields}}
        bins = defaultdict(list)
        for r in rr:
            bins[(r['peakBinHalfPp'],r['closeBinHalfPp'])].append(r)
        matched = []
        for (p,c),br in sorted(bins.items()):
            yes = [r for r in br if r['laterPlus5']]
            no = [r for r in br if not r['laterPlus5']]
            if yes and no:
                matched.append({'peakBin':p,'currentBin':c,'recoveryN':len(yes),
                    'noLaterPlus5N':len(no),
                    'primitiveMedianRecovery':{f:quant([r[f] for r in yes])['median'] for f in fields},
                    'primitiveMedianNoLaterPlus5':{f:quant([r[f] for r in no])['median'] for f in fields}})
        out['byWorld'][a]={'checkpointN':len(rr),'groups':groups,
                           'samePeakAndCurrentHalfPpBins':matched,
                           'overlapBinN':len(matched),
                           'overlapRowsN':sum(z['recoveryN']+z['noLaterPlus5N'] for z in matched)}
    write('PATH_STATE_ANATOMY.json',out)


def figures(entries,pairs,weak,states,paths,opp,initial,pull,floors):
    dest = HERE/'figures'
    dest.mkdir(exist_ok=False)
    def finish(name, title, xlabel, ylabel):
        plt.title(title);plt.xlabel(xlabel);plt.ylabel(ylabel)
        plt.grid(alpha=.2);plt.tight_layout();plt.savefig(dest/name,dpi=160);plt.close()
    known = {a:[r for r in entries if r['arm']==a and r['pathKnown']] for a in WORLD}
    if any(known.values()):
        for a in WORLD:
            v=[r['entryHighPct'] for r in known[a]]
            if v: plt.hist(v,bins=25,alpha=.5,label=f'{a} N={len(v)}')
        plt.legend();finish('01_entry_high.png','Entry to observed High, complete paths','High return %','Entries')
    data=[]; labels=[]
    for m in PAIRS:
        v=[r['maxGivebackPp'] for r in pairs if r['anchorPct']==m and r['targetPct']==PAIRS[m][-1]
           and r['laterHigherReached'] and r['maxGivebackPp'] is not None]
        if v: data.append(v);labels.append(f'+{m} to +{PAIRS[m][-1]}\nN={len(v)}')
    if data:
        plt.boxplot(data,tick_labels=labels,showfliers=True)
        finish('02_milestone_giveback.png','Pre-target giveback (complete paths)','Anchor to later High','Giveback pp')
    data=[];labels=[]
    for m in (1,2,3):
        t=PAIRS[m][-1]
        v=[r['minimumReturnBeforeTargetPct'] for r in pairs if r['anchorPct']==m and
           r['targetPct']==t and r['laterHigherReached'] and r['minimumReturnBeforeTargetPct'] is not None]
        if v:data.append(v);labels.append(f'+{m} to +{t}\nN={len(v)}')
    if data:
        plt.boxplot(data,tick_labels=labels,showfliers=True)
        finish('03_minimum_before_later_winner.png','Minimum before later winner','Anchor to later High','Minimum return %')
    labels=[];values=[]
    for a in WORLD:
        for t in (-.5,-1):
            ww=[r for r in weak if r['arm']==a and r['thresholdPct']==t and r['beforePlus1']]
            if ww:
                labels.append(f'{a} {t}%\nN={len(ww)}')
                values.append([100*sum(r['laterHigh'][str(z)] for r in ww)/len(ww)
                               for z in (1,2,3,5,10)])
    if values:
        x=np.arange(5);width=.8/len(values)
        for i,(label,v) in enumerate(zip(labels,values)):
            plt.bar(x-.4+width*(i+.5),v,width,label=label)
        plt.xticks(x,['+1','+2','+3','+5','+10']);plt.legend(fontsize=7)
        finish('04_weakness_recovery.png','Later High after initial weakness, full paths','Later High','Percent of before-+1 weakness')
    labels=[];v=[];amb=[]
    for a in WORLD:
        for m in FLOORS:
            t=PAIRS[m][-1]; f=floors[a+':ALL'][str(m)]['targets'][str(t)]
            if f['laterWinnerN']:
                labels.append(f'{a} +{m} to +{t}\nN={f["laterWinnerN"]}')
                v.append(100*f['definiteCrossBeforeWinnerN']/f['laterWinnerN'])
                amb.append(100*f['sameBarOrderAmbiguousN']/f['laterWinnerN'])
    if v:
        x=np.arange(len(v));plt.bar(x,v,label='Definite earlier floor touch')
        plt.bar(x,amb,bottom=v,label='Same-bar order unknown',alpha=.5)
        plt.xticks(x,labels,rotation=15,fontsize=8);plt.legend(fontsize=8)
        finish('05_candidate_floor_cross.png','Candidate floor before later High, full paths','World / anchor / target','Percent')
    rr=[r for r in states if not r['excludedPriorOrSameBarPlus5']]
    selected=[]
    for flag in (True,False):
        group=[r for r in rr if r['laterPlus5']==flag]
        if group:
            p=statistics.median(r['priorPeakPct'] for r in group)
            c=statistics.median(r['currentClosePct'] for r in group)
            row=min(group,key=lambda r:(abs(r['priorPeakPct']-p)+abs(r['currentClosePct']-c),r['arm'],r['entryId']))
            selected.append(row)
    if selected:
        for r in selected:
            path=paths[(r['arm'],r['entryId'])]
            x=[i for i,b in enumerate(path) if b['minute']<=r['checkpointMinute']+10]
            plt.plot(x,[path[i]['closePct'] for i in x],label=f'{r["arm"]} {"later +5" if r["laterPlus5"] else "no later +5"}')
        plt.axhline(0,color='gray',linewidth=.7);plt.legend()
        finish('06_causal_state_paths.png','Deterministic median-nearest examples, up to checkpoint +10m','Observed bar index','Close return %')


if __name__=='__main__':
    main()
