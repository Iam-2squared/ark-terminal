"""CI-only fixed artifact restoration; credentials used for GitHub reads only.

No J-Quants request/decryption, broker, or protected data. All payload identities
are fixed before parsing/executing. The original source is frozen and unmodified.
"""
import pathlib,os,subprocess,zipfile,json,hashlib,io,sys
R=pathlib.Path(os.environ['ARK_V2_COMPLETION_ROOT']);tmp=R/'downloads';tmp.mkdir(exist_ok=False)
sha=lambda x:hashlib.sha256(x).hexdigest()
def get(aid,wanted):
 p=tmp/(str(aid)+'.zip')
 with p.open('xb') as f:subprocess.run(['gh','api',f'repos/Iam-2squared/ark-terminal/actions/artifacts/{aid}/zip'],stdout=f,check=True)
 assert sha(p.read_bytes())==wanted,('PINNED_ARTIFACT_HASH',aid)
 return p
p=get(10683107105,'55f24d485a21b68a92a6b5e816cb92c99d50f040a7a53e0bf6ce60cec903c41e')
with zipfile.ZipFile(p) as outer:
 receipt=json.loads(outer.read('source-snapshot-receipt.json'));b=outer.read('source.zip')
 assert sha(b)==receipt['sourceZipSHA256']=='4293f6baf0676a65a596f66543642c78a2c15b1620165ca7f574b8321ee9df2d'
with zipfile.ZipFile(io.BytesIO(b)) as z:
 assert len(z.namelist())==len(set(z.namelist()))
 assert set(z.namelist())==set(receipt['files'])
 for name,h in receipt['files'].items():
  path=pathlib.PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts
  b=z.read(name);assert sha(b)==h,('PRIMARY_SOURCE_PIN',name)
  p=R/'repo'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
(R/'primary-source-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
sys.path.insert(0,str(R/'repo/scripts'))
# The PYTHONPATH directory did not exist when Python started.
# Invalidate its cached missing-path finder after restoring pinned files.
import importlib
importlib.invalidate_caches()
import restore_phase57_state_v2_artifacts as restore
for aid,run,h,m in restore.ARTIFACTS:get(aid,h)
restore.restore(R/'inputs-restored',R/'repo',archives=tmp)
p=get(10688737280,'3606683de2bc60dc8b89bf96d2ea19699aeb091c574c1c32d89f4d6a13d8509d')
with zipfile.ZipFile(p) as z:
 manifest=json.loads(z.read('manifest.json'))
 for name,h in manifest.items():
  path=pathlib.PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts
  b=z.read(name);assert sha(b)==h,('A8_RAW_MEMBER_PIN',name)
  p=R/'a8-recovery-fixed'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 (R/'a8-recovery-fixed/manifest.json').write_bytes(z.read('manifest.json'))
print('PRIMARY_SOURCE_AND_FIXED_DEVELOPMENT_INPUTS_VERIFIED',flush=True)
