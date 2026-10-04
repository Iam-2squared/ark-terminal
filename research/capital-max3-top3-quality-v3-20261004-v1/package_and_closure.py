"""Verify immutable references and package private saved IO/results. No extra fit/replay."""
from pathlib import Path
import zipfile
from checkpoint import *
base=ROOT.parent
sources=json.loads((PRIVATE/'SOURCE_MANIFEST.json').read_text());refs=json.loads((PRIVATE/'REFERENCE_READ_ONLY_HASHES.json').read_text());pin=json.loads((OUT/'MODEL_PRECOMMIT_CODE_PIN.json').read_text())
source_changed=[k for k,v in sources.items() if sha(base/k)!=v];ref_changed=[k for k,v in refs.items() if sha(ROOT/k)!=v];code_changed=[k for k,v in pin['runtime_code_hashes'].items() if sha(Path(__file__).parent/k)!=v]
assert not source_changed and not ref_changed and not code_changed
changed=git('diff','--name-only',CONTROL_HEAD).splitlines();assert all(p.startswith(('research/'+NAME+'/','docs/evidence/'+NAME+'/')) for p in changed)
assert len(list((PRIVATE/'models').glob('*.json')))==24
assert json.loads((OUT/'FOCUSED_TEST_RESULTS.json').read_text())['failed_N']==0
assert json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())['mismatch_N']==0
files={str(p.relative_to(base)):p for p in PRIVATE.rglob('*') if p.is_file()}
files.update({k:base/k for k in sources})
# The focused suffix canary uses only this existing Frozen Development trace.
from io_data import rows
entry=rows(base/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz')[0]
trace=base/'work_inputs/exit_v2/FULL_TRACE'/(entry['session']+'_'+entry['symbol']+'.jsonl.gz');files[str(trace.relative_to(base))]=trace
members={k:{'sha256':sha(p),'bytes':p.stat().st_size} for k,p in sorted(files.items())}
manifest={'jst':now(),'repo':'Iam-2squared/ark-terminal','branch':git('branch','--show-current'),'code_basis_head':git('rev-parse','HEAD'),'code_basis_tree':git('rev-parse','HEAD^{tree}'),'reproduction':'Unzip preserving workspace-relative paths; git-backed code at code_basis_head. Run no fits when consuming existing outputs; scores/models/replays/audits all frozen. Includes existing source bytes and first trace required by focused canary.','members':members,'private_raw_source':True,'H5_new_fits':0,'new_fits':24,'measurement_replays':4,'control_replays':0,'safety':SAFETY}
save(PRIVATE/'PACKAGE_MANIFEST.json',manifest);files[str((PRIVATE/'PACKAGE_MANIFEST.json').relative_to(base))]=PRIVATE/'PACKAGE_MANIFEST.json'
archive=base/'Ark_Capital_MAX3_Top3_Quality_v3_20261004_PRIVATE.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,p in sorted(files.items()):z.write(p,name)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert z.namelist()==sorted(files)
 for name in z.namelist():assert hashlib.sha256(z.read(name)).hexdigest()==sha(files[name])
save(OUT/'FINAL_SOURCE_PRIVACY_AUDIT.json',{'jst':now(),'source_files_verified_N':len(sources),'old_reference_files_verified_N':len(refs),'pinned_runtime_files_verified_N':len(pin['runtime_code_hashes']),'source_changed':source_changed,'old_references_changed':ref_changed,'pinned_runtime_changed':code_changed,'Frozen_entry_exit_changes':0,'H5_byte_hash':sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz'),'control_replays':0,'new_provider_requests':0,'Protected_Holdout_Fresh_Validation_OOS_Prospective_opened':0,'MAX4_MAX5_replays':0,'result_based_retune':0,'safety':SAFETY,'orders':0,'main_merge':0,'force_push':0})
save(PRIVATE/'ARCHIVE_BUILD_RECEIPT.json',{'path':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'member_N':len(files),'basis_HEAD':git('rev-parse','HEAD'),'saved':False})
print(json.dumps({'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'member_N':len(files),'source_changed':0,'reference_changed':0,'pinned_code_changed':0}))
