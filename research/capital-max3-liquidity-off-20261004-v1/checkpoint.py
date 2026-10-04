"""Append-only MAX3 Liquidity-OFF research checkpoints."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,subprocess

NAME='capital-max3-liquidity-off-20261004-v1'
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/evidence'/NAME
PRIVATE=ROOT.parent/'capital_liquidity_off_private'
V2=ROOT.parent/'capital_v2_private'
CONTROL_HEAD='c27413bd681ce2cb5587fa4e692526ca97590a0a'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
 'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed',
 'productionUpdateAllowed','transmitted','productionReady')}
EXPOSURE={'Development_sessions':58,'warmup':20,'OOF':38,'Protected':0,'Holdout':0,
 'Fresh':0,'Validation':0,'OOS':0,'Prospective':0}
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False);f.write('\n')
def checkpoint(label,status,results,blockers=(),next_direction='',extras=()):
 assert git('branch','--show-current')=='capital-state9-vnext-20261004'
 sources=PRIVATE/'SOURCE_MANIFEST.json'
 rec={'jst':now(),'repo':'Iam-2squared/ark-terminal','branch':git('branch','--show-current'),
  'basis_head':git('rev-parse','HEAD'),'result_commit_receipt':f'receipts/{label}.json',
  'source_hashes':json.loads(sources.read_text()) if sources.exists() else {},
  'config_hash':sha(OUT/'DESIGN_PRECOMMIT.json') if (OUT/'DESIGN_PRECOMMIT.json').exists() else None,
  'feature_manifest_hash':sha(ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1/FEATURE_MANIFEST.json'),
  'score_hash':sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz'),
  'new_fit_count':0,'primary_replay_count':int((PRIVATE/'LIQUIDITY_OFF_MAX3_RESULT.json').exists()),
  'MAX4_MAX5_replay_count':0,'current_status':status,'results':results,'blockers':list(blockers),
  'next_direction':next_direction,'exposure':EXPOSURE,'orders':0,'safety':SAFETY}
 save(OUT/'checkpoints'/f'{label}.json',rec)
 subprocess.run(['git','add','--sparse','--',str(OUT.relative_to(ROOT)),
  str(Path(__file__).parent.relative_to(ROOT)),*extras],cwd=ROOT,check=True)
 print(json.dumps({'checkpoint':label,'basis_head':rec['basis_head'],'status':status}))
