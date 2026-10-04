"""Strict source allowlist and authoritative GitHub hash checks; no regeneration."""
import io
import zipfile
from control import *

def main():
    checks=[]
    rankout=ROOT/'docs/evidence/capital-rank-bigwinner-vnext-20261005-v1'
    pins=read(rankout/'INPUT_BYTE_RECOVERY.json')['checks']
    expected={r['member']:r['sha256'] for r in pins}
    mask=read(rankout/'COMMON_EVAL_MASK_FREEZE.json')
    support=read(rankout/'TEACHER_CONTRACT_AUDIT.json')
    source=ROOT.parent/'project_sources/20-Ark_Capital_v4_Rank_Cutoff_Independent_20261004_PRIVATE.zip'
    rankzip=next((ROOT.parent/'quality_archives').rglob('*BigWinner_Rank*.zip'))
    movezip=next((ROOT.parent/'quality_archives').rglob('*Movement*.zip'))
    def put(z,name,dest,want):
        raw=z.read(name)
        got=hashlib.sha256(raw).hexdigest()
        assert got==want, ('SOURCE_HASH_MISMATCH',name,got,want)
        p=INPUTS/dest;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        checks.append({'archive_member':name,'input_relative':dest,'sha256':got,'exact_byte_identity':True})
    with zipfile.ZipFile(rankzip) as z:
        put(z,'private/COMMON_EVAL_MASK.jsonl.gz','COMMON_EVAL_MASK.jsonl.gz',mask['mask_sha256'])
        put(z,'private/TEACHER_SUPPORT_LEDGER.jsonl.gz','TEACHER_SUPPORT_LEDGER.jsonl.gz',support['ledger_sha256'])
        put(z,'inputs/movement/MOVE_P5_SCORE_STREAM.jsonl.gz','MOVE_P5_SCORE_STREAM.jsonl.gz',mask['move_saved_score_sha256'])
        put(z,'inputs/v4/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz','UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz',mask['current_saved_score_sha256'])
    with zipfile.ZipFile(movezip) as z:
        for n in ['RUNTIME_CAUSAL.jsonl.gz','TEACHERS_EVALUATION.jsonl.gz']:
            put(z,'capital_v2_private/'+n,n,expected['capital_v2_private/'+n])
        for b in range(1,9):
            n=f'MOVE_P_BLOCK_{b:02d}.json'
            put(z,'capital_v2_private/models/'+n,'models/'+n,expected['capital_v2_private/models/'+n])
    hfit=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/H2_FITS.json')
    with zipfile.ZipFile(source) as outer:
        data=outer.read('deliverables/Ark_Capital_MAX3_Upward_Staircase_v4_20261004_PRIVATE.zip')
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n,d in [
                ('inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz','MARKET_TEACHER_BOOK.jsonl.gz'),
                ('inputs/v3/capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz','CORE_RUNTIME_CAUSAL.jsonl.gz'),
                ('inputs/v3/work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz','FROZEN_ENTRY.jsonl.gz')]:
                put(z,n,d,expected[n])
            for b in range(1,9):
                for head in ['H2','H3']:
                    n=f'{head}_BLOCK_{b:02d}.json'
                    put(z,'capital_staircase_v4_private/models/'+n,'models/'+n,hfit['model_hashes'][n])
    save(OUT/'INPUT_BYTE_RECOVERY.json',{'exact_jst':now(),'authority':'fixed GitHub base artifacts; archives are byte transport only',
        'strict_member_allowlist':True,'checks':checks,'mismatch_N':0,'new_fits':0,'score_regeneration':0,
        'forbidden_allocation_research_member_reads':0,'protected_fresh_holdout_validation_OOS_prospective_open':0})
    print({'recovered_files':len(checks),'hash_mismatch':0})

if __name__=='__main__':main()
