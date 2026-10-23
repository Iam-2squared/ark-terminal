"""Supplemental R43 report over an independently audited R41 artifact.

This module never fits a model, replays a policy, modifies a frozen scorecard or
changes a gate. Formal selection remains the output of R41 scoring. Supplemental
paired metrics require BOTH resolved executions and BOTH finite metric values;
ratio-of-sums diagnostics have explicitly matched, positive-headroom populations.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ARMS = ('IMMEDIATE', 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF')
BUCKETS = ('<1%', '1-2%', '2-3%', '3-4%', '4-5%', '>=5%', 'NOT_EVALUABLE')
COSTS = ('0.05', '0.10', '0.20')
SAFETY = dict.fromkeys(('executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
    'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
    'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted'), False)
METRICS = {
    'netReturnPct': ('netReturnPctBySellCost', '0.05'),
    'grossEntryToExitPct': ('metrics', 'entryToExitGrossPct'),
    'wholeOpportunityCapturePct': ('metrics', 'wholeOpportunityCapturePct'),
    'sameHighUpsideCapturePct': ('metrics', 'sameHighUpsideCapturePct'),
    'postEntryUpsideCapturePct': ('metrics', 'postEntryUpsideCapturePct'),
    'sameHighEvaluatorGapPp': ('metrics', 'sameHighEvaluatorGapPp'),
    'postEntryHighEvaluatorGapPp': ('metrics', 'postEntryHighEvaluatorGapPp'),
    'ownedPeakGivebackPp': ('metrics', 'ownedPeakGivebackPp'),
    'earlyExitOpportunityCostPp': ('earlyExitOpportunityCostPp',),
    'activeMinutesHeld': ('activeMinutesHeld',),
    'wallMinutesHeld': ('wallMinutesHeld',),
    'entryToPostEntryHighPct': ('metrics', 'entryToPostEntryHighPct'),
    'entryToSameOrderedHighPct': ('metrics', 'entryToSameOrderedHighPct'),
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def finite(value):
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)) and math.isfinite(value)


def scalar_json(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False, default=scalar_json) + '\n').encode()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def read_rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def write_json(path, value):
    require(not path.exists(), 'APPEND_ONLY_OUTPUT_EXISTS')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def flatten(value, prefix=''):
    out = {}
    for key, item in value.items():
        name = prefix + str(key)
        if isinstance(item, dict):
            out.update(flatten(item, name + '.'))
        elif isinstance(item, (list, tuple)):
            out[name] = json.dumps(item, separators=(',', ':'), ensure_ascii=False)
        else:
            out[name] = item
    return out


def write_csv(path, records):
    require(not path.exists(), 'APPEND_ONLY_OUTPUT_EXISTS')
    records = [flatten(record) for record in records]
    fields = sorted({field for record in records for field in record})
    with path.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def bucket(row):
    value = row['metrics'].get('bucket')
    return value if value in BUCKETS[:-1] else 'NOT_EVALUABLE'


def metric(row, name):
    value = row
    for key in METRICS[name]:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def stats(values):
    values = np.asarray([float(v) for v in values if finite(v)], dtype=np.float64)
    if not len(values):
        return dict(n=0, mean=None, median=None, p05=None, p10=None, worst=None)
    return dict(n=int(len(values)), mean=float(values.mean()), median=float(np.median(values)),
                p05=float(np.percentile(values, 5)), p10=float(np.percentile(values, 10)), worst=float(values.min()))


def return_stats(values):
    values = [float(v) for v in values if finite(v)]
    positive = [v for v in values if v > 0]
    negative = [v for v in values if v < 0]
    return {**stats(values), 'profitFactor': sum(positive) / -sum(negative) if negative else None,
            'winRate': len(positive) / len(values) if values else None,
            'averageWin': sum(positive) / len(positive) if positive else None,
            'averageLoss': sum(negative) / len(negative) if negative else None,
            'winningN': len(positive), 'losingN': len(negative),
            'zeroReturnN': len(values) - len(positive) - len(negative)}


def concentration(rows):
    positive = [(row, metric(row, 'netReturnPct')) for row in rows
                if row['exitStatus'] == 'RESOLVED' and finite(metric(row, 'netReturnPct'))
                and metric(row, 'netReturnPct') > 0]
    total = sum(value for _, value in positive)
    result = {'positiveNetContributionN': len(positive), 'positiveNetSumPct': total,
              'largestTradeShare': None, 'topFiveTradeShare': None,
              'largestSessionShare': None, 'largestSymbolShare': None,
              'interpretation': 'UNWEIGHTED_POSITIVE_TRADE_RETURN_CONTRIBUTION_NOT_CAPITAL_CONCENTRATION'}
    if total:
        values = sorted((value for _, value in positive), reverse=True)
        sessions, symbols = collections.Counter(), collections.Counter()
        for row, value in positive:
            sessions[row['session']] += value
            symbols[row['opportunity'].split('|')[1]] += value
        result.update(largestTradeShare=values[0] / total, topFiveTradeShare=sum(values[:5]) / total,
                      largestSessionShare=max(sessions.values()) / total,
                      largestSymbolShare=max(symbols.values()) / total)
    return result


def group_report(rows, population=None):
    resolved = [r for r in rows if r['exitStatus'] == 'RESOLVED']
    population_n = None if population is None else population['populationN']
    result = {'populationN': population_n, 'filledN': len(rows),
              'noEntryN': None if population_n is None else population_n - len(rows),
              'resolvedN': len(resolved), 'censoredN': len(rows) - len(resolved),
              'missingReferenceCaseN': sum(r['missingOrdinaryReferences'] > 0 for r in rows),
              'missingReferenceAttemptN': sum(r['missingOrdinaryReferences'] for r in rows),
              'exitReasons': dict(sorted(collections.Counter(r['exitKind'] or 'UNRESOLVED_TERMINAL' for r in rows).items())),
              'returnRisk': return_stats(metric(r, 'netReturnPct') for r in resolved),
              'costStress': {cost: return_stats(r['netReturnPctBySellCost'][cost] for r in resolved) for cost in COSTS},
              'metrics': {}, 'metricEligibility': {}, 'concentration': concentration(rows)}
    for name in METRICS:
        valid = [r for r in resolved if finite(metric(r, name))]
        result['metrics'][name] = stats(metric(r, name) for r in valid)
        result['metricEligibility'][name] = {'eligibleN': len(valid), 'resolvedN': len(resolved),
            'resolvedMetricMissingN': len(resolved) - len(valid), 'censoredExcludedN': len(rows) - len(resolved),
            'filledN': len(rows), 'rule': 'RESOLVED_EXECUTION_AND_FINITE_METRIC'}
    return result


def unique_rows(rows):
    mapped = {r['opportunity']: r for r in rows}
    require(len(mapped) == len(rows), 'DUPLICATE_OPPORTUNITY_IN_PAIR_SIDE')
    return mapped


def id_hash(ids):
    return hashlib.sha256(canonical(ids)).hexdigest()


def strict_pairs(left, right):
    left, right = unique_rows(left), unique_rows(right)
    common = sorted(set(left) & set(right))
    resolved = [key for key in common if left[key]['exitStatus'] == right[key]['exitStatus'] == 'RESOLVED']
    pairs = {'commonIdN': len(common), 'bothResolvedN': len(resolved),
             'leftOnlyIdN': len(set(left) - set(right)), 'rightOnlyIdN': len(set(right) - set(left)),
             'censoredExcludedN': len(common) - len(resolved), 'metrics': {}}
    for name in METRICS:
        ids = [key for key in resolved if finite(metric(left[key], name)) and finite(metric(right[key], name))]
        pairs['metrics'][name] = {'eligibleN': len(ids), 'bothResolvedN': len(resolved),
            'metricMissingOnEitherSideN': len(resolved) - len(ids), 'matchedIdSha256': id_hash(ids),
            'left': stats(metric(left[key], name) for key in ids),
            'right': stats(metric(right[key], name) for key in ids),
            'deltaLeftMinusRight': stats(metric(left[key], name) - metric(right[key], name) for key in ids)}
    return pairs


def ratio_of_sums(rows, denominator='entryToPostEntryHighPct', *, matched_ids=None):
    require(denominator in ('entryToPostEntryHighPct', 'entryToSameOrderedHighPct'), 'UNKNOWN_HEADROOM')
    mapped = unique_rows(rows)
    selected = sorted(mapped) if matched_ids is None else sorted(matched_ids)
    valid = [key for key in selected if key in mapped and mapped[key]['exitStatus'] == 'RESOLVED'
             and finite(metric(mapped[key], 'grossEntryToExitPct'))
             and finite(metric(mapped[key], denominator)) and metric(mapped[key], denominator) > 0]
    numerator = sum(metric(mapped[key], 'grossEntryToExitPct') for key in valid)
    headroom = sum(metric(mapped[key], denominator) for key in valid)
    return {'eligibleN': len(valid), 'consideredN': len(selected), 'excludedN': len(selected) - len(valid),
            'matchedIds': valid, 'matchedIdSha256': id_hash(valid),
            'grossMoveSumPct': numerator, 'positiveHeadroomSumPct': headroom,
            'ratioOfSumsCapturePct': 100 * numerator / headroom if headroom > 0 else None,
            'denominatorMetric': denominator, 'diagnosticOnly': True, 'usedByFormalGate': False,
            'definition': '100*SUM_GROSS_ENTRY_EXIT_PCT/SUM_POSITIVE_HEADROOM_PCT_ON_IDENTICAL_IDS; NOT_MEAN_OF_INDIVIDUAL_RATIOS'}


def paired_ratio_of_sums(left, right, denominator='entryToPostEntryHighPct'):
    lm, rm = unique_rows(left), unique_rows(right)
    ids = sorted(key for key in set(lm) & set(rm)
                 if all(row['exitStatus'] == 'RESOLVED' and finite(metric(row, 'grossEntryToExitPct'))
                        and finite(metric(row, denominator)) and metric(row, denominator) > 0
                        for row in (lm[key], rm[key])))
    return {'left': ratio_of_sums(left, denominator, matched_ids=ids),
            'right': ratio_of_sums(right, denominator, matched_ids=ids),
            'bothResolvedPositiveHeadroomMatchedIdN': len(ids), 'diagnosticOnly': True}


def classification_scores(root, ledgers, configs, source_hashes):
    """Identity join only. Does not invoke the runtime action mapper or labels."""
    receipt = read_json(root / 'receipt.json')
    source_hashes[str(root / 'receipt.json')] = sha(root / 'receipt.json')
    prediction_path = root / 'oof-predictions.npz'
    require(sha(prediction_path) == receipt['predictionSha256'], 'PREDICTION_SHA_DRIFT')
    source_hashes[str(prediction_path)] = receipt['predictionSha256']
    data_receipt = read_json(root / 'data/data-receipt.json')
    source_hashes[str(root / 'data/data-receipt.json')] = sha(root / 'data/data-receipt.json')
    identity_path = root / 'data/source-row-identity.jsonl.gz'
    require(sha(identity_path) == data_receipt['outputHashes'][identity_path.name], 'IDENTITY_SHA_DRIFT')
    source_hashes[str(identity_path)] = data_receipt['outputHashes'][identity_path.name]
    requested = {(r['entryArm'], r['entryId'], r['decisionNow']) for rows in ledgers.values()
                 for r in rows if bucket(r) == '>=5%' and r['exitKind'] == 'MODEL_EXIT'}
    index = {}
    count = 0
    with gzip.open(identity_path, 'rt', encoding='utf-8') as stream:
        for i, line in enumerate(stream):
            row = json.loads(line)
            require(row['index'] == i, 'IDENTITY_INDEX_NOT_SEQUENTIAL')
            key = (row['arm'], row['entryId'], row['now'])
            if key in requested:
                require(key not in index, 'DUPLICATE_REQUESTED_IDENTITY')
                index[key] = i
            count += 1
    require(count == data_receipt['rows'] and set(index) == requested, 'MODEL_EXIT_IDENTITY_JOIN_INCOMPLETE')
    with np.load(prediction_path) as saved:
        predictions = {spec: saved[spec] for spec in sorted({c['predictionSpec'] for c in configs})}
    require(all(values.shape == (count, 2) for values in predictions.values()), 'C_F_PREDICTION_SHAPE')
    reports = []
    for config in configs:
        for arm in ARMS:
            rows = [r for r in ledgers[config['candidateId']] if r['entryArm'] == arm
                    and bucket(r) == '>=5%' and r['exitKind'] == 'MODEL_EXIT']
            pairs = [predictions[config['predictionSpec']][index[(arm, r['entryId'], r['decisionNow'])]] for r in rows]
            reports.append({'candidateId': config['candidateId'], 'entryArm': arm,
                'subset': 'GE5_MODEL_EXIT_ONLY', 'n': len(rows),
                'continuationScore': stats(float(pair[0]) for pair in pairs),
                'failureScore': stats(float(pair[1]) for pair in pairs),
                'finiteBothN': sum(bool(np.isfinite(pair).all()) for pair in pairs),
                'classificationScoresNotCalibratedProbabilities': True,
                'identitySourceSha256': source_hashes[str(identity_path)],
                'predictionSourceSha256': source_hashes[str(prediction_path)]})
    return reports


def build_report(gen2_root, audit, score_root, out):
    """Return receipt; all artifact access follows the independently supplied PASS."""
    from scripts.phase57_exit_gen2_runtime_r41 import PROTOCOL_SHA256, load_protocol
    # Must fail before reading any artifact or even creating the output folder.
    require(audit.get('status') == 'GEN2_ARTIFACT_AUDIT_PASS'
            and audit.get('protocolSha256') == PROTOCOL_SHA256,
            'INDEPENDENT_ARTIFACT_AUDIT_PASS_REQUIRED')
    gen2_root, score_root, out = Path(gen2_root), Path(score_root), Path(out)
    require(not out.exists(), 'APPEND_ONLY_OUTPUT_EXISTS')
    protocol = load_protocol()
    configs = protocol['candidates']
    require(len(configs) == 16, 'EXACTLY_16_CONFIGURATIONS_REQUIRED')
    score_receipt = read_json(score_root / 'receipt.json')
    require(score_receipt['protocolSha256'] == PROTOCOL_SHA256
            and score_receipt['scorecardRunABByteIdentical'] is True,
            'FROZEN_SCORECARD_IDENTITY_REQUIRED')
    source_hashes = {}
    for name, expected in score_receipt['scoreHashes'].items():
        for run in ('run-a', 'run-b'):
            path = score_root / run / name
            require(sha(path) == expected, 'FROZEN_SCORECARD_HASH_DRIFT')
            source_hashes[str(path)] = expected
    for name in ('receipt.json',):
        source_hashes[str(score_root / name)] = sha(score_root / name)
    for config in configs:
        for run in ('run-a', 'run-b'):
            name = run + '/' + config['candidateId'] + '.jsonl.gz'
            path = gen2_root / name
            require(audit['inputLedgerHashes'].get(name) == sha(path), 'AUDITED_LEDGER_HASH_DRIFT')
            source_hashes[str(path)] = sha(path)
    for run in ('run-a', 'run-b'):
        name = run + '/HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz'
        require(audit['inputLedgerHashes'].get(name) == sha(gen2_root / name), 'AUDITED_HOLD_HASH_DRIFT')
        source_hashes[str(gen2_root / name)] = sha(gen2_root / name)
    selection = read_json(score_root / 'run-a/selection.json')
    require(selection['selection'] == score_receipt['selection'], 'FORMAL_SELECTION_DRIFT')
    require({c['candidateId'] for c in selection['candidates']} == {c['candidateId'] for c in configs}, 'FROZEN_CANDIDATE_SET_DRIFT')
    gates = {c['candidateId']: c['gate'] for c in selection['candidates']}
    neutral = read_rows(gen2_root / 'run-a/HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz')
    ledgers = {c['candidateId']: read_rows(gen2_root / 'run-a' / (c['candidateId'] + '.jsonl.gz')) for c in configs}
    overall, buckets, paired, ratios, negative = [], [], [], [], []
    for config in configs:
        cid = config['candidateId']; rows = ledgers[cid]
        require(all(r['candidateId'] == cid for r in rows), 'LEDGER_CANDIDATE_ID_DRIFT')
        card = read_json(score_root / 'run-a/scorecards' / (cid + '.json'))
        for arm in ARMS:
            own = [r for r in rows if r['entryArm'] == arm]
            other = [r for r in neutral if r['entryArm'] == arm]
            require(len(own) == card['overall'][arm]['filledN'], 'FORMAL_POPULATION_DRIFT')
            overall.append({'candidateId': cid, 'entryArm': arm, 'configuration': config,
                **group_report(own, card['overall'][arm]), 'formalGate': gates[cid]['arms'][arm]})
            losing = [r for r in own if finite(metric(r, 'netReturnPct')) and metric(r, 'netReturnPct') < 0]
            negative.append({'candidateId': cid, 'entryArm': arm, 'subset': 'REALIZED_NEGATIVE_RETURN_EVALUATOR_ONLY', **group_report(losing)})
            require(sum(sum(bucket(r) == b for r in own) for b in BUCKETS) == len(own), 'BUCKET_COUNTS_DO_NOT_SUM')
            for b in BUCKETS:
                subset = [r for r in own if bucket(r) == b]
                buckets.append({'candidateId': cid, 'entryArm': arm, 'bucket': b,
                                **group_report(subset, card['byBucket'][arm][b])})
            for b in ('ALL',) + BUCKETS:
                left = own if b == 'ALL' else [r for r in own if bucket(r) == b]
                right = other if b == 'ALL' else [r for r in other if bucket(r) == b]
                paired.append({'candidateId': cid, 'entryArm': arm, 'bucket': b,
                    'comparison': 'CANDIDATE_MINUS_HOLD_TERMINAL_DIAGNOSTIC', 'notFormalGateRecalculation': True,
                    **strict_pairs(left, right)})
                for denominator in ('entryToPostEntryHighPct', 'entryToSameOrderedHighPct'):
                    ratios.append({'candidateId': cid, 'entryArm': arm, 'bucket': b,
                        'comparison': 'CANDIDATE_VS_HOLD_TERMINAL_DIAGNOSTIC',
                        'denominatorMetric': denominator,
                        **paired_ratio_of_sums(left, right, denominator)})
        for b in ('ALL',) + BUCKETS:
            left = [r for r in rows if r['entryArm'] == ARMS[1] and (b == 'ALL' or bucket(r) == b)]
            right = [r for r in rows if r['entryArm'] == ARMS[0] and (b == 'ALL' or bucket(r) == b)]
            paired.append({'candidateId': cid, 'entryArm': 'R1_VS_IMMEDIATE', 'bucket': b,
                'comparison': 'R1_MINUS_IMMEDIATE', 'notFormalGateRecalculation': True, **strict_pairs(left, right)})
            for denominator in ('entryToPostEntryHighPct', 'entryToSameOrderedHighPct'):
                ratios.append({'candidateId': cid, 'entryArm': 'R1_VS_IMMEDIATE', 'bucket': b,
                    'comparison': 'R1_VS_IMMEDIATE', 'denominatorMetric': denominator,
                    **paired_ratio_of_sums(left, right, denominator)})
    cf_scores = classification_scores(gen2_root, ledgers, configs, source_hashes)
    eligibility = [{**{k: row[k] for k in ('candidateId', 'entryArm')}, 'bucket': row.get('bucket', 'ALL'),
                    'metric': name, **values} for row in overall + buckets for name, values in row['metricEligibility'].items()]
    paired_flat = [{**{k: row[k] for k in ('candidateId', 'entryArm', 'bucket', 'comparison')},
                    'commonIdN': row['commonIdN'], 'bothResolvedN': row['bothResolvedN'],
                    'censoredExcludedN': row['censoredExcludedN'], 'metric': name, **values}
                   for row in paired for name, values in row['metrics'].items()]
    require(len(overall) == 32 and len(buckets) == 224, 'REPORT_DIMENSIONS')
    require(all(sha(Path(path)) == expected for path, expected in source_hashes.items()), 'SOURCE_CHANGED_DURING_REPORT')
    out.mkdir(parents=True)
    tables = {'overall': overall, 'buckets': buckets, 'strict-paired': paired_flat,
              'metric-eligibility': eligibility, 'ratio-of-sums-diagnostic': ratios,
              'negative-return-subset': negative, 'winner-model-exit-cf-scores': cf_scores}
    for name, records in tables.items():
        write_json(out / (name + '.json'), records)
        write_csv(out / (name + '.csv'), records)
    write_json(out / 'strict-paired-detail.json', paired)
    write_json(out / 'formal-selection-unchanged.json', selection['selection'])
    receipt = {'schema': 'phase57-gen2-supplemental-report-r43-v1',
        'protocolSha256': PROTOCOL_SHA256, 'auditSha256': hashlib.sha256(canonical(audit)).hexdigest(),
        'sourceScriptSha256': sha(Path(__file__)), 'sourceHashes': source_hashes,
        'candidateCount': 16, 'overallRows': 32, 'bucketRows': 224,
        'formalSelectionUnchanged': selection['selection'], 'frozenScorecardsAndGatesUnmodified': True,
        'strictPairedRule': 'BOTH_RESOLVED_AND_BOTH_FINITE_PER_METRIC; NO_UNRESOLVED_HOLDING',
        'ratioOfSumsUsedByFormalGate': False, 'modelFitsPerformed': 0, 'policyReplaysPerformed': 0,
        'newCandidates': 0, 'capitalPortfolioReplays': 0, 'providerRequests': 0,
        'protectedPartitionsOpened': 0, 'safety': SAFETY,
        'limitations': ['Supplemental metric populations can differ from frozen scorecards because resolved execution is required.',
            'Mean and median captures remain separate from positive-headroom ratio-of-sums diagnostics.',
            'Concentration describes positive unweighted return contribution, not portfolio capital allocation.',
            'C/F outputs are classification scores, not independently calibrated probabilities.']}
    write_json(out / 'receipt.json', receipt)
    write_json(out / 'hashes.json', {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen2-root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--score-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = build_report(args.gen2_root, read_json(args.audit), args.score_root, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != 'sourceHashes'}, sort_keys=True))
