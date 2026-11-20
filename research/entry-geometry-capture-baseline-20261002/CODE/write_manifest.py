#!/usr/bin/env python3
"""Hash the completed checkpoint tree immediately after C6 stamping, before GitHub save."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
cp=json.loads((P/'CHECKPOINTS/C6_INTERPRETATION.json').read_text())
files=[]
for f in sorted(P.rglob('*')):
 if not f.is_file() or f.name=='MANIFEST.json' or '__pycache__' in f.parts:continue
 b=f.read_bytes();files.append(dict(path=str(f.relative_to(P)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),git_blob_sha=hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()))
obj=dict(document_id='WORK_ENTRY_GEOMETRY_CAPTURE_BASELINE_20261002_V1',
 status=['ENTRY_GEOMETRY_BASELINE_AUDIT_PASS','HYBRID_ENTRY_NEXT_SPEC_DRAFT_READY'],next_spec_status='PROPOSED_NOT_AUTHORIZED',
 saved_at_jst=cp['saved_at_jst'],basis_head=cp['basis_head'],result_head_authority='GitHub C6 commit; no future SHA predicted',
 population_N=2155,arm_rows=4310,sessions=58,symbols=950,
 state9_rc2='NOT_AVAILABLE_EXACT_SOURCE_JOIN_NOT_CERTIFIED',source_manifest='SOURCE_MANIFEST.json',
 files=files,manifest_self_hash='Excluded to avoid self-reference; Git blob/commit is its authority',
 geometry_aliases=['GEOMETRY_ROWS.jsonl.gz','JOINED_GEOMETRY_ROWS.jsonl.gz'],exposure_and_budget=cp['exposure_and_budget'],safety=cp['safety'])
(P/'MANIFEST.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(manifest_files=len(files),status=obj['status'])))
