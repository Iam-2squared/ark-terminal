"""At most16 precommitted fits; future label payloads never decoded before prediction."""
import re, gzip, hashlib, json, pickle
from fractions import Fraction
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from rneg_io import *
from rneg_policy import select_policy, action

def transform(train, test, nn, cc, prep=None):
    def nums(rr):
        a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in nn] for r in rr])
        assert not np.isinf(a).any()
        return np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
    if prep is None:
        a=nums(train); mu=a.mean(axis=0);scale=a.std(axis=0);scale[scale==0]=1
        prep={'numeric_fields':nn,'categorical_fields':cc,'numeric_mean':mu.tolist(),'numeric_scale':scale.tolist(),
              'categorical_train_vocab':{k:sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'}) for k in cc},
              'missing_constant':0,'missing_indicators':True,'train_only':True}
    def apply(rr):
        a=(nums(rr)-np.array(prep['numeric_mean']))/np.array(prep['numeric_scale']);columns=[]
        for k in cc:
            voc=prep['categorical_train_vocab'][k];values=[r['categorical'][k] if r['categorical'][k] in voc else '__UNKNOWN__' for r in rr]
            columns.extend([[float(v==c) for v in values] for c in voc])
        return np.column_stack([a,np.array(columns).T])
    return apply(train) if train else None,apply(test),prep

def target_index():
    index={}
    with gzip.open(PRIVATE/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz','rt') as f:
        for line in f:
            key=re.search(r'"entry_id"\s*:\s*"([^"]+)"',line).group(1);index[key]=line
    return index

def history_label(target):
    return Fraction(target['sell_credit'])/Fraction(target['buy_debit'])-1 if target['known'] else None

def main():
    pre=read(OUT/'MODEL_AND_POLICY_PRECOMMIT.json');receipt=read(OUT/'PRECOMMIT_READBACK.json')
    assert receipt['verified'] and receipt['precommit_sha256']==sha(OUT/'MODEL_AND_POLICY_PRECOMMIT.json')
    assert pre['parameters']==PARAMS and pre['sklearn_version']==__import__('sklearn').__version__
    for name,h in pre['code_hashes'].items():assert sha(CODE/name)==h,'CODE_CHANGED_AFTER_PRECOMMIT'
    cfg=read(OUT/'PREPARED_INPUT_CONFIG.json')
    for name,h in cfg['input_hashes'].items():assert sha(PRIVATE/name)==h
    runtime=rows(PRIVATE/'RUNTIME_FEATURES.jsonl.gz');split=read(SPLIT_PATH);index=target_index()
    recipes=['D1']+(['D2'] if cfg['D2_enabled'] else [])
    histories={k:[] for k in recipes};ledger=[];all_predictions=[];all_actions=[];policies=[]
    assert not (PRIVATE/'OOF_STARTED.json').exists(),'Initial OOF already started; no untracked repeat permitted'
    save(PRIVATE/'OOF_STARTED.json',{'exact_jst':now(),'recipes':recipes,'fit_budget':16,'initial_future_inference':True},exclusive=True)
    for block in split['blocks']:
        b=block['block'];test=[r for r in runtime if r['session'] in block['test']]
        policy=select_policy(histories,b,block['test']);policy['exact_jst']=now()
        save(OUT/'policy_snapshots'/f'BLOCK_{b:02d}.json',policy,exclusive=True);policies.append(policy)
        selected={};baseline=None
        for recipe in recipes:
            nn=cfg[recipe+'_numeric'];cc=cfg['categorical'];flag=recipe+'_asof_ok'
            candidates=[r for r in runtime if r['session'] in block['train'] and r['execution_eligible']]
            labels={}
            for r in candidates:
                target=json.loads(index[r['entry_id']])
                if target['known'] and target['label_maturity']<block['test'][0]:labels[r['entry_id']]=target
            all_known=[r for r in candidates if r['entry_id'] in labels]
            train=[r for r in all_known if r[flag]]
            y=np.array([labels[r['entry_id']]['y_neg'] for r in train],dtype=int)
            base=float(np.mean([labels[r['entry_id']]['y_neg'] for r in all_known])) if all_known else .5
            if recipe=='D1':baseline=base
            trained=(len(train)>=100 and len({r['session'] for r in train})>=10 and sum(y==0)>=20 and sum(y==1)>=20)
            status='FITTED' if trained else 'TRAINING_UNAVAILABLE_CONSTANT_DEFENSE_OFF'
            model_hash=None;prep=None
            if trained:
                x,z,prep=transform(train,test,nn,cc);clf=HistGradientBoostingClassifier(**PARAMS)
                claim={'recipe':recipe,'block':b,'exact_jst':now(),'parameters':PARAMS,'train_ID_N':len(train),'test_teacher_payload_reads_before_fit':0}
                save(PRIVATE/'claims'/f'{recipe}_BLOCK_{b:02d}_STARTED.json',claim,exclusive=True)
                with threadpool_limits(limits=2):
                    clf.fit(x,y);prob=clf.predict_proba(z)[:,1]
                artifact={'model':clf,'preprocessing':prep,'train_entry_ids':[r['entry_id'] for r in train],
                          'train_cutoff':block['train'][-1],'label_maturity':[labels[r['entry_id']]['label_maturity'] for r in train]}
                model_path=PRIVATE/'models'/f'{recipe}_BLOCK_{b:02d}.pkl';model_path.parent.mkdir(exist_ok=True)
                with model_path.open('xb') as f:pickle.dump(artifact,f,protocol=5)
                model_hash=sha(model_path)
            else:prob=np.full(len(test),base)
            fitted_N=sum(x['status']=='FITTED' for x in ledger)+int(trained);assert fitted_N<=16
            fingerprint=hashlib.sha256(json.dumps([{'entry_id':r['entry_id'],'numeric':{k:r['numeric'][k] for k in nn},'categorical':r['categorical'],'y':labels[r['entry_id']]['y_neg']} for r in train],sort_keys=True).encode()).hexdigest()
            record={'recipe':recipe,'block':b,'status':status,'train_N':len(train),'train_session_N':len({r['session'] for r in train}),
                    'negative_N':int(sum(y==1)),'nonnegative_N':int(sum(y==0)),'known_eligible_train_N':len(all_known),
                    'source_training_excluded_N':len(all_known)-len(train),'unknown_label_excluded_N':len(candidates)-len(all_known),
                    'train_through':block['train'][-1],'test_dates':block['test'],'model_hash':model_hash,
                    'training_input_hash':fingerprint,'test_teacher_payload_reads_before_prediction':0,'parameters':PARAMS,
                    'sklearn_version':__import__('sklearn').__version__,'feature_N_numeric':len(nn),'feature_N_transformed':len(prep['numeric_mean'])+sum(len(v) for v in prep['categorical_train_vocab'].values()) if prep else None}
            ledger.append(record)
            predictions=[]
            for r,p in zip(test,prob):
                unseen=sum(r['categorical'][k] not in prep['categorical_train_vocab'][k] for k in cc) if prep else None
                can_veto=trained and r[flag]
                prediction={'entry_id':r['entry_id'],'session':r['session'],'symbol':r['symbol'],'block':b,
                    'score':float(p),'baseline':base,'recipe':recipe,'model_hash':model_hash,'can_veto':can_veto,
                    'prediction_status':'INITIAL_FUTURE_INFERENCE' if can_veto else 'ABSTAIN_OR_CONSTANT',
                    'feature_as_of':r['feature_as_of'],'max_source_available_at':r['max_source_available_at'],
                    'snapshot_hash':r['provenance']['prefix_sha256'],'p0_snapshot_hash':r.get('p0_snapshot_hash') if recipe=='D2' else None,
                    'model_train_cutoff':block['train'][-1],'execution_eligible':r['execution_eligible'],'rank_pass':r['rank_pass'],
                    'novel_category_unknown_encoded_N':unseen,'historical_availability':'HISTORICAL_ASSUMED_AVAILABILITY'}
                predictions.append(prediction)
            gzsave(PRIVATE/'predictions'/f'{recipe}_BLOCK_{b:02d}.jsonl.gz',predictions,exclusive=True)
            selected[recipe]={r['entry_id']:r for r in predictions};all_predictions+=predictions
        decisions=[]
        for r in test:
            chosen=selected.get(policy['selection']['recipe'],{}).get(r['entry_id']) if policy['selection'] else None
            decisions.append({'entry_id':r['entry_id'],'session':r['session'],'symbol':r['symbol'],'block':b,
                'action':action(chosen,policy),'selected_recipe':policy['selection']['recipe'] if policy['selection'] else None,
                'tau':policy['selection']['tau'] if policy['selection'] else None,'score':chosen['score'] if chosen else None})
        gzsave(PRIVATE/'actions'/f'BLOCK_{b:02d}.jsonl.gz',decisions,exclusive=True);all_actions+=decisions
        # Current block teachers are decoded only AFTER all predictions and policy actions are immutable.
        for recipe in recipes:
            for r in test:
                target=json.loads(index[r['entry_id']]);p=selected[recipe][r['entry_id']]
                histories[recipe].append({**p,'r':history_label(target),'y_neg':target['y_neg'], 'label_maturity':target['label_maturity']})
        save(OUT/'FIT_LEDGER.json',{'fits':sum(r['status']=='FITTED' for r in ledger),'by_recipe':{k:sum(r['status']=='FITTED' and r['recipe']==k for r in ledger) for k in recipes},'ledger':ledger,'technical_retries':0})
        print(json.dumps({'block':b,'policy':policy['status'],'selected':policy['selection'],'fits':sum(r['status']=='FITTED' for r in ledger),'veto_N':sum(r['action']=='VETO_THIS_ENTRY' for r in decisions)}),flush=True)
    assert len(all_predictions)==len(test)*0+1039*len(recipes) and len(all_actions)==1039
    gzsave(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz',all_predictions,exclusive=True)
    gzsave(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz',all_actions,exclusive=True)
    save(OUT/'PAST_QUALIFICATION.json',{'procedure':'section8 exact distinct-score selection; no extra fits/replays per tau','snapshots':policies,
        'threshold_model_selection_events':8,'current_or_future_CAL_PAYLOADS':0,'within_block_policy_changes':0})
    save(OUT/'OOF_COMPLETE.json',{'exact_jst':now(),'prediction_N':len(all_predictions),'action_N':len(all_actions),
        'first_inference':True,'fits':sum(r['status']=='FITTED' for r in ledger),'prediction_hash':sha(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz'),
        'action_hash':sha(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz'),'active_block_N':sum(p['status']=='ACTIVE' for p in policies),
        'VETO_N':sum(a['action']=='VETO_THIS_ENTRY' for a in all_actions),'development_only':True})

if __name__=='__main__':main()
