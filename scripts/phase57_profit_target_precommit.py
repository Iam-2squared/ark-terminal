"""Freeze a finite, Development-only target diagnostic before new outcomes.

Only identities, existing contracts, source hashes, and schema are read here.
No new target performance is calculated by this module.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = Path('docs/evidence/phase57-profit-target-extension/cycle-20260929-01')
OUT = ROOT / BASE
ARM = {'IM': 'IMMEDIATE', 'R1': 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF'}
TARGETS = [1, 2, 3, 4, 5, 7, 10]
SAFETY = dict.fromkeys(('executionAllowed', 'brokerWriteAllowed',
    'excelOrderWriteAllowed', 'rssOrderFunctionAllowed', 'liveTradingAllowed',
    'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'transmitted'), False)
SOURCE = {
    'phaseAAccounting': 'docs/evidence/phase57-post-prr-phase-a/ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz',
    'phaseAMask': 'docs/evidence/phase57-post-prr-phase-a/COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz',
    'phaseAPlusManifest': 'docs/evidence/phase57-post-prr-phase-a-plus/cycle-20260929-01/MANIFEST.json',
    'integrationPrecommit': 'docs/evidence/phase57-capital-exit-integrated/INTEGRATION_PRECOMMIT.json',
    'integrationReport': 'docs/evidence/phase57-capital-exit-integrated/RESULT/report.json',
    'integrationZip': 'docs/evidence/phase57-capital-exit-integrated/RESULT/phase57-integrated-result.zip',
    'r50Archive': 'docs/evidence/phase57-capital-exit-integrated/INPUTS/R50_A_LIFECYCLE-run-a.jsonl.gz',
    'capitalScores': 'docs/evidence/phase57-capital-v3/RESULT/scores.json',
    'capitalModelPrecommit': 'docs/evidence/phase57-comprehensive-exit-v1/CAPITAL_V3_PREGEOMETRY_PRECOMMIT.json',
    'rawPath': 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz',
    'ccmgTrace': 'docs/evidence/phase57-checkpoint-certified-guard-exit/CHECKPOINT_DRY_TRACE.jsonl.gz',
    'executionCode': 'scripts/phase57_exit_execution_contract_v1.py',
    'capitalCode': 'scripts/phase57_capital_exit_integrated.py',
    'stateCode': 'scripts/phase57_state_v3_9pattern_entry_v1.py',
    'signalCode': 'scripts/phase57_entry_timing_signals.py',
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def digest(path: Path) -> str:
    return sha(path.read_bytes())


def canonical(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode()


def write(name: str, obj) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(canonical(obj))


def check(ok, msg):
    if not ok:
        raise ValueError(msg)


def jst():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')


def freeze():
    check(not OUT.exists(), 'CYCLE_EXISTS_NO_OVERWRITE')
    check(SAFETY == dict.fromkeys(SAFETY, False), 'SAFETY')
    pins = {k: {'path': p, 'sha256': digest(ROOT / p), 'bytes': (ROOT / p).stat().st_size}
            for k, p in SOURCE.items()}
    parent = json.loads((ROOT / SOURCE['integrationPrecommit']).read_text())
    for p, expected in parent['sources'].items():
        check(digest(ROOT / p) == expected, 'PARENT_SOURCE_HASH:' + p)
    check(parent['sessions'] == sorted(parent['sessions']) and len(parent['sessions']) == 24,
          'PARENT_SESSIONS')
    check(parent['safety'] == SAFETY and parent['capacity'] == 3 and
          parent['lotShares'] == 100 and parent['initialCashJpy'] == 1000000,
          'PARENT_CONTRACT')
    accounting = [json.loads(x) for x in gzip.open(ROOT / SOURCE['phaseAAccounting'], 'rt')]
    entries = {}
    for row in accounting:
        if row['world'] != 'ALL_100':
            continue
        arm = row['arm']
        check(arm in ARM and row['session'] in parent['sessions'] and
              row['quantity'] == 100, 'ENTRY_SCOPE')
        key = (ARM[arm], row['entryId'])
        check(key not in entries and row['entryId'] ==
              f"{row['session']}|{row['symbol']}|{row['entryMinute']}", 'ENTRY_IDENTITY')
        entries[key] = row
    check(Counter(k[0] for k in entries) == {'IMMEDIATE': 819,
          'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF': 795}, 'ENTRY_COUNTS')
    with zipfile.ZipFile(ROOT / SOURCE['integrationZip']) as z:
        manifest = json.loads(z.read('manifest.json'))
        for n, expected in manifest['filesSha256'].items():
            check(sha(z.read(n)) == expected, 'ZIP_MEMBER_HASH:' + n)
        ledgers = {}
        for a in ARM:
            name = f'{a}_V3_B_R50_A_ledger.json.gz'
            ledgers[a] = json.loads(gzip.decompress(z.read(name)))
    funded = {}
    for a, ledger in ledgers.items():
        check(ledger['safety'] == SAFETY and ledger['capacity'] == 3,
              'FUNDED_CONTRACT:' + a)
        for eid, f in ledger['funded'].items():
            key = (ARM[a], eid)
            check(key in entries and f['session'] == entries[key]['session'] and
                  f['entryMinute'] == entries[key]['entryMinute'] and
                  abs(float(f['effectiveEntryPrice']) - entries[key]['entryPrice']) < 1e-7 and
                  f['quantity'] >= 100 and f['quantity'] % 100 == 0,
                  'FUNDED_ENTRY_DIFFERENCE:' + eid)
            funded[key] = f
    check(len(ledgers['IM']['funded']) == 79 and len(ledgers['R1']['funded']) == 32,
          'FUNDED_COUNTS')
    score = json.loads((ROOT / SOURCE['capitalScores']).read_text())['CAPITAL_V3_B']
    for a in ARM:
        check(set(score[ARM[a]]) == {eid for arm, eid in entries if arm == ARM[a]},
              'SAVED_SCORE_SCOPE:' + a)
    # The 34-session archive is projected by frozen exact ID before json.loads.
    arm_re = re.compile(r'"entryArm":"([^"]+)"')
    id_re = re.compile(r'"entryId":"([^"]+)"')
    control = {}
    skipped = 0
    with gzip.open(ROOT / SOURCE['r50Archive'], 'rt') as stream:
        for line in stream:
            ma, mi = arm_re.search(line), id_re.search(line)
            check(ma is not None and mi is not None, 'R50_ID_SCHEMA')
            key = ma.group(1), mi.group(1)
            if key not in entries:
                skipped += 1
                continue
            row, old = json.loads(line), entries[key]
            check(key not in control and row['candidateId'] == 'R50_A_LIFECYCLE' and
                  row['entryMinute'] == old['entryMinute'] and
                  abs(row['entryPrice'] - old['entryPrice']) < 1e-7 and
                  row['decisionNow'] == old['controlDecisionMinute'] and
                  row['exitMinute'] == old['controlExitMinute'] and
                  row['exitPrice'] == old['controlExitPrice'],
                  'R50_CALENDAR_OR_ENTRY_DIFFERENCE:' + key[1])
            check(row['decisionFacts']['maxKnownAt'] <= row['decisionNow'] and
                  row['decisionFacts']['maxBarEnd'] <= row['decisionNow'],
                  'R50_FUTURE_FACT:' + key[1])
            control[key] = row
    check(set(control) == set(entries), 'R50_INCOMPLETE')
    allowlist = {a: sorted([eid for arm, eid in entries if arm == ARM[a]]) for a in ARM}
    feature_registry = [
        {'name': 'currentReturnPct', 'source': 'fresh target close / effective Entry', 'class': 'B'},
        {'name': 'activeMinutesHeld', 'source': 'scheduled continuous-minute grid', 'class': 'B'},
        {'name': 'existingState', 'source': 'classify_state_v3 / saved checkpoint', 'class': 'C_SOURCE'},
        *[{'name': 'signal.' + f, 'source': 'phase57_entry_timing_signals.detect trigger',
           'class': 'C_SOURCE'} for f in ('CONTINUATION', 'BREAKOUT', 'COMPRESSION_EXPANSION',
                          'HIGHER_LOW', 'LOWER_WICK', 'RECLAIM')],
        {'name': 'currentBarVolume', 'source': 'raw 1m column 5', 'class': 'B'},
        {'name': 'currentBarValue', 'source': 'raw 1m column 6', 'class': 'B'},
        {'name': 'observedVWAPDistancePct', 'source': 'as-of raw price/volume; producer audit required',
         'class': 'C_SOURCE'},
    ]
    check(len(feature_registry) == 12, 'FEATURE_BUDGET')
    policy = {
        'family': 'R50_CAPPED_BY_FIRST_CLOSED_TARGET_V1', 'targetPct': TARGETS,
        'arms': list(ARM), 'entryScope': 'ALL_100_FROZEN_24_SESSION; funded subset same IDs',
        'firstDecision': 'fresh completed continuous one-minute CLOSE / effective Entry - 1 >= x',
        'choice': 'strictly before saved R50 decision and no preceding R50 pending; tie delegates',
        'fill': 'single exact next scheduled continuous OPEN, no retry; missing remains null',
        'terminal': 'R50 saved terminal, exact 15:30 auction only',
        'noTrigger': 'delegate fully to saved R50, including unresolved',
        'entryBarOwned': True, 'exitOpenBarHighLowOwned': False,
        'historicalKnownAt': 'bar start + 1 publication proxy',
        'cost': {'sellEntryNotionalRate': 0.0005,
                 'pnl': 'q * exactFillPrice - B * (1 + sellEntryNotionalRate)',
                 'entry': 'frozen effective paid price includes buy semantics'},
        'missingReference': 'TARGET_FIRST_REFERENCE_UNRESOLVED; no R50/zero/next seen substitute',
        'sameTimestamp': 'SAME_TIME_CONTROL_DELEGATION',
        'evaluationEndpoint': 'same-session continuous 15:25 decision and saved 15:30 auction; separate R50 horizon',
        'thresholdComparison': 'unrounded float price ratio, >=; report rounding only',
        'forbidden': ['CCMG_ON', 'EXTEND', 'fit', 'provider', 'protected', 'integratedCapitalReplay'],
        'safety': SAFETY,
    }
    budget = {'cycle': 'PROFIT_TARGET_EXTENSION_V1_DIAGNOSTIC', 'entryArms': list(ARM),
              'targets': TARGETS, 'focal': 3, 'newPolicyFamiliesImplemented': 1,
              'mainPolicyArmEvaluationsMax': 14,
              'independentIdenticalPolicyArmRecalculationsMax': 14,
              'totalRealDataPolicyArmEvaluationsMax': 28,
              'savedControlAccountingChecksMax': 2,
              'mainEvaluated': 0, 'auditRecalculated': 0,
              'fits': 0, 'ccmgHybrid': 0, 'extensionReplay': 0,
              'integratedCapitalReplays': 0, 'newProviderRequests': 0,
              'protectedPartitionOpenings': 0, 'externalLlmRequests': 0,
              'orders': 0, 'mainMerges': 0, 'formalSelectionAuthorized': False}
    bootstrap = {'unit': 'entry', 'cluster': 'session', 'sessions': parent['sessions'],
                 'replicates': 10000, 'seed': 20260929, 'bitGenerator': 'PCG64',
                 'quantiles': [0.025, 0.975], 'method': 'linear',
                 'draw': '24 session indices with replacement; all rows and arms together',
                 'emptyOrInvalid': 'count invalid; no zero imputation'}
    OUT.mkdir(parents=True)
    now = jst()
    write('START_AUDIT.json', {'basisHead': '6eb22edb57dab19d7d63ea9b71adc99a4a843ebc',
          'pr': 587, 'branch': 'research/phase57-long-only-cash-equity',
          'latestCheckedAtJst': now, 'previousCycle': 'A_PLUS_COMPLETE_WITH_BLOCKERS',
          'priorExposure': 'Development outcomes already inspected in Phase A/A+ and Capital integration',
          'duplicateCycleAtStart': False, 'newTargetPerformanceInspected': False})
    write('PRIOR_CYCLE_TRANSITION.json', {'priorOptionB': 'DESIGN_ONLY_EXPERIMENT_BLOCKED',
          'newPriority': 'DEPRIORITIZED_BY_OPERATOR',
          'experimentalDisposition': 'NOT_EXPERIMENTALLY_REJECTED',
          'phaseAReplayRetrospectiveChange': False, 'phaseAPlusRerun': False})
    write('SOURCE_MANIFEST.json', {'basisHead': '6eb22edb57dab19d7d63ea9b71adc99a4a843ebc',
          'pins': pins, 'integrationParentSourcePinsVerified': True,
          'integrationZipMemberHashesVerified': True,
          'priorAPlusSourceHashes': 'SOURCE_MANIFEST.json; parent pins separately verified',
          'r50OutsideAllowlistPayloadsSkippedBeforeJsonDecode': skipped,
          'rawAllowlistPayloadsDecoded': 0})
    write('ENTRY_ALLOWLIST.json', allowlist)
    write('POLICY_SPEC.json', policy)
    write('BUDGET_LEDGER.json', budget)
    write('BOOTSTRAP_SPEC.json', bootstrap)
    write('TARGET_FEATURE_REGISTRY.json', {'focalTargetPct': 3, 'primaryColumns': feature_registry,
          'associationSelectionAuthorized': False, 'valuesUnverifiedAtFreeze': True})
    rng = np.random.Generator(np.random.PCG64(20260929))
    draw = rng.integers(0, 24, (10000, 24), dtype=np.int16)
    np.savez_compressed(OUT / 'SESSION_DRAWS.npz', drawIndices=draw)
    bootstrap['numpyVersion'] = np.__version__
    bootstrap['drawSha256'] = digest(OUT / 'SESSION_DRAWS.npz')
    # The spec above is intentionally the fixed source for the draw definition.
    spec = {'schema': 'profit-target-extension-precommit-v1', 'createdJst': now,
            'basisHead': '6eb22edb57dab19d7d63ea9b71adc99a4a843ebc',
            'sourceManifestSha256': digest(OUT / 'SOURCE_MANIFEST.json'),
            'entryAllowlistSha256': digest(OUT / 'ENTRY_ALLOWLIST.json'),
            'policySpecSha256': digest(OUT / 'POLICY_SPEC.json'),
            'budgetSha256': digest(OUT / 'BUDGET_LEDGER.json'),
            'bootstrapSpecSha256': digest(OUT / 'BOOTSTRAP_SPEC.json'),
            'drawSha256': bootstrap['drawSha256'],
            'featureRegistrySha256': digest(OUT / 'TARGET_FEATURE_REGISTRY.json'),
            'entryIds': {a: len(allowlist[a]) for a in ARM},
            'fundedIds': {a: len(ledgers[a]['funded']) for a in ARM},
            'r50IdentityAndClockVerified': True, 'targets': TARGETS,
            'arms': list(ARM), 'bootstrap': bootstrap,
            'priorOutcomesExposed': True, 'newTargetOutcomesComputed': False,
            'missingHandling': 'UNKNOWN stays null; no imputation or favorable-order assumption'}
    write('MEASUREMENT_PRECOMMIT.json', spec)
    (OUT / 'MEASUREMENT_PRECOMMIT.sha256').write_text(
        digest(OUT / 'MEASUREMENT_PRECOMMIT.json') + '  MEASUREMENT_PRECOMMIT.json\n')
    print(json.dumps({'status': 'FROZEN_BEFORE_NEW_TARGET_PERFORMANCE',
                      'precommitSha256': digest(OUT / 'MEASUREMENT_PRECOMMIT.json'),
                      'entryIds': spec['entryIds'], 'fundedIds': spec['fundedIds'],
                      'r50Skipped': skipped, 'createdJst': now}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true', required=True)
    args = parser.parse_args()
    freeze()
