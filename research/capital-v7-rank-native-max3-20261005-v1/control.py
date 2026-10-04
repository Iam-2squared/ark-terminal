"""Append-only research IO. No production or order interfaces."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,gzip,hashlib
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent/'v7_work'
PRIVATE=WORK/'private'
INPUT=WORK/'inputs'
OUT=ROOT/'docs/evidence/capital-v7-rank-native-max3-20261005-v1'
CODE=Path(__file__).resolve().parent
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
BASE_COUNTS={k:0 for k in ('new_fits','rank_fits','slot_fits','teacher_regeneration','control_replay','v6_replay','MAX4_MAX5','retune','result_rescue','provider_request','Claude','orders','main_merge','force_push','protected_fresh_holdout_validation_OOS_prospective_open')}
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8') as f:return [json.loads(x) for x in f if x.strip()]
def gzsave(p,rr):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(gzip.compress(('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False) for r in rr)+'\n').encode(),mtime=0))
def checkpoint(name,state,completed,result,next_policy,counts=None):
 basis=read(WORK/'latest_basis.json')
 obj={'checkpoint':name,'exact_jst':now(),'basis_HEAD':basis['HEAD'],'basis_tree':basis['tree'],'current_state':state,'completed':completed,'result':result,'next_policy':next_policy,'counts':BASE_COUNTS|{'oracle_solves':0,'primary_replays':0}|(counts or {}),'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False}
 save(OUT/'checkpoints'/f'{name}.json',obj);return obj
