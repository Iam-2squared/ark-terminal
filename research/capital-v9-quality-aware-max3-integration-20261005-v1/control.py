"""Isolated, append-only Development integration; no order interfaces."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json, gzip, hashlib
ROOT = Path(__file__).resolve().parents[2]
CODE = Path(__file__).resolve().parent
WORK = ROOT.parent / 'v9_work'
PRIVATE = WORK / 'private'
AUTH = ROOT.parent / 'v9_authorities'
MAIN = AUTH / 'main'
QUALITY = AUTH / 'quality_original'
RECOVERY = AUTH / 'quality'
OUT = ROOT / 'docs/evidence/capital-v9-quality-aware-max3-integration-20261005-v1'
PARENT = ROOT / 'docs/evidence/capital-v8r1-cash-constrained-online-max3-20261005-v1'
V7 = ROOT / 'docs/evidence/capital-v7-rank-native-max3-20261005-v1'
V5 = ROOT / 'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1'
SPLIT = ROOT / 'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json'
BRANCH = 'capital-v9-quality-aware-max3-20261005'
MAIN_SHA = 'b1abed001c8d8918d4a40776068a0eff384c7b18'
QUALITY_SHA = 'a977e30aa3318f639569f806f389acb99b3596e4'
ARMS = ['QUALITY_PARETO_U2_TENURE_MAX3_V1', 'QUALITY_PARETO_U2_U3_TENURE_MAX3_V1']
SAFETY = {k: False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
ZERO = {k: 0 for k in ('newFits','new_rank_fits','MOVE_U2_fits','MOVE_U3_fits','slot_ML_fits','teacher_regeneration','calibration','threshold_search','grid','v5_replay','v7_A1_replay','v7_A2_replay','v8R1_B1_replay','v8R1_B2_replay','old_Oracle_solve','pP_clairvoyant_solve','MAX4_MAX5','replacement','result_rescue','retune','orders','main_merge','force_push','provider_request','Claude','fresh_open','Quality_history_merge','old_evidence_rewrite')}
def now(): return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f: return [json.loads(s) for s in f if s.strip()]
def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f: json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def gzsave(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    raw=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False) for r in data)+'\n').encode()
    with p.open('xb') as f: f.write(gzip.compress(raw,mtime=0))
def counts():
    n=sum((PRIVATE/f'{a}_COMPLETE.json').exists() for a in ARMS)
    return ZERO | {'I1_replay':int((PRIVATE/f'{ARMS[0]}_COMPLETE.json').exists()),'I2_replay':int((PRIVATE/f'{ARMS[1]}_COMPLETE.json').exists()),'CapitalReplays':n}
def checkpoint(name,result,next_policy):
    basis=read(WORK/'latest_basis.json')
    o={'checkpoint':name,'exact_jst':now(),'branch':BRANCH,'basis_HEAD':basis['HEAD'],'basis_tree':basis['tree'],'Main_parent_SHA':MAIN_SHA,'Quality_parent_SHA':QUALITY_SHA,'current_state':name,'completed':True,'result':result,'next_policy':next_policy,'counts':counts(),'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False}
    save(OUT/'checkpoints'/f'{name}.json',o)
    p=OUT/'WORK_STATUS_LOG.jsonl';prior=p.read_bytes() if p.exists() else b''
    with p.open('ab') as f:f.write((json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode())
    assert p.read_bytes().startswith(prior)
    return o
