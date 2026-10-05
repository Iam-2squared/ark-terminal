"""Deterministic final R1 delivery pack. No fits, inference, evaluations, or replays."""
from pathlib import Path
import argparse, gzip, hashlib, io, json, zipfile

ROOT=Path('/workspace/scratch/f3d0aa747c89')
WORK=ROOT/'r1_work'
FIXED_TIME=(2026,10,5,0,0,0)
DEFAULT_OUTPUT=ROOT/'deliverables/Ark_Capital_V5_Anchor_Slot3_R1_20261005_PRIVATE.zip'
DIRECTORIES=('inputs','score_certification','code','authority_code','spec_review','primary_canaries',
             'primary_pre_main','evidence','metrics','independent','runs')
ROOT_FILES=('prepare_inputs.py','precommit_r1.py','publish_stage.py','prepare_main_claim.py',
            'prepare_independent_claim.py','prepare_closure.py','score_distribution_diagnostic.py',
            'package_private_r1.py','R2_ACTUAL_GET_RECEIPT.json','OFF_ACTUAL_GET_RECEIPT.json',
            'INDEPENDENT_ACTUAL_GET_RECEIPT.json','D_PRIMARY_ACTUAL_GET_RECEIPT.json',
            'DR_PRIMARY_ACTUAL_GET_RECEIPT.json','DR_LAUNCH_INVESTIGATION.json',
            'ACTIONS_FINAL_ACTUAL_GET.json',
            'MAIN_ACTUAL_GET_RECEIPT.json','POST_MAIN_ACTUAL_GET_RECEIPT.json',
            'FINAL_ACTUAL_GET_RECEIPT.json')
OLD_RECEIPTS=('audit_input/NESTED_ARCHIVE_INVENTORY.json','audit_input/INPUT_AUDIT_SUMMARY.json',
              'audit_input/V5_SOURCE_BYTES_AUDIT.json','work/V5_PUBLIC_PRIVATE_BYTE_AUDIT.json',
              'work/evidence/SPECIFICATION_CONFLICT.json','work/evidence/START_AUDIT.json',
              'work/evidence/receipts/BLOCKED_CLOSURE_ACTUAL_GET_20261005.json')

def sha(data):return hashlib.sha256(data).hexdigest()
def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def excluded(path):
    parts=path.parts
    return (any(x=='__pycache__' or x.startswith('.') for x in parts)
            or any(x in ('synthetic_report_writer','synthetic_plot_writer') for x in parts)
            or path.name=='SYNTHETIC_EMPTY_RUN_MANIFEST.json'
            or 'WRITE_PAYLOAD' in path.name or path.suffix in ('.pyc','.pyo','.tmp','.log')
            or path.name.endswith(('~','.swp')))

def gzip_certificate(name,raw):
    decoded=gzip.decompress(raw)
    jsonl=name.endswith('.jsonl.gz')
    record={'member':name,'compressed_sha256':sha(raw),'compressed_bytes':len(raw),
            'decoded_sha256':sha(decoded),'decoded_bytes':len(decoded),'decode_reencode_roundtrip':False}
    # Lossless byte round-trip, independent of original header mtime and compression level.
    canonical=gzip.compress(decoded,mtime=0)
    assert gzip.decompress(canonical)==decoded
    record['decode_reencode_roundtrip']=True
    if jsonl:
        all_lines=decoded.splitlines()
        # Frozen gz writers represent an empty row list as a single newline.
        # Count actual JSON records while retaining and hashing every original byte.
        lines=[line for line in all_lines if line.strip()]
        for line in lines:json.loads(line)
        record['JSONL_N']=len(lines)
        record['blank_line_N']=len(all_lines)-len(lines)
    elif name.endswith('.json.gz'):
        json.loads(decoded);record['JSON_body_valid']=True
    return record

def package(closure_path,output,basis_head,basis_tree):
    closure_path=Path(closure_path);closure=json.loads(closure_path.read_text())
    assert ('R12' in closure.get('CURRENT_STATE','') or closure.get('fixed_STOP') is True
            or closure.get('fixedStop') is True or closure.get('fixed_STOP')=='true'), 'FINAL_FIXED_STOP_CLOSURE_REQUIRED'
    assert closure.get('activeCapitalChampion','V5')=='V5'
    assert closure.get('selectedCapitalCandidate') is None
    assert closure.get('championUpdated',False) is False
    report=WORK/'metrics/final/REPORT_FINAL-ja.md'
    assert report.is_file(),'FINAL_REPORT_REQUIRED'
    assert (WORK/'metrics/final/D_EXACT_EVALUATION.json').is_file()
    assert (WORK/'metrics/final/DR_EXACT_EVALUATION.json').is_file()
    output=Path(output);assert not output.exists(),'PACK_EXISTS_NO_REBUILD'
    payload={}
    for dirname in DIRECTORIES:
        folder=WORK/dirname
        if not folder.exists():continue
        for p in sorted(folder.rglob('*')):
            if not p.is_file() or excluded(p):continue
            assert not p.is_symlink()
            payload[str(p.relative_to(ROOT))]=p.read_bytes()
    for filename in ROOT_FILES:
        p=WORK/filename
        if p.is_file():payload[str(p.relative_to(ROOT))]=p.read_bytes()
    for name in OLD_RECEIPTS:
        p=ROOT/name
        assert p.is_file(),('READ_ONLY_RECEIPT_MISSING',name)
        payload['previous_cycle_read_only/'+name]=p.read_bytes()
    # Include the supplied terminal closure if it is outside the ordinary evidence directory.
    ckey='r1_work/evidence/DELIVERY_TERMINAL_CLOSURE.json'
    if str(closure_path.relative_to(ROOT)) not in payload:payload[ckey]=closure_path.read_bytes()
    gzcert=[gzip_certificate(name,data) for name,data in sorted(payload.items()) if name.endswith('.gz')]
    readme=(
      'Ark Capital V5 Anchor Slot3 R1 — fixed STOP private evidence\n\n'
      'The strategy parent and active Capital Champion remain V5. The package contains frozen inputs, '
      'completed claims, actual ledgers, score references, independent audits and exact final evaluations.\n'
      'r1_work/metrics/final/REPORT_FINAL-ja.md is the primary report. The original completed claims '
      'record the consumed budgets; packing performs no fit, inference, evaluation or market replay.\n'
      'r1_work/inputs/RUNTIME_INPUT_MANIFEST.json maps the exact source bytes. Absolute scratch paths '
      'in historical receipts describe the executed environment; map them to the corresponding relative '
      'package paths when inspecting in another directory. The frozen native code is bundled under '
      'r1_work/inputs/v5/repo/research/capital-v5-max3-slot-intelligence-20261004-v1/.\n'
      'Evaluation-only teacher and protected100 identities are under r1_work/metrics/evaluation_only/; '
      'they are not policy inputs. Future execution source coverage diagnostics are not candidate filters.\n'
      'All names in PACKAGE_MANIFEST.json are individually SHA256-certified. ZIP_GET_VERIFY.json '
      'is generated next to the ZIP after an independent reopened-ZIP byte verification.\n')
    payload['README_FIRST.txt']=readme.encode()
    members={name:{'sha256':sha(data),'bytes':len(data)} for name,data in sorted(payload.items())}
    manifest={'schema':'CAPITAL_V5_ANCHOR_SLOT3_R1_PRIVATE_DELIVERY_V1',
       'basis_HEAD':basis_head,'basis_tree':basis_tree,'strategy_parent':'710656491be06235901b45c50a8b5cbd714ba4eb',
       'activeCapitalChampion':'V5','selectedCapitalCandidate':None,'championUpdated':False,
       'terminal_closure_sha256':sha(closure_path.read_bytes()),
       'report_sha256':sha(report.read_bytes()),'payload_member_N':len(members),'members':members,
       'gzip_certifications':gzcert,'packing_counts':{'newFits':0,'modelInference':0,'marketReplays':0,
       'newEconomicEvaluations':0,'newScorePnLJoins':0,'providerRequests':0,'orders':0,'GitWrites':0},
       'excluded':'WRITE_PAYLOAD duplicates, pycache, temporary files, synthetic report/plot fixtures',
       'compression':{'method':'ZIP_DEFLATED','level':9,'fixed_timestamp':list(FIXED_TIME),'entry_mode':'100644'}}
    payload['PACKAGE_MANIFEST.json']=(json.dumps(manifest,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=True) as z:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,date_time=FIXED_TIME);info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3;info.external_attr=0o100644<<16;info.flag_bits|=0x800
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    # GET the completed bytes again rather than relying on the write buffers.
    packed=output.read_bytes();checks=[]
    with zipfile.ZipFile(io.BytesIO(packed)) as z:
        assert len(z.namelist())==len(set(z.namelist()))==len(payload)
        assert set(z.namelist())==set(payload)
        assert z.testzip() is None
        for name in sorted(payload):
            got=z.read(name);expected=payload[name]
            assert got==expected
            checks.append({'member':name,'sha256':sha(got),'bytes':len(got),'exact_bytes_match':True})
        reopened=json.loads(z.read('PACKAGE_MANIFEST.json'))
        assert reopened==manifest
        for name,item in reopened['members'].items():assert sha(z.read(name))==item['sha256']
    receipt={'schema':'R1_PRIVATE_ZIP_GET_VERIFY_V1','filename':output.name,'path':str(output),
      'file_sha256':sha(packed),'bytes':len(packed),'member_N':len(checks),
      'payload_member_hash_checks':len(members),'member_mismatch_N':0,'ZIP_CRC_PASS':True,
      'manifest_sha256':sha(payload['PACKAGE_MANIFEST.json']),'all_member_sha256':checks,
      'gzip_file_N':len(gzcert),'JSONL_file_N':sum('JSONL_N' in x for x in gzcert),
      'JSONL_total_N':sum(x.get('JSONL_N',0) for x in gzcert),'gzip_roundtrip_all_PASS':True,
      'basis_HEAD':basis_head,'basis_tree':basis_tree,'terminal_closure_sha256':manifest['terminal_closure_sha256'],
      'activeCapitalChampion':'V5','selectedCapitalCandidate':None,'championUpdated':False,
      'packing_counts':manifest['packing_counts']}
    receipt_path=output.with_suffix('.ZIP_GET_VERIFY.json')
    write_new(receipt_path,receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='all_member_sha256'},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--closure',required=True)
    parser.add_argument('--output',default=str(DEFAULT_OUTPUT));parser.add_argument('--head',required=True)
    parser.add_argument('--tree',required=True);args=parser.parse_args()
    package(args.closure,args.output,args.head,args.tree)
