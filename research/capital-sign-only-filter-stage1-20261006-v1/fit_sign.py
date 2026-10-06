"""32 fits maximum; snapshots before prediction, current labels after prediction/action hashes."""
import pickle
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from sign_io import *
from sign_model import transform
from sign_policy import select_threshold, action

def main():
    pre=read(OUT/'MODEL_PRECOMMIT.json'); rb=read(OUT/'PRECOMMIT_READBACK.json')
    assert rb['verified'] and rb['precommit_sha256']==sha(OUT/'MODEL_PRECOMMIT.json')
    assert pre['parameters']==PARAMS and pre['sklearn_version']==sklearn.__version__
    for name,h in pre['code_hashes'].items():assert sha(CODE/name)==h,'CODE_CHANGED_AFTER_PRECOMMIT'
    for name,h in pre['input_hashes'].items():assert sha(PRIVATE/name)==h
    family=read(OUT/'FEATURE_FAMILY_MAP.json')['recipes']; runtime=rows(PRIVATE/'INPUT_ROWS.jsonl.gz')
    split=read(SPLIT);target=SignIndex(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz')
    refs=rows(PRIVATE/'REFERENCE_OOF.jsonl.gz');refmap={(r['recipe'],r['entry_id']):r for r in refs}
    history={k:[] for k in RECIPES+['B0','HL0','OLD_D1','OLD_D2']}; ledger=[]; allpred=[]; allactions=[]
    oldcfg=read(OLD_OUT/'PREPARED_INPUT_CONFIG.json');oldledger=read(OLD_OUT/'FIT_LEDGER.json')['ledger']
    save(PRIVATE/'OOF_STARTED.json',{'exact_jst':now(),'fit_budget':32,'technical_retries_max':2,'recipes':RECIPES,'precommit_sha256':sha(OUT/'MODEL_PRECOMMIT.json')},exclusive=True)
    for block in split['blocks']:
        b=block['block'];test=[r for r in runtime if r['session'] in block['test']]
        # Runtime threshold payload cannot see current predictions or current signs.
        snapshots={k:{a:select_threshold(history[k],a,block['test'][0]) for a in ALPHAS} for k in history}
        snapshot={'block':b,'exact_jst':now(),'test_sessions':block['test'],'thresholds':snapshots,'locked_before_current_prediction':True}
        snapfile=OUT/'SIGN_ONLY_THRESHOLD_SNAPSHOTS'/f'BLOCK_{b:02d}.json';save(snapfile,snapshot,exclusive=True)
        candidates=[r for r in runtime if r['session'] in block['train'] and r['execution_eligible']]
        labels={}
        for r in candidates:
            label=target.get(r['entry_id'],before=block['test'][0],purpose='training')
            if label['y_neg'] is not None and label['label_maturity']<block['test'][0]:labels[r['entry_id']]=label
        known=[r for r in candidates if r['entry_id'] in labels]
        baseline=float(np.mean([labels[r['entry_id']]['y_neg'] for r in known])) if known else .5
        blockpred=[]
        for recipe in RECIPES:
            spec=family[recipe];nn=spec['numeric'];cc=spec['categorical'];flag=spec['asof_flag']
            train=[r for r in known if r[flag]];trainlabels=[labels[r['entry_id']] for r in train]
            payload=training_payload(train,labels,nn,cc);ph=digest(payload)
            y=np.array([r['y_neg'] for r in trainlabels],dtype=int)
            trained=spec['enabled'] and sufficient(trainlabels)
            matching=[k for k in ['D1','D2'] if nn==oldcfg[k+'_numeric'] and cc==oldcfg['categorical']]
            prep=None;mh=None;origin='BASELINE_FALLBACK';reuse_recipe=None;started=now();technical_retry_N=0
            if trained and matching:
                reuse_recipe=matching[0];modelpath=OLD/'models'/f'{reuse_recipe}_BLOCK_{b:02d}.pkl'
                artifact=pickle.loads(modelpath.read_bytes());clf=artifact['model'];prep=artifact['preprocessing'];mh=sha(modelpath)
                oldrec=next(r for r in oldledger if r['recipe']==reuse_recipe and r['block']==b)
                fingerprint=__import__('hashlib').sha256(json.dumps([{'entry_id':r['entry_id'],'numeric':{k:r['numeric'][k] for k in nn},'categorical':r['categorical'],'y':labels[r['entry_id']]['y_neg']} for r in train],sort_keys=True).encode()).hexdigest()
                assert oldrec['training_input_hash']==fingerprint and oldrec['model_hash']==mh
                assert artifact['train_entry_ids']==[r['entry_id'] for r in train] and artifact['label_maturity']==[r['label_maturity'] for r in trainlabels]
                x,z,computed=transform(train,test,nn,cc);assert computed==prep and clf.get_params()==pre['all_resolved_learner_parameters']
                prob=np.array([refmap[('OLD_'+reuse_recipe,r['entry_id'])]['score_neg'] for r in test])
                # Preserve saved first-inference bytes; no refit/rebackscore.
                origin='REUSED_INITIAL_OOF'
            elif trained:
                claim={'recipe':recipe,'block':b,'exact_jst':started,'training_payload_hash':ph,'parameters':PARAMS,
                       'training_N':len(train),'sample_weight':None,'class_weight':None,'current_test_sign_reads_before_prediction':0}
                save(PRIVATE/'claims'/f'{recipe}_BLOCK_{b:02d}_STARTED.json',claim,exclusive=True)
                x,z,prep=transform(train,test,nn,cc);clf=HistGradientBoostingClassifier(**PARAMS)
                # No automatic performance retries. Only same-input technical restart may be separately recorded (max2).
                with threadpool_limits(limits=2):clf.fit(x,y);prob=clf.predict_proba(z)[:,1]
                artifact={'model':clf,'preprocessing':prep,'train_entry_ids':[r['entry_id'] for r in train],
                          'train_cutoff':block['train'][-1],'label_maturity':[r['label_maturity'] for r in trainlabels],
                          'training_payload_hash':ph,'sklearn_version':sklearn.__version__}
                modelpath=PRIVATE/'models'/f'{recipe}_BLOCK_{b:02d}.pkl';modelpath.parent.mkdir(exist_ok=True)
                with modelpath.open('xb') as f:pickle.dump(artifact,f,protocol=5)
                mh=sha(modelpath);origin='NEW_DISTINCT_INFORMATION_FIT'
            else:prob=np.full(len(test),baseline)
            assert sum(r['origin']=='NEW_DISTINCT_INFORMATION_FIT' for r in ledger)+int(origin=='NEW_DISTINCT_INFORMATION_FIT')<=32
            ledger.append({'recipe':recipe,'block':b,'origin':origin,'reuse_recipe':reuse_recipe,'model_hash':mh,
                           'exact_started_jst':started,'exact_completed_jst':now(),'training_payload_hash':ph,
                           'train_N':len(train),'train_session_N':len({r['session'] for r in train}),
                           'positive_N':int(sum(y==0)),'negative_N':int(sum(y==1)),'model_available':bool(trained),
                           'known_eligible_train_N':len(known),'unknown_or_zero_or_immature_excluded_N':len(candidates)-len(known),
                           'asof_training_excluded_N':len(known)-len(train),'numeric_N':len(nn),'categorical_N':len(cc),
                           'transformed_N':len(prep['numeric_mean'])+sum(len(v) for v in prep['categorical_train_vocab'].values()) if prep else None,
                           'train_cutoff':block['train'][-1],'test_sessions':block['test'],'sample_weight':None,'class_weight':None,
                           'technical_retries':technical_retry_N,'future_test_sign_reads_before_prediction':0})
            preds=[]
            for r,p in zip(test,prob):
                valid=bool(trained and r[flag])
                preds.append({'entry_id':r['entry_id'],'session':r['session'],'block':b,'recipe':recipe,'score_neg':float(p),
                              'baseline':baseline,'model_prediction_valid':valid,'prediction_status':origin if valid else 'MODEL_UNAVAILABLE_OR_ASOF',
                              'model_hash':mh,'model_train_cutoff':block['train'][-1],'execution_eligible':r['execution_eligible'],
                              'rank_pass':r['rank_pass'],'feature_as_of':r['feature_as_of'],'historical_availability':'HISTORICAL_ASSUMED_AVAILABILITY',
                              'threshold_snapshot_sha256':sha(snapfile),
                              'novel_category_UNKNOWN_N':sum(r['categorical'][k] not in prep['categorical_train_vocab'][k] for k in cc) if prep else None})
            predpath=PRIVATE/'predictions'/f'{recipe}_BLOCK_{b:02d}.jsonl.gz';gzsave(predpath,preds,exclusive=True)
            gzsave(PRIVATE/'training_payloads'/f'{recipe}_BLOCK_{b:02d}.jsonl.gz',payload['rows'],exclusive=True)
            blockpred+=preds
        for recipe in ['B0','HL0','OLD_D1','OLD_D2']:
            preds=[]
            for r in test:
                original=refmap[(recipe,r['entry_id'])] if recipe!='B0' else None
                preds.append({'entry_id':r['entry_id'],'session':r['session'],'block':b,'recipe':recipe,
                              'score_neg':original['score_neg'] if original else baseline,
                              'model_prediction_valid':bool(original and original['model_prediction_valid']) if recipe!='B0' else True,
                              'prediction_status':'REUSED_INITIAL_OOF' if original else 'PAST_SIGN_BASELINE',
                              'execution_eligible':r['execution_eligible'],'rank_pass':r['rank_pass'],
                              'model_hash':original['model_hash'] if original else None,'model_train_cutoff':block['train'][-1],
                              'threshold_snapshot_sha256':sha(snapfile)})
            gzsave(PRIVATE/'predictions'/f'{recipe}_BLOCK_{b:02d}.jsonl.gz',preds,exclusive=True);blockpred+=preds
        decisions=[{'entry_id':p['entry_id'],'session':p['session'],'block':b,'recipe':p['recipe'],'alpha':a,
                    'action':action(p,snapshots[p['recipe']][a]),'tau':snapshots[p['recipe']][a]['tau'],
                    'threshold_status':snapshots[p['recipe']][a]['status']} for p in blockpred for a in ALPHAS]
        decpath=PRIVATE/'actions'/f'BLOCK_{b:02d}.jsonl.gz';gzsave(decpath,decisions,exclusive=True)
        save(PRIVATE/'claims'/f'BLOCK_{b:02d}_PREDICTIONS_ACTIONS_IMMUTABLE.json',
             {'exact_jst':now(),'prediction_hashes':{k:sha(PRIVATE/'predictions'/f'{k}_BLOCK_{b:02d}.jsonl.gz') for k in history},
              'action_hash':sha(decpath),'snapshot_hash':sha(snapfile),'future_test_sign_reads':0},exclusive=True)
        # Only now current block signs can enter evaluator/history, after files are closed and hashed.
        current={r['entry_id']:target.get(r['entry_id'],purpose='post_prediction_history') for r in test}
        for p in blockpred:
            y=current[p['entry_id']];history[p['recipe']].append({**p,'y_neg':y['y_neg'],'label_maturity':y['label_maturity']})
        allpred+=blockpred;allactions+=decisions
        save(OUT/'FIT_LEDGER.json',{'new_fits':sum(r['origin']=='NEW_DISTINCT_INFORMATION_FIT' for r in ledger),
                                  'reused_equivalent_fits':sum(r['origin']=='REUSED_INITIAL_OOF' for r in ledger),
                                  'old_reference_refits':0,'technical_retries':0,'attempts':ledger})
        print(canonical({'block':b,'new_fits':sum(r['origin']=='NEW_DISTINCT_INFORMATION_FIT' for r in ledger),
                         'D_standard_threshold':snapshots['SF_D_UNION']['0.10']['status'],
                         'current_actions_saved_before_sign_read':True}),flush=True)
    assert len(allpred)==1039*8 and len(allactions)==1039*8*3
    gzsave(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz',allpred,exclusive=True)
    gzsave(PRIVATE/'SIGN_FILTER_ACTIONS.jsonl.gz',allactions,exclusive=True)
    gzsave(PRIVATE/'SIGN_READ_ACCESS_LOG.jsonl.gz',target.read_log,exclusive=True)
    save(OUT/'OOF_COMPLETE.json',{'exact_jst':now(),'prediction_N':len(allpred),'new_recipe_prediction_N':1039*4,
        'action_N':len(allactions),'new_fits':sum(r['origin']=='NEW_DISTINCT_INFORMATION_FIT' for r in ledger),
        'reused_equivalent_fits':sum(r['origin']=='REUSED_INITIAL_OOF' for r in ledger),'reused_reference_OOF_N':1039*3,
        'prediction_hash':sha(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz'),'action_hash':sha(PRIVATE/'SIGN_FILTER_ACTIONS.jsonl.gz'),
        'current_future_training_sign_reads':0,'current_future_CAL_reads':0,'warmup_insample_CAL_rows':0,
        'exposure':'ITERATIVE_DEVELOPMENT; prior sign and expert results known during design; not Fresh/OOS',
        'capital_replay':0,'stage2':0,'productionReady':False})

if __name__=='__main__':main()
