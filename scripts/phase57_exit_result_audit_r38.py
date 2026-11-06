"""Read-only R36 artifact audit and owned-metric erratum; never fit or replay policy.

R36 remains immutable. Only ownedPeakGivebackPp is repaired from the frozen R20
completed prefix, at the already-recorded execution's unique decision endpoint.
No estimator, prediction, entry, decision, execution, cost, gate or grid changes.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scripts import phase57_exit_finite_r36 as frozen
from scripts.phase57_exit_capture_metrics_v1 import evaluate_capture

ZIP_SHA = '1c574848c6106d34c1d53e902b339e1be2f43b7b5c615e40a7010c29332d997a'
SOURCE_SHA = '4c9c9e9bd7e1caa382745d96c1facc0ac0eb12392ba7c881ae01aada9d0a662d'


def read_rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def decision_now(row):
    if row['exitKind'] == 'FORCED_TERMINAL':
        frozen.require(row['exitMinute'] == 930, 'TERMINAL_GEOMETRY')
        return 925
    frozen.require(row['exitKind'] == 'MODEL_EXIT', 'UNKNOWN_EXIT_KIND')
    start = row['exitMinute']
    now = 690 if start == 750 else start
    frozen.require(frozen.execution.next_execution_start(row['session'], now) == start,
                   'EXECUTION_DECISION_INVERSE')
    return now


def corrected_row(row, path):
    result = copy.deepcopy(row)
    if row['exitStatus'] != 'RESOLVED':
        frozen.require(row['metrics']['ownedPeakGivebackPp'] is None, 'UNRESOLVED_OWNED')
        return result
    now = decision_now(row)
    prefix = frozen.r20.closed_prefix(row['session'], now, path)
    entry = dict(session=row['session'], entryId=row['entryId'],
                 entryMinute=row['entryMinute'], price=row['entryPrice'])
    pos = frozen.r20.position_features(entry, now, prefix)
    # Preserve R36 float32 transport precision; convert back to a Python scalar
    # before R21's strict numeric boundary. No missing value is synthesized.
    peak = pos['observedRunningHigh']
    at = pos['peakConfirmedAt']
    if peak is not None:
        peak = float(np.float32(peak))
        at = int(np.float32(at))
    metric = evaluate_capture(entry_price=row['entryPrice'],
        entry_minute=row['entryMinute'], exit_price=row['exitPrice'],
        exit_minute=row['exitMinute'], cost_pp=.05, geometry=None, owned_peak=peak,
        owned_peak_confirmed_at=at, owned_path_complete=pos['fullOwnedPrefix'])
    result['metrics']['ownedPeakGivebackPp'] = metric['ownedPeakGivebackPp']
    check = copy.deepcopy(result)
    check['metrics']['ownedPeakGivebackPp'] = row['metrics']['ownedPeakGivebackPp']
    frozen.require(check == row, 'NON_OWNED_FIELD_CHANGED')
    return result


def verify_artifact(root, archive):
    frozen.require(frozen.sha(archive) == ZIP_SHA, 'ARCHIVE_SHA')
    receipt = frozen.read_json(root / 'receipt.json')
    fit = frozen.read_json(root / 'fit-receipt.json')
    selection = frozen.read_json(root / 'run-a/selection.json')
    frozen.require(frozen.sha(Path(frozen.__file__)) == SOURCE_SHA == receipt['sourceSha256'],
                   'FROZEN_RUNNER_CHANGED')
    hashes = frozen.tree_hashes(root / 'run-a')
    frozen.require(hashes == frozen.tree_hashes(root / 'run-b') == receipt['runAHashes'],
                   'RUN_AB_OR_MANIFEST_DRIFT')
    frozen.require(len(hashes) == 50, 'RUN_FILE_COUNT')
    frozen.require(receipt['modelFits'] == fit['modelFits'] == len(fit['models']) == 144,
                   'MODEL_COUNT')
    frozen.require(receipt['candidatePoliciesReplayed'] == len(selection['candidates']) == 24,
                   'POLICY_COUNT')
    frozen.require([r['configuration'] for r in selection['candidates']] ==
                   frozen.r25.candidate_grid(), 'GRID_DRIFT')
    frozen.require(frozen.sha(root / 'oof-predictions.npz') ==
                   receipt['predictionSha256'] == fit['predictionSha256'], 'PREDICTION_SHA')
    for model in fit['models']:
        frozen.require(frozen.sha(root / 'models' / model['file']) == model['sha256'], 'MODEL_SHA')
    for report in (receipt, fit, selection):
        frozen.require(report['providerRequests'] == report['protectedPartitionsOpened'] == 0,
                       'EXPOSURE_BOUNDARY')
        frozen.require(report['safety'] == frozen.SAFETY, 'SAFETY')
    frozen.require(receipt['status'] == selection['selection']['outcome'] == 'NO_SELECTION_STOP',
                   'STOP_RESULT_DRIFT')
    frozen.require(all(r['gate']['arms'][arm]['primaryMeanNetGate']['mean'] < 2
                       for r in selection['candidates'] for arm in frozen.ARMS),
                   'PRIMARY_STOP_NOT_INDEPENDENT_OF_OWNED_ERRATUM')
    return receipt, fit, selection


def correction_pass(root, out, raw, records, selection):
    out.mkdir()
    cache = {}
    def correct(rows):
        result = []
        for row in rows:
            key = (row['entryArm'], row['entryId'], row['exitKind'], row['exitMinute'])
            if key not in cache:
                cache[key] = corrected_row(row, raw[row['opportunity']]['today'])['metrics']['ownedPeakGivebackPp']
            item = copy.deepcopy(row)
            item['metrics']['ownedPeakGivebackPp'] = cache[key]
            result.append(item)
        return result
    neutral = correct(read_rows(root / 'run-a/neutral-hold-terminal.jsonl.gz'))
    frozen.write_jsonl_gz(out / 'neutral-hold-terminal.jsonl.gz', neutral)
    results, report = [], []
    for original in selection['candidates']:
        cid = original['candidateId']
        before = read_rows(root / 'run-a/ledgers' / (cid + '.jsonl.gz'))
        rows = correct(before)
        card = frozen.full_scorecard(rows, SimpleNamespace(opportunity_records=records))
        old_card = frozen.read_json(root / 'run-a/scorecards' / (cid + '.json'))
        for arm in frozen.ARMS:
            frozen.require(card['overall'][arm]['returnRisk'] == old_card['overall'][arm]['returnRisk'],
                           'RETURN_CHANGED')
        gate = frozen.gate_candidate(rows, neutral, original['configuration'])
        results.append(dict(original, gate=gate))
        frozen.write_json(out / 'scorecards' / (cid + '.json'), card)
        frozen.write_jsonl_gz(out / 'ledgers' / (cid + '.jsonl.gz'), rows)
        report.append({'candidateId':cid, 'configuration':original['configuration'],
            'pass':bool(gate['pass']), 'arms':{arm:{
                'net':card['overall'][arm]['returnRisk'],
                'filledN':card['overall'][arm]['filledN'],
                'resolvedN':card['overall'][arm]['resolvedN'],
                'censoredN':card['overall'][arm]['censoredN'],
                'ownedMetricN':card['overall'][arm]['metrics']['ownedPeakGivebackPp']['n'],
                'failedGates': ([k for k in ('winner','retention','loss','concentration')
                                if not gate['arms'][arm][k]['pass']] +
                    (['primaryMeanNet'] if gate['arms'][arm]['primaryMeanNetGate']['mean'] < 2 else []) +
                    (['coverage'] if gate['arms'][arm]['coverage'] < .95 else []) +
                    (['cost10'] if gate['arms'][arm]['cost10']['profitFactor'] is None or
                        gate['arms'][arm]['cost10']['profitFactor'] < 1 else []) +
                    (['cost20'] if gate['arms'][arm]['cost20']['profitFactor'] is None or
                        gate['arms'][arm]['cost20']['profitFactor'] < .95 else []) +
                    ['bucket:'+b for b,v in gate['arms'][arm]['bucketGates'].items() if not v['pass']])
            } for arm in frozen.ARMS}})
    outcome = frozen.rank_selection(results)
    frozen.require(outcome == selection['selection'], 'CORRECTION_CHANGED_STOP')
    frozen.write_json(out / 'selection.json', {'selection':outcome,'candidates':results})
    frozen.write_json(out / 'candidate-summary.json', report)
    return report


def run(root, archive, out):
    frozen.require(not out.exists(), 'APPEND_ONLY_OUTPUT_EXISTS')
    receipt, fit, selection = verify_artifact(root, archive)
    for path, expected in ((frozen.RAW_PATHS, frozen.RAW_PATHS_SHA256),
                           (frozen.OPPORTUNITY_RECORDS, frozen.OPPORTUNITY_RECORDS_SHA256)):
        frozen.require(frozen.sha(path) == expected, 'PINNED_SOURCE_SHA')
    records = {r['opportunity']:r for r in frozen.read_json(frozen.OPPORTUNITY_RECORDS)}
    frozen.require(len(records) == 2155, 'COHORT_COUNT')
    raw = frozen.read_json(frozen.RAW_PATHS)
    out.mkdir(parents=True)
    report = correction_pass(root, out / 'run-a', raw, records, selection)
    correction_pass(root, out / 'run-b', raw, records, selection)
    hashes = frozen.tree_hashes(out / 'run-a')
    frozen.require(hashes == frozen.tree_hashes(out / 'run-b'), 'ERRATUM_AB_MISMATCH')
    audit = {'schema':'phase57-r38-result-audit-v1', 'outcome':'NO_SELECTION_STOP',
        'artifactId':10901042535,'runId':36222151340,'artifactSha256':ZIP_SHA,
        'executionHead':'a10b3f25f79f8221c9a71c1b3ede245777bce058',
        'originalRunABFilesVerified':50,'modelHashesVerified':144,
        'originalModelFits':144,'originalPolicies':24,
        'additionalFits':0,'additionalPolicyReplays':0,'portfolioReplays':0,
        'correction':'OWNED_METRIC_NUMPY_FLOAT32_TO_PYTHON_SCALAR_ONLY',
        'decisionExecutionAndReturnUnchanged':True,'correctedRunABByteIdentical':True,
        'correctedHashes':hashes,'passingCandidates':0,'primaryGatePassesAcross48ArmCases':0,
        'sourceSha256':frozen.sha(Path(__file__)),
        'providerRequests':0,'protectedPartitionsOpened':0,'safety':frozen.SAFETY}
    frozen.write_json(out / 'audit.json', audit)
    # Compact original receipts retain the unmodified result and all model hashes.
    frozen.write_json(out / 'original-receipt.json', receipt)
    frozen.write_json(out / 'original-fit-receipt.json', fit)
    frozen.write_json(out / 'original-selection.json', selection)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root,args.archive,args.out),sort_keys=True))
