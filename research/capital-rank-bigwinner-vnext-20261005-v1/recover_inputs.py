"""Strict member allowlist; restore existing bytes without regenerating artifacts."""
import io
import json
import zipfile
from control import WORK, ROOT, OUT, INPUTS, now, save, sha

def put(source, name, dest, expected):
    import hashlib
    data = source.read(name)
    got = hashlib.sha256(data).hexdigest()
    assert got == expected, ('MISSING_EVIDENCE_HASH_MISMATCH',name,got,expected)
    path = INPUTS/dest
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        f.write(data)
    return {'member':name, 'local_relative':str(path.relative_to(WORK)), 'sha256':got, 'exact_byte_identity':True}

def main():
    v4hash=json.loads((ROOT/'docs/evidence/capital-v6-counterfactual-slot-value-20261004-v1/SOURCE_HASHES.json').read_text())
    checks=[]
    outer=next((WORK/'project_sources').glob('20-*.zip'))
    with zipfile.ZipFile(outer) as z:
        with zipfile.ZipFile(io.BytesIO(z.read('deliverables/Ark_Capital_MAX3_Upward_Staircase_v4_20261004_PRIVATE.zip'))) as v4:
            names=['capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz',
                'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz',
                'inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz',
                'inputs/v3/capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz',
                'inputs/v3/work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz']
            for name in names:
                checks.append(put(v4,name,'v4/'+name,v4hash['source_main/'+name]))
            # Ledger not part of the D1 subset: verify the attached package manifest.
            manifest=json.loads(v4.read('PACKAGE_MANIFEST.json'))
            ledger='capital_staircase_v4_private/TEACHER_UNSUPPORTED_HIGH_LEDGER.jsonl.gz'
            # Leave this optional redundant ledger unopened; original book supports the census.
    movement=next((WORK/'rank_work/archives').rglob('*.zip'))
    fixed=json.loads((ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1/FIXED_ARMS_SCORE_STREAMS.json').read_text())
    mat=json.loads((ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1/FEATURE_MATERIALIZATION_RESULT.json').read_text())
    fits=json.loads((ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1/ROLLING_ORIGIN_HEAD_FITS.json').read_text())
    with zipfile.ZipFile(movement) as z:
        for name,expected in [('MOVE_P5_SCORE_STREAM.jsonl.gz',fixed['arms']['MOVE_P5']['score_stream_sha256']),
            ('RUNTIME_CAUSAL.jsonl.gz',mat['runtime_sha256']),('TEACHERS_EVALUATION.jsonl.gz',mat['teacher_sha256'])]:
            checks.append(put(z,'capital_v2_private/'+name,'movement/'+name,expected))
        for b in range(1,9):
            name=f'MOVE_P_BLOCK_{b:02d}.json'
            checks.append(put(z,'capital_v2_private/models/'+name,'movement/models/'+name,fits['model_hashes'][name]))
    save(OUT/'INPUT_BYTE_RECOVERY.json', {'exact_jst':now(),'source_authority':'GitHub latest pinned existing artifacts; archives are byte transports only',
        'strict_member_allowlist':True,'checks':checks,'mismatch_N':0,'fit_count':0,'score_regeneration':0,'teacher_regeneration':0,'replay_count':0,
        'protected_fresh_holdout_validation_OOS_prospective_open':0})
    print(json.dumps({'recovered_files':len(checks),'mismatch_N':0}))

if __name__=='__main__':
    main()
