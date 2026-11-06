"""Adapter-only replay of two immutable Entry ledgers through frozen Candidate A.

No Entry policy, model, provider, allocation or production module is invoked.
Calendar/price conventions are preregistered in ADAPTER_CONTRACT_R13.json.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import importlib.util
import io
import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/phase57-dual-entry-exit-integration-v1'
CONTRACT = EVIDENCE / 'ADAPTER_CONTRACT_R13.json'
FREEZE = 'docs/evidence/phase57-entry-all-material-v1/ENTRY_DUAL_FREEZE_R10.json'
IMM = 'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz'
RAW = 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
COHORT = 'docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json'
CANDIDATE = 'scripts/phase57_new_long_exit_candidate_a.py'
FIXED = 'predict/long-only/phase57_long_exit_continuation_v1.py'
ARMS = ('IMMEDIATE', 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF')
SAFETY = {k: False for k in (
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
    'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
    'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted')}
ENVELOPE_KEYS = ('opportunity', 'session', 'symbol', 'entryId', 'entryMinute', 'price')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       allow_nan=False, separators=(',', ':')) + '\n').encode()


def read(path):
    p = Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())



def read_allowlisted_paths(path, allowed):
    """Deserialize only preauthorized top-level values of the saved raw archive.

    Other values are opaque: scan structural boundaries without decoding their
    contents or materializing records. Archive bytes are SHA-pinned separately.
    """
    text = gzip.decompress(Path(path).read_bytes()).decode('utf-8')
    decoder = json.JSONDecoder()
    tokens = re.compile(r'"(?:[^"\\]|\\.)*"|[{}\[\]]')
    def whitespace(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos
    pos = whitespace(0)
    if pos >= len(text) or text[pos] != '{':
        raise ValueError('RAW_ARCHIVE_NOT_OBJECT')
    pos = whitespace(pos + 1)
    seen, selected = set(), {}
    while pos < len(text) and text[pos] != '}':
        key, pos = decoder.raw_decode(text, pos)
        if not isinstance(key, str) or key in seen:
            raise ValueError('DUPLICATE_RAW_IDENTITY')
        seen.add(key)
        pos = whitespace(pos)
        if text[pos] != ':':
            raise ValueError('INVALID_RAW_ARCHIVE_SEPARATOR')
        pos = whitespace(pos + 1)
        if key in allowed:
            value, pos = decoder.raw_decode(text, pos)
            if not isinstance(value, dict):
                raise ValueError('RAW_PATH_NOT_OBJECT')
            selected[key] = value
        else:
            if text[pos] != '{':
                raise ValueError('QUARANTINED_VALUE_NOT_OBJECT')
            depth = 0
            for token in tokens.finditer(text, pos):
                value = token.group()
                if value in ('{', '['):
                    depth += 1
                elif value in ('}', ']'):
                    depth -= 1
                    if depth == 0:
                        pos = token.end()
                        break
            else:
                raise ValueError('UNTERMINATED_QUARANTINED_VALUE')
        pos = whitespace(pos)
        if text[pos] == ',':
            pos = whitespace(pos + 1)
        elif text[pos] != '}':
            raise ValueError('INVALID_RAW_ARCHIVE_SEPARATOR')
    if pos >= len(text) or text[pos] != '}' or text[pos + 1:].strip():
        raise ValueError('INVALID_RAW_ARCHIVE_END')
    if set(selected) != set(allowed):
        raise ValueError('MISSING_ALLOWED_RAW_IDENTITIES')
    return selected



def write_new(path, value):
    p = Path(path)
    data = encoded(value)
    if p.suffix == '.gz':
        buf = io.BytesIO()
        with gzip.GzipFile(filename='', fileobj=buf, mode='wb', mtime=0) as fh:
            fh.write(data)
        data = buf.getvalue()
    with p.open('xb') as fh:
        fh.write(data)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def stamp(day, minute):
    return f'{day}T{minute // 60:02d}:{minute % 60:02d}:00+09:00'


def elapsed(start, end):
    return (dt.datetime.fromisoformat(end) - dt.datetime.fromisoformat(start)).total_seconds() / 60


def envelope(record):
    """Whitelist, not a copy of the future-labeled record. Never reselect Entry."""
    e = {k: record[k] for k in ENVELOPE_KEYS}
    if e['opportunity'] != f"{e['session']}|{e['symbol']}":
        raise ValueError('ENTRY_IDENTITY_MISMATCH')
    dt.date.fromisoformat(e['session'])
    if e['entryId'] is None:
        if e['entryMinute'] is not None or e['price'] is not None:
            raise ValueError('NO_ENTRY_WITH_PRICE_OR_TIME')
        return e
    minute = e['entryMinute']
    if not isinstance(minute, int) or isinstance(minute, bool):
        raise ValueError('INVALID_ENTRY_MINUTE')
    if e['entryId'] != f"{e['opportunity']}|{minute}":
        raise ValueError('ENTRY_IDENTITY_MISMATCH')
    if not number(e['price']) or e['price'] <= 0:
        raise ValueError('INVALID_FROZEN_ENTRY_PRICE')
    return e


def calendar_end(day):
    # EXACT inherited regular-grid calendar parameter; do not silently shorten
    # 15:30 to 15:25 to make missing terminal reference bars evaluable.
    return 900 if day < '2024-11-05' else 930


def regular_start(minute, end):
    return 540 <= minute < end and not 690 <= minute < 750


def adapt(e, raw_path):
    """Build calendar-anchored bars entirely after immutable Entry time.

    The containing partial bucket is not a completed post-entry regular5m bar.
    Sparse observed-minute aggregation is inherited, never interpolated. Its
    OPEN is timestamped at its first actual source minute, never backdated.
    """
    if e['entryId'] is None:
        return {'status': 'NO_ENTRY', 'entry': e, 'future': []}
    start, day, price = e['entryMinute'], e['session'], e['price']
    end = calendar_end(day)
    if not regular_start(start, end):
        raise ValueError('ENTRY_OUTSIDE_REGULAR_SESSION')
    rows = {}
    for r in raw_path['today']:
        if len(r) != 7 or not all(number(x) for x in r[:5]) or r[0] != int(r[0]):
            raise ValueError('INVALID_SOURCE_MINUTE')
        minute = int(r[0])
        if minute in rows or not 0 <= minute < 1440:
            raise ValueError('DUPLICATE_OR_INVALID_SOURCE_MINUTE')
        if min(r[1:5]) <= 0 or r[2] < max(r[1], r[4]) or r[3] > min(r[1], r[4]):
            raise ValueError('INVALID_SOURCE_OHLC')
        rows[minute] = r
    opening = rows.get(start)
    if opening is None or not math.isclose(price, opening[1] * 1.0005, rel_tol=1e-12):
        raise ValueError('FROZEN_FILL_VS_RAW_OPEN_MISMATCH')
    first = ((start + 4) // 5) * 5
    starts = [m for m in range(540, end, 5) if m >= first and regular_start(m, end)]
    bars = []
    for slot, m in enumerate(starts, 1):
        observed = [rows[t] for t in range(m, m + 5) if t in rows and t not in (690, 930)]
        b = {'slot': slot, 'start': stamp(day, m), 'end': stamp(day, m + 5),
             'minutes': m + 5 - start, 'missing': not observed,
             'observedMinutes': len(observed)}
        if observed:
            values = (observed[0][1], max(r[2] for r in observed),
                      min(r[3] for r in observed), observed[-1][4])
            b.update({k: 100 * (v / price - 1) for k, v in zip(('o', 'h', 'l', 'c'), values)})
            b.update(openTimestamp=stamp(day, int(observed[0][0])),
                     lastSourceMinute=int(observed[-1][0]))
            if b['openTimestamp'] < b['start'] or b['openTimestamp'] >= b['end']:
                raise ValueError('OPEN_TIMESTAMP_OUTSIDE_BUCKET')
        bars.append(b)
    return {'status': 'REFERENCE_POSITION', 'entry': e, 'direction': 'LONG',
            'positionStartTimestamp': stamp(day, start), 'startMinute': start,
            'sessionEndMinute': end, 'expectedBars': len(bars),
            'initialPartialBucketMinutesNotUsed': first - start,
            'fillPriceAssumption': price, 'rawEntryOpen': opening[1],
            'sourceHash': raw_path.get('sourceHash'),
            'fillSemantics': 'FROZEN_RAW_1M_OPEN_PLUS_5BPS_NOT_EXECUTION',
            'future': bars}


def replay_pair(event, candidate, fixed_runtime):
    if event['status'] == 'NO_ENTRY':
        return {k: {'status': 'NO_ENTRY', 'netPct': None} for k in ('fixed12', 'candidateA')}
    fixed = fixed_runtime.replay(event, 'FIXED12')
    cap = min(12, event['expectedBars'])
    bars = event['future'][:cap]
    # A Fixed12-unresolved future must NOT suppress an earlier causal Candidate
    # exit. The same unchanged policy runs; only its unavailable fallback is null.
    fallback = fixed if fixed['status'] == 'EXIT_REFERENCE' else {
        'exitBar': cap, 'grossPct': None, 'netPct': None}
    out = candidate.policy(bars, fallback)
    if out['status'] == 'PROTECT_EXIT':
        target = bars[out['exitBar'] - 1]
        signal = bars[out['signalBar'] - 1]
        when = target['openTimestamp']
        if when < signal['end']:
            raise ValueError('EXIT_BEFORE_COMPLETED_SIGNAL')
        a = dict(out, status='EXIT_REFERENCE', reason='PROTECT_EXIT',
                 exitTimestamp=when, signalTimestamp=signal['end'],
                 holdingClockMinutes=elapsed(event['positionStartTimestamp'], when),
                 referenceAt='FIRST_OBSERVED_OPEN_OF_NEXT_REGULAR5M_BUCKET',
                 sparseOpenDelayMinutes=elapsed(target['start'], when))
    elif fixed['status'] == 'EXIT_REFERENCE':
        a = dict(fixed, candidateExitReason='FIXED12_FALLBACK',
                 referenceAt='FROZEN_FIXED12_COMPLETED_CLOSE')
    else:
        a = dict(fixed, candidateExitReason='UNRESOLVED_FIXED12_FALLBACK')
    for r in (fixed, a):
        if r['status'] == 'CENSORED':
            gap = next((b for b in bars if b['missing']), None)
            r['unknownAt'] = gap['end'] if gap else event['positionStartTimestamp']
            r['capitalMustRemainLocked'] = True
        elif r['status'] == 'EXIT_REFERENCE':
            if not math.isclose(r['netPct'], r['grossPct'] - .05, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError('COST_PARITY_FAILURE')
            if r['exitTimestamp'] < event['positionStartTimestamp']:
                raise ValueError('EXIT_BEFORE_ENTRY')
    return {'fixed12': fixed, 'candidateA': a}


def quantile(xs, p):
    if not xs:
        return None
    a = sorted(xs)
    x = (len(a) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return a[lo] + (a[hi] - a[lo]) * (x - lo)


def distribution(values):
    a = list(values)
    if any(not number(v) for v in a):
        raise ValueError('NONFINITE_METRIC')
    return {'n': len(a), 'mean': statistics.mean(a) if a else None,
            'median': quantile(a, .5), 'p05': quantile(a, .05),
            'worst': min(a) if a else None, 'best': max(a) if a else None}


def performance(results):
    rows = list(results)
    resolved = [r for r in rows if r['status'] == 'EXIT_REFERENCE']
    vals = [r['netPct'] for r in resolved]
    pos = sum(v for v in vals if v > 0)
    neg = -sum(v for v in vals if v < 0)
    return {'population': len(rows), 'resolved': len(vals),
            'statusCounts': dict(sorted(collections.Counter(r['status'] for r in rows).items())),
            'netReturnPct': distribution(vals), 'profitFactor': pos / neg if neg else None,
            'zeroLossDenominator': bool(vals) and neg == 0,
            'winRatePct': 100 * sum(v > 0 for v in vals) / len(vals) if vals else None,
            'holdingClockMinutes': distribution(r['holdingClockMinutes'] for r in resolved),
            'exitReasons': dict(sorted(collections.Counter(
                r.get('candidateExitReason', r.get('reason', r['status'])) for r in rows).items()))}


def preservation(paired, level):
    winners = []
    for row in paired:
        hit = next((b for b in row['path']['future'][:row['fixed12']['exitBar']]
                    if not b['missing'] and b['h'] >= level), None)
        if hit is not None:
            winners.append((row, hit))
    legacy = strict = exit_bar_only = 0
    for row, hit in winners:
        a = row['candidateA']
        legacy += a['exitBar'] >= hit['slot']
        # The old slot >= test credits the HIGH of a bar even after exiting at
        # that bar's OPEN. Preserve that legacy statistic AND disclose strict
        # ownership-time credit separately; never silently rename its meaning.
        held = a['exitBar'] > hit['slot'] or a.get('reason') != 'PROTECT_EXIT'
        if a['exitBar'] == hit['slot'] and a.get('reason') == 'PROTECT_EXIT':
            held = hit['o'] >= level
            exit_bar_only += not held
        strict += held
    n = len(winners)
    return {'winnerDenominator': n, 'legacySlotPreserved': legacy,
            'legacySlotRatePct': 100 * legacy / n if n else None,
            'ownershipTimeCredited': strict,
            'ownershipTimeRatePct': 100 * strict / n if n else None,
            'exitBarHighOnlyNotCredited': exit_bar_only}


def concentration(rows, policy, field):
    resolved = [r for r in rows if r[policy]['status'] == 'EXIT_REFERENCE']
    counts = collections.Counter(r['entry'][field] for r in resolved)
    profit = collections.defaultdict(float)
    for r in resolved:
        profit[r['entry'][field]] += max(0, r[policy]['netPct'])
    total = sum(profit.values())
    ordered = sorted(profit.items(), key=lambda p: (-p[1], str(p[0])))
    return {'resolvedN': len(resolved), 'unique': len(counts),
            'topCount': [{'value': k, 'n': n} for k, n in counts.most_common(5)],
            'positiveUnitNotionalProfitShareTop5': (
                sum(v for _, v in ordered[:5]) / total if total else None),
            'notCapitalWeighted': True}


def summarize(ledgers):
    panels = {}
    for arm, rows in ledgers.items():
        paired = [r for r in rows if all(r[p]['status'] == 'EXIT_REFERENCE' for p in ('fixed12', 'candidateA'))]
        fills = [r for r in rows if r['entry']['entryId'] is not None]
        panel = {'population': len(rows), 'fills': len(fills), 'pairedResolved': len(paired),
                 'candidateOnlyResolved': sum(r['candidateA']['status'] == 'EXIT_REFERENCE'
                    and r['fixed12']['status'] != 'EXIT_REFERENCE' for r in rows),
                 'fixed12AllPopulation': performance(r['fixed12'] for r in rows),
                 'candidateAAllPopulation': performance(r['candidateA'] for r in rows),
                 'pairedFixed12': performance(r['fixed12'] for r in paired),
                 'pairedCandidateA': performance(r['candidateA'] for r in paired),
                 'pairedDeltaCandidateMinusFixedPct': distribution(
                     r['candidateA']['netPct'] - r['fixed12']['netPct'] for r in paired),
                 'plus3Preservation': preservation(paired, 3),
                 'plus5Preservation': preservation(paired, 5),
                 'offGridFills': sum(r['entry']['entryMinute'] % 5 != 0 for r in fills),
                 'initialPartialMinutesNotUsed': distribution(
                     r['path']['initialPartialBucketMinutesNotUsed'] for r in fills),
                 'concentration': {p: {f: concentration(rows, p, f) for f in ('symbol', 'session', 'entryMinute')}
                                   for p in ('fixed12', 'candidateA')}}
        panels[arm] = panel
    left, right = ({r['entry']['opportunity']: r for r in ledgers[a]} for a in ARMS)
    common_filled = [k for k in sorted(left) if left[k]['entry']['entryId'] and right[k]['entry']['entryId']]
    cross = {}
    for policy in ('fixed12', 'candidateA'):
        keys = [k for k in common_filled if left[k][policy]['status'] == right[k][policy]['status'] == 'EXIT_REFERENCE']
        cross[policy] = {'pairedN': len(keys),
                         'immediate': performance(left[k][policy] for k in keys),
                         'allMaterialR1': performance(right[k][policy] for k in keys),
                         'deltaR1MinusImmediatePct': distribution(right[k][policy]['netPct'] - left[k][policy]['netPct'] for k in keys)}
    keys4 = [k for k in common_filled if all(d[k][p]['status'] == 'EXIT_REFERENCE'
              for d in (left, right) for p in ('fixed12', 'candidateA'))]
    indexes = dict(zip(ARMS, (left, right)))
    cross['fourCellCommonResolved'] = {'pairedN': len(keys4),
        'cells': {a: {p: performance(indexes[a][k][p] for k in keys4)
                      for p in ('fixed12', 'candidateA')} for a in ARMS}}
    return {'status': 'DEVELOPMENT_REFERENCE_REPLAY_NOT_FRESH_OOS_OR_EXECUTION',
            'policy': 'NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1',
            'commonOpportunityPopulation': len(left), 'commonFilled': len(common_filled),
            'byEntry': panels, 'crossEntryPaired': cross, 'portfolioMetricsComputed': False,
            'entryWinnerSelected': False, 'safety': SAFETY}


def run(r1_path, outdir, execution_head='LOCAL_UNCOMMITTED'):
    contract = read(CONTRACT)
    if contract['safety'] != SAFETY:
        raise ValueError('SAFETY_CONTRACT_MISMATCH')
    for name, expected in contract['inputPins'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('INPUT_SHA256_MISMATCH:' + name)
    if digest(r1_path) != contract['r1EntryRecordsSHA256']:
        raise ValueError('R1_LEDGER_SHA256_MISMATCH')
    freeze = read(ROOT / FREEZE)
    if freeze['decision']['retain'] != list(ARMS) or not freeze['decision']['noFurtherEntryOptimization']:
        raise ValueError('DUAL_FREEZE_CHANGED')
    raw_records = {ARMS[0]: read(ROOT / IMM), ARMS[1]: read(r1_path)}
    envelopes = {a: [envelope(r) for r in rs] for a, rs in raw_records.items()}
    expected_ids = set(read(ROOT / COHORT)['opportunityIds'])
    for arm, rows in envelopes.items():
        if len(rows) != 2155 or len({r['opportunity'] for r in rows}) != 2155 or {r['opportunity'] for r in rows} != expected_ids:
            raise ValueError('CURRENT_DEVELOPMENT_POPULATION_MISMATCH:' + arm)
    # Read only the already restored, outcome-exposed raw artifact. All further
    # adaptation/evaluation is an exact 2,155-ID whitelist; no other partition.
    selected_raw = read_allowlisted_paths(ROOT / RAW, expected_ids)
    del raw_records
    candidate = load_module(CANDIDATE, 'dual_entry_candidate_a_frozen')
    fixed = load_module(FIXED, 'dual_entry_fixed12_frozen')
    ledgers = {}
    for arm in ARMS:
        rows = []
        for e in sorted(envelopes[arm], key=lambda r: r['opportunity']):
            event = adapt(e, selected_raw[e['opportunity']])
            result = replay_pair(event, candidate, fixed)
            # Bars after the frozen terminal cap are not used, exported or
            # supplied to downstream Capital. expectedBars still binds the cap.
            event['future'] = event['future'][:12]
            rows.append({'entry': e, 'path': event, **result})
        ledgers[arm] = rows
    summary = summarize(ledgers)
    for name, expected in contract['inputPins'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('INPUT_MUTATED_DURING_REPLAY:' + name)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=False)
    write_new(out / 'summary.json', summary)
    write_new(out / 'entry-envelopes.json.gz', envelopes)
    write_new(out / 'exit-ledgers.json.gz', ledgers)
    audit = {'status': 'PASS', 'populationPerEntry': 2155, 'rawPathIdentitiesUsed': len(selected_raw),
             'entryDecisionsRecomputed': 0, 'modelFits': 0, 'modelPredictions': 0,
             'frozenPolicySourceUnchanged': True, 'frozenFixed12SourceUnchanged': True,
             'entryFillTimeOrPriceChanges': 0, 'providerRequests': 0,
             'newProtectedPartitionsOpened': 0, 'rawValuesOutsideWhitelistDeserialized': 0,
             'futureLabelsInEntryEnvelope': 0,
             'unknownPositionsOmitted': 0, 'forwardFill': 0, 'interpolation': 0,
             'auctionSubstitution': 0, 'capitalBackflow': 0, 'safety': SAFETY}
    write_new(out / 'audit.json', audit)
    write_new(out / 'manifest.json', {
        'schemaVersion': 'phase57-dual-entry-exit-integration-v1',
        'executionHead': execution_head, 'dualFreezeCommit': contract['dualFreezeCommit'],
        'adapterContractSHA256': digest(CONTRACT), 'adapterScriptSHA256': digest(__file__),
        'r1EntryRecordsSHA256': digest(r1_path), 'inputPins': contract['inputPins'],
        'outputs': {p: digest(out / p) for p in ('summary.json', 'entry-envelopes.json.gz', 'exit-ledgers.json.gz', 'audit.json')},
        'safety': SAFETY})
    return summary


def no_network(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.bind'):
        raise RuntimeError('OFFLINE_REPLAY_NETWORK_FORBIDDEN')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r1-records', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--execution-head', required=True)
    args = parser.parse_args()
    sys.addaudithook(no_network)
    summary = run(args.r1_records, args.out, args.execution_head)
    print(json.dumps({'status': summary['status'], 'population': summary['commonOpportunityPopulation'],
                      'byEntry': {a: {'fills': r['fills'], 'pairedResolved': r['pairedResolved']}
                                  for a, r in summary['byEntry'].items()}, 'safety': SAFETY}, sort_keys=True))


if __name__ == '__main__':
    main()
