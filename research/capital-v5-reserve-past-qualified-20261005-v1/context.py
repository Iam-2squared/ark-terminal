"""Append-only research context. No model inference or market replay on import."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip, hashlib, json, subprocess

REPO = Path(__file__).resolve().parents[2]
SCRATCH = REPO.parent
INPUT = SCRATCH / 'work/bridge_private'
OUT = REPO / 'docs/evidence/capital-v5-reserve-past-qualified-20261005-v1'
PRIVATE = SCRATCH / 'work/r_work/private'
CODE = Path(__file__).resolve().parent
PARENT = '710656491be06235901b45c50a8b5cbd714ba4eb'
BRANCH = 'capital-v5-reserve-past-qualified-20261005'
PROFILE = 'V5_RESERVE_PAST_QUALIFIED_RECOVERY_V1'
SAFETY = dict.fromkeys(['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
    'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed',
    'productionUpdateAllowed','transmitted','productionReady'],False)
ZERO_COUNTS = dict.fromkeys(['newFits','refits','calibration','teacherRegeneration','currentInference',
    'originalAucRecalculation','originalBootstrapRecalculation','BridgeDiagnosticReplay',
    'V5ControlReplays','DDRM1M2Replays','primaryRReplays','independentRReconstructions',
    'providerRequests','Fresh','Claude','orders','mainMerge','forcePush','automaticPromotion',
    'workflowDispatches','workflowCancels','extraArms','OracleSolves'],0)
ROLES = {
 'packet':'bridge_work/private/FROZEN_EXPERT_PACKET.jsonl.gz',
 'reference32':'r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json',
 'canonical_scores':'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz',
 'proposals':'r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz',
 'native_decisions':'r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz',
 'native_trades':'r1_work/runs/OFF_PRIMARY/TRADES.jsonl.gz',
 'native_intents':'r1_work/runs/OFF_PRIMARY/INTENTS.jsonl.gz',
 'native_curve':'r1_work/inputs/v5/capital_v5_slot_private/CAPITAL_MAX3_SLOT_RESERVE_V1_CURVE.jsonl.gz',
 'native_result':'r1_work/inputs/v5/capital_v5_slot_private/CAPITAL_MAX3_SLOT_RESERVE_V1_RESULT.json',
 'candidate_stream':'r1_work/inputs/v5_source/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz',
 'arrival':'r1_work/inputs/v5/repo/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/ARRIVAL_TABLE.json',
 'split':'r1_work/inputs/v5_source/repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json',
 'books':'r1_work/inputs/v5_source/inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz',
 'teachers':'r1_work/metrics/evaluation_only/TEACHERS_EVALUATION.jsonl.gz',
 'outcomes':'r1_work/metrics/evaluation_only/OUTCOMES_EXACT_EVALUATION.json',
 'native_authority':'r1_work/metrics/V5_EXACT_EVALUATION_AUTHORITY.json',
 'protected100':'r1_work/metrics/evaluation_only/PROTECTED100_IDS.json',
 'score_certificate':'r1_work/score_certification/SCORE_REFERENCE_CERTIFICATION.json',
 'materialization_certificate':'r1_work/score_certification/NATIVE_SCORE_MATERIALIZATION_CERTIFICATION.json',
 'original_skill_certificate':'bridge_work/evidence/ORIGINAL_SKILL_REPRODUCTION.json',
 'reference_certificate':'bridge_work/evidence/REFERENCE_HASH_AND_CERTIFICATE_REUSE.json',
 'source_review':'r1_work/metrics/evaluation_only/TEACHER_TRANSPORT_RECEIPT.json',
}
NATIVE_ROOT = INPUT/'r1_work/inputs/v5/repo/research/capital-v5-max3-slot-intelligence-20261004-v1'

def now(): return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(o): return hashlib.sha256(canonical(o)).hexdigest()
def read(role):
    p=INPUT/ROLES.get(role,role)
    if p.suffix=='.gz':
        with gzip.open(p,'rt',encoding='utf-8') as f: return [json.loads(s) for s in f]
    return json.loads(p.read_text(encoding='utf-8'))
def save(name,o,private=False):
    p=(PRIVATE if private else OUT)/name
    p.parent.mkdir(parents=True,exist_ok=True)
    assert not p.exists(),f'APPEND_ONLY_FILE_ALREADY_EXISTS:{p}'
    p.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    return p
def gzsave(name,rows):
    p=PRIVATE/name;p.parent.mkdir(parents=True,exist_ok=True)
    assert not p.exists(),f'APPEND_ONLY_FILE_ALREADY_EXISTS:{p}'
    with p.open('wb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:
            for r in rows:z.write(canonical(r)+b'\n')
    return p
def checkpoint(step,state,result,next_step,counts=None):
    r={'schema':'V5_R_CHECKPOINT_V1','exact_jst':now(),'branch':BRANCH,
       'basis_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
       'basis_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=REPO,text=True).strip(),
       'strategy_parent':PARENT,'policy_sha256':sha(OUT/'DIRECTIVE.txt'),
       'code_hashes':{p.name:sha(p) for p in sorted(CODE.glob('*.py'))},
       'input_binding_sha256':sha(OUT/'INPUT_BINDING.json') if (OUT/'INPUT_BINDING.json').exists() else None,
       'CURRENT_STATE':state,'step':step,'result':result,'NEXT_POLICY':next_step,
       'counts':ZERO_COUNTS| (counts or {}),'Safety':SAFETY,'activeCapitalChampion':'V5',
       'selectedCapitalCandidate':None,'championUpdated':False,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE'}
    save('checkpoints/'+step+'.json',r)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'WORK_STATUS_LOG.jsonl').open('a',encoding='utf-8',newline='\n') as f:f.write(canonical(r).decode()+'\n')
    return r
