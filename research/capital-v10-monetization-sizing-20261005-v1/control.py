"""Separate append-only sizing cycle; immutable parents, no order interfaces."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json, gzip, hashlib
ROOT=Path(__file__).resolve().parents[2]
CODE=Path(__file__).resolve().parent
WORK=ROOT.parent/'v10_work';PRIVATE=WORK/'private';AUTH=WORK/'authority'
V9PRIVATE=AUTH/'v9/private';MAIN=AUTH/'main';QUALITY=AUTH/'quality_original';RECOVERY=AUTH/'quality'
OUT=ROOT/'docs/evidence/capital-v10-monetization-sizing-20261005-v1'
PARENT=ROOT/'docs/evidence/capital-v9-quality-aware-max3-integration-20261005-v1'
B2=ROOT/'docs/evidence/capital-v8r1-cash-constrained-online-max3-20261005-v1'
V5=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1'
SPLIT=ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json'
BRANCH='capital-v10-monetization-sizing-20261005'
V9_SHA='0672aa0fe04afb304f10391ed9634c1da08ee4f8'
MAIN_SHA='b1abed001c8d8918d4a40776068a0eff384c7b18'
QUALITY_SHA='a977e30aa3318f639569f806f389acb99b3596e4'
I2='QUALITY_PARETO_U2_U3_TENURE_MAX3_V1'
ARMS=['I2_EQUAL_WEIGHT_SIZING_V1','I2_CONSENSUS_MINRANK_SIZING_V1']
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
ZERO={k:0 for k in ('newFits','rank_fits','quality_fits','realized_teacher_fits','HF1_HL0_refits','calibration','threshold_search','grid','retune','result_rescue','v5_replay','v9_I2_replay','old_Oracle_solve','replacement','forced_exit','later_topup','forced_backfill','orders','main_merge','force_push','provider_request','Claude','fresh_open','old_evidence_rewrite')}
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:return [json.loads(z) for z in f if z.strip()]
def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def gzsave(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    raw=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False) for r in data)+'\n').encode()
    with p.open('xb') as f:f.write(gzip.compress(raw,mtime=0))
def counts():
    n=[int((PRIVATE/f'{a}_COMPLETE.json').exists()) for a in ARMS]
    return ZERO|{'S1_replay':n[0],'S2_replay':n[1],'SizingReplays':sum(n)}
def checkpoint(name,result,next_policy):
    basis=read(WORK/'latest_basis.json')
    o={'checkpoint':name,'exact_jst':now(),'branch':BRANCH,'basis_HEAD':basis['HEAD'],'basis_tree':basis['tree'],'v9_parent_SHA':V9_SHA,'Main_parent_SHA':MAIN_SHA,'Quality_parent_SHA':QUALITY_SHA,'current_state':name,'completed':True,'result':result,'next_policy':next_policy,'counts':counts(),'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False}
    save(OUT/'checkpoints'/f'{name}.json',o)
    p=OUT/'WORK_STATUS_LOG.jsonl';prior=p.read_bytes() if p.exists() else b''
    with p.open('ab') as f:f.write((json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode())
    assert p.read_bytes().startswith(prior)
    return o
