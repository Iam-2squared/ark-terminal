"""One finite offline cycle, immutable parents and exclusive artifacts."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json, gzip, hashlib
ROOT=Path(__file__).resolve().parents[2]
CODE=Path(__file__).resolve().parent
WORK=ROOT.parent/'v11_work'; PRIVATE=WORK/'private'; AUTH=WORK/'authority'
V10=AUTH/'v10'; V9=AUTH/'v9'; MAIN=AUTH/'main'; QUALITY=AUTH/'quality_original'
OUT=ROOT/'docs/evidence/capital-v11-realized-monetization-signal-20261005-v1'
PARENT=ROOT/'docs/evidence/capital-v10-monetization-sizing-20261005-v1'
NEG=ROOT/'docs/evidence/capital-max3-top3-quality-v3-20261004-v1'
MOV=ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1'
SPLIT=ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json'
BRANCH='capital-v11-realized-monetization-signal-20261005'
PARENT_SHA='fe300dadf75867e3437cecfadd7e5317beaaa397'
PACK=ROOT.parent/'Ark_Capital_v10_Monetization_Sizing_20261005_PRIVATE.zip'
PACK_SHA='c4e64c6f8c4657509b530419b52cabcefc3e000d2db85cd521b97f0720327f04'
I2='QUALITY_PARETO_U2_U3_TENURE_MAX3_V1'
ARMS=['I2_MRET_CONTINUOUS_CAP_THROTTLE_V1','I2_MRET_MEDIAN_MINLOT_THROTTLE_V1']
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
ZERO={k:0 for k in ('pP_fits','MOVE_U2_fits','MOVE_U3_fits','HF1_fits','HL0_fits','other_model_fits','within_block_refits','calibration','hyperparameter_search','feature_search','teacher_sweep','threshold_sweep','grid','retune','result_rescue','control_replays','old_oracle_solve','replacement','forced_exit','later_topup','backfill','orders','main_merge','force_push','provider_request','Claude','fresh_open','old_evidence_rewrite')}
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(s) for s in f if s.strip()]
def save(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(o,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def gzsave(p,rr):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    b=('\n'.join(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False) for x in rr)+'\n').encode()
    with p.open('xb') as f:f.write(gzip.compress(b,mtime=0))
def counts():
    fits=len(list((PRIVATE/'claims').glob('MRET_BLOCK_*_COMPLETE.json')))
    replays=[int((PRIVATE/f'{a}_COMPLETE.json').exists()) for a in ARMS]
    return ZERO|{'newFits':fits,'MRET_fits':fits,'M1_replay':replays[0],'M2_replay':replays[1],'CapitalReplays':sum(replays)}
def checkpoint(name,result,next_policy):
    b=read(WORK/'latest_basis.json');assert b['actual_GET_verified']
    o={'checkpoint':name,'exact_jst':now(),'branch':BRANCH,'basis_HEAD':b['HEAD'],'basis_tree':b['tree'],'v10_parent_SHA':PARENT_SHA,'current_state':name,'completed':True,'result':result,'next_policy':next_policy,'counts':counts(),'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False}
    save(OUT/'checkpoints'/f'{name}.json',o)
    with (OUT/'WORK_STATUS_LOG.jsonl').open('ab') as f:f.write((json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode())
    return o
