"""Provenance only. No inference, outcomes join, evaluator or market runner."""
import json, hashlib, pathlib, zipfile, io, fnmatch, datetime
ROOT=pathlib.Path('/workspace/scratch/f3d0aa747c89')
OUT=ROOT/'bridge_work'
BRANCH='capital-v5-frozen-expert-bridge-20261005'
def sha(b): return hashlib.sha256(b).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
def save(name,x):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 assert not p.exists(),str(p)
 p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def run():
 selected=[]
 a=ROOT/'deliverables/Ark_Capital_V5_Anchor_Slot3_R1_20261005_PRIVATE.zip'
 assert sha(a.read_bytes())=='b28ea245b8db4e1e4a44ce2e03369007735ad1950b78e26edb67fa6180c728b6'
 with zipfile.ZipFile(a) as z:
  manifest=json.loads(z.read('PACKAGE_MANIFEST.json'))
  save('sources/R1_PACKAGE_MANIFEST.json',manifest)
  names=[n for n in z.namelist() if n.startswith(('r1_work/score_certification/','r1_work/metrics/evaluation_only/','r1_work/metrics/supplement/')) or n in ['r1_work/metrics/V5_EXACT_EVALUATION_AUTHORITY.json','r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz','r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz','r1_work/runs/OFF_PRIMARY/TRADES.jsonl.gz','r1_work/runs/OFF_PRIMARY/INTENTS.jsonl.gz']]
  for n in names:
   b=z.read(n);p=ROOT/n;assert p.exists() and p.read_bytes()==b,n
   selected.append({'archive':'A','member':n,'bytes':len(b),'sha256':sha(b),'local':str(p),'match':'ZIP_LOCAL_EXACT'})
 d=ROOT/'project_sources/23-Ark_Capital_v11R1_Numeric_Cert_Recovery_20261005_PRIVATE-1-.zip'
 assert sha(d.read_bytes())=='bca2ba95b095132ce69eef2f207d1980ce2cc8ae688a1aad313c59f37a2c3e86'
 dz=zipfile.ZipFile(d)
 mb=dz.read('authority/Ark_Capital_v11_Realized_Monetization_Signal_20261005_PRIVATE_CONTRACT_FAIL.zip')
 assert sha(mb)=='134977744baab20ea75310d8c263322281d4f8289ad60afdd1a6b83e3875156f'
 mz=zipfile.ZipFile(io.BytesIO(mb))
 for n in ['MANIFEST.json','private/MRET_EVALUATION_ROWS.jsonl.gz','private/MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz','private/MRET_EVALUATION_EXCLUSIONS.jsonl.gz']:
  b=mz.read(n);p=OUT/'sources/mret'/n;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(b)
  selected.append({'archive':'D!MRET','member':n,'sha256':sha(b),'bytes':len(b),'local':str(p)})
 # Prior verified transport remains read-only; rehash every member actually referenced.
 transport=json.loads((ROOT/'r1_work/inputs/INPUT_TRANSPORT_MANIFEST.json').read_text())
 for r in transport['members']:
  p=pathlib.Path(r['local']);assert p.exists() and sha(p.read_bytes())==r['sha256'],str(p)
  selected.append({**r,'verified_this_work':True})
 inventory=json.loads((ROOT/'audit_input/NESTED_ARCHIVE_INVENTORY.json').read_text())
 for arc in inventory['archives']:
  if arc['sha256'].startswith(('e3d349','b91b15')):
   prefix='e3d349607207' if arc['sha256'].startswith('e3d349') else 'b91b15dab231'
   for r in arc.get('members',[]):
    if r['name'].startswith(('private/BASELINE','private/QUALITY_COMMON','private/QUALITY_TEACHERS','inputs/COMMON_EVAL_MASK','inputs/FROZEN_ENTRY','inputs/models/MOVE_P','private/models/MOVE_U')) and not r['name'].endswith('.npz'):
     p=ROOT/'audit_input/selected'/prefix/r['name']
     # Resolve members unavailable as a local transport from the certified nested archive.
     if not p.exists():
      zb=d.read_bytes()
      for member in arc['chain'].split('!')[1:]: zb=zipfile.ZipFile(io.BytesIO(zb)).read(member)
      b=zipfile.ZipFile(io.BytesIO(zb)).read(r['name']);p=OUT/'sources'/prefix/r['name'];p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(b)
     b=p.read_bytes();assert sha(b)==r['sha256'],str(p)
     selected.append({'archive_sha256':arc['sha256'],'member':r['name'],'bytes':len(b),'sha256':sha(b),'local':str(p)})
 w=json.loads((ROOT/'workflow_audit/WORKFLOW_TRIGGER_PARSED.json').read_text())
 matches=[]
 for r in w['workflows']:
  on=r.get('triggers',{})
  push=on.get('push') if isinstance(on,dict) else None
  if isinstance(push,dict):
   branches=push.get('branches');ignored=push.get('branches-ignore',[])
   if (branches is None or any(fnmatch.fnmatchcase(BRANCH,b) for b in branches)) and not any(fnmatch.fnmatchcase(BRANCH,b) for b in ignored):matches.append({'path':r['path'],'push':push})
  elif isinstance(on,list) and 'push' in on:matches.append({'path':r['path'],'push':True})
 save('evidence/WORKFLOW_TRIGGER_CHECK.json',{'exact_jst':now(),'workflow_N':len(w['workflows']),'parse_errors':w['parse_errors'],'branch':BRANCH,'push_matches':matches,'tree_authority':'428c3bf52fe7f232ceba641f023a5e6862374dcc','cached_parse_sha256':sha((ROOT/'workflow_audit/WORKFLOW_TRIGGER_PARSED.json').read_bytes()),'dispatches':0,'skip_ci_alone_proof':False})
 save('evidence/SOURCE_MANIFEST.json',{'exact_jst':now(),'scope':'selected members and prior transport only; not whole archives re-audited','members':selected,'A_sha256':sha(a.read_bytes()),'D_sha256':sha(d.read_bytes()),'B_external_zip':'not mounted; original common scores and pinned Rank contract reused, no external ZIP verification claimed','C_archive_sha256':'e3d3496072075a7929bdaca726e73f020cbee83aec7954fc153934ba5b9f0c6d','protected_payloads_opened':0})
 print(json.dumps({'selected_member_N':len(selected),'workflow_N':len(w['workflows']),'push_matches':matches,'exact_jst':now()}))
if __name__=='__main__': run()
