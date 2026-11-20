"""Package private row-level research evidence, excluding Git-backed source/reports."""
import gzip
import json
import zipfile
from pathlib import Path
from settings import HERE, INPUT, PRIVATE, SAFETY, WORKSPACE, entries, jsonline, load, now, save, sha

NAME = 'Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip'

def main():
    if load(HERE/'INDEPENDENT_AUDIT.json')['mismatch_N'] != 0:
        raise SystemExit('Cannot package failed audit')
    selected = {r['watch_key'] for r in entries()}
    root = PRIVATE/'PACKAGE_INPUTS'
    root.mkdir(parents=True, exist_ok=True)
    input_members = {}
    for name in ['raw_paths_selected.json.gz', 'PRIVATE_SELECTED_SOURCE_TOKENS.json.gz']:
        source = INPUT/'base'/name
        mapping = {k:v for k,v in load(source).items() if k in selected}
        assert set(mapping) == selected
        dest = root/name
        with dest.open('wb') as out, gzip.GzipFile(fileobj=out, mode='wb', mtime=0) as gz:
            gz.write(jsonline(mapping))
        input_members['SAVED_INPUTS/'+name] = {
            'selection': 'all and only the unchanged 1600 Frozen Entry watch keys',
            'source_sha256': sha(source), 'subset_sha256': sha(dest), 'N': len(mapping),
            'values_changed': 0,
        }
    components = []
    for receipt in load(PRIVATE/'TRACE_RECEIPTS.json'):
        trace = PRIVATE/'FULL_TRACE'/(receipt['watch_key'].replace('|','_')+'.jsonl.gz')
        assert sha(trace) == receipt['trace_sha256']
        components.append(('FULL_TRACE/'+trace.name, trace))
    assert len(components) == 1600
    for name in ['TRACE_RECEIPTS.json', 'REPLAY_ROWS.jsonl.gz', 'ECONOMICS_ROWS.jsonl.gz']:
        components.append((name, PRIVATE/name))
    components.append(('FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz', INPUT/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'))
    components.extend(('SAVED_INPUTS/'+n, root/n) for n in ['raw_paths_selected.json.gz','PRIVATE_SELECTED_SOURCE_TOKENS.json.gz'])
    manifest = {
        'saved_at_jst': now(), 'document_id': 'WORK_STATE9_STRUCTURAL_EXIT_V2_20261003',
        'package_type': 'PRIVATE_RESEARCH_EVIDENCE', 'Entry_N': 1600,
        'trace_slots_N': 523200, 'trace_gzip_containers_N': 1600,
        'code_repository': 'Iam-2squared/ark-terminal',
        'code_branch': 'state9-structural-exit-v2-20261003',
        'code_path': 'research/state9-structural-exit-v2-20261003/',
        'code_basis_head_actual_GET': load(HERE/'S2_HEAD_GET_RECEIPT.json')['actual_head'],
        'code_final_checkpoint': 'FINAL_AUDIT_AND_EVIDENCE; use actual commit returned after final save',
        'source_packages': load(HERE/'IDENTITY_RECEIPT.json')['base_package_SHA256'],
        'input_subset_provenance': input_members,
        'historical_actual_known_at': 'UNKNOWN; assumed available_at=bar_end',
        'post_exit_full_trace_and_high': 'evaluation evidence only; position decisions stop at first valid intent',
        'private_row_level_evidence_publication': False, 'safety': SAFETY,
        'components': {name:{'sha256':sha(path),'bytes':path.stat().st_size} for name,path in components},
    }
    save(root/'MANIFEST.json', manifest)
    readme = (
        'STATE9_STRUCTURAL_EXIT_V2 private evidence\n\n'
        '1600 exact full trace files, 1600 position replay/economics rows, original Frozen Entry gzip bytes, '
        'and saved raw/M0 source subsets. No new data, teacher/model or old EXIT data is included.\n'
        'Public code, reports, frozen kernels and independent audit are in the named Git branch. '
        'Use the FINAL_AUDIT_AND_EVIDENCE commit actual GET, not a fabricated future SHA.\n'
        'MANIFEST.json gives every component SHA and source-subset provenance. '
        'Entry gzip contains the original 2155 watch rows; entry_status=FIRST_ENTRY selects the unchanged 1600.\n'
        'For full saved-overlap reconstruction and the independent exact original-package identity check, '
        'the two pre-existing source archives listed in the Git README are also required. '
        'They are available as previously saved files.\n'
        'Historical market arrival time is UNKNOWN; causal verification is under the stated bar_end assumption. '
        'Observed High is not a complete-session High where source is incomplete. '
        'UNRESOLVED remains explicit; last-observed Close is never substituted.\n'
    )
    target = WORKSPACE/NAME
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for name,path in components:
            archive.write(path, name)
        archive.write(root/'MANIFEST.json', 'MANIFEST.json')
        archive.writestr('README.txt', readme)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(components)+2
        for name,path in components:
            import hashlib
            digest = hashlib.sha256(archive.read(name)).hexdigest()
            assert digest == manifest['components'][name]['sha256']
    receipt = {'saved_at_jst':now(),'filename':NAME,'bytes':target.stat().st_size,
        'sha256':sha(target),'zip_crc_all_pass':True,'component_sha256_all_pass':True,
        'private_data_components_N':len(components),'Entry_N':1600,'trace_files_N':1600,
        'trace_slots_N':523200,'public_code_reports_duplicated':False,'safety':SAFETY}
    save(HERE/'PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json',receipt)
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
