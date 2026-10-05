"""Separate finite certification cycle; zero optimizer and old signal-evaluation calls."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,gzip,hashlib
ROOT=Path(__file__).resolve().parents[2];CODE=Path(__file__).resolve().parent
WORK=ROOT.parent/'v11r1_work';PRIVATE=WORK/'private';AUTH=WORK/'authority'
V11=AUTH/'v11';V10=AUTH/'v10';V9=AUTH/'v9';MAIN=AUTH/'main';QUALITY=AUTH/'quality_original'
OUT=ROOT/'docs/evidence/capital-v11r1-numeric-cert-recovery-20261005-v1'
PARENT=ROOT/'docs/evidence/capital-v11-realized-monetization-signal-20261005-v1'
B2=ROOT/'docs/evidence/capital-v8r1-cash-constrained-online-max3-20261005-v1'
V5=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1'
SPLIT=ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json'
BRANCH='capital-v11r1-numeric-cert-recovery-20261005'
PARENT_SHA='489fc4f9bc164b3150e374e9f4011a9888ad2d55'
PACK=ROOT.parent/'Ark_Capital_v11_Realized_Monetization_Signal_20261005_PRIVATE_CONTRACT_FAIL.zip'
PACK_SHA='134977744baab20ea75310d8c263322281d4f8289ad60afdd1a6b83e3875156f'
I2='QUALITY_PARETO_U2_U3_TENURE_MAX3_V1'
ARMS=['I2_MRET_CONTINUOUS_CAP_THROTTLE_V1','I2_MRET_MEDIAN_MINLOT_THROTTLE_V1']
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
ZERO={k:0 for k in ('newFits','refits','audit_refits','optimizer_calls','primary_signal_evaluations','bootstrap_reruns','threshold_sweep','teacher_change','feature_change','policy_change','calibration','grid','retune','result_rescue','control_replays','old_oracle_solve','replacement','forced_exit','later_topup','backfill','orders','main_merge','force_push','provider_request','Claude','fresh_open','old_evidence_rewrite','tolerance_relaxation')}
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
    raw=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False) for r in rr)+'\n').encode()
    with p.open('xb') as f:f.write(gzip.compress(raw,mtime=0))
def counts():
    n=[int((PRIVATE/f'{a}_COMPLETE.json').exists()) for a in ARMS]
    return ZERO|{'reusedMRETFits':8 if (OUT/'MRET_COMPLETED_FITS_REUSE_FREEZE.json').exists() else 0,'M1_replay':n[0],'M2_replay':n[1],'CapitalReplays':sum(n)}
def checkpoint(name,result,next_policy):
    b=read(WORK/'latest_basis.json');assert b['actual_GET_verified']
    o={'checkpoint':name,'exact_jst':now(),'branch':BRANCH,'basis_HEAD':b['HEAD'],'basis_tree':b['tree'],'v11_parent_SHA':PARENT_SHA,'current_state':name,'completed':True,'result':result,'next':next_policy,'counts':counts(),'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False}
    save(OUT/'checkpoints'/f'{name}.json',o)
    with (OUT/'WORK_STATUS_LOG.jsonl').open('ab') as f:f.write((json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode())
    return o
