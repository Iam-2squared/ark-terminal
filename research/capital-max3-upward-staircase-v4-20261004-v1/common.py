"""Research-only immutable IO and receipts; no trading/provider operations."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip, hashlib, json, os
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent
SRC=Path(os.environ.get('ARK_V4_SOURCE',str(WORK/'inputs/v3')))
PRIVATE=WORK/'capital_staircase_v4_private'
OUT=ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1'
CODE=Path(__file__).resolve().parent
PROFILE='UPWARD_STAIRCASE_V4_MAX3'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
EXPOSURE='ITERATIVE_DEVELOPMENT_EVIDENCE'
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt')]
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,sort_keys=True,indent=2,allow_nan=False,ensure_ascii=False);f.write('\n')
def gzwrite(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 data=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False) for r in x)+'\n').encode()
 with p.open('xb') as f:f.write(gzip.compress(data,mtime=0))
def source_books():return {r['entry_id']:r for r in rows(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
def checkpoint(name,status,results=None,next_direction='Continue fixed one-shot contract.'):
 state=json.loads((WORK/'publish_state.json').read_text());remote=state['remote']
 src=json.loads((OUT/'SOURCE_HASHES.json').read_text()) if (OUT/'SOURCE_HASHES.json').exists() else {}
 models=json.loads((PRIVATE/'MODEL_HASHES.json').read_text()) if (PRIVATE/'MODEL_HASHES.json').exists() else {}
 sc=PRIVATE/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'
 obj={'checkpoint':name,'JST':now(),'repo':'Iam-2squared/ark-terminal','branch':remote['branch'],'instruction_basis_HEAD':'f196722f96347ca5f324d478f98ff8dedd24b6c9','basis_HEAD':remote['head'],'basis_tree':remote['tree'],'actual_result_HEAD_tree':'See separately appended actual postcommit GET receipt; self-referential future SHA not fabricated.','status':status,'source_hashes':src,'feature_hash':sha(OUT/'CORE_FEATURE_MANIFEST.json'),'model_hashes':models,'score_hash':sha(sc) if sc.exists() else None,'PAVA_config_hash':sha(OUT/'PAVA_CONFIG.json') if (OUT/'PAVA_CONFIG.json').exists() else None,'fit_count':{'H2':len(list((PRIVATE/'models').glob('H2_BLOCK_*.json'))),'H3':0,'H5':0,'HF1':0,'HL0':0,'H10':0,'Movement':0},'replay_count':{'v4_main':int((PRIVATE/'MAIN_REPLAY_STARTED.json').exists()),'control':0,'MAX4':0,'MAX5':0,'rank_diagnostics':0,'independent_audit':int((OUT/'INDEPENDENT_AUDIT.json').exists())},'results':results or {},'blockers':[],'next_direction':next_direction,'exposure':EXPOSURE,'protected_holdout_fresh_validation_OOS_prospective_opened':0,'Safety':SAFETY,'orders':0,'main_merge':0,'force_push':0,'new_provider_requests':0,'result_based_retune':0}
 save(OUT/'checkpoints'/f'{name}.json',obj)
