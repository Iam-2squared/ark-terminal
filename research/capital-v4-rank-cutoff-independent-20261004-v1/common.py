"""Frozen-rank diagnostic IO. No model fitting or trading operations."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent
CODE=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/capital-v4-rank-cutoff-independent-20261004-v1'
PRIVATE=WORK/'capital_v4_rank_cutoff_private'
FROZEN=WORK/'capital_staircase_v4_private'
SRC=WORK/'inputs/v3'
PROFILE='B_PLUS_MAX3'
PROFILES=('S_ONLY_MAX3','A_PLUS_MAX3','B_PLUS_MAX3')
ALLOWED={'S_ONLY_MAX3':{'S'},'A_PLUS_MAX3':{'S','A'},'B_PLUS_MAX3':{'S','A','B'}}
BASIS='dd35da3fc19770823b3844e2e2798e6c1e9a91d3'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
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
def checkpoint(name,status,results=None,next_direction='Continue frozen independent diagnostic; no promotion.'):
 remote=json.loads((WORK/'rank_cutoff_publish_state.json').read_text())['remote']
 hashes=json.loads((OUT/'SOURCE_HASHES.json').read_text()) if (OUT/'SOURCE_HASHES.json').exists() else {}
 obj={'checkpoint':name,'JST':now(),'repo':'Iam-2squared/ark-terminal','branch':remote['branch'],'instruction_basis_HEAD':BASIS,'basis_HEAD':remote['head'],'basis_tree':remote['tree'],'actual_result_HEAD_tree':'Separately appended actual postcommit GET receipt; no future SHA fabricated.','status':status,'source_hashes':hashes,'config_hash':sha(OUT/'DIAGNOSTIC_CONFIG.json') if (OUT/'DIAGNOSTIC_CONFIG.json').exists() else None,'score_hash':sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),'new_fit':0,'replay_counts':{p:int((PRIVATE/f'{p}_STARTED.json').exists()) for p in PROFILES},'v4_main_replay':0,'control_replay':0,'MAX4_MAX5':0,'results':results or {},'blockers':[],'next_direction':next_direction,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','overfit_risk':'Same 58 Development sessions repeatedly used across cycles; not fresh/OOS.','protected_holdout_fresh_validation_OOS_prospective_opened':0,'Safety':SAFETY,'orders':0,'main_merge':0,'force_push':0,'new_provider_requests':0,'retune':0,'Frozen_changes':0}
 save(OUT/'checkpoints'/f'{name}.json',obj)
