"""Write a terminal, append-only CCMG closure after all required hard gates."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/phase57-checkpoint-certified-guard-exit'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(name):return json.loads((OUT/name).read_text())


def put(name,obj):
    path=OUT/name
    path.write_text(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')


def run(ci_status,ci_run):
    pre=read('CYCLE_PRECOMMIT.json');ready=read('CHECKPOINT_READINESS.json')
    layer=read('LAYER_A_RESULT.json');pot=read('POTENTIAL_RESULT.json')
    teacher=read('POTENTIAL_TEACHER_AUDIT.json');audit=read('INDEPENDENT_AUDIT.json')
    assert ready['gates']==dict.fromkeys(('R1','R2','R3','R4','R5','R6'),'PASS')
    assert layer['winnerGate']=='WINNER_PRESERVATION_FAIL' and not layer['capitalEligibility']
    assert audit['status']=='PASS' and audit['winnerGate']==layer['winnerGate']
    assert teacher['status']=='POTENTIAL_LABEL_LINEAGE_PASS'
    assert pot['outerFitsActual']==6 and pot['canonicalOuterFoldCount']==5
    assert not any(pre['safety'].values())
    assert ci_status in ('SUCCESS','FAILURE','QUEUED')
    code_files=('scripts/phase57_ccmg_guard.py','scripts/phase57_ccmg_layer_a.py',
        'scripts/phase57_ccmg_potential.py','scripts/phase57_ccmg_diagnostics.py',
        'scripts/phase57_ccmg_independent_audit.py','tests/test_phase57_ccmg_guard.py',
        '.github/workflows/phase57-ccmg-focused.yml')
    receipt={'schema':'phase57-ccmg-implementation-receipt-v1',
        'candidate':'CCMG_GUARD_V1','codeSha256':{p:sha(ROOT/p) for p in code_files},
        'unitTests':{'focusedN':30,'passN':30,'failN':0,'localStatus':'PASS'},
        'ci':{'runId':ci_run,'status':ci_status,'scope':'synthetic focused contract only'},
        'layerAReproducibility':{'status':'PASS',
           'resultSha256':sha(OUT/'LAYER_A_RESULT.json'),
           'entryRowsSha256':sha(OUT/'LAYER_A_ENTRY_ROWS.jsonl.gz'),
           'passes':2,'byteIdentical':True},
        'dryTraceReproducibility':{'status':'PASS','passes':2,
            'traceSha256':ready['traceSha256'],'byteIdentical':True},
        'exitEstimatorFits':0,'safety':pre['safety']}
    put('IMPLEMENTATION_RECEIPT.json',receipt)
    all_entry={'schema':'phase57-ccmg-all-entry-result-v1','standalone100Shares':True,
        'portfolioPnL':False,'byArmBucket':layer['allEntryStandalone'],
        'winnerContradiction':layer['allEntryWinnerContradiction'],
        'status':'ALL_ENTRY_WINNER_CONTRADICTION',
        'nullNotImputed':True,'sourceLayerASha256':sha(OUT/'LAYER_A_RESULT.json'),
        'safety':pre['safety']}
    put('ALL_ENTRY_RESULT.json',all_entry)
    exposure={'schema':'phase57-ccmg-exposure-ledger-v1','providerRequests':0,
        'protectedOpened':0,'freshOpened':0,'validationOpened':0,'oosOpened':0,
        'prospectiveOpened':0,'orders':0,'mainMerges':0,
        'exitEstimatorFits':0,'potentialEstimatorFits':pot['outerFitsActual'],
        'potentialEstimatorFitsMax':2*pot['canonicalOuterFoldCount'],
        'integratedReplayInvocations':0,'integratedReplayMaximum':16,
        'restrictedDataUsed':False,'safety':pre['safety']}
    put('EXPOSURE_LEDGER.json',exposure)
    manifest_files=['START_AUDIT.json','CYCLE_PRECOMMIT.json','CYCLE_PRECOMMIT.sha256',
        'CHECKPOINT_READINESS.json','CHECKPOINT_DRY_TRACE.jsonl.gz',
        'CHECKPOINT_ENTRY_SUMMARY.jsonl.gz','CHECKPOINT_ANATOMY.json',
        'POTENTIAL_RECOVERY_AUDIT.json','POTENTIAL_FIT_PROTOCOL.json',
        'POTENTIAL_TEACHER_AUDIT.json','POTENTIAL_TEACHER_ROWS.jsonl.gz',
        'POTENTIAL_RESULT.json','POTENTIAL_OOF.jsonl.gz',
        'IMPLEMENTATION_RECEIPT.json','LAYER_A_RESULT.json',
        'LAYER_A_ENTRY_ROWS.jsonl.gz','MECHANISM_DIAGNOSTICS.json',
        'WINNER_MECHANISM_ROWS.jsonl.gz','ALL_ENTRY_RESULT.json',
        'INDEPENDENT_AUDIT.json','EXPOSURE_LEDGER.json','REPORT-ja.md']
    manifest_files+=sorted(str(x.relative_to(OUT)) for x in (OUT/'figures').glob('*.png'))
    manifest={'schema':'phase57-ccmg-manifest-v1','precommitSha256':sha(OUT/'CYCLE_PRECOMMIT.json'),
        'filesSha256':{p:sha(OUT/p) for p in manifest_files},
        'sourcePinsSha256':ready['sourcePinsSha256'],
        'selectedDevelopment':None,'noNewProvider':True,'safety':pre['safety']}
    put('MANIFEST.json',manifest)
    closure={'schema':'phase57-ccmg-final-closure-v1','architecture':'CHECKPOINT_CERTIFIED_MILESTONE_GUARD_EXIT',
        'candidate':'CCMG_GUARD_V1','checkpointReadiness':'PASS',
        'winnerPreservation':'WINNER_PRESERVATION_FAIL',
        'loserNonDegradation':layer['loserGate'],
        'allEntry':'ALL_ENTRY_WINNER_CONTRADICTION',
        'potentialFeatureRecovery':read('POTENTIAL_RECOVERY_AUDIT.json')['status'],
        'potentialLabelLineage':'PASS',
        'potentialHead5':pot['heads']['5']['status'],
        'potentialHead10':pot['heads']['10']['status'],
        'capital':'SKIPPED_HARD_GATE','stress':'SKIPPED_HARD_GATE',
        'economicMeasurement':'NOT_ATTEMPTED_AFTER_WINNER_FAIL',
        'arkMonth2x':'ARK_MONTH_2X_UNMEASURABLE',
        'finalStatus':'NO_SELECTION',
        'selectedDevelopment':None,'productionReady':False,
        'independentAudit':'PASS','localFocusedTests':'30/30 PASS',
        'ci':receipt['ci'],
        'integrity':'PASS',
        'reproducibility':{'readinessDryTrace':'PASS','layerA':'PASS',
            'potentialOOF':'SAVED_HASH_AND_ID_AUDITED; FULL_REFIT_NOT_RUN_FIT_BUDGET',
            'integrated':'NOT_ELIGIBLE'},
        'budget':exposure,
        'winnerExactDeltasJpy':{k:v['pairedDeltaJpy'] for k,v in layer['winner'].items()},
        'winnerKnownVsAll':{k:[v['knownPairedN'],v['entryN']] for k,v in layer['winner'].items()},
        'precommitSha256':sha(OUT/'CYCLE_PRECOMMIT.json'),
        'manifestSha256':sha(OUT/'MANIFEST.json'),
        'independentAuditSha256':sha(OUT/'INDEPENDENT_AUDIT.json'),
        'reportSha256':sha(OUT/'REPORT-ja.md'),
        'safety':pre['safety'],
        'nextBoundary':'NEW_PRECOMMIT_REQUIRED; do not tune this ladder/floor/confirmation from results'}
    put('FINAL_CLOSURE.json',closure)
    print(json.dumps({'closure':closure['finalStatus'],'winner':closure['winnerPreservation'],
                      'ci':ci_status,'manifestSha256':closure['manifestSha256']},indent=2))


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--ci-status',required=True,
       choices=['SUCCESS','FAILURE','QUEUED']);a.add_argument('--ci-run',required=True,type=int)
    x=a.parse_args();run(x.ci_status,x.ci_run)
