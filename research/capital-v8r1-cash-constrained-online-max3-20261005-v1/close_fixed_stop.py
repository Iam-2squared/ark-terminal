"""Final static freeze verification and append-only closure. No research execution."""
from control import *
import ast
import subprocess


def main():
    authority = read(OUT / 'AUTHORITY_FREEZE.json')
    source = read(OUT / 'INPUT_BYTE_FREEZE.json')
    claim = read(OUT / 'MAIN_REPLAY_CLAIM.json')
    selection = read(OUT / 'WINNER_AND_NEXT_BOTTLENECK.json')
    audit = read(OUT / 'INDEPENDENT_AUDIT.json')
    assert audit['status'] == 'PASS' and audit['mismatch_N'] == 0
    for name, expected in authority['sha256'].items():
        assert sha(ROOT / name) == expected, 'FROZEN_AUTHORITY_CHANGED_STOP: ' + name
    for row in source['files']:
        assert sha(PRIOR / row['path']) == row['sha256'], 'FROZEN_BYTE_CHANGED_STOP'
    for name, expected in claim['code_sha256'].items():
        assert sha(CODE / name) == expected, 'POST_MAIN_RUNTIME_CHANGED_STOP: ' + name
    for name, expected in claim['table_sha256'].items():
        assert sha(OUT / name) == expected, 'COMPLETED_TABLE_CHANGED_STOP: ' + name
    for arm in ARMS:
        result = read(OUT / f'{arm}_RESULT.json')
        assert result['valid_primary_day_N'] == 38 and result['blocked_execution_day_N'] == 0
        assert result['execution_source_unresolved_N'] == 0
        assert len(result['daily_series']) == 38 and all(d['status'] == 'COMPLETE' for d in result['daily_series'])
        assert (PRIVATE / f'{arm}_STARTED.json').exists()
        for kind, expected in result['ledger_sha256'].items():
            assert sha(PRIVATE / f'{arm}_{kind}.jsonl.gz') == expected, 'COMPLETED_LEDGER_CHANGED_STOP'
    assert selection['status'] == 'V8R1_NO_GO' and selection['selectedCapitalCandidate'] is None
    assert selection['diagnosticArm'] == ARMS[1] and selection['NEXT_BOTTLENECK'] == 'CAPACITY_RESERVE'
    diagnostic = read(OUT / 'PPRANK_CASH_DIAGNOSTIC_RESULT.json')
    assert diagnostic['status'] == 'CERTIFIED' and diagnostic['primary_execution_package_N'] == 1
    assert read(OUT / 'PPRANK_INDEPENDENT_AUDIT.json')['mismatch_N'] == 0
    assert read(OUT / 'CAUSAL_CANARY_RESULTS.json')['PASS_N'] == 43
    receipt = read(OUT / 'PRIVATE_DELIVERY_RECEIPT.json')
    pack = read(OUT / 'PRIVATE_PACK_MANIFEST.json')
    assert receipt['save_status'] == 'succeeded' and receipt['all_returned_xattrs_applied']
    assert receipt['sha256'] == pack['sha256'] == sha(ROOT.parent / 'deliverables' / pack['filename'])
    assert pack['readback_all_member_hashes_PASS'] and not pack['contains_repository_backed_code_reports']
    for path in CODE.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    # Path-only comparison. No protected/fresh/OOS source contents are opened.
    base = '54722d28a81532279616ee50b62ac625d46871f0'
    basis = read(WORK / 'latest_basis.json')
    fetched = subprocess.check_output(['git', 'rev-parse', 'FETCH_HEAD'], cwd=ROOT, text=True).strip()
    assert fetched == basis['HEAD'], 'FETCHED_BRANCH_NOT_CURRENT_BASIS_STOP'
    changed = subprocess.check_output(['git', 'diff', '--name-status', base, fetched], cwd=ROOT, text=True).splitlines()
    prefixes = (str(OUT.relative_to(ROOT)) + '/', str(CODE.relative_to(ROOT)) + '/')
    assert all(line.startswith('A\t') and line.split('\t', 1)[1].startswith(prefixes) for line in changed)
    old_v8 = read(V8 / 'CLOSURE.json')
    assert old_v8['status'] == 'V8_CONTRACT_FAIL' and old_v8['CURRENT_STATE'] == 'CAPITAL_V8_D16_CLOSURE_FIXED_STOP'
    static = {'exact_jst': now(), 'status': 'PASS', 'basis_HEAD': basis['HEAD'], 'basis_tree': basis['tree'],
              'frozen_authority_hash_N': len(authority['sha256']), 'frozen_input_byte_hash_N': len(source['files']),
              'fetched_new_cycle_add_only_path_N': len(changed), 'old_evidence_modified_N': 0,
              'post_Main_runtime_or_table_changes': 0, 'completed_ledger_hashes_exact': True,
              'Python_AST_syntax_PASS': True, 'private_delivery_hash_exact': True,
              'old_v8_remains_fixed_contract_fail': True, 'independent_mismatch': 0,
              'research_reruns_from_this_static_audit': 0, 'Safety': SAFETY}
    save(OUT / 'CLOSURE_STATIC_SCOPE_AUDIT.json', static)
    save(OUT / 'NEXT_WORK_HANDOFF.json', {
        'exact_jst': now(), 'status': selection['status'], 'selectedRankCandidate': 'EXISTING_MOVE_P5',
        'selectedCapitalCandidate': None, 'retainedCapitalBenchmark': 'V5_FROZEN_REFERENCE',
        'diagnosticArm': selection['diagnosticArm'], 'NEXT_BOTTLENECK': selection['NEXT_BOTTLENECK'],
        'observed_U5_gaps': selection['observed_U5_exclusive_gaps'],
        'Physical_U5_Oracle': 149, 'Admission_U5_Oracle': 116, 'B2_U5_funded': 47,
        'physical_unavoidable': 21, 'admission_ceiling_loss': 33, 'Admission_Oracle_to_runtime_gap': 69,
        'pP_clairvoyant_U5_is_not_upper_bound': True, 'permanent_freeze': ['Selector', 'Entry', 'EXIT'],
        'Rank_admission_sizing_change_this_cycle': False, 'next_work_requires_independent_new_instruction': True,
        'no_automatic_Admission_research': True, 'same_cycle_B3_or_retune_allowed': False,
        'private_filename': pack['filename'], 'private_sha256': pack['sha256'],
        'private_delivery_receipt': 'PRIVATE_DELIVERY_RECEIPT.json',
        'counts': selection['counts'], 'Exposure': 'ITERATIVE_DEVELOPMENT_EVIDENCE',
        'fresh_OOS_claim': False, 'productionReady': False, 'Safety': SAFETY})
    closure = {'exact_jst': now(), 'branch': BRANCH, 'basis_HEAD': basis['HEAD'], 'basis_tree': basis['tree'],
               'CURRENT_STATE': 'CAPITAL_V8R1_R15_CLOSURE_FIXED_STOP', 'status': selection['status'],
               'selectedRankCandidate': 'EXISTING_MOVE_P5', 'selectedCapitalCandidate': None,
               'retainedCapitalBenchmark': 'V5_FROZEN_REFERENCE', 'diagnosticArm': selection['diagnosticArm'],
               'NEXT_BOTTLENECK': selection['NEXT_BOTTLENECK'], 'closed': True, 'fixed_stop': True,
               'resume_same_cycle_allowed': False, 'additional_research_allowed': False,
               'old_v8_cycle_resumed': False, 'old_records_rewritten': False,
               'cash_diagnostic_status': diagnostic['status'], 'independent_mismatch': 0,
               'causal_canary_PASS_N': 43, 'Primary_B1_B2_replays': 2,
               'report_sha256': sha(OUT / 'REPORT_FINAL-ja.md'),
               'selection_sha256': sha(OUT / 'WINNER_AND_NEXT_BOTTLENECK.json'),
               'static_scope_sha256': sha(OUT / 'CLOSURE_STATIC_SCOPE_AUDIT.json'),
               'handoff_sha256': sha(OUT / 'NEXT_WORK_HANDOFF.json'),
               'private_sha256': pack['sha256'], 'counts': selection['counts'],
               'post_closure_allowed': 'actual GET receipts / static path-and-byte verification / local git fast-forward only; no research',
               'Exposure': 'ITERATIVE_DEVELOPMENT_EVIDENCE', 'fresh_OOS_claim': False,
               'productionReady': False, 'Safety': SAFETY}
    save(OUT / 'CLOSURE.json', closure)
    checkpoint('R15_CLOSURE_FIXED_STOP', closure['CURRENT_STATE'],
               ['R0–R14', 'Report/private delivery', 'final static freeze verification', 'independent mismatch=0'],
               {'status': closure['status'], 'selectedCapitalCandidate': None,
                'NEXT_BOTTLENECK': closure['NEXT_BOTTLENECK'], 'fixed_stop': True},
               'STOP; actual GET receipt and byte/path verification only; no B3/retune/replay/fit', selection['counts'])
    print(json.dumps({'status': closure['status'], 'CURRENT_STATE': closure['CURRENT_STATE'],
                      'static_scope_PASS': True, 'authority_N': len(authority['sha256']), 'input_N': len(source['files'])}))


if __name__ == '__main__':
    main()
