"""Append-only isolated Development research IO; no execution interface."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,gzip,hashlib
ROOT=Path(__file__).resolve().parents[2]
CODE=Path(__file__).resolve().parent
WORK=ROOT.parent/'v8r1_work';PRIVATE=WORK/'private'
PRIOR=ROOT.parent/'v7_work';INPUT=PRIOR/'inputs';PIN=PRIOR/'private'
OUT=ROOT/'docs/evidence/capital-v8r1-cash-constrained-online-max3-20261005-v1'
V7=ROOT/'docs/evidence/capital-v7-rank-native-max3-20261005-v1'
V8=ROOT/'docs/evidence/capital-v8-capacity-aware-online-max3-20261005-v1'
BRANCH='capital-v8r1-cashfix-20261005'
RANK=ROOT/'docs/evidence/capital-rank-bigwinner-vnext-20261005-v1'
ARMS=['CAPACITY_ORDERSTAT_MAX3_V1','TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1']
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
COUNTS={k:0 for k in ('new_rank_fits','new_slot_ML_fits','teacher_regeneration','v5_replay','v6_replay','v7_A1_replay','v7_A2_replay','old_physical_admission_Oracle_solves','old_v8_replay','B1_replay','B2_replay','uniqueness_no_good_solve','independent_full_recalculations','primary_pP_diagnostic_solve','independent_pP_diagnostic_solve','threshold_sweep','grid_search','result_rescue','retune','MAX4_MAX5','replacement','provider_request','Claude','orders','main_merge','force_push','protected_holdout_fresh_validation_OOS_prospective_open')}
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
 obj={'checkpoint':name,'branch':BRANCH,'exact_jst':now(),'basis_HEAD':basis['HEAD'],'basis_tree':basis['tree'],'current_state':state,'completed':completed,'result':result,'next_policy':next_policy,'counts':COUNTS|(counts or {}),'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False}
 save(OUT/'checkpoints'/f'{name}.json',obj)
 # Append generated records only; prior bytes and record ordering are preserved.
 log=OUT/'WORK_STATUS_LOG.jsonl';prior=log.read_bytes() if log.exists() else b''
 with log.open('ab') as f:f.write((json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode())
 assert log.read_bytes().startswith(prior)
 return obj
