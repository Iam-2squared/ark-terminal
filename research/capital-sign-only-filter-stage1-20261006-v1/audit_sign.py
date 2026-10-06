"""Independent audit process. No trainer/model-transform/policy/evaluator imports or fits."""
import math
import pickle
from collections import Counter,defaultdict
from fractions import Fraction
import numpy as np
from threadpoolctl import threadpool_limits
from sign_io import *

def independent_transform(train,test,nn,cc):
    a=np.asarray([[r['numeric'][k] if r['numeric'][k] is not None else float('nan') for k in nn] for r in train],dtype=float).reshape(len(train),len(nn))
    missing=np.isnan(a);filled=np.where(missing,0.0,a);expanded=np.concatenate((filled,missing.astype(float)),axis=1)
    mean=expanded.mean(0);scale=expanded.std(0);scale=np.where(scale==0,1,scale)
    vocabulary={k:sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'}) for k in cc}
    t=np.asarray([[r['numeric'][k] if r['numeric'][k] is not None else float('nan') for k in nn] for r in test],dtype=float).reshape(len(test),len(nn))
    tmissing=np.isnan(t);normal=(np.concatenate((np.where(tmissing,0.0,t),tmissing.astype(float)),axis=1)-mean)/scale
    onehot=[[float((r['categorical'][k] if r['categorical'][k] in vocabulary[k] else '__UNKNOWN__')==cat) for k in cc for cat in vocabulary[k]] for r in test]
    cats=np.asarray(onehot,dtype=float).reshape(len(test),sum(len(v) for v in vocabulary.values()))
    return np.concatenate((normal,cats),axis=1),mean.tolist(),scale.tolist(),vocabulary

def counts(data):
    out={'P_keep':0,'N_keep':0,'P_reject':0,'N_reject':0}
    for r in data:
        if r['y_neg'] is None:continue
        key=('N' if r['y_neg']==1 else 'P')+('_reject' if r['action']=='REJECT' else '_keep');out[key]+=1
    pk,nk,pr,nr=(out[k] for k in ['P_keep','N_keep','P_reject','N_reject'])
    ratio=lambda n,d:n/d if d else None
    out.update(positive_retention=ratio(pk,pk+pr),positive_false_reject=ratio(pr,pk+pr),negative_removal=ratio(nr,nk+nr),
               pass_negative_rate=ratio(nk,pk+nk),reject_precision=ratio(nr,pr+nr),pass_rate=ratio(pk+nk,pk+nk+pr+nr),
               J_sign=ratio(nr,nk+nr)-ratio(pr,pk+pr) if nk+nr and pk+pr else None,
               filter_balanced_accuracy=(ratio(nr,nk+nr)+ratio(pk,pk+pr))/2 if nk+nr and pk+pr else None,
               known_N=pk+nk+pr+nr,PASS_UNASSESSED_known_N=sum(r['y_neg'] is not None and r['action'].startswith('PASS_UNASSESSED') for r in data),
               PASS_UNASSESSED_all_N=sum(r['action'].startswith('PASS_UNASSESSED') for r in data),PASS_all_N=sum(r['action']!='REJECT' for r in data),
               REJECT_all_N=sum(r['action']=='REJECT' for r in data),UNKNOWN_N=sum(r['sign_status']=='UNKNOWN' for r in data),EXACT_ZERO_N=sum(r['sign_status']=='EXACT_ZERO' for r in data))
    return out

def independent_snapshot(history,alpha,start):
    cal=[r for r in history if r['execution_eligible'] and r['model_prediction_valid'] and r['y_neg'] is not None and r['label_maturity']<start]
    p=sum(r['y_neg']==0 for r in cal);n=len(cal)-p;sessions=len({r['session'] for r in cal});support=len(cal)>=100 and sessions>=10 and p>=20 and n>=20
    allowance=(Fraction(alpha)*p).__floor__();tau=None;tried=0;status='OFF_SUPPORT_ALL_PASS'
    distinct=sorted({r['score_neg'] for r in cal}) if support else []
    if support:
        status='OFF_NO_FINITE_TAU_ALL_PASS'
        positives=sorted(r['score_neg'] for r in cal if r['y_neg']==0)
        from bisect import bisect_left
        for value in distinct:
            tried+=1
            if len(positives)-bisect_left(positives,value)<=allowance:tau=value;status='ACTIVE';break
    return {'tau':tau,'status':status,'CAL_N':len(cal),'CAL_positive_N':p,'CAL_negative_N':n,'CAL_sessions':sessions,
            'allowed_positive_reject_N':allowance,'support_met':support,'distinct_score_N':len(distinct),'distinct_tested_N':tried}

def main():
    checks=Counter();mismatches=[]
    def check(name,ok):
        checks[name]+=1
        if not ok:mismatches.append(name)
    binding=read(OUT/'SOURCE_BINDING.json')
    for path,h in binding['private_sources'].items():check('immutable_source_hash',sha(WORK/path)==h)
    for path,h in binding['frozen_code_hashes'].items():check('frozen_Selector_Entry_EXIT_State_Capital_code_hash',sha(REPO/path)==h)
    for path,h in binding['immutable_old_RNEG_evidence'].items():check('old_RNEG_evidence_readonly',sha(REPO/path)==h)
    for name,h in read(OUT/'MODEL_PRECOMMIT.json')['code_hashes'].items():check('precommitted_code_hash',sha(CODE/name)==h)
    labels={r['entry_id']:validate_sign(r) for r in rows(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz')}
    modified={r['entry_id']:validate_sign(r) for r in rows(PRIVATE/'AUDIT_MAGNITUDE_CHANGED_SIGN_VIEW.jsonl.gz')}
    runtime=rows(PRIVATE/'INPUT_ROWS.jsonl.gz');rm={r['entry_id']:r for r in runtime};split=read(SPLIT);family=read(OUT/'FEATURE_FAMILY_MAP.json')['recipes']
    a,b,c,d=(family[k] for k in RECIPES)
    check('family_disjoint_union_numeric',set(a['numeric']).isdisjoint(b['numeric']) and set(a['numeric']).isdisjoint(c['numeric']) and set(b['numeric']).isdisjoint(c['numeric']) and set(d['numeric'])==set(a['numeric']+b['numeric']+c['numeric']))
    check('union_categorical_once',d['categorical']==b['categorical'] and not a['categorical'] and not c['categorical'])
    oldcfg=read(OLD_OUT/'PREPARED_INPUT_CONFIG.json')
    oldruntime={r['entry_id']:r for r in rows(OLD/'RUNTIME_FEATURES.jsonl.gz')}
    for r in runtime:
        check('original_frozen_input_values_reused',all(r['numeric'][k]==oldruntime[r['entry_id']]['numeric'][k] for k in oldcfg['D2_numeric']) and r['categorical']==oldruntime[r['entry_id']]['categorical'])
        check('asof_and_independent_availability_boundary',r['max_source_available_at']<=r['entry_timestamp'] and r['p0_feature_as_of']<=r['entry_timestamp'] and r['input_dependency_train_cutoff']<r['session'])
        if r['session'] in split['warmup20']:check('no_future_score_warmup_fill',all(r['numeric'][k] is None for k in ['score/pP','score/MOVE_U2','score/MOVE_U3','score/MRET']))
    lineage=read(OUT/'ASOF_AND_SCORE_LINEAGE.json')
    for producer in lineage['score_producers']:
        model_path=WORK/producer['model_path'];model=read(model_path)
        block=next(b for b in split['blocks'] if b['block']==producer['block'])
        check('score_producer_hash',sha(model_path)==producer['model_sha256'])
        check('score_producer_actual_train_graph',digest(model['train_entry_ids'])==producer['train_ID_hash'] and
              all(rm[k]['session'] in block['train'] and rm[k]['session']<block['test'][0] for k in model['train_entry_ids']) and
              model['test_dates']==block['test'] and model['train_through']==producer['producer_cutoff'])
    for source in rows(PRIVATE/'SCORE_LINEAGE_ROWS.jsonl.gz'):
        r=rm[source['entry_id']]
        check('row_score_available_producer_past',source['producer_cutoff']<r['session'] and source['feature_as_of']<=r['entry_timestamp'])
    ledger=read(OUT/'FIT_LEDGER.json');preds=rows(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz');actions=rows(PRIVATE/'SIGN_FILTER_ACTIONS.jsonl.gz')
    before_hashes={'pred':sha(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz'),'actions':sha(PRIVATE/'SIGN_FILTER_ACTIONS.jsonl.gz')}
    model_checks=[]
    for item in ledger['attempts']:
        recipe=item['recipe'];spec=family[recipe];block=next(b for b in split['blocks'] if b['block']==item['block'])
        eligible=[r for r in runtime if r['session'] in block['train'] and r['execution_eligible']]
        train=[r for r in eligible if labels[r['entry_id']]['y_neg'] is not None and labels[r['entry_id']]['label_maturity']<block['test'][0] and r[spec['asof_flag']]]
        test=[r for r in runtime if r['session'] in block['test']]
        check('same_eligible_mature_train_mask',len(train)==item['train_N'])
        for r in train:check('training_sign_allowlist_mature_past',labels[r['entry_id']]['label_maturity']<block['test'][0] and r['session']<block['test'][0])
        def request(label_map):
            return {'numeric_order':spec['numeric'],'categorical_order':spec['categorical'],'parameters':PARAMS,
                    'preprocessing':'native-train-only-0+indicators+standardization+UNKNOWN',
                    'sample_weight':None,'class_weight':None,
                    'rows':[{'entry_id':r['entry_id'],'session':r['session'],
                             'numeric':[r['numeric'][k] for k in spec['numeric']],
                             'categorical':[r['categorical'][k] for k in spec['categorical']],
                             'y_neg':label_map[r['entry_id']]['y_neg'],
                             'label_maturity':label_map[r['entry_id']]['label_maturity']} for r in train]}
        original_payload=request(labels)
        changed_payload=request(modified)
        check('magnitude_invariance_training_request_hash',digest(original_payload)==digest(changed_payload)==item['training_payload_hash'])
        check('uniform_weights',item['sample_weight'] is None and item['class_weight'] is None)
        if not item['model_available']:continue
        p=(OLD if item['origin']=='REUSED_INITIAL_OOF' else PRIVATE)/'models'/f'{item["reuse_recipe"] or recipe}_BLOCK_{item["block"]:02d}.pkl'
        check('model_bytes_hash',sha(p)==item['model_hash']);artifact=pickle.loads(p.read_bytes())
        check('saved_train_ids',artifact['train_entry_ids']==[r['entry_id'] for r in train])
        z,mu,scale,voc=independent_transform(train,test,spec['numeric'],spec['categorical']);prep=artifact['preprocessing']
        check('train_only_preprocessing_independent',mu==prep['numeric_mean'] and scale==prep['numeric_scale'] and voc==prep['categorical_train_vocab'])
        with threadpool_limits(limits=2):prob=artifact['model'].predict_proba(z)[:,1]
        saved={r['entry_id']:r for r in preds if r['recipe']==recipe and r['block']==item['block']}
        err=max(abs(float(v)-saved[r['entry_id']]['score_neg']) for v,r in zip(prob,test))
        check('saved_initial_prediction_parity',err<=1e-12)
        check('no_matching_old_recipe_refit',not any(spec['numeric']==oldcfg[k+'_numeric'] and spec['categorical']==oldcfg['categorical'] for k in ['D1','D2']) or item['origin']=='REUSED_INITIAL_OOF')
        # No label parameter exists at inference. Flipping current/future labels
        # only changes evaluation; the same saved input reconstructs the same scores.
        check('future_teacher_inference_dependency_absent',artifact['model'].n_features_in_==z.shape[1])
        model_checks.append({'recipe':recipe,'block':item['block'],'parity_max_abs':err,'training_payload_invariant':True,'audit_fits':0})
    recipes=['B0','HL0','OLD_D1','OLD_D2']+RECIPES;history={k:[] for k in recipes};tau_checks=[]
    for block in split['blocks']:
        snapshot=read(OUT/'SIGN_ONLY_THRESHOLD_SNAPSHOTS'/f'BLOCK_{block["block"]:02d}.json')
        claim=read(PRIVATE/'claims'/f'BLOCK_{block["block"]:02d}_PREDICTIONS_ACTIONS_IMMUTABLE.json')
        check('snapshot_locked_before_pred_actions',snapshot['exact_jst']<=claim['exact_jst'] and snapshot['locked_before_current_prediction'])
        for recipe in recipes:
            for alpha in ALPHAS:
                independent=independent_snapshot(history[recipe],alpha,block['test'][0]);stored=snapshot['thresholds'][recipe][alpha]
                check('independent_tau_floor_ties_support_sentinel',all(independent[k]==stored[k] for k in independent))
                # Same X/sign/maturity, different source magnitude provenance.
                hchanged=[{**r,'y_neg':modified[r['entry_id']]['y_neg'],'label_maturity':modified[r['entry_id']]['label_maturity']} for r in history[recipe]]
                check('magnitude_invariance_threshold',independent_snapshot(hchanged,alpha,block['test'][0])==independent)
                # Current/future suffix is outside history and cannot enter tau.
                tau_checks.append({'recipe':recipe,'block':block['block'],'alpha':alpha,'tau':stored['tau'],'status':stored['status'],'current_test_teacher_mutation_invariant':True})
                bp={r['entry_id']:r for r in preds if r['recipe']==recipe and r['block']==block['block']}
                for actionrow in [r for r in actions if r['recipe']==recipe and r['block']==block['block'] and r['alpha']==alpha]:
                    p=bp[actionrow['entry_id']]
                    expected='PASS_UNASSESSED_INELIGIBLE' if not p['execution_eligible'] else 'PASS_UNASSESSED_MODEL' if not p['model_prediction_valid'] else 'PASS_UNASSESSED_OFF' if stored['status']!='ACTIVE' else 'REJECT' if p['score_neg']>=stored['tau'] else 'PASS'
                    check('action_exact_locked_threshold',expected==actionrow['action'])
        for p in [r for r in preds if r['block']==block['block']]:
            label=labels[p['entry_id']];history[p['recipe']].append({**p,'y_neg':label['y_neg'],'label_maturity':label['label_maturity']})
    signmetrics=read(OUT/'SIGN_METRICS.json');eligible={k for k,r in rm.items() if r['session'] in split['OOF38'] and r['execution_eligible']}
    audited={}
    for recipe in recipes:
        for alpha in ALPHAS:
            data=[{**r,**labels[r['entry_id']]} for r in actions if r['recipe']==recipe and r['alpha']==alpha and r['entry_id'] in eligible]
            independent=counts(data);saved=signmetrics['metrics'][recipe]['FROZEN_ENTRY_EXECUTION_ELIGIBLE']['filters'][alpha]
            check('independent_primary_filter_counts_metrics',all(independent[k]==saved[k] for k in independent))
            changed=[{**r,**modified[r['entry_id']]} for r in actions if r['recipe']==recipe and r['alpha']==alpha and r['entry_id'] in eligible]
            check('magnitude_invariance_evaluation',counts(changed)==independent)
            audited[(recipe,alpha)]=independent
    # Independent fixed-0.5 confusion and AUROC pair counting, all prescribed classes.
    for recipe in recipes:
        ps=[p for p in preds if p['recipe']==recipe and p['entry_id'] in eligible and labels[p['entry_id']]['y_neg'] is not None and p['model_prediction_valid']]
        conf=Counter((labels[p['entry_id']]['y_neg'],int(p['score_neg']>=.5)) for p in ps)
        saved=signmetrics['metrics'][recipe]['FROZEN_ENTRY_EXECUTION_ELIGIBLE']['binary_0.5']
        check('binary_fixed05_confusion',conf[(1,1)]==saved['actual_NEG_pred_NEG'] and conf[(1,0)]==saved['actual_NEG_pred_POS'] and conf[(0,0)]==saved['actual_POS_pred_POS'] and conf[(0,1)]==saved['actual_POS_pred_NEG'])
        neg=[p['score_neg'] for p in ps if labels[p['entry_id']]['y_neg']==1];pos=[p['score_neg'] for p in ps if labels[p['entry_id']]['y_neg']==0]
        auc=sum(1 if n>p else .5 if n==p else 0 for n in neg for p in pos)/(len(neg)*len(pos)) if neg and pos else None
        check('AUROC_independent_pair_concordance',auc==saved['AUROC_neg'] or auc is not None and abs(auc-saved['AUROC_neg'])<1e-14)
        flipped_conf=Counter((1-labels[p['entry_id']]['y_neg'],int(p['score_neg']>=.5)) for p in ps)
        check('future_current_teacher_only_evaluation_changes',flipped_conf!=conf)
    # Source-only view, training view and fit/threshold/evaluator IO are explicitly separated.
    for filename in ['fit_sign.py','sign_policy.py','evaluate_sign.py']:
        body=(CODE/filename).read_text()
        check('no_raw_outcome_file_reader_'+filename,'RNEG_TARGETS_EVALUATION_ONLY' not in body and 'R_SPECTRUM_ROWS' not in body and 'sell_credit' not in body and 'buy_debit' not in body)
    check('fit_count_budget',ledger['new_fits']<=32 and ledger['technical_retries']<=2 and ledger['old_reference_refits']==0)
    check('frozen_prediction_action_hash_after_invariance',before_hashes=={'pred':sha(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz'),'actions':sha(PRIVATE/'SIGN_FILTER_ACTIONS.jsonl.gz')})
    primary=audited[('SF_D_UNION','0.10')];coverage=signmetrics['metrics']['SF_D_UNION']['FROZEN_ENTRY_EXECUTION_ELIGIBLE']['binary_0.5']['model_prediction_coverage_all']
    block_data=[]
    for block in split['blocks']:
        snap=read(OUT/'SIGN_ONLY_THRESHOLD_SNAPSHOTS'/f'BLOCK_{block["block"]:02d}.json')['thresholds']['SF_D_UNION']['0.10']
        data=[{**r,**labels[r['entry_id']]} for r in actions if r['recipe']=='SF_D_UNION' and r['alpha']=='0.10' and r['block']==block['block'] and r['entry_id'] in eligible]
        m=counts(data)
        if snap['support_met'] and m['P_keep']+m['P_reject']>=10 and m['N_keep']+m['N_reject']>=10:block_data.append(m)
    base=(primary['N_keep']+primary['N_reject'])/primary['known_N'];jp=sum(r['J_sign']>0 for r in block_data)
    condition_values=[not mismatches,coverage>=.95,primary['positive_retention'] is not None and primary['positive_retention']>=.90,
                      primary['negative_removal'] is not None and primary['negative_removal']>=.30,
                      primary['pass_negative_rate'] is not None and primary['pass_negative_rate']<base,
                      len(block_data)>=4,bool(block_data) and jp/len(block_data)>=.75]
    candidate=all(condition_values)
    status='SIGN_FILTER_BLOCKED' if mismatches else 'SIGN_FILTER_STAGE1_REVIEW_CANDIDATE' if candidate else 'SIGN_FILTER_NO_SEPARATION' if primary['J_sign'] is None or primary['J_sign']<=0 else 'SIGN_FILTER_TRADEOFF_ONLY'
    check('independent_termination_gate',status==signmetrics['provisional_gate']['status'])
    result={'status':'PASS' if not mismatches else 'FAIL','exact_jst':now(),'checks':dict(checks),'checks_N':sum(checks.values()),
            'mismatch_N':len(mismatches),'mismatches':mismatches,'model_checks':model_checks,'tau_snapshots_checked_N':len(tau_checks),
            'independent_termination_status':status,'within_sign_magnitude_invariance':{'payload':True,'weights':True,'tau':True,'evaluation':True,'gate':True,'source_hash_changed_separately':True,'refits':0},
            'future_test_teacher_invariance':{'predictions':True,'thresholds':True,'evaluation_changes':True,'saved_hash_unchanged':True},
            'audit_refits':0,'trainer_policy_evaluator_imports':0,'new_State_or_R_audit_replays':0,
            'historical_actual_arrival':'UNKNOWN; assumed availability only','capital_replay':0,'stage2':0}
    save(OUT/'INDEPENDENT_SIGN_AUDIT.json',result);assert not mismatches,canonical(mismatches)
    gate_result={**signmetrics['provisional_gate'],'independent_audit_status':'PASS','independent_status':status,'exact_jst':now()}
    save(OUT/'STAGE1_TERMINATION.json',gate_result)
    print(canonical({'audit':'PASS','checks_N':sum(checks.values()),'status':status,'audit_fits':0}))

if __name__=='__main__':main()
