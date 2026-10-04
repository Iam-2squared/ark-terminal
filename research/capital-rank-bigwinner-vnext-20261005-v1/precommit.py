"""Fix tournament and gate details before reading candidate metrics."""
import json
from control import OUT, ROOT, now, save, sha, checkpoint, SAFETY

def main():
    spec={'exact_jst':now(),'stage':'A','new_fit_budget':0,'candidate_count':2,
        'candidate_fields':{'CURRENT_V4_ML':'ML','EXISTING_MOVE_P5':'pP'},
        'mask_manifest_sha256':sha(OUT/'COMMON_EVAL_MASK_FREEZE.json'),
        'PR_AUC':'average precision, step-wise precision-recall integral; sklearn average_precision_score',
        'ROC_AUC':'pairwise positive/negative concordance; half credit for score ties',
        'top_fraction_K':'ceil(fraction*N); fixed .10/.20/.30; no thresholds or rank-band sweeps',
        'CURRENT_ties':['ML DESC','m5 DESC','m3 DESC','m2 DESC','Frozen Entry timestamp ASC','symbol ASC'],
        'MOVE_ties':['pP DESC','Frozen Entry timestamp ASC','symbol ASC'],
        'bootstrap':{'unit':'paired session cluster','seed':5701005,'resamples':1999,
            'CI_quantiles':[.025,.975],'quantile_method':'linear','single_class':'discard and report N',
            'primary_delta':'U5 ROC-AUC candidate minus supported Current','secondary_deltas':['U5 PR-AUC','U10 ROC-AUC','U10 PR-AUC']},
        'ordinal_order':['>=10','5-<10','3-<5','2-<3','<2'],
        'ordinal_metric':'NDCG at10/20/30 percent; ordinal gains0,1,3,7,15; discount1/log2(rank+1)',
        'session_top3_top5':'diagnostic only; within session with same saved-score ties',
        'calibration':'Associated saved U5 probability-head Brier/logloss diagnostic; ML is not a probability; absent U10 head reported null; no probability-skill claim',
        'catastrophic_block_failure_definition':'Either U5 or U10 block ROC-AUC falls below .5 from Current>=.5, with delta<=-.10. Undefined single-class block fails comparable block gate.',
        'gates':{'A':'U5 ROC-AUC, PR-AUC and top20 density strictly exceed Current',
            'B':'U10 ROC-AUC, PR-AUC and top20 density each >=Current',
            'C':'top20 below2 contamination <=Current',
            'D':'U5 block AUC improves in>=5/8; catastrophic blocks0; bootstrap direction reported',
            'E':'leakage/asof/identity/independent audit mismatch0'},
        'status':{'STRONG':'A/B/C/D/E PASS and U5 AUC delta CI lower>0',
            'PROMISING':'point gates and integrity pass and CI crosses0',
            'NO_GO':'Any point gate fails','LABEL_BLOCKED':'teacher authority unresolved'},
        'winner_priority':['U5 PR-AUC','U5 ROC-AUC','U10 PR-AUC','top20 U5','lower below2','block stability'],
        'optional_stage_B_only_if_stage_A_no_winner':{'head':'MOVE_P10','fit_cap':8,
            'feature_manifest':'exact saved MOVE_P5,46 numeric+7 categorical',
            'preprocessing':'same algorithm, constant0 missing plus indicators, train-only mean/std/vocabulary',
            'parameters':{'C':1.0,'class_weight':None,'max_iter':2000,'penalty':'l2','random_state':57,'solver':'lbfgs'},
            'split':'same8 expanding-origin blocks,20 warmup+38 OOF, no within-block refit',
            'teacher_unknown':'exclude from new training; do not impute0',
            'dual_formula':'(r5+r10)/2, right-continuous training empirical CDF; number training scores<=test decision score divided by training N',
            'dual_ties':['r10 DESC','r5 DESC','Frozen Entry timestamp ASC','stable symbol ASC'],
            'feature_search':0,'hyperparameter_search':0,'weight_or_threshold_search':0},
        'capital_replay':0,'control_replay':0,'MAX3_replay':0,'new_provider':0,'Safety':SAFETY,
        'float_tolerance':1e-12,'count_identity_and_order_tolerance':0,
        'saved_score_regeneration':0,'legacy_current_value_rewrite':0,'fresh_OOS_claim':False}
    save(OUT/'TOURNAMENT_PRECOMMIT.json',spec)
    code=__import__('pathlib').Path(__file__).resolve().parent
    save(OUT/'STAGE_A_CODE_PIN.json',{'exact_jst':now(),'code':{p.name:sha(p) for p in code.glob('*.py')},
        'scores_not_read_for_candidate_metrics_before_pin':True,'new_fits':0,'replays':0})
    checkpoint('R4_EXISTING_SCORE_TOURNAMENT_PRECOMMIT','STAGE_A_READ_ONLY_TOURNAMENT_COMMITTED_BEFORE_EXECUTION',
        ['Mask/score fields/ties/metrics/bootstrap/catastrophe and selection gates fixed before comparison'],
        {'precommit_sha256':sha(OUT/'TOURNAMENT_PRECOMMIT.json'),'new_fits':0,'replays':0,'StageA_candidate_N':2},
        'After actual GET confirms precommit, execute one saved-score tournament; no Rank fit or Capital replay')

if __name__=='__main__':main()
