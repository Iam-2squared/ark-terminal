"""Research I/O only; immutable v2 trace and entry. No engine, models or provider."""
from pathlib import Path
import datetime, gzip, hashlib, json
from zoneinfo import ZoneInfo
from reused_clock import *

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
INPUT = WORKSPACE/'inputs_v3'
V2 = INPUT/'v2_data'
PUBLIC_V2 = INPUT/'v2_public'
PRIVATE = WORKSPACE/'private_structural_v3'
ENTRY_FILE = V2/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
POLICY = 'STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD'
SAFETY = {k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')}
BUDGET = {k:0 for k in ('new_fits','new_teacher','OOF_model','probability_score_rank','threshold_hyperparameter_feature_search','provider_requests','new_market_data','Entry_replay_refit','State9_full_reconstruction','Path_full_reconstruction','State9_semantic_changes','Path_semantic_changes','profile_changes','M0_changes','v2_replay','old_EXIT_replay','R50_R54_WPSD_Guard_CCMG_PRR','buffer_variants','pivot_threshold_variants','profit_threshold','dwell_stop_count_threshold','model_variants','Hard1','fixed_stop','fixed_trailing','Protected_Fresh_Validation_OOS_Prospective','Reentry','Capital','Portfolio','orders','main_merge','force_push')}
BUDGET.update(new_EXIT_policies=1,local_guard_variants=1)

def now():return datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def load(path):
    p=Path(path)
    with (gzip.open(p,'rt') if p.suffix=='.gz' else p.open()) as f:return json.load(f)

def rows(path):
    with gzip.open(path,'rt') as f:
        for line in f:yield json.loads(line)

def line(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()

def save(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def entries():
    assert sha(ENTRY_FILE)=='e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb','BLOCKED_V3_LINEAGE_MISMATCH'
    watch=list(rows(ENTRY_FILE));selected=[r for r in watch if r['entry_status']=='FIRST_ENTRY']
    assert len(watch)==2155 and len(selected)==1600 and len({r['watch_key'] for r in selected})==1600
    return selected

def trace_path(key):return V2/'FULL_TRACE'/(key.replace('|','_')+'.jsonl.gz')
