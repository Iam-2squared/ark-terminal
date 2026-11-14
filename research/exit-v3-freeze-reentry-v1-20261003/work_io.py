"""Work identity, immutable inputs and safety; no market/model computation."""
from pathlib import Path
from zoneinfo import ZoneInfo
import datetime, hashlib, json

ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[2]
V3=ROOT.parent/'state9-structural-exit-v3-local-guard-20261003'
V4=ROOT.parent/'state9-structural-exit-v4-recovery-failure-20261003'
TRACE=WORK/'inputs_v3/v2_data'
P3=WORK/'private_structural_v3'
PRIVATE=WORK/'private_reentry_v1'
INPUT=WORK/'inputs_reentry'
ENTRY_HEAD='4a2d6f35946b16820a13449a9288a6685a5c283c'
V3_HEAD='c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad'
V4_HEAD='4a5be18763cebb08c658ba7a9725ada979dd80c9'
DOCUMENT='WORK_EXIT_V3_FREEZE_TO_REENTRY_V1_FASTTRACK_20261003'
POLICY='PERSISTENT_REENTRY_V1_P1_Q70_FRESH_CROSS'
BRANCH='exit-v3-freeze-reentry-v1-20261003'
SAFETY={k:False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady']}
BUDGET={k:0 for k in ['EXIT_v3_baseline_new_replay','V4_replay','new_Entry_model_fits','new_EXIT_model_fits','new_teacher','new_score_calculation','threshold_model_feature_search','provider','new_market_data','State9_reconstruction','Path_reconstruction','Entry_changes','EXIT_v3_changes','fixed_stop_profit_trailing','cooldown','reentry_count_cap','Capital','Portfolio_Replay','orders','main_merge','force_push']}
PINS={'RC2_CONTRACT.txt':'45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff','profile.json':'77ee61ba1808a2c17614439fe7d14212a53cbfa7358c032ce16989eeb5248922','source_snapshot.json':'08e1a20a4d022a1429b74387169dd8729a2eaeb4dc0008f3af2b52ec0e661c23','M0.md':'08cad3ca8316ccab644872e3d843e2d491ac6a953a03193d5c391be3bcf73bb3','STATE_PATH_CONTRACT_V1.md':'fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268','PATH_FROZEN.py':'ad59222fcc0f9dfed4698efb49a87d66ea4e01b90562cdcaa8b9bc028ffffbf8'}
def now():return datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def checkpoint(name,basis,status,completed,evidence,next_step,blockers=None,budget=None):
    x={'document_id':DOCUMENT,'checkpoint':name,'saved_at_jst':now(),'actual_basis_head':basis,'current_status':status,'completed':completed,'key_evidence':evidence,'blockers':blockers,'current_direction':'Official V3 freeze; one unchanged P1_Q70 fresh-cross policy, no rescue rules','next_step':next_step,'frozen_boundaries':{'FIRST_ENTRY_HEAD':ENTRY_HEAD,'Entry_N':1600,'EXIT_v3_FINAL_HEAD':V3_HEAD,'V4_rejected_FINAL_HEAD':V4_HEAD,'State9_Path_semantic_changes':0,'LONG_only':True,'cash_equity_only':True,'Capital_pending':True},'budget_exposure':budget or BUDGET,'safety':SAFETY}
    write(ROOT/'CHECKPOINTS'/f'{name}.json',x)
    return x
