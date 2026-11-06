"""Content-addressed private dependencies and verification evidence, once per stage."""
from io_utils import *
import tarfile,io,zipfile,sys,platform

def tarpack(filename,paths):
    p=PRI/filename;tmp=p.with_suffix(p.suffix+'.tmp');members=[]
    with tarfile.open(tmp,'w:xz',format=tarfile.PAX_FORMAT,preset=6) as t:
        for item in sorted(set(paths)):
            if not item.is_file():continue
            name=item.relative_to(ROOT).as_posix();b=item.read_bytes();info=tarfile.TarInfo(name);info.size=len(b);info.mtime=0;info.mode=0o644;info.uid=info.gid=0;t.addfile(info,io.BytesIO(b));members.append({'path':name,**pin(item)})
    tmp.replace(p)
    save(PRI/(filename+'.MANIFEST.json'),{'archive':filename,**pin(p),'deterministic_tar_mtime':0,'members':members,'visibility':'PRIVATE'})
    return pin(p)

def source_prefixes():
    out=PRI/'immutable/ORIGINAL_STATE_PREFIX_LINES.jsonl.gz'
    if out.exists():return
    binding=json.loads((ROOT/'inputs/STATE9_TRACE_ARCHIVE_BINDING.json').read_text());cache=rows(PRI/'immutable/STATE_PREFIX_CACHE.jsonl.gz');manifest=[];count=0
    tmp=out.with_suffix('.tmp');tmp.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ROOT/'inputs/STATE9_V2_FROZEN_TRACE_ARCHIVE.zip') as z, tmp.open('wb') as dest, gzip.GzipFile(fileobj=dest,mode='wb',mtime=0,filename='') as g:
        for case in cache:
            key=case['entry_id'];member=binding['trace_members'][key];b=z.read(member);assert hashlib.sha256(b).hexdigest()==binding['manifest']['components'][member]['sha256']
            frames={r['checkpoint_minute']:r for r in case['frames']};selected=[]
            for line in gzip.decompress(b).splitlines(keepends=True):
                q=json.loads(line);t=q['bar_end_minute']
                if t in frames:
                    assert q['watch_key']==key and hashlib.sha256(line).hexdigest()==frames[t]['source_line_sha256'];selected.append(line)
            raw=b''.join(selected);g.write(raw);count+=len(selected)
            manifest.append({'entry_id':key,'original_member':member,'original_full_member_sha256':hashlib.sha256(b).hexdigest(),'exact_post_buy_through_control_prefix_sha256':hashlib.sha256(raw).hexdigest(),'raw_line_N':len(selected),'buy_fill_minute':case['buy_fill_minute'],'control_intent_minute':case['control_intent_minute'],'prefix_matches_previously_independently_verified_source_lines':True})
    tmp.replace(out)
    save(PRI/'immutable/ORIGINAL_STATE_PREFIX_LINES_MANIFEST.json',{'cache':out.name,**pin(out),'Entry_N':len(manifest),'line_N':count,'members':manifest,'original_source_archive_reference':'inputs/STATE9_TRACE_ARCHIVE_BINDING.json','not_original_whole_archive_identity':True,'new_State_kernel_runs':0})

def main():
    source_prefixes()
    needed=[]
    for p in (ROOT/'inputs/v5').iterdir():
        if p.name!='teachers':needed.append(p)
    needed+=list((ROOT/'inputs/frozen_models').glob('*.json'))+list((ROOT/'inputs/lineage').glob('*'))
    needed+=list((PRI/'immutable').glob('*'))
    needed+=list(NATIVE.glob('*.py'))+[NATIVE.parent.parent/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/POLICY_PRECOMMIT.json']
    needed+=[ROOT/'inputs'/name for name in ['STATE9_TRACE_ARCHIVE_BINDING.json','S6_COVERAGE_AND_WINDOWS.json','S6_ACTUAL_GET_RECEIPT.json','V5_RESET20_RESULT.json','reset_private_ref.json','S3_MAIN_EXIT_FREEZE_20261007.json','S4_PRIVATE_CARRIER_MANIFEST.json','v5_source.json','reset_binding.json']]
    needed+=list((ROOT/'inputs/reset_archive/Ark_Capital_V51_PRIVATE/runs/V5_RESET20').rglob('*'))
    needed+=[SHARP/'implementation/numeric_adapter.py',SHARP/'parent/implementation/fill_and_evaluate.py',SHARP/'parent/inputs/frozen_v3_code/reused_clock.py',SHARP/'parent/inputs/frozen_v3_code/reused_fill.py']
    state_binding=json.loads((ROOT/'inputs/STATE9_TRACE_ARCHIVE_BINDING.json').read_text())
    save(PRI/'DEPENDENCY_BOOTSTRAP_MANIFEST.json',{'shared_inputs_archive':'PRIVATE_SHARED_INPUTS.tar.xz','all_formal_reproduction_inputs_materialized':True,'original_full_State_archive_external_for_original_archive_audit':{'source_archive_member':state_binding['source_archive_member'],'library_file_id':'libfile_67d946a85b688191b1793379bd909ae0','extracted_archive':pin(ROOT/'inputs/STATE9_V2_FROZEN_TRACE_ARCHIVE.zip'),'scope':'Existing Development trace archive only, original independent audit re-read exact members; whole source not duplicated per window'},'saved_exact_original_State_prefix_lines':'private/immutable/ORIGINAL_STATE_PREFIX_LINES.jsonl.gz','previous72_full_source_reference':{'private_commit':'03c013cd4d9b4f94340cda8f14d1927ac68b9531','manifest':'research/exit-sharp-drop-overlay-counterfactual-20261007/technical-resume-72-20261007/PRIVATE_CARRIER_MANIFEST.json','SHA256':'293da80200312d6ae1c17175010fdfc4ef1005a863bf68bacd997dc5384be73d','part_N':28,'reference_only_no_raw_duplicate':True},'market_provider_request_N':0,'fit_inference_State_run_N':0,'cache_shared_across_all_windows':True})
    needed+=[PRI/'DEPENDENCY_BOOTSTRAP_MANIFEST.json',ROOT/'inputs/S6_FINAL_COMPARISON.json']
    shared=tarpack('PRIVATE_SHARED_INPUTS.tar.xz',needed)
    independent=tarpack('INDEPENDENT_RECONSTRUCTION.tar.xz',[p for p in (PRI/'independent').rglob('*') if p.is_file()]+[ROOT/'independent_audit.py',ROOT/'independent_supplement.py'] if (ROOT/'independent_supplement.py').exists() else [p for p in (PRI/'independent').rglob('*') if p.is_file()]+[ROOT/'independent_audit.py'])
    reproduction=tarpack('REPRODUCTION_VERIFICATION.tar.xz',[p for p in (PRI/'reproduction').rglob('*') if p.is_file() and '/sessions/' not in p.as_posix()]+[ROOT/'reproduce_once.py'])
    print(json.dumps({'shared_inputs':shared,'independent':independent,'reproduction':reproduction}))
if __name__=='__main__':main()
