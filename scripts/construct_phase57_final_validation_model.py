#!/usr/bin/env python3
"""One authorized final artifact construction. No performance evaluation or CV.

prepare freezes input identity before fit; fit refuses an existing output directory.
The original model fits its own scaler and checks training probabilities internally.
Only five deterministic synthetic probe rows are predicted outside that integrity check.
"""
import argparse
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_phase57_development_preservation import verify

SCOPE = ROOT / 'predict/research/phase57-msh-entry-long-v1-final-model-scope-v1.json'
OUT = ROOT / 'docs/evidence/phase57-msh-entry-long-v1-final-validation-model'
FEATURES = ['frozenSelectorRidgeScore', 'frozenSelectorRidgeRank']
PINS = {
 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz': '73e566aba4d1a3f5af33b74be52ae90736c088b1091841f1eb44e93d5476084c',
 'docs/evidence/phase57-msh-entry-long-v1-offline-freeze/development-evidence-freeze.json': '68d2a02c988a05b3178e903d628a53662b01bb704fa0700ebcb98e3b32547ead',
}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(value).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')

def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)

def inputs():
    verify()  # hash-only protection; no model/prediction/performance imports
    for name, expected in PINS.items():
        require(digest((ROOT/name).read_bytes()) == expected, 'ARTIFACT_INTEGRITY_FAILED:'+name)
    fit = json.loads((ROOT/'predict/research/phase57-msh-entry-long-v1-fit-contract-v1.json').read_text())
    selector = json.loads((ROOT/'predict/research/phase57-long-only-frozen-selector-v1.json').read_text())
    sessions = selector['freezePayload']['development']['sessions']
    with gzip.open(ROOT/next(iter(PINS)), 'rt') as f:
        rows = [json.loads(line) for line in f]
    with gzip.open(ROOT/'docs/evidence/phase57-msh-entry-long-v1-first-development/row-ledger.ndjson.gz','rt') as f:
        ledger = [json.loads(line) for line in f]
    ids = [r['selectorEventId'] for r in rows]
    require(len(rows)==len(set(ids))==3800, 'TRAINING_IDENTITY_MISMATCH')
    require(sessions==sorted({r['sessionDate'] for r in rows}) and len(sessions)==76, 'TRAINING_IDENTITY_MISMATCH')
    require(len({r['symbolSessionId'] for r in rows})==2743, 'TRAINING_IDENTITY_MISMATCH')
    projected = [dict(selectorEventId=r['selectorEventId'], sessionDate=r['sessionDate'],
                      symbol=r['symbol'], decisionTimestamp=r['decisionTimestamp'],
                      labelable=r['label']['labelable'], reason=r['label']['reason']) for r in rows]
    require(projected==[{k:r[k] for k in projected[0]} for r in ledger], 'TRAINING_IDENTITY_MISMATCH')
    for r in rows:
        require(r['direction']=='LONG' and r['shortScoreEvaluated'] is False, 'LONG_ONLY_REQUIRED')
        l = r['label']
        if l['labelable']:
            require(l['expectedBarCount']==l['observedBarCount']==6 and l['highAvailable'], 'LABELABLE_ROW_MISMATCH')
            delta = datetime.fromisoformat(l['windowEndTimestamp'].replace('Z','+00:00'))-datetime.fromisoformat(r['decisionTimestamp'])
            require(delta.total_seconds()==1800 and l['ordinalClass'] in range(5), 'LABELABLE_ROW_MISMATCH')
        else:
            require(l['ordinalClass'] is None, 'UNLABELABLE_IS_NOT_NEGATIVE')
    train = [r for r in rows if r['label']['labelable']]
    counts = [sum(r['label']['ordinalClass']==k for r in train) for k in range(5)]
    reasons = dict(Counter(r['label']['reason'] for r in rows if not r['label']['labelable']))
    require(len(train)==1828 and counts==[606,423,271,281,247], 'LABELABLE_ROW_MISMATCH')
    require(reasons=={'PROVIDER_GAP':1424,'LUNCH_BREAK':380,'SESSION_END':168}, 'LABELABLE_ROW_MISMATCH')
    identity = {'trainingSessions':sessions, 'sessionCount':76, 'sessionListSha256':digest(canonical(sessions)),
        'selectionEventCount':3800, 'labelableCount':1828, 'unlabelableCount':1972,
        'unlabelableReasons':reasons, 'classCounts':counts, 'uniqueSymbolSessions':2743,
        'allEventIdsSha256':digest(canonical(ids)),
        'trainingEventIdsSha256':digest(canonical([r['selectorEventId'] for r in train])),
        'trainingPayloadSha256':digest(canonical([[r['selectorEventId'],r['ridgeScore'],r['ridgeRank'],r['label']['ordinalClass']] for r in train])),
        'rowOrder':'EXISTING_FEASIBILITY_LEDGER_ORDER', 'featureOrder':FEATURES,
        'featureOrderSha256':digest(canonical(FEATURES)), 'hashEncoding':'SORTED_KEY_COMPACT_JSON_UTF8_NO_NEWLINE'}
    return fit, train, identity

def prepare():
    require(not SCOPE.exists() and not OUT.exists(), 'SCOPE_OR_ARTIFACT_ALREADY_EXISTS')
    fit, _, identity = inputs()
    scope = {'schemaVersion':1, 'dateJst':'2026-09-16', 'status':'FROZEN_BEFORE_FINAL_FIT',
        'purpose':'SINGLE_VALIDATION_ARTIFACT_CONSTRUCTION_NOT_DEVELOPMENT_PERFORMANCE',
        'authorization':'User explicitly authorizes all76 Development labelable rows, one construction fit, then one determinism verification only after first fit passes.',
        'additiveOnly':True, 'priorFinalAll76SessionRefitZeroRemainsHistoricalFact':True,
        'trainingIdentity':identity, 'sourcePins':PINS,
        'fitContractPath':'predict/research/phase57-msh-entry-long-v1-fit-contract-v1.json',
        'fitContractSha256':'64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938',
        'selector':fit['sourceIntegrity'], 'model':fit['architecture'], 'features':fit['features'],
        'label':fit['label'], 'mathematics':fit['mathematics'], 'solver':fit['fit'],
        'runtime':fit['runtime'], 'classWeight':'UNWEIGHTED',
        'scaler':{'scope':'ALL_76_DEVELOPMENT_LABELABLE_ROWS_ONLY', 'ddof':0, 'nonpositiveStd':'FAIL_CLOSED',
                  'implementation':'Frozen model.fit computes scaler internally. Pass RAW Core, never double-standardize.'},
        'fitBudget':{'construction':1,'determinismVerificationAfterInitialPass':1,'performanceRetry':0},
        'determinism':{'parametersAtol':1e-12,'parametersRtol':0,'solverStatusExact':True,
                       'objectiveAtol':1e-12,'scalerExact':True},
        'integrityPredictions':{'internalFit':'Frozen model checks all1828 training probabilities once per fit; no metrics/scores saved.',
            'external':'Five fixed synthetic standardized probes [-2,-1],[ -1,1],[0,0],[1,-1],[2,1]; probability integrity and serialization only.',
            'projectPerformancePredictions':0},
        'performanceEvaluationAllowed':False,'oofRegenerationAllowed':False,
        'validationAccessAllowed':False,'oosAccessAllowed':False,'exitAccessAllowed':False,
        'providerRequestsAllowed':False,'thresholdPerformanceAllowed':False,
        'candidateThreshold':2.0,'candidateNotAdoption':True,'safety':fit['safety'],
        'failurePolicy':'STOP_NO_RETRY_NO_RECONFIGURATION_NO_FOLD_SUBSTITUTION',
        'constructionScriptSha256':digest(Path(__file__).read_bytes())}
    write(SCOPE, scope)
    print(json.dumps({'scopeSha256':digest(SCOPE.read_bytes()),'trainingIdentity':identity}))

def construct(expected_scope_sha):
    require(os.environ.get('ARK_TEST_OFFLINE')=='1', 'OFFLINE_GUARD_REQUIRED')
    require(digest(SCOPE.read_bytes())==expected_scope_sha, 'SCOPE_SHA_MISMATCH')
    scope = json.loads(SCOPE.read_text())
    require(digest(Path(__file__).read_bytes())==scope['constructionScriptSha256'],'SOURCE_CHANGED_AFTER_SCOPE_FREEZE')
    fit, train, identity = inputs()
    require(identity==scope['trainingIdentity'], 'TRAINING_IDENTITY_MISMATCH')
    require(not OUT.exists(), 'ONE_FIT_ONLY_OUTPUT_ALREADY_EXISTS')
    # Output marker is created before model import/fit. Failure leaves it in place.
    OUT.mkdir()
    audit = {'status':'STARTED','scopeSha256':expected_scope_sha,'constructionFitCalls':0,
             'determinismFitCalls':0,'developmentPerformanceEvaluations':0,'oofRegeneration':0,
             'thresholdPerformanceSearch':0,'validationAccess':0,'oosAccess':0,'exitAccess':0,
             'shortEvaluation':0,'providerRequests':{'yahoo':0,'jquants':0,'otherMarketData':0},
             'safety':fit['safety']}
    write(OUT/'construction-audit.json',audit)
    try:
        import numpy as np
        import scipy
        require(sys.version_info[:2]==(3,12) and np.__version__=='2.3.5' and scipy.__version__=='1.17.0','ENVIRONMENT_MISMATCH')
        source = ROOT/fit['sourceIntegrity']['implementationPath']
        spec = importlib.util.spec_from_file_location('frozen_final_ordinal',source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        X = np.asarray([[r['ridgeScore'],r['ridgeRank']] for r in train],dtype=np.float64)
        y = np.asarray([r['label']['ordinalClass'] for r in train])
        require(np.isfinite(X).all() and tuple(np.unique(y))==(0,1,2,3,4),'FINAL_SCALER_FAILED')
        audit['constructionFitCalls']=1
        write(OUT/'construction-audit.json',audit)
        model = module.ProportionalOddsOrdinalLogit().fit(X,y,feature_order=FEATURES)
        artifact = model.to_artifact()
        require(artifact['solver']['success'] is True,'CONVERGENCE_FAILED')
        require(artifact['featureOrder']==FEATURES,'ARTIFACT_INTEGRITY_FAILED')
        model.save_json(OUT/'final-model.json')
        scaler = dict(artifact['scaler'],featureOrder=FEATURES,trainingScope='ALL76_LABELABLE_ONLY',
                      trainingEventIdsSha256=identity['trainingEventIdsSha256'],
                      sessionListSha256=identity['sessionListSha256'])
        write(OUT/'final-scaler.json',scaler)
        # No project-row external predictions: these are predetermined synthetic probes.
        probe = np.asarray([[-2,-1],[-1,1],[0,0],[1,-1],[2,1]],dtype=float)*model.scaler_std_+model.scaler_mean_
        p = model.predict_proba(probe)
        loaded = module.ProportionalOddsOrdinalLogit.load_json(OUT/'final-model.json')
        require(np.array_equal(p,loaded.predict_proba(probe)),'ARTIFACT_INTEGRITY_FAILED')
        require(np.isfinite(p).all() and (p>=0).all() and np.allclose(p.sum(1),1,atol=1e-12,rtol=0),'PROBABILITY_INTEGRITY_FAILED')
        # Explicitly authorized verification fit, never used as the final artifact.
        audit['determinismFitCalls']=1
        write(OUT/'construction-audit.json',audit)
        repeat = module.ProportionalOddsOrdinalLogit().fit(X,y,feature_order=FEATURES)
        repeated = repeat.to_artifact()
        require(artifact==repeated,'DETERMINISM_FAILED')
        require(np.array_equal(p,repeat.predict_proba(probe)),'DETERMINISM_FAILED')
        require(np.array_equal(p@np.arange(5),repeat.predict_proba(probe)@np.arange(5)),'DETERMINISM_FAILED')
        audit.update(status='PASS',trainingIdentity=identity,modelArtifactSha256=digest((OUT/'final-model.json').read_bytes()),
            scalerSha256=digest((OUT/'final-scaler.json').read_bytes()),sourceSha256=digest(source.read_bytes()),
            runtime={'python':sys.version.split()[0],'numpy':np.__version__,'scipy':scipy.__version__},
            convergence=artifact['solver'],probabilityIntegrity='PASS_INTERNAL_ALL_TRAINING_AND_FIVE_SYNTHETIC_PROBES',
            serialization='EXACT_SYNTHETIC_PROBE_PROBABILITY_EQUALITY',determinism='EXACT_ARTIFACT_AND_PROBE_EQUALITY',
            constructionScalerFits=1,verificationScalerRecomputations=1,
            internalTrainingProbabilityCheckRowsPerFit=1828,externalProjectPredictions=0,
            syntheticProbeRows=5,performanceMetricsCreated=[],frozenPreservation=verify())
    except Exception as error:
        audit.update(status='FINAL_MODEL_FIT_FAILED',error=str(error),retryAllowed=False)
        raise
    finally:
        write(OUT/'construction-audit.json',audit)
    print(json.dumps({k:audit[k] for k in ['status','modelArtifactSha256','scalerSha256','convergence','determinism']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','fit'])
    parser.add_argument('--scope-sha')
    args=parser.parse_args()
    if args.action=='prepare':
        prepare()
    else:
        require(bool(args.scope_sha),'EXPLICIT_SCOPE_SHA_REQUIRED')
        construct(args.scope_sha)
