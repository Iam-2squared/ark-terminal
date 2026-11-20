#!/usr/bin/env python3
"""Contract-only metadata audit: never imports a model or computes a risk score."""
import argparse
import collections
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 'predict/research/phase57-msh-entry-long-v2-1-predevelopment-contract-v1.json'
EVIDENCE = 'docs/evidence/phase57-msh-entry-long-v2-1-predevelopment'
FEATURES = 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
PREDICTIONS = 'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/frozen-predictions.ndjson.gz'
LABELS = 'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz'
FROZEN_SHA = '82c17234b482118919b092df4af56c0e6a60d792de5ce3a551a509bcc3d293c7'
ORDER = ['directionalMomentum3Pct', 'directionalPullback6Pct', 'momentum3Missing', 'pullback6Missing']
SAFETY = ['executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
          'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
          'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted']
PRIMARY = {'precision1RatioMin': .9, 'precision2RatioMin': .9,
           'winnerRetention3Min': .9, 'winnerRetention5Min': .9,
           'adverseMeanRatioMax': .9, 'adverseES95RatioMax': 1., 'throughputRatioMin': .8}
GUARDRAILS = {'absoluteStrictLabelCoverageGapMax': .05, 'entrySymbolHHIRatioMax': 1.1,
              'chronologicalNonWorseFoldsMin': 3, 'chronologicalFoldCount': 4,
              'directRiskRejectedMinusAcceptedMeanD30Min': 0.}
CROSS = {'pooledMeanD30RatioMax': 1., 'macroSymbolMeanD30RatioMax': 1.,
         'nonWorseGroupsMin': 3, 'groups': 5, 'precision1RatioMin': .9,
         'precision2RatioMin': .9, 'winnerRetention3Min': .9, 'winnerRetention5Min': .9,
         'throughputRatioMin': .8, 'absoluteStrictLabelCoverageGapMax': .05}
IDENTITIES = {
    'selectorFreezeCommit':'565d74b3dea823581fdb32380113aac5913a248d',
    'selectorPayloadSHA':'3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59',
    'selectorRidgeSHA':'994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb',
    'v1ModelSHA':'b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e',
    'v1ScalerSHA':'1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b',
    'v1EnterIdentitySHA':'72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236',
    'v2ContractSHA':'18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f',
    'v2DevelopmentEvidenceSHA':'35cec58faedcebfd09190ed5c404e2e874647eca90b92e12bc9021ff80385a75',
    'rootCauseEvidenceSHA':'5e6f10fb978b06efb0bfdc842570c75d6a277c1515ee3b5ffca1e02e170dbe71',
    'globalBudgetSHA':'b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f'}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def symbol_group(symbol):
    return int.from_bytes(hashlib.sha256(('PHASE57_MSH_LONG_V2_GROUP_V1|' + symbol).encode()).digest(), 'big') % 5


def validate_contract(c):
    require(c['status'] == 'MSH_ENTRY_LONG_V2_1_PREDEVELOPMENT_CONTRACT_FROZEN', 'STATUS')
    require(c['scope'] == 'CONTRACT_ONLY_STOP_BEFORE_TRAINING', 'SCOPE')
    require(all(c['identity'][k] == v for k,v in IDENTITIES.items()), 'FROZEN_IDENTITIES')
    require(c['architecture']['scope'] == 'V1_REFINEMENT_EXACT_ANCHOR_SUBSET', 'REFINEMENT')
    require(c['architecture']['newPrimaryModelCount'] == 1 and c['architecture']['riskOnlyEntry'] is False and
            c['architecture']['fullReplacement'] is False, 'ARCHITECTURE_BOUNDARY')
    require(c['opportunityAxis']['threshold'] == 2. and c['opportunityAxis']['modelRefit'] is False, 'OPPORTUNITY_FROZEN')
    require(c['state']['anchorConsumption'] == 'FROZEN_V1_SHADOW_ENTER_CONSUMES_BEFORE_RISK', 'SHADOW_LATCH')
    require(c['state']['outputs'] == ['ENTER', 'SKIP_THIS_DECISION'], 'STATE')
    for k in ['wait', 'expiry', 'retryAfterRiskReject', 'v1SkipRecovery', 'entryTimingChange']:
        require(c['state'][k] is False, 'STATE_' + k)
    t = c['target']
    require(t['disposition'] == 'A_KEEP_PRIMARY', 'TARGET_DISPOSITION')
    require(t['primary'] == 'D30_CONTINUOUS_ADVERSE_MAGNITUDE_PCT', 'TARGET')
    require(t['horizonMinutes'] == 30 and t['requiredBars'] == 6 and t['clock'] == 'WALL_CLOCK', 'LABEL_WINDOW')
    require(t['soleEnterGate'] is False and t['clipping'] is False and t['binaryTailTarget'] is False, 'TARGET_ROLE')
    require(t['missingExpectedBar'] == 'CENSORED' and t['auctionAllowed'] is False, 'CENSORING')
    u = c['universe']
    require((u['candidateCount'], u['decisionCount'], u['sessionCount'], u['rawScoreQualified'],
             u['riskAnchorCount'], u['riskLabelableCount'], u['riskUnlabelableCount']) ==
            (3800, 760, 76, 353, 277, 181, 96), 'UNIVERSE')
    require(u['fullLiveUniversePITClaim'] is False and u['labelAvailabilityInRuntimeEligibility'] is False, 'UNIVERSE_CLAIM')
    require(c['trainingRows']['unit'] == 'FROZEN_V1_FIRST_QUALIFYING_SELECTION_EVENT', 'TRAINING_ROW')
    require(c['trainingRows']['weightFormula'] == '1/(S*d_s*n_sd)', 'WEIGHTS')
    require(c['trainingRows']['sameSymbolSessionAcrossTrainEval'] is False and
            c['trainingRows']['symbolSpecificOverrides'] is False, 'REPEATED_PROTECTION')
    f = c['features']
    require(f['order'] == ORDER and f['effectiveInputCount'] == 4 and f['rawPredictorCount'] == 2, 'FEATURE_ORDER')
    require([x['name'] for x in f['definitions']] == ORDER, 'FEATURE_DEFINITIONS')
    require(f['selectorScoreInsideRisk'] is False and f['selectorRankInsideRisk'] is False and f['v1ScoreInsideRisk'] is False, 'OPPORTUNITY_CONTAMINATION')
    require(f['activeOptionalFeatures'] == [] and not f['featureInteractions'] and not f['polynomials'], 'EXTRA_FEATURES')
    m = c['missing']
    require(m['strategy'] == 'FOLD_LOCAL_FEATURE_ONLY_WEIGHTED_MEDIAN_PLUS_TWO_INDICATORS', 'MISSING')
    require(m['scaledRawPredictors'] == ORDER[:2] and m['unscaledIndicators'] == ORDER[2:], 'SCALING')
    for k in ['missingIsZero','forwardFill','futureFill','nextObservationFill','interpolation','outcomeDerivedImputation','volumeMissingAsZero']:
        require(m[k] is False, 'FILL_' + k)
    model = c['model']
    require(model['family'] == 'WEIGHTED_L2_LINEAR_RIDGE_REGRESSION' and model['modelCount'] == 1, 'MODEL')
    require(model['lambda'] == 1. and model['solver'] == 'numpy.linalg.solve' and model['featureCount'] == 4, 'REGULARIZATION')
    require(model['interceptPenalized'] is False and model['calibrationModel'] == 'NONE', 'MODEL_CAPACITY')
    require(model['minRows'] == 7 and model['minSymbols'] == 2, 'FIT_SUPPORT')
    require(model['runtime'] == {'python':'3.12','numpy':'2.3.5','scipyRequired':False,'dtype':'float64','threads':1}, 'RUNTIME')
    sessions = u['sessions']
    require(len(sessions) == 76 and sessions == sorted(set(sessions)), 'SESSION_ORDER')
    require(len(c['cv']['folds']) == 4, 'FOLD_COUNT')
    for f, (n,lo,hi) in zip(c['cv']['folds'], [(16,17,31),(31,32,46),(46,47,61),(61,62,76)]):
        cut = 3*n//4
        require(f['trainOrdinals'] == [1,n] and f['evaluationOrdinals'] == [lo,hi], 'OUTER_SPLIT')
        require(f['innerFitOrdinals'] == [1,cut] and f['innerCalibrationOrdinals'] == [cut+1,n], 'INNER_SPLIT')
        require(f['trainDates'] == sessions[:n] and f['evaluationDates'] == sessions[lo-1:hi], 'FOLD_DATES')
    require(c['cv']['randomSplit'] is False and c['cv']['fitStatisticsFromEvaluation'] is False, 'FOLD_LEAK')
    require(c['crossSymbol']['groups'] == 5 and c['crossSymbol']['postHocRebalancing'] is False and
            c['crossSymbol']['heldGroupOutcomesUsedForThreshold'] is False, 'SYMBOL_CV')
    require(c['decision']['thresholdCandidatesPct'] == [1.,2.,5.,10.], 'THRESHOLDS')
    require(c['decision']['selectionOrder'] == ['ALL_INNER_ENTRY_GATES_MUST_PASS', 'LARGEST_THRESHOLD_LEAST_RESTRICTIVE'], 'THRESHOLD_SELECTION')
    for k in ['opportunityRiskProduct','positionSizingUsesScore','opportunityTierThresholds','fallbackToV1']:
        require(c['decision'][k] is False, 'DECISION_' + k)
    require(c['numericGates']['primary'] == PRIMARY and c['numericGates']['guardrails'] == GUARDRAILS and
            c['numericGates']['crossSymbol'] == CROSS, 'NUMERIC_GATES')
    require(c['metrics']['primaryPreservation'] == 'EXACT_V1_ENTRY_ANCHOR_WINNER_RETENTION', 'PRESERVATION_DENOMINATOR')
    require(c['executionQuality']['role'] == 'DIAGNOSTIC_ONLY_NO_GATE', 'EXECUTION_ROLE')
    require(c['portfolio']['role'] == 'SECONDARY_DIAGNOSTIC_NOT_ENTRY_SELECTION_OR_PRIMARY_GATE', 'PORTFOLIO_ROLE')
    require(c['portfolio']['fabricatedLiquidationAllowed'] is False and c['portfolio']['engineChangesAllowed'] is False, 'PORTFOLIO_FABRICATION')
    fair = c['fairComparator']
    require(fair['entryOnlyChange'] is True and fair['primaryOwnAcceptedSets'] is True, 'FAIR_SETS')
    require(fair['exit'] == 'LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1' and fair['allocation'] == 'EQUAL_MAX3 / V3_0_EQUAL', 'DOWNSTREAM')
    require(fair['ledger'] == 'scripts/phase57_long_capital_integration.py::replay', 'LEDGER')
    require((fair['initialCashJpy'],fair['lotSize'],fair['maximumConcurrentPositions'],fair['budgetDivisor'],fair['roundTripCostPctOfEntryNotional']) == (1000000,100,10,3,.05), 'CASH_COST')
    require(c['dataProtection']['trainingAuthorizedByThisContractFreeze'] is False and
            c['dataProtection']['newProviderRequestsAllowed'] is False, 'AUTHORIZATION')
    require(c['dataProtection']['globalFreshBudgetSessions'] == 195, 'FRESH_BUDGET')
    require(c['dataProtection']['globalBudgetSHA'] == IDENTITIES['globalBudgetSHA'], 'GLOBAL_BUDGET_SHA')
    require(all(type(v) is int and v == 0 for v in c['currentScopeCounters'].values()), 'COUNTERS')
    require(set(c['safety']) == set(SAFETY) and all(c['safety'][k] is False for k in SAFETY), 'SAFETY')
    require(all(c[k] is False for k in ['shortAllowed','marginAllowed','leverageAllowed','promotionAllowed']), 'TRADING')
    require(c['repository']['mainMergeAllowed'] is False and c['exactNextAction'].startswith('STOP.'), 'STOP')


def shadow_anchor_audit(rows, saved):
    """Verify existing v1 states from SAVED v1 scores; no model prediction or v2.1 decision."""
    require(len(saved) == len(rows), 'BASELINE_DUPLICATE_OR_MISSING')
    seen, anchors = set(), []
    for r in sorted(rows, key=lambda r:(r['decisionTimestamp'],r['selectorEventId'])):
        p = saved[r['selectorEventId']]
        score = p['expectedClass']
        require(isinstance(score,(int,float)) and math.isfinite(score), 'V1_SCORE_INVALID')
        raw = score >= 2.
        eligible = raw and r['symbolSessionId'] not in seen
        reason = 'FIRST_QUALIFYING_DECISION' if eligible else 'ALREADY_ENTERED' if r['symbolSessionId'] in seen else 'BELOW_FROZEN_THRESHOLD'
        require(p['state'] == ('ENTER' if eligible else 'SKIP_THIS_DECISION') and p['reason'] == reason, 'FROZEN_V1_STATE_PARITY')
        if eligible:
            seen.add(r['symbolSessionId'])
            anchors.append(r)
    return anchors


def inventory(rows, labels):
    return {'rows':len(rows), 'symbols':len({r['symbol'] for r in rows}),
            'symbolSessions':len({r['symbolSessionId'] for r in rows}),
            'labelable':sum(labels[r['selectorEventId']]['labelable'] for r in rows),
            'unlabelable':sum(not labels[r['selectorEventId']]['labelable'] for r in rows),
            'censorReasons':dict(sorted(collections.Counter(labels[r['selectorEventId']]['reason'] for r in rows if not labels[r['selectorEventId']]['labelable']).items())),
            'available':{k:sum(r['features'][k]['status']=='AVAILABLE' for r in rows) for k in ORDER[:2]}}


def split_plan(rows, anchors, labels, c):
    """Identity/time splits; labelability is reported AFTER grouping, never used for assignment."""
    sessions = c['universe']['sessions']
    mapping = {s:symbol_group(s) for s in sorted({r['symbol'] for r in rows})}
    plans = []
    for f in c['cv']['folds']:
        cut = f['innerFitOrdinals'][1]
        windows = {'innerFit':sessions[:cut], 'innerCalibration':sessions[cut:f['trainOrdinals'][1]],
                   'outerRefit':f['trainDates'], 'outerEvaluation':f['evaluationDates']}
        for g in [None,0,1,2,3,4]:
            sets = {k:[r for r in anchors if r['sessionDate'] in ds and (g is None or (mapping[r['symbol']]==g if k=='outerEvaluation' else mapping[r['symbol']]!=g))] for k,ds in windows.items()}
            a,b = sets['outerRefit'],sets['outerEvaluation']
            require(not ({r['symbolSessionId'] for r in a} & {r['symbolSessionId'] for r in b}), 'SYMBOL_SESSION_OVERLAP')
            require(not ({r['symbolSessionId'] for r in sets['innerFit']} & {r['symbolSessionId'] for r in sets['innerCalibration']}), 'INNER_SESSION_OVERLAP')
            if g is not None:
                held={s for s in mapping if mapping[s]==g}
                require(not any(r['symbol'] in held for k in ['innerFit','innerCalibration','outerRefit'] for r in sets[k]), 'HELD_SYMBOL_LEAK')
            purged = 0
            for fit_key,next_dates in [('innerFit',windows['innerCalibration']),('outerRefit',windows['outerEvaluation'])]:
                start = datetime.datetime.fromisoformat(next_dates[0]+'T00:00:00+09:00')
                for r in sets[fit_key]:
                    if labels[r['selectorEventId']]['labelable']:
                        end=datetime.datetime.fromisoformat(r['decisionTimestamp'])+datetime.timedelta(minutes=30)
                        purged += int(end>=start)
            require(purged == 0, 'LABEL_WINDOW_OVERLAP')
            plans.append({'fold':f['fold'],'heldGroup':g,'windows':{k:inventory(v,labels) for k,v in sets.items()},
                          'symbolSessionOverlap':0,'heldSymbolLeakCount':0,'purgedByBoundaryCount':purged})
    return {'purpose':'METADATA_ONLY_NO_OOF_NO_THRESHOLD_EVALUATION','groupNamespace':'PHASE57_MSH_LONG_V2_GROUP_V1|',
            'groups':[{'group':g,'symbols':[s for s in mapping if mapping[s]==g],
                       'anchorInventory':inventory([r for r in anchors if mapping[r['symbol']]==g],labels)} for g in range(5)],
            'replicas':plans,'outerUniverseRows':3000,'outerRiskAnchors':sum(r['sessionDate'] in sessions[16:] for r in anchors)}


def audit(root=ROOT):
    c = read(root/CONTRACT)
    require(sha(root/CONTRACT) == FROZEN_SHA == (root/(CONTRACT+'.sha256')).read_text().strip(), 'CONTRACT_HASH')
    validate_contract(c)
    for path,h in c['sourcePins'].items():
        require(sha(root/path) == h, 'SOURCE_PIN:'+path)
    selector=read(root/'predict/research/phase57-long-only-frozen-selector-v1.json')
    require(hashlib.sha256(canonical(selector['freezePayload'])).hexdigest()==IDENTITIES['selectorPayloadSHA'], 'SELECTOR_PAYLOAD_SHA')
    require(selector['hashes']['savedModelArtifactSha256']==IDENTITIES['selectorRidgeSHA'], 'SELECTOR_RIDGE_SHA')
    def lines(path):
        with gzip.open(root/path,'rt') as h:
            return [json.loads(line) for line in h]
    rows, pp = lines(FEATURES),lines(PREDICTIONS)
    saved = {r['selectorEventId']:r for r in pp}
    with gzip.open(root/LABELS,'rt') as h:
        ll=json.load(h)['events']
    labels={r['selectorEventId']:r for r in ll}
    ids=[r['selectorEventId'] for r in rows]
    require(len(ids)==len(set(ids))==len(pp)==len(ll)==3800 and set(ids)==set(saved)==set(labels), 'UNIVERSE_IDENTITY')
    require(hashlib.sha256(canonical(ids)).hexdigest()==c['identity']['eventIdentitySHA'], 'EVENT_SHA')
    require(sorted({r['sessionDate'] for r in rows}) == c['universe']['sessions'], 'SESSIONS')
    for r in rows:
        require(r['direction']=='LONG' and r['shortScoreEvaluated'] is False, 'LONG_ONLY')
        for name in ORDER[:2]:
            x=r['features'][name]
            require(x['status']!='AVAILABLE' or (isinstance(x['value'],(int,float)) and math.isfinite(x['value'])), 'INVALID_FEATURE')
    anchors=shadow_anchor_audit(rows,saved)
    inv=inventory(anchors,labels)
    require((len(anchors),inv['labelable'],inv['unlabelable'])==(277,181,96), 'RISK_POPULATION')
    require(sum(p['expectedClass']>=2 for p in pp)==353, 'RAW_QUALIFIED')
    ledger=[]
    for r in anchors:
        lab=labels[r['selectorEventId']]
        ledger.append({k:r[k] for k in ['selectorEventId','symbol','symbolSessionId','sessionDate','decisionTimestamp']} |
                      {'v1Anchor':True,'labelable':lab['labelable'],'trainingLabelStatus':'ELIGIBLE_FOR_FOLD_TRAINING_ONLY' if lab['labelable'] else 'EXCLUDED_TRAINING_LOSS_ONLY',
                       'censorReason':lab['reason'],'featureStatus':{n:r['features'][n]['status'] for n in ORDER[:2]}})
    report={'verdict':c['status'],'contractSHA':FROZEN_SHA,'sourcePinsVerified':len(c['sourcePins']),
            'frozenSelectorEntryExitAllocationLedgerUnchanged':True,'modelRuntimeImported':False,
            'all3800':inventory(rows,labels),'rawScoreQualified':353,'repeatedQualifiedAfterV1Anchor':76,
            'riskAnchors':inv,'labelableRiskAnchors':inventory([r for r in anchors if labels[r['selectorEventId']]['labelable']],labels),
            'trainingExclusions':{'nonV1Anchor':3523,'unlabelableV1Anchor':96},
            'metadataAuditOnly':True,'newRiskScores':0,'newRiskDecisions':0,'counters':c['currentScopeCounters'],'safety':c['safety']}
    return report,split_plan(rows,anchors,labels,c),ledger


def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');args=p.parse_args()
    report,plan,ledger=audit()
    if args.write:
        for name,value in [('static-audit.json',report),('split-metadata.json',plan),('risk-universe-ledger.json',ledger)]:
            path=ROOT/EVIDENCE/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'verdict':report['verdict'],'contractSHA':FROZEN_SHA,'riskAnchors':report['riskAnchors'],'allCountersZero':not any(report['counters'].values())}))


if __name__ == '__main__':
    main()
