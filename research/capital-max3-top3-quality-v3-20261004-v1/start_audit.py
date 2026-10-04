"""Read-only latest and frozen-source audit. No outcome measurement or fit."""
from pathlib import Path
import json
from checkpoint import *
assert git('rev-parse','HEAD')==CONTROL_HEAD
assert git('rev-parse','origin/capital-state9-vnext-20261004')==CONTROL_HEAD
assert not git('status','--porcelain') or all(NAME in x for x in git('status','--porcelain').splitlines())
base=ROOT.parent
sources=[V2/'RUNTIME_CAUSAL.jsonl.gz',V2/'TEACHERS_EVALUATION.jsonl.gz',V2/'CORE_P5_SCORE_STREAM.jsonl.gz',base/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz',base/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz',base/'work_inputs/exit_v3/REPLAY_ROWS.jsonl.gz']
sources+=sorted((V2/'models').glob('CORE_P_BLOCK_*.json'))
sources+=[base/'capital_liquidity_off_private'/s for s in ('LIQUIDITY_OFF_MAX3_RESULT.json','LIQUIDITY_OFF_MAX3_DECISIONS.jsonl.gz','LIQUIDITY_OFF_MAX3_TRADES.jsonl.gz','LIQUIDITY_OFF_MAX3_CURVE.jsonl.gz','LIQUIDITY_OFF_MAX3_INTENTS.jsonl.gz','OLD_REJECT52_LEDGER.jsonl.gz')]
assert len(list((V2/'models').glob('CORE_P_BLOCK_*.json')))==8
manifest={str(p.relative_to(base)):sha(p) for p in sources}
assert manifest['capital_v2_private/CORE_P5_SCORE_STREAM.jsonl.gz']=='a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731'
save(PRIVATE/'SOURCE_MANIFEST.json',manifest)
refs={}
for parent in (ROOT/'docs/evidence',ROOT/'research'):
 for name in ('capital-state9-vnext-20261004-v1','capital-vnext-bigwinner-20261004-v1','capital-vnext-v2-movement-20261004-v1','capital-max3-liquidity-off-20261004-v1'):
  for p in (parent/name).rglob('*'):
   if p.is_file() and '__pycache__' not in str(p):refs[str(p.relative_to(ROOT))]=sha(p)
p=ROOT/'docs/policies/CAPITAL_MAX_CONCURRENT_3_RESEARCH_POLICY_V1.md';assert p.exists();refs[str(p.relative_to(ROOT))]=sha(p)
save(PRIVATE/'REFERENCE_READ_ONLY_HASHES.json',refs)
save(OUT/'START_AUDIT.json',{'jst':now(),'instruction_basis':CONTROL_HEAD,'latest_remote_head':git('rev-parse','origin/capital-state9-vnext-20261004'),'additional_commits':0,'reconciliation':'Latest equals instruction basis; frozen references unchanged.','source_hashes':manifest,'reference_namespace_file_N':len(refs),'control_replays':0,'H5_new_fits':0,'MAX4_MAX5_replays':0,'Frozen_entry':'4a2d6f35946b16820a13449a9288a6685a5c283c','Frozen_exit':'c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad','exit_receipt':'1ecbcc43f75279fa302f19fd896add2aac15b537','policy':'CAPITAL_MAX_CONCURRENT_3_RESEARCH_POLICY_V1','exposure':EXPOSURE,'safety':SAFETY,'orders':0})
checkpoint('Q0_START_LATEST_AUDIT','VNEXT_V3_START_AUDITED',{'latest':CONTROL_HEAD,'additional_commits':0,'sources':len(sources)},next_direction='Freeze Control, objectives, CORE-only manifest and single Main design before outcome evaluation.')
