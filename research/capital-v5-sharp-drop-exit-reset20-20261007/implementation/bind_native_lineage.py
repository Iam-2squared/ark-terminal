"""Hash-only binding of original frozen model/table members. No inference or fit."""
from io_utils import *
import zipfile,io,re

def main():
    source=json.loads((PUB/'SOURCE_BINDING.json').read_text());route=source['V5_resolved_members']['candidate_stream']['archive_member'].split('!')
    def exact_archive(parts):
        z=zipfile.ZipFile(ROOT.parent/'project_sources'/parts[0]);layers=[]
        for member in parts[1:-1]:
            b=z.read(member);layers.append({'member':member,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
            z=zipfile.ZipFile(io.BytesIO(b))
        return z,layers
    z,layers=exact_archive(route)
    assert hashlib.sha256(z.read(route[-1])).hexdigest()==pin(ROOT/'inputs/v5/candidate_stream')['sha256']
    native_route=source['V5_resolved_members']['native_trades']['archive_member'].split('!')
    v5,native_layers=exact_archive(native_route)
    assert hashlib.sha256(v5.read(native_route[-1])).hexdigest()==pin(ROOT/'inputs/v5/native_trades')['sha256']
    model_route=source['V5_resolved_members']['split']['archive_member'].split('!')
    z,model_layers=exact_archive(model_route)
    assert hashlib.sha256(z.read(model_route[-1])).hexdigest()==pin(ROOT/'inputs/v5/split')['sha256']
    src=json.loads((ROOT/'inputs/v5_source.json').read_text());models=[]
    for member,h in sorted(src.items()):
        if member.startswith('capital_staircase_v4_private/models/') and re.search(r'/models/H[235]_BLOCK_\d+\.json$',member):
            b=z.read(member);assert hashlib.sha256(b).hexdigest()==h,member
            dest=ROOT/'inputs/frozen_models'/Path(member).name;atomic(dest,b)
            models.append({'archive_member':member,'local_member':dest.relative_to(ROOT).as_posix(),**pin(dest)})
    assert len(models)==24
    mapping={(int(re.search('H([235])_',m['archive_member']).group(1)),int(re.search(r'BLOCK_(\d+)',m['archive_member']).group(1))):m['sha256'] for m in models}
    stream=rows(ROOT/'inputs/v5/candidate_stream');split=json.loads((ROOT/'inputs/v5/split').read_text())
    for r in stream:
        for h in [2,3,5]:assert r['H'+str(h)+'_hash']==mapping[h,r['block']]
        assert r['session'] in split['blocks'][r['block']-1]['test'],r['entry_id']
    extra=[]
    manifest=json.loads(v5.read('MANIFEST_SHA256.json'))
    for member in ['capital_v5_slot_private/TRAINING_ONLY_SCORED_ARRIVALS.jsonl.gz','repo/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/checkpoints/V1_V4_MODEL_RANK_CONTROL_FREEZE.json','repo/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/SOURCE_HASHES.json']:
        b=v5.read(member);dest=ROOT/'inputs/lineage'/Path(member).name;atomic(dest,b);extra.append({'archive_member':member,**pin(dest)})
    policy=json.loads((NATIVE.parent.parent/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/POLICY_PRECOMMIT.json').read_text())
    assert extra[0]['sha256']==policy['training_predictions_sha256']
    assert pin(ROOT/'inputs/v5/arrival')['sha256']==policy['arrival_table_sha256']
    assert pin(ROOT/'inputs/v5/candidate_stream')['sha256']==policy['fixed_score_sha256']
    record={'status':'EXACT_MEMBER_HASH_PASS','original_model_member_N':24,'stream_ID_N':len(stream),'every_stream_row_original_block_and_model_hash_match':True,'model_payloads_verified_without_inference_or_fitting':True,'native_preprocessing_rank_semantics':'Pinned serialized original H2/H3/H5 plus unmodified native preprocessing and native saved rank/ML stream','models':models,'source_manifest_pin':pin(ROOT/'inputs/v5_source.json'),'nested_score_archive_lineage':layers,'nested_native_archive_lineage':native_layers,'nested_original_model_archive_lineage':model_layers,'additional_members':extra,'new_inference':0,'new_fit':0,'new_rank':0}
    save(PRI/'FROZEN_NATIVE_INPUT_LINEAGE.json',record);save(PUB/'FROZEN_NATIVE_INPUT_LINEAGE.json',record)
    source['frozen_model_table_score_binding']=record;save(PUB/'SOURCE_BINDING.json',source)
    print(json.dumps({'status':record['status'],'model_N':24,'matched_stream_N':len(stream)}))
if __name__=='__main__':main()
