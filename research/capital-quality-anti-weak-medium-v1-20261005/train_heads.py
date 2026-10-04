"""Only16 claimed fixed Logistic fits; trainer reads no heldout teacher payload."""
import warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from control import *
from movement_preprocessing import transform, predict_saved

def main():
    claim=read(OUT/'FIT_CLAIM.json');design=read(OUT/'FEATURE_MODEL_SPLIT_PRECOMMIT.json')
    assert claim['hard_cap']==16 and len(claim['claims'])==16
    for n,want in claim['code_sha256'].items():assert sha(Path(__file__).parent/n)==want,('CODE_PIN_MISMATCH',n)
    assert sha(OUT/'ZERO_FIT_BASELINE.json')==claim['baseline_sha256']
    assert sha(OUT/'FEATURE_MODEL_SPLIT_PRECOMMIT.json')==claim['design_sha256']
    runtime=rows(INPUTS/'RUNTIME_CAUSAL.jsonl.gz');rm={r['entry_id']:r for r in runtime}
    all_predictions=[];fit_ledger=[]
    for item in claim['claims']:
        head=item['head'];block=item['block'];target=item['target'];name=f'{head}_BLOCK_{block:02d}'
        started=PRIVATE/'fit_claims'/(name+'_STARTED.json');done=PRIVATE/'fit_claims'/(name+'_COMPLETE.json')
        artifact_path=PRIVATE/'models'/(name+'.json');state_path=PRIVATE/'models'/(name+'_FITTED_STATE.npz')
        prediction_path=PRIVATE/'predictions'/(name+'.jsonl.gz')
        if done.exists():
            receipt=read(done)
            assert started.exists() and sha(artifact_path)==receipt['artifact_sha256'] and sha(state_path)==receipt['state_sha256'] and sha(prediction_path)==receipt['prediction_sha256']
            fit_ledger.append(receipt);all_predictions+=rows(prediction_path);continue
        assert not started.exists() and not artifact_path.exists() and not state_path.exists() and not prediction_path.exists(),'AMBIGUOUS_FIT_CLAIM_STOP'
        training_path=PRIVATE/'training'/f'BLOCK_{block:02d}_PAST_ONLY.jsonl.gz'
        assert sha(training_path)==item['training_payload_sha256']
        payload=rows(training_path);train=[rm[r['entry_id']] for r in payload]
        split=design['split']['blocks'][block-1];test=[r for r in runtime if r['session'] in split['test']]
        assert {r['session'] for r in train}<=set(split['train']) and max(r['session'] for r in train)<min(split['test'])
        original=read(INPUTS/'models'/f'MOVE_P_BLOCK_{block:02d}.json')
        assert sha(INPUTS/'models'/f'MOVE_P_BLOCK_{block:02d}.json')==item['preprocessing_authority_sha256']
        assert [r['entry_id'] for r in train]==original['train_entry_ids']
        y=np.array([r[target] for r in payload],dtype=int);assert set(y)=={0,1}
        a,z,prep=transform(train,test,design['feature_numeric_order'])
        assert prep==original['preprocessing']
        clf=LogisticRegression(**design['parameters'])
        save(started,{'exact_jst':now(),'head':head,'block':block,'attempt':1,'status':'STARTED',
            'claim_sha256':sha(OUT/'FIT_CLAIM.json'),'training_sha256':sha(training_path)})
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter('always');clf.fit(a,y)
        bad=[w for w in observed if issubclass(w.category,ConvergenceWarning)]
        if bad:
            save(PRIVATE/'CONTRACT_FAIL.json',{'exact_jst':now(),'head':head,'block':block,'reason':'ConvergenceWarning',
                'configuration_rescue':0,'further_fits':0,'messages':[str(w.message) for w in bad]})
            raise RuntimeError('QUALITY_CONTRACT_FAIL_CONVERGENCE_NO_RETRY')
        probability=clf.predict_proba(z)[:,1]
        artifact={'head':head,'target':target,'block':block,'train_session_N':len(split['train']),
            'train_through':max(split['train']),'test_dates':split['test'],'train_N':len(train),
            'train_positive_N':int(y.sum()),'train_entry_ids':[r['entry_id'] for r in train],
            'parameters':design['parameters'],'preprocessing':prep,'coef':clf.coef_[0].tolist(),
            'intercept':float(clf.intercept_[0]),'iterations':int(clf.n_iter_[0]),
            'heldout_teacher_payload_reads':0,'ConvergenceWarning_N':0,'fit_attempt':1}
        assert np.max(np.abs(predict_saved(test,artifact)-probability))<=1e-12
        save(artifact_path,artifact)
        state_path.parent.mkdir(exist_ok=True,parents=True)
        with state_path.open('xb') as f:
            np.savez(f,coef=clf.coef_,intercept=clf.intercept_,classes=clf.classes_,iterations=clf.n_iter_,
                preprocessing_json=np.array(json.dumps(prep,sort_keys=True)),parameters_json=np.array(json.dumps(design['parameters'],sort_keys=True)))
        prediction=[{'entry_id':r['entry_id'],'session':r['session'],'block':block,'head':head,'probability':float(probability[i])} for i,r in enumerate(test)]
        gzsave(prediction_path,prediction)
        receipt={'exact_jst':now(),'head':head,'block':block,'target':target,'status':'COMPLETE','attempts':1,
            'train_N':len(train),'train_positive_N':int(y.sum()),'test_N':len(test),'iterations':int(clf.n_iter_[0]),
            'artifact_sha256':sha(artifact_path),'state_sha256':sha(state_path),'prediction_sha256':sha(prediction_path),
            'ConvergenceWarning_N':0,'heldout_teacher_payload_reads':0}
        save(done,receipt);fit_ledger.append(receipt);all_predictions+=prediction
        print(json.dumps({'fit':len(fit_ledger),'head':head,'block':block,'iterations':int(clf.n_iter_[0]),'convergence_warning':0}),flush=True)
    assert counts()['total_fits']==16 and len(fit_ledger)==16
    assert len(all_predictions)==2078 and len({(r['head'],r['entry_id']) for r in all_predictions})==2078
    gzsave(PRIVATE/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz',all_predictions)
    report={'exact_jst':now(),'fit_count':{'MOVE_U2':8,'MOVE_U3':8,'total':16,'CORE_H2_H3':0,'pP':0},
        'fit_ledger':fit_ledger,'OOF_per_head_N':1039,'common_supported_per_head_N':1028,
        'OOF_duplicates':0,'ConvergenceWarning_N':0,'heldout_teacher_payload_reads':0,
        'within_block_refit':0,'feature_hyperparameter_class_weight_threshold_search':0,
        'predictions_sha256':sha(PRIVATE/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz'),'CapitalReplay':0,'MAX3Replay':0,'Safety':SAFETY}
    save(OUT/'FITS_COMPLETE.json',report)
    checkpoint('Q6_FITS_COMPLETE','COMPLETE',['16 claimed fits completed exactly once',
        '8 expanding-origin blocks, no within-block refit or test label reads'],
        {'fit_count':16,'ConvergenceWarning_N':0,'OOF_duplicate_N':0},'Q7 primary Quality evaluation; no more fits')

if __name__=='__main__':main()
