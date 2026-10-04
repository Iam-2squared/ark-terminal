"""Capital v5 fixed-development IO; no fitting, providers or trading operations."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip, hashlib, json
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent
CODE=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1'
PRIVATE=WORK/'capital_v5_slot_private'
SOURCE=WORK/'source_main'
FROZEN=SOURCE/'capital_staircase_v4_private'
SRC=SOURCE/'inputs/v3'
BASIS='45d98b6338c1fd7d40b9b26f8ba433dba964e0c5'
PROFILE='CAPITAL_MAX3_SLOT_RESERVE_V1'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt')]
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf8') as f:json.dump(x,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def gzwrite(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 data=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False) for r in x)+'\n').encode()
 with p.open('xb') as f:f.write(gzip.compress(data,mtime=0))
def checkpoint(name,status,result=None,next_direction='Continue precommitted one-shot v5; no retune or promotion.',blockers=None):
 remote=json.loads((WORK/'remote_state.json').read_text())
 source=json.loads((OUT/'SOURCE_HASHES.json').read_text()) if (OUT/'SOURCE_HASHES.json').exists() else {}
 obj={'checkpoint':name,'JST':now(),'repo':remote['repo'],'branch':remote['branch'],'instruction_basis_HEAD':BASIS,'basis_HEAD':remote['head'],'basis_tree':remote['tree'],
 'actual_result_HEAD_tree':'Recorded in the separately appended postcommit GET receipt; not predicted.',
 'hashes':{'source':source,'code':{p.name:sha(p) for p in CODE.glob('*.py')},'config':sha(OUT/'POLICY_PRECOMMIT.json') if (OUT/'POLICY_PRECOMMIT.json').exists() else None,'model':json.loads((FROZEN/'MODEL_HASHES.json').read_text()),'score':sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')},
 'status':status,'result':result or {},'blocker':blockers or [],'next':next_direction,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','overfit_risk':'Same 58 Development sessions repeatedly reused; 38 OOF evaluation days are not fresh/OOS.',
 'protected_holdout_fresh_validation_OOS_prospective_opened':0,'new_provider':0,'new_fit':0,'retune':0,'Claude':0,'orders':0,'main_merge':0,'force_push':0,'control_replay':0,'Frozen_changes':0,'MAX4_MAX5':0,'Movement_use':0,'HF1_HL0_use':0,'Safety':SAFETY}
 save(OUT/'checkpoints'/f'{name}.json',obj)
