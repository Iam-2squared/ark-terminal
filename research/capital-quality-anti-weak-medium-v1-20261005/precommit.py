"""Q3 exact inherited X/model/split and outcome-independent metric definitions."""
import ast
import importlib.util
import numpy as np
import sklearn
from control import *

def main():
    old=ROOT/'research/capital-vnext-v2-movement-20261004-v1'
    original=read(ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1/MODEL_PRECOMMIT.json')
    fields=original['numeric_matrix_order']['MOVE_P'];cats=original['categorical_matrix_order']
    assert len(fields)==46 and len(cats)==7
    assert sklearn.__version__==original['sklearn_version'] and np.__version__==original['numpy_version']
    text=(old/'model.py').read_text();tree=ast.parse(text)
    functions={n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
    generated='"""Exact inherited Movement preprocessing/prediction functions; no fits."""\nimport numpy as np\nUNKNOWN="__UNKNOWN__"\nCATEGORICAL='+repr(cats)+'\n\n'+functions['transform']+'\n\n'+functions['predict_saved']+'\n'
    p=Path(__file__).parent/'movement_preprocessing.py'
    with p.open('x') as f:f.write(generated)
    spec=importlib.util.spec_from_file_location('exact_move_preprocessing',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    runtime=rows(INPUTS/'RUNTIME_CAUSAL.jsonl.gz');rm={r['entry_id']:r for r in runtime}
    split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')
    validations=[]
    for bl in split['blocks']:
        artifact=read(INPUTS/'models'/f"MOVE_P_BLOCK_{bl['block']:02d}.json")
        train=[rm[k] for k in artifact['train_entry_ids']];test=[r for r in runtime if r['session'] in bl['test']]
        a,z,prep=module.transform(train,test,fields)
        assert prep==artifact['preprocessing'] and artifact['parameters']==original['parameters']
        assert prep['numeric_fields']==fields and prep['categorical_fields']==cats
        for r in train+test:
            assert set(r['numeric'])==set(fields) and set(r['categorical'])==set(cats)
        validations.append({'block':bl['block'],'train_N':len(train),'test_N':len(test),'preprocessing_exact_equal':True,'matrix_columns':a.shape[1]})
    design={'exact_jst':now(),'source_base':BASE,'permanent_freeze':['Selector','Entry','EXIT'],
        'selectedBigWinnerRank':'EXISTING_MOVE_P5','pP_refit_blend_replacement':0,
        'feature_numeric_order':fields,'feature_categorical_order':cats,'pP_in_X':False,'feature_add_delete':0,
        'feature_manifest_sha256':sha(ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1/FEATURE_MANIFEST.json'),
        'source_model_sha256':sha(old/'model.py'),'exact_function_AST_reuse':['transform','predict_saved'],
        'preprocessing_validations':validations,'model':'sklearn.linear_model.LogisticRegression','parameters':original['parameters'],
        'sklearn_version':sklearn.__version__,'numpy_version':np.__version__,'split':split,
        'split_source_sha256':sha(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json'),
        'fit_plan':{'MOVE_U2':8,'MOVE_U3':8,'hard_cap':16,'all_existing_heads':0,'Weak_separate':0},
        'training_only_past_supported':'use only Q2 block-specific past-only labels; train identity exactly MOVE_P5',
        'convergence_policy':'ConvergenceWarning => QUALITY_CONTRACT_FAIL, no config rescue',
        'ROC_AUC':'positive-negative concordance; score ties half credit',
        'PR_AUC':'sklearn average_precision_score; stepwise precision-recall integral',
        'top_fractions':[.10,.20,.30,.40],'bottom_fractions':[.10,.20,.30],
        'fixed_budget_K':'ceil(fraction*common1028)',
        'score_ties':['score descending','Frozen Entry timestamp ascending','symbol ascending','entry_id ascending'],
        'legacy_ML_ties':['ML descending','m5 descending','m3 descending','m2 descending','Entry timestamp ascending','symbol ascending','entry_id ascending'],
        'CORE_control_scores':'raw saved p2/p3; not PAVA m2/m3',
        'conditional_deciles':'per fixed supported test block; pP-descending outcome-free rank j; bin=min(9,floor(10*j/N)); score ties use frozen identity only',
        'conditional_aggregate':'sum valid positive-negative pair concordance / sum valid pairs; never pair-as-independent N',
        'same_session_conditional':'within (session,block,pP decile); session bootstrap only',
        'bootstrap':{'unit':'paired session cluster','resamples':1999,'seed':5701005,'quantiles':[.025,.975],'method':'linear','deciles':'frozen before resampling','single_class':'discard and report'},
        'ordinal_percentile':'(average ascending score rank-1)/(N-1); ties share percentile',
        'NDCG_gain':[0,1,3,7,15],'NDCG_discount':'1/log2(rank+1)','NDCG_budgets':[.10,.20,.30,.40],
        'AntiWeak_gates':['AUC>CORE_H2','PR>CORE_H2','Top20 below2 lower','Top30 below2 lower','block AUC improves>=5/8','catastrophic0 and comparable8/8','pP conditional > CORE_H2 conditional','integrity0'],
        'MediumPlus_gates':['AUC>CORE_H3','PR>CORE_H3','Top20 U3 density higher','Top30 U3 capture higher','block AUC improves>=5/8','catastrophic0 and comparable8/8','pP conditional > CORE_H3 conditional','integrity0'],
        'catastrophic':'control AUC>=.5; candidate<.5; delta<=-.10',
        'status':'All point gates PASS + AUC delta CI lower>0 => STRONG; point PASS + CI crosses0 => PROMISING; point gate fail => NO_GO; integrity violation => QUALITY_CONTRACT_FAIL',
        'final_status_mapping':'Both STRONG=>ANTI_WEAK_MEDIUM_STRONG; both point PASS=>ANTI_WEAK_MEDIUM_PROMISING; only U2=>ANTI_WEAK_ONLY; only U3=>MEDIUM_PLUS_ONLY; neither=>QUALITY_NO_GO',
        'BigMega_guard':'Top30 U5/U10 capture vs frozen pP; both>= preserving; one>= partial; neither not preserving; diagnostic only',
        'realized_PnL':'diagnostic only <=0, <=-1%, <=-3%, >=+1%',
        'combined_score_threshold_allocator_capital_replay':0,'fresh_OOS_claim':False,'productionReady':False,
        'Safety':SAFETY,'exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE',
        'independent_audit':'Separate process; trainer/evaluator/metrics imports0; raw source labels, preprocessing and all metrics reconstructed; coefficient/intercept compared to separate fitted-state snapshots; no audit refits'}
    save(OUT/'FEATURE_MODEL_SPLIT_PRECOMMIT.json',design)
    save(OUT/'CODE_PRECOMMIT.json',{'exact_jst':now(),'files':{p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},
        'fits_before_precommit':0,'new_head_results_seen_before_gate_freeze':0,'auditor_refits':0})
    checkpoint('Q3_FEATURE_MODEL_SPLIT_PRECOMMIT','COMPLETE',['Exact46+7 manifest and preprocessing matched8/8',
        'Model/split/metrics/gates/bootstrap/ties precommitted'],{'planned_fits':16,'preprocessing_mismatch_N':0,'search0':True},'Q4 zero-fit baseline; then Q5 claim before fit')
    print({'preprocessing_exact_blocks':8,'fit_plan':16,'features':(46,7)})

if __name__=='__main__':main()
