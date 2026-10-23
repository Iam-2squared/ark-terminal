"""Outcome-blind Capital v3 geometry from the pinned v2 control ledger.

Only structural sizing events and aggregate label support are read. Neither
candidate predictions nor which entries won are available to this module.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/phase57-comprehensive-exit-v1'
SOURCE = EVIDENCE / 'CAPITAL_RANK_V2_RESULT'
ARMS = {'IM': 'IMMEDIATE', 'R1': 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geometry():
    pre = EVIDENCE / 'CAPITAL_V3_PREGEOMETRY_PRECOMMIT.json'
    spec = json.loads(pre.read_text())
    assert spec['status'] == 'FROZEN_BEFORE_V3_GEOMETRY_AND_FUNDED_PERFORMANCE'
    assert not any(spec['safety'].values())
    prior = json.loads((SOURCE / 'report.json').read_text())
    folds = json.loads((EVIDENCE / 'CAPITAL_RANK_V2_PRECOMMIT.json').read_text())['split']['folds']
    out = {'schema': 'phase57-capital-v3-outcome-blind-geometry-v1',
           'precommitSha256': sha(pre), 'priorControlReportSha256': sha(SOURCE / 'report.json'),
           'controlLedgerSha256': {}, 'arms': {}, 'protectedOpened': 0,
           'newPredictionsInspected': 0, 'newFundedPerformanceInspected': 0,
           'providerRequests': 0, 'safety': spec['safety']}
    for short, arm in ARMS.items():
        p = SOURCE / (short + '_MAX3') / 'ledger.json.gz'
        ledger = json.loads(gzip.decompress(p.read_bytes()))
        assert ledger['capacity'] == 3 and ledger['arm'] == arm
        out['controlLedgerSha256'][short] = sha(p)
        event_rows, fold_rows = [], collections.defaultdict(list)
        for event in ledger['events']:
            s = event['sizing']
            if not s:
                continue
            sized = sum(x['status'] == 'SIZED' for x in s)
            rejects = collections.Counter(x.get('reason') for x in s if x['status'] == 'REJECTED')
            row = {'session': event['session'], 'timestamp': event['session'] + '|' + str(event['minute']),
                   'candidates': len(s), 'funded': sized,
                   'slotsFull': rejects['MAX_CONCURRENT_SYMBOLS'] > 0,
                   'cashOrSlotBudgetBinding': rejects['NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH'] > 0,
                   'unresolvedMark': rejects['MISSING_FRESH_MARK_UNRESOLVED_SIZING'] > 0,
                   'trueRankingContest': sized > 0 and
                       (rejects['MAX_CONCURRENT_SYMBOLS'] > 0 or
                        rejects['NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH'] > 0),
                   'sameTimeCompetition': len(s) > 1}
            event_rows.append(row)
            for fold in folds:
                if row['session'] in fold['testSessions']:
                    fold_rows[fold['id']].append(row)
        total = sum(x['candidates'] for x in event_rows)
        funded = sum(x['funded'] for x in event_rows)
        support = prior['result']['control'][arm]
        known, n = support['totalKnown'], support['totalCandidates']
        positive = round(known * support['baselineHitRate'])
        assert total == n and funded == len(ledger['funded'])
        assert math.isclose(positive / known, support['baselineHitRate'])
        # The upper bound assumes all funded rows have known labels and a
        # perfect ranking; it is deliberately optimistic and not a result.
        ceiling_rate = min(positive, funded) / funded if funded else None
        out['arms'][short] = {
            'candidateEvents': len(event_rows), 'candidates': total, 'fundedControl': funded,
            'fundedShareControl': funded / total, 'competitionEvents': sum(x['sameTimeCompetition'] for x in event_rows),
            'slotsFullEvents': sum(x['slotsFull'] for x in event_rows),
            'cashOrSlotBudgetBindingEvents': sum(x['cashOrSlotBudgetBinding'] for x in event_rows),
            'unresolvedMarkEvents': sum(x['unresolvedMark'] for x in event_rows),
            'trueRankingContestEvents': sum(x['trueRankingContest'] for x in event_rows),
            'trueRankingContestCandidates': sum(x['candidates'] for x in event_rows if x['trueRankingContest']),
            'folds': [{'id': f['id'], 'candidateEvents': len(fold_rows[f['id']]),
                       'trueRankingContestEvents': sum(x['trueRankingContest'] for x in fold_rows[f['id']]),
                       'fundedControl': sum(x['funded'] for x in fold_rows[f['id']])} for f in folds],
            'aggregatePriorKnownSupport': known, 'aggregatePriorCensored': n-known,
            'aggregatePriorPositiveSupport': positive, 'baselineHitRatePrior': support['baselineHitRate'],
            'optimisticMaxHitRateAtControlFundedCount': ceiling_rate,
            'optimisticMaxEnrichmentAtControlFundedCount': ceiling_rate / support['baselineHitRate'],
            'optimisticMaxReachAtControlFundedCount': min(positive, funded) / positive,
            'denominatorInterpretation': 'funded hit denominator excludes censored; reach denominator all known positive Entry candidates',
        }
    return out


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    Path(args.out).write_text(json.dumps(geometry(), sort_keys=True, indent=2) + '\n')
