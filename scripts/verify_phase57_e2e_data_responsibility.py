#!/usr/bin/env python3
"""Read-only, stdlib metadata checks. Never imports research models or providers."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-long-only-e2e-data-responsibility'


def main():
    contract = json.loads((BASE / 'responsibility-budget-contract.json').read_text())
    blocks = {b['blockId']: b for b in contract['acquisitionBlocks']}
    budget = contract['globalBudget']
    checks = {}

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks[name] = 'PASS'

    check('unique_blocks', len(blocks) == len(contract['acquisitionBlocks']) == 8)
    check('fixed_block_sizes', {k: v['sessions'] for k, v in blocks.items()} ==
          {'DEV': 76, 'A': 30, 'B': 30, 'C': 30, 'D': 30, 'E': 20, 'F': 30, 'G': 25})
    role_counts = collections.Counter()
    for row in contract['responsibilityMatrix']:
        check('row_' + row['stage'], sum(blocks[b]['sessions'] for b in row['blocks']) == row['minimumSessions'])
        role_counts.update(row['blocks'])
    check('only_declared_sharing', dict(role_counts) ==
          {'DEV': 3, 'A': 1, 'B': 1, 'C': 1, 'D': 1, 'E': 3, 'F': 1, 'G': 1})
    check('gross_count', sum(b['sessions'] * role_counts[k] for k, b in blocks.items()) == budget['grossSessionRoleCount'] == 463)
    check('net_count', sum(b['sessions'] for b in blocks.values()) == budget['netUniqueAllSessions'] == 271)
    check('fresh_shortage', sum(b['sessions'] for k, b in blocks.items() if k != 'DEV') ==
          budget['netUniqueFreshSessions'] == budget['newFreshShortage'] == 195)
    check('reuse_deduction', 463 - 152 - 40 == 271 and 271 - 76 == 195)
    check('event_floor_net', sum(b['minimumDistinctFirstEntryEvents'] or 0 for b in blocks.values()) == budget['netApplicableDistinctEventFloors'] == 491)
    check('event_floor_gross', sum(b['minimumDistinctFirstEntryEvents'] or 0 for row in contract['responsibilityMatrix'] for b in [blocks[row['blocks'][-1]]]) == budget['grossApplicableDistinctEventFloors'] == 685)
    check('no_new_dates', all(b['actualNewSessionAllocation'] == [] for b in blocks.values()))
    check('development_identity', len(contract['existingDevelopmentIdentity']['trainingSessions']) == 76 and
          len(set(contract['existingDevelopmentIdentity']['trainingSessions'])) == 76)
    dates = contract['existingDevelopmentIdentity']['trainingSessions']
    digest = hashlib.sha256(json.dumps(dates, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    check('development_session_hash', digest == contract['existingDevelopmentIdentity']['sessionListSha256'])
    check('unknown_excluded', contract['existingCounts']['UNKNOWN'] == 101 and contract['existingUsableFreshSessions'] == [])
    check('future20_not_credited', contract['future20Allocation']['newLongCredit'] == 0 and contract['future20Allocation']['unchanged'])
    check('safety', all(v is False for v in contract['safety'].values()))
    check('incident_not_hidden', contract['counts']['outcomeDerivedMetadataDisplay'] == 1 and not contract['globalBudgetFrozen'] and contract['globalBudgetContractSha256'] is None)
    check('no_unresolved_session_budget', contract['remainingUnresolvedSessionBudgets'] == [])
    check('no_execution', all(v == 0 for k, v in contract['counts'].items() if k != 'outcomeDerivedMetadataDisplay'))
    conservation = json.loads((BASE / 'conservation-table.json').read_text())
    for row in conservation:
        check('remaining_' + row['checkpoint'], row['remainingFreshSessionsDesign'] == sum(blocks[b]['sessions'] for b in row['remainingBlocks']))
    check('no_event_based_expansion', 'no extra sessions' in contract['budgetDerivation']['shortfallHandling'])
    check('independence_qualification', 'NOT an IID sample' in contract['budgetDerivation']['dependence'])
    expected = json.loads((BASE / 'protected-hash-verification.json').read_text())
    for path, record in expected.items():
        if path == 'selectorPayloadSha256':
            payload = json.loads((ROOT / 'predict/research/phase57-long-only-frozen-selector-v1.json').read_text())['freezePayload']
            raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        else:
            raw = (ROOT / path).read_bytes()
        check('hash_' + path, hashlib.sha256(raw).hexdigest() == record['expected'])
    print(json.dumps({'scope': 'READ_ONLY_METADATA_INTEGRITY_NOT_OUTCOME_BLIND_FREEZE_APPROVAL',
                      'total': len(checks), 'pass': len(checks), 'fail': 0, 'skip': 0,
                      'checks': checks, 'globalFreezeEligible': False,
                      'blocker': 'OUTCOME_BLIND_METADATA_DISPLAY_VIOLATION'}, indent=2))


if __name__ == '__main__':
    main()
