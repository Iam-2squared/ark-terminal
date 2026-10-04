"""v6 scoped, append-only evidence IO. No providers or order operations."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent
CODE=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/capital-v6-counterfactual-slot-value-20261004-v1'
PRIVATE=WORK/'capital_v6_slot_private'
V5CODE=ROOT/'research/capital-v5-max3-slot-intelligence-20261004-v1'
V5OUT=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1'
V5PRIVATE=WORK/'capital_v5_slot_private'
SOURCE=WORK/'source_main'
FROZEN=SOURCE/'capital_staircase_v4_private'
SRC=SOURCE/'inputs/v3'
BASIS='710656491be06235901b45c50a8b5cbd714ba4eb'
PROFILE='COUNTERFACTUAL_SLOT_VALUE_V6_MAX3'
STATE=WORK/'v6_remote_state.json'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
EXPOSURE={'classification':'ITERATIVE_DEVELOPMENT_EVIDENCE','development_sessions':58,'reused_development':True,'fresh_OOS_claim':False,'protected_holdout_fresh_validation_OOS_prospective_opened':0,'new_provider':0,'Claude':0}
DO_NOT=['No Winner/rank/Entry/EXIT/MTM/cost/MAX change','No second arm, threshold/feature/model/arrival retune or result rescue','No protected/fresh/holdout opening, production promotion, orders, main merge or force push']
def now(): return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p): return [json.loads(s) for s in gzip.open(p,'rt')]
def save(p,x):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf8',newline='\n') as f: json.dump(x,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False); f.write('\n')
def gzwrite(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(gzip.compress(('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False) for r in x)+'\n').encode(),mtime=0))
def status(checkpoint,phase,current_state,completed=None,not_executed=None,result=None,blockers=None,next_policy=None,counts=None):
 remote=json.loads(STATE.read_text()); OUT.mkdir(parents=True,exist_ok=True)
 obj={'exact_jst':now(),'checkpoint':checkpoint,'phase':phase,'repo':remote['repo'],'branch':remote['branch'],'basis_head':BASIS,'current_head':remote['head'],'current_tree':remote['tree'],'current_state':current_state,'completed':completed or [],'not_executed':not_executed or [],'result_so_far':result or {},'blockers':blockers or [],'next_policy':next_policy or ['Continue frozen one-shot sequence; obey STOP gates'],'do_not':DO_NOT,'exposure':EXPOSURE,'safety':SAFETY,'counts':counts or {'winner_fit':0,'slot_fit':0,'main_replay':0,'v4_v5_control_replay':0,'retune':0,'orders':0,'main_merge':0,'force_push':0},'hashes':{'code':{p.name:sha(p) for p in CODE.glob('*.py')},'source_manifest':sha(OUT/'SOURCE_HASHES.json') if (OUT/'SOURCE_HASHES.json').exists() else None,'teacher_precommit':sha(OUT/'TEACHER_PRECOMMIT.json') if (OUT/'TEACHER_PRECOMMIT.json').exists() else None,'model_precommit':sha(OUT/'SLOT_MODEL_PRECOMMIT.json') if (OUT/'SLOT_MODEL_PRECOMMIT.json').exists() else None,'winner_models':json.loads((FROZEN/'MODEL_HASHES.json').read_text()),'score':sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')},'actual_result_commit_tree':'See append-only postcommit actual GET receipts; not predicted'}
 with (OUT/'WORK_STATUS_LOG.jsonl').open('a',encoding='utf8',newline='\n') as f:f.write(json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
 save(OUT/'checkpoints'/f'{checkpoint}_{phase}.json',obj)
 return obj
