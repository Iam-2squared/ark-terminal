"""R45 evaluator/selection only, invoked in the NEXT Work after artifact audit.

This module is not imported or called by the finite learning workflow. The
numeric R25/R31 gates are unchanged; the explicit R45 rank-tie rule is new.
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

from scripts import phase57_exit_finite_r36 as frozen
from scripts.phase57_exit_gen3_runtime_r45 import load_protocol, PROTOCOL_SHA256


def select_from_gates(results):
    protocol = load_protocol()
    expected = {c['candidateId'] for c in protocol['candidates']}
    frozen.require(len(results) == len(expected)
                   and {r['candidateId'] for r in results} == expected, 'R45_ALL_4_REQUIRED')
    passing = [r for r in results if r['gate']['pass'] is True]
    if not passing:
        return {'outcome': 'NO_SELECTION_STOP', 'selectedCandidateId': None,
                'reason': 'NO_CANDIDATE_PASSED_ALL_FROZEN_GATES'}
    axes = ('winner', 'retention', 'loss')
    frozen.require(all(type(r['gate']['capabilityMargins'][a]) in (int, float)
                       and math.isfinite(r['gate']['capabilityMargins'][a])
                       for r in passing for a in axes), 'R45_NONFINITE_PASS_MARGIN')
    axis_values = {a: sorted({r['gate']['capabilityMargins'][a] for r in passing}, reverse=True)
                   for a in axes}
    ranked = []
    for row in passing:
        ranks = {a: axis_values[a].index(row['gate']['capabilityMargins'][a]) + 1 for a in axes}
        ranked.append((max(ranks.values()), sum(ranks.values()), row, ranks))
    best_key = min((r[0], r[1]) for r in ranked)
    best = [r for r in ranked if (r[0], r[1]) == best_key]
    if len(best) != 1:
        return {'outcome': 'NO_SELECTION_STOP', 'selectedCandidateId': None,
                'reason': 'BEST_WORST_RANK_AND_RANK_SUM_TIE',
                'tiedCandidateIds': sorted(r[2]['candidateId'] for r in best)}
    _, _, row, ranks = best[0]
    return {'outcome': 'SELECT', 'selectedCandidateId': row['candidateId'],
            'capabilityRanks': ranks, 'capabilityMargins': row['gate']['capabilityMargins']}


def _rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def score_audited_artifact(root: Path, audit: dict, data, out: Path):
    """Post-run function. Caller must supply the independently verified audit.

    The audit identifies all source ledgers; no model is fitted or policy replayed.
    `data` needs only the pinned opportunity_records for population accounting.
    """
    frozen.require(audit.get('status') == 'GEN3_ARTIFACT_AUDIT_PASS'
                   and audit.get('protocolSha256') == PROTOCOL_SHA256,
                   'R45_POST_RUN_INDEPENDENT_AUDIT_REQUIRED')
    frozen.require(not out.exists(), 'APPEND_ONLY_OUTPUT_EXISTS')
    protocol = load_protocol()
    for name, expected in protocol['baselineSourceHashes'].items():
        frozen.require(frozen.sha(frozen.ROOT / name) == expected, 'R45_BASELINE_SOURCE_DRIFT:' + name)
    ledger_paths = [f'{run}/{c["candidateId"]}.jsonl.gz'
                    for run in ('run-a', 'run-b') for c in protocol['candidates']]
    ledger_paths += [f'{run}/HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz' for run in ('run-a', 'run-b')]
    for name in ledger_paths:
        frozen.require(audit['inputLedgerHashes'].get(name) == frozen.sha(root / name),
                       'R45_AUDITED_LEDGER_IDENTITY:' + name)
    out.mkdir(parents=True)
    decisions = []
    for run in ('run-a', 'run-b'):
        neutral = _rows(root / run / 'HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz')
        results = []
        for config in protocol['candidates']:
            cid = config['candidateId']
            rows = _rows(root / run / (cid + '.jsonl.gz'))
            frozen.require(all(row['candidateId'] == cid for row in rows), 'R45_LEDGER_CANDIDATE_ID')
            card = frozen.full_scorecard(rows, data)
            gate = frozen.gate_candidate(rows, neutral, config)
            frozen.write_json(out / run / 'scorecards' / (cid + '.json'), card)
            results.append({'candidateId': cid, 'configuration': config, 'gate': gate})
        result = {'selection': select_from_gates(results), 'candidates': results}
        frozen.write_json(out / run / 'selection.json', result)
        decisions.append(result['selection'])
    hashes_a, hashes_b = frozen.tree_hashes(out / 'run-a'), frozen.tree_hashes(out / 'run-b')
    frozen.require(hashes_a == hashes_b and decisions[0] == decisions[1], 'R45_SCORE_AB_MISMATCH')
    receipt = {'schemaVersion': 'phase57-gen3-audited-scorecard-r45-v1',
               'protocolSha256': PROTOCOL_SHA256, 'selection': decisions[0],
               'candidateCount': 4, 'modelFitsPerformed': 0, 'policyReplaysPerformed': 0,
               'scorecardRunABByteIdentical': True, 'scoreHashes': hashes_a,
               'providerRequests': 0, 'protectedPartitionsOpened': 0, 'safety': frozen.SAFETY,
               'exitFreezeCreated': False, 'capitalPortfolioReplays': 0}
    frozen.write_json(out / 'receipt.json', receipt)
    return receipt
