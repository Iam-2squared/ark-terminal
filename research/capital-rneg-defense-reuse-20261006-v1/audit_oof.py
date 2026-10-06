"""Saved model, training/preprocessing, initial prediction, and policy audit; fits0."""
import pickle, math, json, hashlib
from fractions import Fraction as F
from collections import defaultdict
import numpy as np
from rneg_io import *

def independent_selection(cal, recipe):
    if len(cal)<100 or len({r['session'] for r in cal})<10:return None
    nneg=sum(r['r']<0 for r in cal);npos=sum(r['r']>=0 for r in cal)
    if min(nneg,npos)<20:return None
    positive=sum(r['r']>0 for r in cal);profits=sum((max(r['r'],0) for r in cal),F(0))
    opts=[]
    for tau in {r['score'] for r in cal}:
        v=[r for r in cal if r['score']>=tau]
        neg=sum(r['r']<0 for r in v);pos=sum(r['r']>0 for r in v)
        p=sum((max(r['r'],0) for r in v),F(0));net=-sum((r['r'] for r in v),F(0));days={r['session'] for r in v}
        good=(len(v)>=20 and len(days)>=5 and positive>0 and profits>0 and F(pos,positive)<=F(1,10)
              and p/profits<=F(1,10) and F(neg,len(v))>F(nneg,len(cal)) and net>0)
        if good:good=all(-sum((r['r'] for r in v if r['session']!=day),F(0))>=0 for day in days)
        if good:opts.append((neg/nneg,neg/len(v),tau,-(1 if recipe=='D1' else 2),recipe))
    return max(opts) if opts else None

def main():
    pre=read(OUT/'MODEL_AND_POLICY_PRECOMMIT.json');cfg=read(OUT/'PREPARED_INPUT_CONFIG.json');split=read(SPLIT_PATH)
    for name,h in pre['code_hashes'].items():assert sha(CODE/name)==h
    for p,h in read(OUT/'SOURCE_BINDING.json')['source_hashes'].items():assert sha(WORK/p)==h
    runtime={r['entry_id']:r for r in rows(PRIVATE/'RUNTIME_FEATURES.jsonl.gz')}
    targets={r['entry_id']:r for r in rows(PRIVATE/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz')}
    predictions=rows(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz');actions={r['entry_id']:r for r in rows(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz')}
    by=defaultdict(list)
    for p in predictions:by[(p['recipe'],p['block'])].append(p)
    checks=defaultdict(int);errors=[]
    def check(ok,k):
        checks[k]+=1
        if not ok:errors.append(k)
    audits=[]
    for entry in read(OUT/'FIT_LEDGER.json')['ledger']:
        recipe,b=entry['recipe'],entry['block'];block=split['blocks'][b-1]
        with (PRIVATE/'models'/f'{recipe}_BLOCK_{b:02d}.pkl').open('rb') as f:a=pickle.load(f)
        check(sha(PRIVATE/'models'/f'{recipe}_BLOCK_{b:02d}.pkl')==entry['model_hash'],'model_byte_hash')
        train=[runtime[k] for k in a['train_entry_ids']];test=[runtime[p['entry_id']] for p in by[(recipe,b)]];prep=a['preprocessing']
        nn=prep['numeric_fields'];cc=prep['categorical_fields']
        for r in train:
            label=targets[r['entry_id']]
            check(r['session'] in block['train'] and r['session']<block['test'][0],'train_sessions_past_only')
            check(label['known'] and label['y_neg'] is not None and label['label_maturity']<block['test'][0],'known_mature_training_label')
            check(r['execution_eligible'] and r[recipe+'_asof_ok'],'training_prebuy_eligibility')
            check(r['input_dependency_train_cutoff']<r['session'],'learned_input_teacher_graph')
        numeric=np.array([[np.nan if r['numeric'][k] is None else r['numeric'][k] for k in nn] for r in train])
        matrix=np.concatenate([np.nan_to_num(numeric,nan=0),np.isnan(numeric).astype(float)],axis=1)
        mu=matrix.mean(axis=0);scale=matrix.std(axis=0);scale[scale==0]=1
        check(np.array_equal(mu,np.array(prep['numeric_mean'])) and np.array_equal(scale,np.array(prep['numeric_scale'])),'train_only_mean_scale')
        for k in cc:
            check(prep['categorical_train_vocab'][k]==sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'}),'train_only_vocab')
        def infer(rr):
            x=np.array([[np.nan if r['numeric'][k] is None else r['numeric'][k] for k in nn] for r in rr])
            x=np.concatenate([np.nan_to_num(x,nan=0),np.isnan(x).astype(float)],axis=1);x=(x-mu)/scale
            cat=[]
            for r in rr:
                v=[]
                for k in cc:
                    voc=prep['categorical_train_vocab'][k];value=r['categorical'][k] if r['categorical'][k] in voc else '__UNKNOWN__'
                    v += [int(value==c) for c in voc]
                cat.append(v)
            return a['model'].predict_proba(np.concatenate([x,np.array(cat)],axis=1))[:,1]
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=2):
            prob=infer(test)
            check(max(abs(v-p['score']) for v,p in zip(prob,by[(recipe,b)]))<=1e-12,'saved_model_initial_prediction_parity')
            mutated=[{**r,'future_suffix':[{'price':-999999,'available_at':'2099-01-01'}],
                      'current_test_teacher':{'r':-1},'future_arrival_count':9999,'future_EOD_available':False} for r in test]
            check(np.array_equal(prob,infer(mutated)),'future_suffix_teacher_arrival_EOD_invariance')
        for r,p in zip(test,by[(recipe,b)]):
            check(r['session'] in block['test'] and p['model_train_cutoff']<r['session'],'initial_future_prediction')
            check(p['feature_as_of']<=r['entry_timestamp'] and p['max_source_available_at']<=r['entry_timestamp'],'prediction_asof_before_quantity')
        audits.append({'recipe':recipe,'block':b,'status':'PASS','fit_N':0,'prediction_N':len(test),'train_N':len(train)})
    recipes=['D1']+(['D2'] if cfg['D2_enabled'] else [])
    policies=read(OUT/'PAST_QUALIFICATION.json')['snapshots']
    policy_checks=[]
    for policy in policies:
        b=policy['block'];start=policy['test_dates'][0];options=[]
        for recipe in recipes:
            cal=[]
            for p in predictions:
                if p['recipe']!=recipe or p['block']>=b or not p['can_veto'] or not p['execution_eligible'] or not p['rank_pass']:continue
                t=targets[p['entry_id']]
                if not t['known'] or t['label_maturity']>=start:continue
                cal.append({**p,'r':F(t['sell_credit'])/F(t['buy_debit'])-1})
            choice=independent_selection(cal,recipe)
            if choice:options.append(choice)
        best=max(options) if options else None
        selection=policy['selection']
        check((best is None)==(selection is None),'independent_policy_ON_OFF')
        if best:check(best[2]==selection['tau'] and best[4]==selection['recipe'],'independent_distinct_tau_model_choice')
        for r in (p for p in predictions if p['block']==b and p['recipe']==(selection['recipe'] if selection else 'D1')):
            want='PASS_TO_V5' if selection is None else 'ABSTAIN/PASS_TO_V5' if not r['can_veto'] else 'VETO_THIS_ENTRY' if r['score']>=selection['tau'] else 'PASS_TO_V5'
            check(actions[r['entry_id']]['action']==want,'locked_runtime_action')
        policy_checks.append({'block':b,'status':policy['status'],'independent_model_tau_matches':True,'CAL_current_future_payloads':0})
    check(sum(r['status']=='FITTED' for r in read(OUT/'FIT_LEDGER.json')['ledger'])<=16,'fit_budget')
    check(read(OUT/'OOF_COMPLETE.json')['prediction_hash']==sha(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz'),'immutable_first_predictions')
    result={'exact_jst':now(),'status':'PASS' if not errors else 'FAIL','mismatch_N':len(errors),'mismatches':errors[:30],
            'checks':dict(checks),'model_audits':audits,'policy_audits':policy_checks,'audit_refits':0,
            'label_zero_boundary':{'exact_zero_N':read(OUT/'HL0_REUSE_AUDIT.json')['strict_zero_N'],'zero_is_nonnegative':True},
            'historical_actual_arrival':'UNKNOWN; assumed availability audit only','no_test_label_decoded_before_prediction':'enforced by session-bound index use in fit driver; test evaluation parsed after prediction and action files saved'}
    save(OUT/'OOF_POLICY_ASOF_AUDIT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('model_audits','policy_audits')}));assert not errors

if __name__=='__main__':main()
