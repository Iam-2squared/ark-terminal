"""Package fixed V3 evidence. No acquisition, labels, fitting, or new draws."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, base64, copy, csv, hashlib, io, json, os, re, subprocess, zipfile

R = Path(__file__).resolve().parent
REPO = 'Iam-2squared/ark-terminal'
PREFIX = 'research/state-reversal-v3-20261002'
V2_SHA = '85662d3890178e74aae36994bdcc51ff488d01f672fd27394bcf49c26b282d63'
OOF_SHA = '2b13dd18c80723dc2ab4838e62c6804d4e999b94f3019c8a54d71e0f7d4b87fe'
REQUIRED = '''00_README.txt PREDICTIVENESS_V3_REVERSAL_CONTRACT.md
PREDICTIVENESS_V3_REVERSAL_PRECOMMIT.json FROZEN_IDENTITY_RECEIPT.json
DEVELOPMENT_COMPLETION_LEDGER.csv UNAVAILABLE_INPUTS.csv DATA_SCOPE_V3.json
V1_V2_EXPOSED_DEV.json V3_NEW_DEV_EVAL.json DATASET_MANIFEST.json
REVERSAL_TARGET_SCHEMA.json FEATURE_SCHEMA_V3.json SPLIT_PLAN_V3.json
SPLIT_REALIZED_V3.json FIT_INDEX_V3.json MODEL_EXECUTION_LEDGER.jsonl
OOF_ALL.jsonl CONTEXT_REVERSAL_OOF_PREDICTIONS.csv
MOTION_REVERSAL_OOF_PREDICTIONS.csv NEXT_DISTINCT_PRIMARY_OOF_PREDICTIONS.csv
NEXT_OBSERVED_PRIMARY_OOF_PREDICTIONS.csv REVERSAL_METRICS_AGGREGATE.csv
REVERSAL_METRICS_BY_FOLD.csv REVERSAL_PER_CLASS_METRICS.csv
REVERSAL_CONFUSION_MATRIX.csv CALIBRATION_METRICS.csv CALIBRATION_BUCKETS.csv
UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv DOWN_TO_UP_FALSE_NEGATIVE.csv
REVERSAL_PATH_ANATOMY_LENGTH1.csv REVERSAL_PATH_ANATOMY_LENGTH2.csv
REVERSAL_PATH_ANATOMY_LENGTH3.csv REVERSAL_PATH_ANATOMY_LENGTH4.csv
PATH_ANATOMY_SUPPORT_SUMMARY.csv R0_R1_R2_R3_R4_INCREMENTAL.csv
NEXTSTATE_9CLASS_V3.csv CONFUSION_MATRIX_9STATE_V3.csv
PER_STATE_PRECISION_RECALL_F1_V3.csv NEGATIVE_CONTROL_V3.csv SHIFT60_STRESS_V3.csv
PROMOTION_GATE_V3.csv GATE_ASSESSMENT_V3.json INDEPENDENT_AUDIT_V3.json
INDEPENDENT_SUPPLEMENT_V3.json REPORT-ja.md NEXT_STAGE_HANDOFF.md
FINAL_RECEIPT.json BUDGET_FINAL_V3.json BOOTSTRAP_GLOBAL_DATE_DRAWS.json
BOOTSTRAP_GLOBAL_1000_RECEIPT.json C3_DATASET_FIXATION_RECEIPT.json
C4_LABEL_FIXATION_RECEIPT.json C5_OOF_FIXATION_RECEIPT.json C5_RESTORE_RECEIPT.json
PERMUTATION_MAPPING_V3.csv CHART_MANIFEST.json EXPOSURE_APPEND_ONLY_DELTA.json
ROUTINE_REPAIR_RECEIPT.json GITHUB_REQUEST_USAGE_AT_DELIVERY.json'''.split()

def stamp():
    return datetime.now(timezone(timedelta(hours=9))).isoformat()

def digest_bytes(b):
    return hashlib.sha256(b).hexdigest()

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''):
            h.update(b)
    return h.hexdigest()

def encoded(v):
    return (json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()

def load(n):
    return json.loads((R/n).read_text())

def check_file(p, expected=None):
    assert p.is_file(), str(p)
    if expected:
        assert digest(p) == expected, ('FILE_HASH', str(p), expected)

def source_index(head):
    entries = []
    for p in sorted(R.glob('*.py')):
        path = PREFIX+'/'+p.name
        entries.append({'name': p.name, 'repository': REPO, 'commit': head,
                        'path': path, 'SHA256': digest(p),
                        'URL': f'https://github.com/{REPO}/blob/{head}/{path}'})
    payload = R/'payload.b64'
    raw = base64.b64decode(payload.read_bytes())
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in sorted(z.namelist()):
            if n.endswith('/'):
                continue
            entries.append({'name': 'runner/'+n, 'repository': REPO,
                            'commit': head, 'path': PREFIX+'/payload.b64',
                            'archive_member': n, 'SHA256': digest_bytes(z.read(n)),
                            'payload_ZIP_SHA256': digest_bytes(raw),
                            'format': 'base64 decode to ZIP; read-only source, do not execute'})
    return {'JST': stamp(), 'final_commit': head, 'repository': REPO,
            'branch': 'state-predictiveness-v3-reversal-20261002-v1',
            'code_storage': 'GitHub only; source code is not duplicated in this evidence ZIP.',
            'source_files': entries,
            'inherited_sources': 'Original V2 bundle SOURCE_CODE_LOCATION_INDEX.json',
            'primitive_oracle': {'repository': REPO, 'commit': head,
                'path': PREFIX+'/INHERITED_INDEPENDENT_PRIMITIVE_V1.py',
                'SHA256': 'd32174bd02b1526997c92b8dbec58624aa957e94a9e78ae1d968273a16040ae9'},
            'instruction': 'Read saved results and portable input locations. No rerun of fits, labels, acquisition, or bootstrap under V3.',
            'original_script_paths': 'Original absolute paths remain in frozen source/manifests; INPUT_LOCATION_INDEX_V3.csv resolves data without changing any frozen bytes.'}

def inputs():
    manifest = load('DATASET_MANIFEST.json')
    portable = copy.deepcopy(manifest)
    rows = []
    members = {}
    for original, pair in zip(manifest['pairs'], portable['pairs']):
        pid = pair['pair_id']
        feature = Path(original['feature_path'])
        primitive = Path(original['original_feature_path'])
        trace = Path(original['trace_path'])
        path = primitive.parent.parent/'PATH_ENDPOINTS'/f'{pid}.jsonl'
        label = R/'LABELS'/f'{pid}.jsonl'
        specs = [('feature_path', feature, f'FEATURES/{pid}.jsonl', original['feature_SHA256']),
                 ('original_feature_path', primitive, f'ORIGINAL_FEATURES/{pid}.jsonl', original['original_feature_SHA256']),
                 ('trace_path', trace, f'STATE9_TRACES/{pid}.jsonl', original['state_trace_SHA256']),
                 ('path_endpoint_path', path, f'PATH_ENDPOINTS/{pid}.jsonl', original['path_endpoint_SHA256']),
                 ('label_path', label, f'LABELS/{pid}.jsonl', None)]
        if original.get('old_labels'):
            old = Path(original['old_labels'])
            specs.append(('old_labels', old, f'PRIOR_LABELS/{pid}.jsonl', None))
        for field, src, dest, expected in specs:
            check_file(src, expected)
            pair[field] = dest
            members[dest] = src
            rows.append({'pair_id': pid, 'date': pair['date'], 'security_id': pair['security_id'],
                         'field': field, 'archive_path': dest, 'original_path': str(src),
                         'SHA256': expected or digest(src), 'bytes': src.stat().st_size})
    portable['portability'] = {'path_rewrite_only': True,
        'original_manifest_SHA256': digest(R/'DATASET_MANIFEST.json'),
        'original_file': 'DATASET_MANIFEST.json',
        'note': 'Original bytes and labels are unchanged. Additional archive-relative locations resolve every V3 analysis input.'}
    assert len(manifest['pairs']) == 90
    return members, portable, rows

def preflight(v2_zip):
    for n in REQUIRED:
        check_file(R/n)
    check_file(v2_zip, V2_SHA)
    check_file(R/'OOF_ALL.jsonl', OOF_SHA)
    for n in ['INDEPENDENT_AUDIT_V3.json', 'INDEPENDENT_SUPPLEMENT_V3.json']:
        assert load(n)['status'] == 'PASS' and load(n)['mismatch_N'] == 0
    for item in load('FIT_INDEX_V3.json')['items']:
        check_file(R/item['path'], item['SHA256'])
    assert len(load('FIT_INDEX_V3.json')['items']) == 180
    assert len(list((R/'CHARTS').glob('*.png'))) == 12
    assert len(list((R/'CHARTS').glob('*.svg'))) == 12
    with (R/'OOF_ALL.jsonl').open('rb') as f:
        assert sum(1 for _ in f) == 105090
    members, portable, rows = inputs()
    return members, portable, rows

def report_html():
    text = (R/'REPORT-ja.md').read_text()
    node = os.environ['CODEX_PRIMARY_RUNTIME_NODE']
    program = "const m = await import(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + '/marked/lib/marked.esm.js'); let s=''; for await (const b of process.stdin) s+=b; process.stdout.write(m.marked.parse(s));"
    body = subprocess.run([node, '--input-type=module', '-e', program],
                          input=text, text=True, capture_output=True, check=True).stdout
    def embed(match):
        p = R/match.group(1)
        check_file(p)
        return 'src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'"'
    body = re.sub(r'src="(CHARTS/[^"<>]+\.png)"', embed, body)
    assert body.count('data:image/png;base64,') == 12
    return ('<!doctype html><html lang="ja"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Ark Terminal State Predictiveness V3 最終報告</title>'
        '<style>body{max-width:1120px;margin:36px auto;padding:0 20px;font-family:system-ui,sans-serif;line-height:1.7;color:#17212e}'
        'img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow:auto;font-size:14px;width:100%;margin:20px 0}'
        'th,td{border:1px solid #d4dbe2;padding:8px 10px;text-align:left}th{background:#eef3f7}h1,h2{line-height:1.4}'
        'code{word-break:break-all}p{margin:16px 0}@media print{body{margin:0;font-size:10pt}table{font-size:8pt}img{break-inside:avoid}h2{break-after:avoid}}</style>'
        '<body>'+body+'</body></html>').encode()

def build(v2_zip, head, destination):
    members, portable, rows = preflight(v2_zip)
    for p in R.iterdir():
        if p.is_file() and p.suffix in ['.json', '.csv', '.jsonl', '.md', '.txt', '.log']:
            members[p.name] = p
    for directory in ['FEATURES', 'LABELS', 'FITTED', 'FROZEN_INPUTS', 'NEW_DEVELOPMENT',
                      'RECOVERY_FINDINGS', 'CHECKPOINTS', 'CHARTS', 'INHERITED_V2']:
        for p in sorted((R/directory).rglob('*')):
            if p.is_file() and p.suffix not in ['.py', '.pyc', '.b64']:
                members[str(p.relative_to(R))] = p
    members['INHERITED_V2_ORIGINAL/'+v2_zip.name] = v2_zip
    members['DEVELOPMENT_COMPLETION_ARTIFACT.zip'] = R/'DEVELOPMENT_COMPLETION_ARTIFACT.zip'
    supplemental = {'DATASET_MANIFEST_PORTABLE.json': encoded(portable),
                    'SOURCE_CODE_LOCATION_INDEX.json': encoded(source_index(head)),
                    'REPORT-ja.html': report_html()}
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    supplemental['INPUT_LOCATION_INDEX_V3.csv'] = buffer.getvalue().encode()
    record = {'JST': stamp(), 'source_HEAD': head, 'status': load('FINAL_RECEIPT.json')['status'],
              'integrity': 'PASS', 'hash_scope': 'All members except DELIVERY_MANIFEST.json; outer archive SHA in separate receipt.',
              'immutable_original_V2_SHA256': V2_SHA, 'OOF_SHA256': OOF_SHA,
              'members': [{'path': n, 'SHA256': digest(p), 'bytes': p.stat().st_size}
                          for n, p in sorted(members.items())] +
                         [{'path': n, 'SHA256': digest_bytes(b), 'bytes': len(b)}
                          for n, b in sorted(supplemental.items())]}
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination/'Ark_Terminal_State_Predictiveness_V3_ALL_20261002.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for n, p in sorted(members.items()):
            z.write(p, n)
        for n, b in sorted(supplemental.items()):
            z.writestr(n, b)
        z.writestr('DELIVERY_MANIFEST.json', encoded(record))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names)) == len(record['members'])+1
        assert all(not n.endswith(('.py', '.pyc', '.b64')) for n in names)
        for item in record['members']:
            b = z.read(item['path'])
            assert len(b) == item['bytes'] and digest_bytes(b) == item['SHA256'], item['path']
        for row in rows:
            assert digest_bytes(z.read(row['archive_path'])) == row['SHA256']
        assert set(REQUIRED) <= set(names)
        assert z.read('DATASET_MANIFEST.json') == (R/'DATASET_MANIFEST.json').read_bytes()
    report = destination/'Ark_Terminal_State_Predictiveness_V3_Report_20261002.html'
    report.write_bytes(supplemental['REPORT-ja.html'])
    receipt = {'JST': stamp(), 'status': 'DELIVERY_PACKAGE_VERIFIED', 'source_HEAD': head,
        'archive': archive.name, 'archive_bytes': archive.stat().st_size,
        'archive_SHA256': digest(archive), 'member_N': len(record['members'])+1,
        'member_hash_mismatch_N': 0, 'CRC': 'PASS', 'portable_input_references': len(rows),
        'core_rows': 597, 'core_dates': 6, 'core_folds': 3, 'fits': 180, 'OOF_records': 105090,
        'figures': 12, 'report': report.name, 'report_SHA256': digest(report),
        'original_V2_preserved_SHA256': V2_SHA, 'new_fit_label_draw_provider_operations': 0}
    receipt_path = destination/'V3_DELIVERY_VERIFICATION_20261002.json'
    receipt_path.write_bytes(encoded(receipt))
    print(json.dumps(receipt, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--v2-zip', type=Path, required=True)
    parser.add_argument('--head')
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    if args.preflight_only:
        members, _, rows = preflight(args.v2_zip)
        print(json.dumps({'preflight': 'PASS', 'pairs': 90, 'input_references': len(rows),
                          'source_files': len(members), 'fits': 180, 'OOF_records': 105090}))
    else:
        assert args.head and re.fullmatch('[0-9a-f]{40}', args.head)
        assert args.destination
        build(args.v2_zip, args.head, args.destination)

if __name__ == '__main__':
    main()
