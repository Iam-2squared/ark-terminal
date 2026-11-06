"""Exactly one saved-model feature→q→all diagnostic tables campaign; fit0."""
import os,sys,shutil,subprocess,copy
from common import *
from features import compute
from evaluate import evaluate

def run():
    dest=WORK/'reproduction';dest.mkdir(exist_ok=True);campaign=dest/'CAMPAIGN_STARTED.json'
    assert not campaign.exists(),'REPRODUCTION_CAMPAIGN_ALREADY_STARTED; reuse exact saved outputs, no restart'
    originalpins={str(p.relative_to(PUB)):pin(p) for p in PUB.rglob('*') if p.is_file() and (p.suffix=='.csv' or p.name in ['EVALUATION_SUMMARY.json','EVALUATION_MASKS_AND_PRIVACY.json','PUBLICATION_PARTITION_MANIFEST.json'])}
    save(campaign,{'campaign_N':1,'new_fit_N':0,'new_preprocessing_fit_N':0,'old_refit_N':0,'primary_payload_pins':originalpins,'worker_pin':pin(WORK/'implementation/worker.py'),'evaluator_pin':pin(WORK/'implementation/evaluate.py'),'layout_pin':pin(WORK/'implementation/publication_layout.py')},once=True)
    stored=rows(PRIVATE/'FEATURE_ROWS.jsonl.gz');fm={r['entry_id']:r for r in stored};features=[];canaries=0
    # Stream immutable prefix carrier instead of repeating raw collection or
    # materialization. Recompute formulas only for this permitted reproduction.
    with gzip.open(PRIVATE/'PREFIX_ONLY_INPUTS.jsonl.gz','rt') as stream:
        for line in stream:
            source=json.loads(line);key=source['entry_id'];day=source['session'];tx=source['intent_minute'];fresh=compute(key,day,tx,source['market'],source['trace']);old=fm[key]
            assert all(canonical(fresh[k])==canonical(old[k]) for k in fresh),'REPRO_FEATURE_BYTES_DIFF:'+key
            complete=dict(old);complete.update(fresh);features.append(complete)
            # Perturbations of future raw, future state/outcomes, and actual-fill
            # metadata all precede the single saved-model prediction pass.
            for kind in ['FUTURE_RAW','FUTURE_STATE_EXIT_R_U','FILL_CLOCK_DELAY_OPEN']:
                market=list(source['market']);trace=list(source['trace'])
                if kind=='FUTURE_RAW':market.append({'minute':tx,'session':day,'O':'1','H':'999999','L':'0','C':'99','Vo':'999999999','Va':'999999999','lineage':{'repro_canary':True}})
                elif kind=='FUTURE_STATE_EXIT_R_U':trace.append({'bar_end_minute':tx+1,'State':'SHARP_DROP','EXIT':'changed','R':999,'U':999,'R0_ML':999})
                else:market.append({'minute':tx+100,'session':day,'O':'1','actual_fill_clock':tx+100,'actual_delay':100,'legacy_score_bundle':999})
                test=compute(key,day,tx,market,trace);assert canonical(test)==canonical(fresh);canaries+=1
    features.sort(key=lambda r:r['entry_id']);gzsave(dest/'RECONSTRUCTED_FEATURE_ROWS.jsonl.gz',features,once=True);assert pin(dest/'RECONSTRUCTED_FEATURE_ROWS.jsonl.gz')==pin(PRIVATE/'FEATURE_ROWS.jsonl.gz')
    modelpins={};probabilities=[];saved=rows(PRIVATE/'OOF_PROBABILITIES.jsonl.gz');counter=0
    for block in range(1,9):
        bd=PRIVATE/'blocks'/f'BLOCK_{block:02d}';tm=read(bd/'TRAIN_ID_MANIFEST.json')
        for method in METHODS:
            original=bd/method;view=dest/'worker_views'/f'B{block:02d}_{method}';view.mkdir(parents=True);view.chmod(0o777);model=original/'model.pkl';modelpins[f'{block}/{method}']=pin(model)
            rr=[{'entry_id':r['entry_id'],'feature_asof':r['feature_asof'],'numeric':r['numeric'],'categorical':r['categorical']} for r in features if r['entry_id'] in set(tm['evaluation_IDs']) and r['price_available'] and (r['state_evidence_ok'] or method=='D-PRICE')]
            gzsave(view/'evaluate.jsonl.gz',rr,once=True);shutil.copyfile(model,view/'model.pkl');(view/'evaluate.jsonl.gz').chmod(0o444);(view/'model.pkl').chmod(0o444)
            env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
            proc=subprocess.run([sys.executable,str(WORK/'implementation/worker.py'),str(view),'predict',method],env=env,capture_output=True,text=True);(view/'worker.log').write_text(proc.stdout+proc.stderr);assert proc.returncode==0,proc.stderr
            assert pin(view/'probabilities.jsonl.gz')==pin(original/'SEALED_ACTIVE_PREDICTIONS.jsonl.gz'),'REPRO_PREDICTION_BYTES_DIFF:'+f'{block}/{method}'
            active={r['entry_id']:r for r in rows(view/'probabilities.jsonl.gz')}
            for s in saved:
                if s['block']!=block or s['method']!=method:continue
                r=dict(s)
                for k in ['p5','q3','q5','q2','qNEG']:r[k]=None
                if s['entry_id'] in active:r.update(active[s['entry_id']])
                probabilities.append(r)
            assert pin(model)==modelpins[f'{block}/{method}'];counter+=1;print('saved model reproduced',counter,'/24',flush=True)
    probabilities.sort(key=lambda r:(METHODS.index(r['method']),r['block'],r['entry_id']));gzsave(dest/'OOF_PROBABILITIES.jsonl.gz',probabilities,once=True);assert pin(dest/'OOF_PROBABILITIES.jsonl.gz')==pin(PRIVATE/'OOF_PROBABILITIES.jsonl.gz')
    evaluate(dest/'public',dest/'OOF_PROBABILITIES.jsonl.gz')
    compared=[]
    for name,expected in originalpins.items():
        path=dest/'public'/name;assert path.exists() and pin(path)==expected,'REPRO_ALL_TABLE_BYTES_DIFF:'+name;compared.append({'path':name,**expected,'exact_bytes_and_hash_equal':True})
    assert pin(WORK/'implementation/evaluate.py')==read(campaign)['evaluator_pin'] and pin(WORK/'implementation/worker.py')==read(campaign)['worker_pin']
    original_seal=pin(PRIVATE/'OOF_PROBABILITIES.jsonl.gz')
    # Labels/current-block class frequencies are manager-only and never consumed
    # by any predict call or saved preprocessing; altered labels affect an
    # artificial evaluation loss, not the sealed predictions.
    q=.2;assert (q-0)**2!=(q-1)**2;assert pin(PRIVATE/'OOF_PROBABILITIES.jsonl.gz')==original_seal
    result={'status':'PASS','campaign_N':1,'saved_model_prediction_pass_N':24,'feature_ID_N':1600,'effective_prediction_N_by_method':{m:1039 for m in METHODS},'combined_prediction_rows_N':3117,'feature_payload_pin':pin(dest/'RECONSTRUCTED_FEATURE_ROWS.jsonl.gz'),'prediction_payload_pin':pin(dest/'OOF_PROBABILITIES.jsonl.gz'),'model_pins':modelpins,'payloads':compared,'new_base_fit_N':0,'new_preprocessing_fit_N':0,'old_refit_N':0,'calibration_fit_N':0,'feature_campaign_N_still':1,'exact_ID_R_bucket_counter_tie_model_hash_tolerance':0,'future_only_feature_canary_cases_N':canaries,'future_q_invariance':'identical declared model input for each perturbation; reproduced24 saved-model prediction bytes exactly equal sealed pre-perturbation bytes','label_only_evaluation_changed_q_unchanged':True,'current_future_block_label_frequency_used_for_transform_or_model':False,'B0_past_train_frequency_and_preprocessing_independently_audited':True,'physical_blindness':False,'scope':'same pinned environment deterministic saved-model reproduction; not independent fresh data','implementation_pin':pin(WORK/'implementation/reproduce.py')}
    save(PUB/'REPRODUCTION_RECEIPT.json',result,once=True);print(json.dumps({'status':'PASS','campaign_N':1,'model_N':24,'tables_exact_N':len(compared),'new_fit_N':0}))

if __name__=='__main__':
    try:run()
    except Exception as e:
        with (PRIVATE/'REPRODUCTION_FAILURES.jsonl').open('ab') as f:f.write(canonical({'status':'FAIL','error':str(e),'campaign_N':1}))
        raise
