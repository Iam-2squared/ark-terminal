#!/usr/bin/env python3
"""Static predevelopment audit. No model runtime, labels-to-features, or predictions.

Reads pinned metadata and saved artifacts only. The split plan is identity metadata,
not OOF generation. An explicit error survives Python -O (no assert-only guards).
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 'predict/research/phase57-msh-entry-long-v2-predevelopment-contract-v1.json'
EVIDENCE = 'docs/evidence/phase57-msh-entry-long-v2-predevelopment'
FEATURE_ROWS = 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
DATASET = 'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/dataset-contract.json'
FROZEN_SHA = '18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f'
ORDER = ['frozenSelectorRidgeScore', 'directionalMomentum3Pct',
         'directionalPullback6Pct', 'momentum3Missing', 'pullback6Missing']
SAFETY = ['executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
          'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
          'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted']
PRIMARY = {
    'adverseMeanRatioMax': .9, 'adverseES95RatioMax': 1.,
    'preservation3RatioMin': .9, 'preservation5RatioMin': .9,
    'throughputRatioMin': .8, 'portfolioNetPnlDeltaMinJpy': 0.,
    'portfolioRequirePFImprovementOrDDImprovement': True,
    'symbolDisjointMeanD30RatioMax': 1., 'symbolDisjointMacroMeanD30RatioMax': 1.,
    'symbolDisjointNonWorseHashGroupsMin': 3, 'symbolDisjointHashGroupCount': 5,
    'symbolDisjointPreservation3RatioMin': .9,
    'symbolDisjointPreservation5RatioMin': .9,
    'symbolDisjointThroughputRatioMin': .8,
}
GUARDRAILS = {
    'precision1RatioMin': .9, 'precision2RatioMin': .9,
    'portfolioProfitFactorRatioMin': .9, 'portfolioMaxDrawdownRatioMax': 1.1,
    'positiveSymbolHHIRatioMax': 1.1, 'negativeSymbolHHIRatioMax': 1.1,
    'absoluteStrictLabelCoverageGapMax': .05,
}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode()


def read(path):
    return json.loads(path.read_text())


def symbol_group(symbol):
    require(isinstance(symbol, str) and symbol, 'INVALID_SYMBOL_METADATA')
    digest = hashlib.sha256(('PHASE57_MSH_LONG_V2_GROUP_V1|' + symbol).encode()).digest()
    return int.from_bytes(digest, 'big') % 5


def validate_contract(c):
    require(c['status'] == 'MSH_ENTRY_LONG_V2_PREDEVELOPMENT_CONTRACT_FROZEN', 'STATUS')
    require(c['scope'] == 'CONTRACT_ONLY_STOP_BEFORE_TRAINING', 'SCOPE')
    require(c['repository']['mainMergeAllowed'] is False, 'MAIN_MERGE')
    require(c['identity']['selectorFreezeCommit'] == '565d74b3dea823581fdb32380113aac5913a248d', 'SELECTOR_COMMIT')
    require(c['identity']['selectorPayloadSHA'] == '3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59', 'SELECTOR_PAYLOAD')
    require(c['identity']['selectorRidgeSHA'] == '994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb', 'SELECTOR_RIDGE')
    require(c['identity']['v1Threshold'] == 2., 'V1_THRESHOLD')
    require(c['identity']['v1EnterIdentitySHA'] == '72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236', 'V1_277_IDENTITY')
    require(c['identity']['p0Head'] == '13148321d7ef586975ab973a04392e2af73b6503', 'P0_HEAD')
    require(c['architecture']['primaryModelCount'] == 1, 'MODEL_COUNT')
    require(c['architecture']['alternativesActive'] == [], 'ALTERNATIVE_SEARCH')
    for key in ['twoHead', 'wait', 'ensemble', 'symbolModel', 'v1ScoreGateInsideV2']:
        require(c['architecture'][key] is False, 'ARCHITECTURE_' + key)
    t = c['target']
    require(t['primary'] == 'D30_CONTINUOUS_ADVERSE_MAGNITUDE_PCT', 'TARGET')
    require(t['horizonMinutes'] == 30 and t['requiredBars'] == 6 and t['clock'] == 'WALL_CLOCK', 'TARGET_WINDOW')
    require(t['binaryTailTarget'] is False and t['clipping'] is False, 'TARGET_CAPACITY')
    require(t['auctionAllowed'] is False and t['missingExpectedBar'] == 'CENSORED', 'TARGET_CENSORING')
    u = c['universe']
    require((u['candidateCount'], u['decisionCount'], u['sessionCount']) == (3800, 760, 76), 'UNIVERSE')
    require(u['trainingNotRestrictedToV1Enter'] is True and u['fullLiveUniversePITClaim'] is False, 'UNIVERSE_CLAIM')
    require(u['direction'] == 'LONG' and u['cashEquityOnly'] is True, 'CASH_LONG')
    require(c['trainingRows']['unit'] == 'FROZEN_TOP5_SELECTION_EVENT', 'ROW_UNIT')
    require(c['trainingRows']['symbolSpecificOverrides'] is False, 'SYMBOL_WEIGHT_OVERRIDE')
    require(c['trainingRows']['sameSymbolSessionAcrossTrainEval'] is False, 'SYMBOL_SESSION_SPLIT')
    f = c['features']
    require(f['order'] == ORDER and f['effectiveInputCount'] == 5 and f['rawPredictorCount'] == 3, 'INPUT_ORDER')
    require([x['name'] for x in f['definitions']] == ORDER, 'INPUT_DEFINITIONS')
    require(f['activeOptionalFeatures'] == [] and not f['featureInteractions'] and not f['polynomials'], 'FEATURE_ZOO')
    m = c['missing']
    require(m['strategy'] == 'FOLD_LOCAL_FEATURE_ONLY_WEIGHTED_MEDIAN_PLUS_TWO_INDICATORS', 'MISSING_STRATEGY')
    for key in ['missingIsZero', 'forwardFill', 'futureFill', 'nextObservationFill',
                'interpolation', 'outcomeDerivedImputation', 'volumeMissingAsZero']:
        require(m[key] is False, 'MISSING_' + key)
    model = c['model']
    require(model['family'] == 'WEIGHTED_L2_LINEAR_RIDGE_REGRESSION', 'MODEL_FAMILY')
    require(model['lambda'] == 1. and model['solver'] == 'numpy.linalg.solve', 'MODEL_REGULARIZATION')
    require(model['featureCount'] == 5 and model['interceptPenalized'] is False, 'MODEL_DESIGN')
    require(model['runtime'] == {'python': '3.12', 'numpy': '2.3.5', 'scipyRequired': False,
                                 'dtype': 'float64', 'threads': 1}, 'MODEL_RUNTIME')
    sessions = u['sessions']
    require(len(sessions) == 76 and sessions == sorted(set(sessions)), 'SESSION_ORDER')
    seen = []
    for fold, (n, lo, hi) in zip(c['cv']['folds'], [(16,17,31), (31,32,46), (46,47,61), (61,62,76)]):
        require(fold['trainOrdinals'] == [1,n] and fold['evaluationOrdinals'] == [lo,hi], 'OUTER_SPLIT')
        cut = 3 * n // 4
        require(fold['innerFitOrdinals'] == [1,cut] and fold['innerCalibrationOrdinals'] == [cut+1,n], 'INNER_SPLIT')
        require(fold['trainDates'] == sessions[:n] and fold['evaluationDates'] == sessions[lo-1:hi], 'FOLD_DATES')
        require(max(fold['trainDates']) < min(fold['evaluationDates']), 'TEMPORAL_LEAK')
        seen.extend(fold['evaluationDates'])
    require(len(c['cv']['folds']) == 4 and seen == sessions[16:], 'EVALUATION_COVERAGE')
    require(c['cv']['randomSplit'] is False and c['cv']['fitStatisticsFromEvaluation'] is False, 'CV_LEAK')
    require(c['crossSymbol']['groups'] == 5 and c['crossSymbol']['heldGroupOutcomesUsedForThreshold'] is False, 'SYMBOL_LEAK')
    require(c['crossSymbol']['postHocRebalancing'] is False, 'POSTHOC_SYMBOL_SPLIT')
    require(c['state']['outputs'] == ['ENTER', 'SKIP_THIS_DECISION'] and c['state']['wait'] is False, 'STATE')
    require(c['decision']['thresholdCandidatesPct'] == [1.,2.,5.,10.], 'THRESHOLD_GRID')
    require(c['decision']['positionSizingUsesScore'] is False and c['decision']['opportunityRiskProduct'] is False, 'SCORE_MISUSE')
    require(c['numericGates']['primary'] == PRIMARY, 'PRIMARY_GATES')
    require(c['numericGates']['guardrails'] == GUARDRAILS, 'GUARDRAILS')
    require(set(c['numericGates']['applicationScopes']) == {'chronological','symbolDisjoint','innerCalibration'}, 'GATE_SCOPE')
    fair = c['fairComparator']
    require(fair['entryOnlyChange'] is True and fair['primaryOwnAcceptedSets'] is True, 'FAIR_SETS')
    require(fair['exit'] == 'LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1', 'FROZEN_EXIT')
    require(fair['allocation'] == 'EQUAL_MAX3 / V3_0_EQUAL', 'FROZEN_EQUAL')
    require(fair['ledger'] == 'scripts/phase57_long_capital_integration.py::replay', 'FROZEN_LEDGER')
    require((fair['initialCashJpy'], fair['lotSize'], fair['maximumConcurrentPositions'],
             fair['budgetDivisor'], fair['roundTripCostPctOfEntryNotional']) == (1000000,100,10,3,.05), 'FAIR_CASH_COST')
    require(c['dataProtection']['globalBudgetSHA'] == 'b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f', 'BUDGET_SHA')
    require(c['dataProtection']['globalFreshBudgetSessions'] == 195, 'FRESH_BUDGET')
    require(c['dataProtection']['trainingAuthorizedByThisContractFreeze'] is False, 'TRAINING_AUTHORIZATION')
    require(c['dataProtection']['newProviderRequestsAllowed'] is False, 'PROVIDER')
    require(all(type(v) is int and v == 0 for v in c['currentScopeCounters'].values()), 'SCOPE_COUNTERS')
    require(set(c['safety']) == set(SAFETY) and all(c['safety'][k] is False for k in SAFETY), 'SAFETY')
    require(all(c[k] is False for k in ['shortAllowed','marginAllowed','leverageAllowed','promotionAllowed']), 'TRADING')
    require(c['exactNextAction'].startswith('STOP.'), 'STOP_BOUNDARY')


def split_metadata(rows, c):
    """No outcome, feature values, predicted score or accepted set enters this plan."""
    identities = [{k: r[k] for k in ['selectorEventId','symbol','sessionDate','decisionTimestamp']} for r in rows]
    mapping = {s: symbol_group(s) for s in sorted({r['symbol'] for r in identities})}
    groups = [{'group': g, 'symbols': [s for s in mapping if mapping[s] == g],
               'candidateEvents': sum(mapping[r['symbol']] == g for r in identities)} for g in range(5)]
    require(all(g['symbols'] for g in groups), 'EMPTY_SYMBOL_GROUP')
    folds = []
    for f in c['cv']['folds']:
        train = [r for r in identities if r['sessionDate'] in f['trainDates']]
        evaluation = [r for r in identities if r['sessionDate'] in f['evaluationDates']]
        require(not ({(r['symbol'],r['sessionDate']) for r in train} &
                     {(r['symbol'],r['sessionDate']) for r in evaluation}), 'SYMBOL_SESSION_OVERLAP')
        for g in range(5):
            train_symbols = {r['symbol'] for r in train if mapping[r['symbol']] != g}
            eval_symbols = {r['symbol'] for r in evaluation if mapping[r['symbol']] == g}
            require(not (train_symbols & eval_symbols), 'HELD_SYMBOL_LEAK')
        folds.append({'fold': f['fold'], 'trainingCandidateEvents': len(train),
                      'evaluationCandidateEvents': len(evaluation), 'heldSymbolLeakCount': 0})
    return {'purpose': 'IDENTITY_ONLY_SPLIT_PLAN_NOT_OOF', 'contractSHA': FROZEN_SHA,
            'usesOutcomes': False, 'predictionsGenerated': 0, 'uniqueSymbols': len(mapping),
            'groups': groups, 'chronologicalFolds': folds}


def audit(root=ROOT):
    c = read(root / CONTRACT)
    validate_contract(c)
    digest = sha(root / CONTRACT)
    require(digest == FROZEN_SHA == (root / (CONTRACT+'.sha256')).read_text().strip(), 'CONTRACT_HASH')
    for name, expected in c['sourcePins'].items():
        require(sha(root / name) == expected, 'SOURCE_PIN:'+name)
    dataset = read(root / DATASET)
    require(c['universe']['sessions'] == dataset['sessionList'], 'DATASET_DATES')
    with gzip.open(root / FEATURE_ROWS, 'rt') as handle:
        rows = [json.loads(line) for line in handle]
    ids = [r['selectorEventId'] for r in rows]
    require(len(ids) == len(set(ids)) == 3800, 'EVENT_IDENTITIES')
    require(hashlib.sha256(canonical(ids)).hexdigest() == c['universe']['eventIdentitySHA'], 'EVENT_IDENTITY_SHA')
    counts = collections.Counter((r['sessionDate'],r['decisionTimestamp']) for r in rows)
    require(len(counts) == 760 and set(counts.values()) == {5}, 'TOP5_UNIVERSE')
    availability = {'frozenSelectorRidgeScore': sum(isinstance(r['ridgeScore'], (float,int)) for r in rows)}
    for name in ORDER[1:3]:
        availability[name] = sum(r['features'][name]['status'] == 'AVAILABLE' for r in rows)
    require(availability == {d['name']:d['available3800'] for d in c['features']['definitions'][:3]}, 'FEATURE_AVAILABILITY')
    require(sum(bool(r['label']['labelable']) for r in rows) == 1828, 'LABEL_AVAILABILITY_ONLY')
    plan = split_metadata(rows, c)
    # Static contract and lineage audit only: deliberately no target calculations or replay.
    result = {'status': 'STATIC_PREDEVELOPMENT_CONTRACT_AUDIT_PASS', 'contractSHA': digest,
              'sourceHead': c['repository']['sourceHead'], 'sourcePinsVerified': len(c['sourcePins']),
              'frozenSelectorEntryExitAllocationLedgerUnchanged': True,
              'candidateEvents': 3800, 'decisionTimestamps': 760, 'sessions': 76,
              'featureAvailability': availability, 'labelAvailabilityRows': 1828,
              'splitMetadataOnly': True, 'modelRuntimeImported': False,
              'counters': c['currentScopeCounters'], 'safety': c['safety'],
              'verdict': c['status'], 'stop': True}
    return result, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Write static audit receipt and metadata plan only')
    args = parser.parse_args()
    result, plan = audit()
    if args.write:
        for name, value in [('static-audit.json',result), ('split-metadata.json',plan)]:
            (ROOT/EVIDENCE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
