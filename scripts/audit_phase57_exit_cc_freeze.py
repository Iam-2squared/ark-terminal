"""Read-only Candidate C freeze audit. Never modifies A/B/C or upstream logic."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HEAD = '52c2a11b3f38b1f3d1e4146a0e42b18a0748beda'
INITIAL = 'INITIAL_ENTRY_OPPORTUNITY'
DIP = 'DIP_REPRICE_OPPORTUNITY'
BLOB_PINS = {
    'scripts/phase57_new_long_exit_candidate_a.py': '03d403b1b7b390c9cfbe2232d4de55704a0971d6',
    'scripts/phase57_new_long_exit_candidate_b.py': '79a7ce4faa0a6e27725201bbb6fa5a61a8e2ac71',
    'scripts/phase57_new_long_exit_candidate_c.py': 'ccf65e6cbc3a3d2047deb370db657c08f44045d9',
    'docs/evidence/phase57-new-long-exit-candidate-c-contract-2026-09-18.md': '9ca6b789aa215e3a3ed084d1cc201e14c3105b7e',
    'docs/evidence/phase57-new-long-exit-candidate-a-freeze-2026-09-18.md': '09992550dab39e99c24708e73a52adbab47d19e7',
}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blob_digest(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def quantile(values, p):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * p
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def metrics(values):
    losses = -sum(x for x in values if x < 0)
    return {'n': len(values), 'mean': statistics.mean(values) if values else None,
            'PF': sum(x for x in values if x > 0) / losses if losses else None,
            'p05': quantile(values, .05)}


def paired(rows):
    result = {key: metrics([r[key] for r in rows]) for key in ('fixed', 'candidateA', 'candidateC')}
    for key in ('fixed', 'candidateA'):
        result['meanDeltaVs' + key] = statistics.mean([r['candidateC'] - r[key] for r in rows]) if rows else None
    return result


def preserved(row, level, strict=True):
    first = row['first' + str(level)]
    if first is None:
        return None
    result = row['effectiveResult']
    if result['exitBar'] != first:
        return result['exitBar'] > first
    # Fixed12 exits at the completed CLOSE, protection exits at OPEN.
    # The HIGH later in an OPEN-exit bar is not a captured opportunity.
    return not strict or result['status'] == 'FIXED12_FALLBACK' or result['grossPct'] >= level


def preservation(rows, level, strict):
    values = [preserved(r, level, strict) for r in rows if r['first' + str(level)] is not None]
    return {'n': sum(values), 'denominator': len(values), 'rate': sum(values) / len(values) if values else None}


def ordering_findings(bars, result):
    if result['status'] == 'FIXED12_FALLBACK':
        return []
    signal = result['signalBar']
    prefix = [b for b in bars if b['slot'] <= signal and not b.get('missing')]
    level = 2 if result['status'] == 'EARLY_2_TO_0_EXIT' else 3
    armed = next((b['slot'] for b in prefix if b['h'] >= level), None)
    findings = []
    if armed is None or signal <= armed:
        findings.append({'type': 'NOT_LATER_THAN_ARM_BAR', 'level': level, 'armBar': armed, 'signalBar': signal})
    if result['exitBar'] != signal + 1:
        findings.append({'type': 'NOT_NEXT_REGULAR_OPEN', 'signalBar': signal, 'exitBar': result['exitBar']})
    return findings


def synthetic_probes(ca, cb):
    fixed = {'exitBar': 3, 'grossPct': 4., 'netPct': 3.95}
    def bars(high, close):
        return [{'slot': 1, 'missing': False, 'o': 0., 'h': high, 'l': min(0., close), 'c': close},
                {'slot': 2, 'missing': False, 'o': .5, 'h': 4., 'l': .5, 'c': 4.},
                {'slot': 3, 'missing': False, 'o': 4., 'h': 4., 'l': 4., 'c': 4.}]
    out = []
    for level, high, close in ((2, 2.5, -.2), (3, 3.5, .5)):
        sample = bars(high, close)
        result = cb.policy(sample, fixed)
        out.append({'case': 'DIP_FIRST_ARM_' + str(level), 'bars': sample,
                    'actual': result, 'contractRequires': 'NO_EXIT_SIGNAL_ON_FIRST_ARM_BAR',
                    'findings': ordering_findings(sample, result),
                    'candidateAControl': ca.policy(sample, fixed)})
    return out


def build():
    for path, expected in BLOB_PINS.items():
        assert blob_digest(ROOT / path) == expected, ('SOURCE_CHANGED', path)
    ca = module('audit_cc_a', 'scripts/phase57_new_long_exit_candidate_a.py')
    cc = module('audit_cc_c', 'scripts/phase57_new_long_exit_candidate_c.py')
    cb = module('audit_cc_b', 'scripts/phase57_new_long_exit_candidate_b.py')
    cond = module('audit_cc_cond', 'scripts/phase57_new_long_entry_exit_conditional.py')
    for path, expected in cond.PINS.items():
        assert digest(ROOT / path) == expected, ('UPSTREAM_CHANGED', path)
    for path, expected in cond.PARITY_PINS.items():
        assert digest(cond.BASE / 'entry-parity' / path) == expected, ('ENTRY_CHANGED', path)
    ledger_a, _ = ca.build()
    ledger_c, development = cc.build()
    keys_a = [(r['anchorId'], r['cohort']) for r in ledger_a]
    keys_c = [(r['anchorId'], r['cohort']) for r in ledger_c]
    assert keys_a == keys_c and len(set(keys_c)) == len(keys_c)
    amap = dict(zip(keys_a, ledger_a))
    entries = cond.read(cond.BASE / 'entry-parity/ledger.ndjson.gz')
    anchor_digest = hashlib.sha256(('\n'.join(sorted(e['anchorId'] for e in entries)) + '\n').encode()).hexdigest()
    assert anchor_digest == cond.ANCHOR_SHA
    source = cond.read(ROOT / cond.PATHS)
    assert source['providerRequests'] == source['freshAccess'] == source['oosAccess'] == 0
    paths = {e['selectorEventId']: e for e in source['events']}
    meta = {}
    sessions = sorted({e['sessionDate'] for e in entries})
    for entry in entries:
        for name in ('initialEvent', 'secondaryEvent'):
            op = entry['decision'][name]
            if op is not None:
                key = (entry['anchorId'], op['eventType'])
                assert key not in meta
                meta[key] = (entry, op, name)
    rows, ordering, ledger_mismatches, prefix_mismatches = [], [], [], []
    runtime = cond.module('audit_cc_fixed', cond.RUNTIME)
    summary_reproduced = True
    for source_row in ledger_c:
        key = (source_row['anchorId'], source_row['cohort'])
        old_a = amap[key]
        entry, op, name = meta[key]
        position = cond.adapt(op, paths[key[0]])
        fixed = runtime.replay(position, 'FIXED12')
        assert fixed['status'] == 'EXIT_REFERENCE'
        bars = [b for b in position['future'] if b['slot'] <= fixed['exitBar']]
        selected_policy = ca.policy if key[1] == INITIAL else cb.policy
        effective = selected_policy(bars, fixed)
        assert effective == (old_a['result'] if key[1] == INITIAL else source_row['result'])
        assert effective['netPct'] == source_row['candidateCNetPct']
        assert fixed['netPct'] == source_row['fixed'] == old_a['fixed']
        assert source_row['candidateA'] == old_a['result']['netPct']
        fields = ('signalBar', 'exitBar', 'grossPct', 'netPct')
        if any(source_row['result'].get(k) != effective.get(k) for k in fields):
            ledger_mismatches.append({'identity': list(key), 'storedResult': source_row['result'], 'selectedRouteResult': effective})
        for finding in ordering_findings(bars, effective):
            ordering.append({'identity': list(key), **finding})
        if effective['status'] != 'FIXED12_FALLBACK':
            signal_bar = next(b for b in bars if b['slot'] == effective['signalBar'])
            exit_bar = next(b for b in bars if b['slot'] == effective['exitBar'])
            assert exit_bar['start'] >= signal_bar['end']
            assert effective['grossPct'] == exit_bar['o']
            mutated = [dict(b) for b in bars[:effective['exitBar']]]
            mutated[-1].update(h=999., l=-999., c=999.)
            if selected_policy(mutated, fixed) != effective:
                prefix_mismatches.append(list(key))
        tags = []
        ev = entry['evaluator']
        if name == 'secondaryEvent' and ev['primary60'] and ev.get('buyImprovementPct', 0) > 0:
            tags = [f'D30_{d}' for d in (2, 5) if ev['secondaryD30']['downside'] >= d]
        assert tags == source_row['riskTags']
        rows.append({'anchorId': key[0], 'cohort': key[1], 'symbol': entry['symbol'], 'sessionDate': entry['sessionDate'],
                     'block': 1 + sessions.index(entry['sessionDate']) // 19,
                     'fixed': source_row['fixed'], 'candidateA': source_row['candidateA'],
                     'candidateC': source_row['candidateCNetPct'], 'effectiveResult': effective,
                     'first3': source_row['first3'], 'first5': source_row['first5'], 'riskTags': tags})
    report = {'schemaVersion': 1, 'sourceHead': SOURCE_HEAD, 'developmentStatus': development['status'],
              'developmentGates': development['gates'], 'anchorIdentitySHA256': anchor_digest,
              'sessions': sessions, 'cohorts': {}, 'risk': {}, 'safety': development['safety'],
              'scope': {'freshAccess': 0, 'oosAccess': 0, 'providerRequests': 0, 'modelFitPrediction': 0,
                        'selectorChanges': 0, 'entryChanges': 0, 'exitPolicyChanges': 0,
                        'capitalPortfolioTuning': 0, 'mainMerge': 0},
              'syntheticProbes': synthetic_probes(ca, cb)}
    gates = dict(development['gates'])
    for cohort in (INITIAL, DIP):
        rs = [r for r in rows if r['cohort'] == cohort]
        count = collections.Counter(r['symbol'] for r in rs)
        top = count.most_common(3)
        excluded = [r for r in rs if r['symbol'] not in dict(top)]
        blocks = {str(b): paired([r for r in rs if r['block'] == b]) for b in range(1, 5)}
        item = paired(rs)
        item.update(blocks=blocks, top3Frequency=[{'symbol': s, 'n': n} for s, n in top],
                    top3Fraction=sum(n for _, n in top) / len(rs),
                    symbolHHI=sum((n / len(rs)) ** 2 for n in count.values()),
                    excludeTop3=paired(excluded),
                    legacyPreservation={str(k): preservation(rs, k, False) for k in (3, 5)},
                    timeOrderedPreservation={str(k): preservation(rs, k, True) for k in (3, 5)})
        report['cohorts'][cohort] = item
        item['nonnegativeBlocksVsFixed12'] = sum(v['meanDeltaVsfixed'] is not None and v['meanDeltaVsfixed'] >= 0 for v in blocks.values())
        gates[cohort + '_chronological3of4_vsFixed12'] = item['nonnegativeBlocksVsFixed12'] >= 3
        gates[cohort + '_excludeTop3_vsFixed12'] = item['excludeTop3']['meanDeltaVsfixed'] is not None and item['excludeTop3']['meanDeltaVsfixed'] >= 0
        original = development['cohorts'][cohort]
        for key, original_value in [('mean', original['policy']['mean']), ('p05', original['policy']['p05']), ('PF', original['policyPF'])]:
            summary_reproduced &= math.isclose(item['candidateC'][key], original_value, abs_tol=1e-12)
        for k in (3, 5):
            summary_reproduced &= item['legacyPreservation'][str(k)] == original['plus' + str(k)]
            gates[cohort + '_timeOrdered_plus' + str(k)] = item['timeOrderedPreservation'][str(k)]['rate'] >= .9
    for d, n in ((2, 106), (5, 21)):
        rs = [r for r in rows if f'D30_{d}' in r['riskTags']]
        assert len(rs) == n and all(r['cohort'] == DIP for r in rs)
        report['risk'][str(d)] = {**paired(rs), 'identitySHA256': hashlib.sha256(encoded(sorted(r['anchorId'] for r in rs))).hexdigest()}
        gates['risk' + str(d) + '_independent'] = report['risk'][str(d)]['meanDeltaVscandidateA'] >= 0
    report['integrity'] = {'identityN': len(rows), 'sourcePinsVerified': True,
        'laterBarViolationsN': len(ordering), 'laterBarViolationsByLevel': dict(collections.Counter(x['level'] for x in ordering if 'level' in x)),
        'initialStoredResultMismatchN': len(ledger_mismatches),
        'fillBarFuturePerturbationMismatchN': len(prefix_mismatches),
        'summaryReproduced': summary_reproduced,
        'laterBarExamples': ordering[:8], 'ledgerMismatchExamples': ledger_mismatches[:3]}
    gates.update(sourceIdentity=True, sourcePins=True, summaryReproduced=bool(summary_reproduced),
                 contractLaterBarOrder=not ordering and all(not x['findings'] for x in report['syntheticProbes']),
                 exactRoutedLedger=not ledger_mismatches, causalFillPrefix=not prefix_mismatches,
                 safety=all(v is False for v in development['safety'].values()))
    report['gates'] = gates
    report['failedGates'] = [k for k, value in gates.items() if not value]
    passed = all(gates.values())
    report['robustnessVerdict'] = 'PASS' if passed else 'FAIL'
    report['status'] = 'NEW_LONG_EXIT_CANDIDATE_C_DEVELOPMENT_FREEZE_READY' if passed else 'NEW_LONG_EXIT_CANDIDATE_C_KILL'
    report['freezeAllowed'] = passed
    report['candidateAFallback'] = 'EXISTING_FREEZE_ARTIFACT_PRESERVED_NOT_REVALIDATED_OR_PROMOTED'
    report['limitations'] = ['Development only; no standalone or portfolio profitability claim.',
        'Legacy preservation is retained, not silently rewritten; time-ordered audit distinguishes OPEN vs CLOSE exits.',
        'An audit PASS would only permit a separate explicit freeze attestation; no automatic promotion.',
        'No retune, repaired policy, Candidate D/E, or Fresh/OOS evaluation is authorized.']
    inputs = set(BLOB_PINS) | set(cond.PINS)
    inputs.update(str((cond.BASE / 'entry-parity' / p).relative_to(ROOT)) for p in cond.PARITY_PINS)
    inputs.update(['scripts/phase57_new_long_entry_exit_conditional.py',
                   str(Path(__file__).relative_to(ROOT)),
                   'docs/evidence/phase57-exit-cc-freeze-audit-method-2026-09-18.md'])
    report['inputSHA256'] = {p: digest(ROOT / p) for p in sorted(inputs)}
    details = {'rows': rows, 'orderingFindings': ordering, 'storedLedgerMismatches': ledger_mismatches,
               'prefixMismatches': prefix_mismatches}
    return details, report


def run(outdir):
    details, report = build()
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=False)
    (outdir / 'summary.json').write_bytes(encoded(report))
    (outdir / 'ledger.audit.json.gz').write_bytes(gzip.compress(encoded(details), mtime=0))
    manifest = {'schemaVersion': 1, 'sourceHead': SOURCE_HEAD, 'status': report['status'],
                'inputSHA256': report['inputSHA256'],
                'outputSHA256': {p: digest(outdir / p) for p in ('summary.json', 'ledger.audit.json.gz')}}
    (outdir / 'manifest.json').write_bytes(encoded(manifest))
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    run(args.out)
