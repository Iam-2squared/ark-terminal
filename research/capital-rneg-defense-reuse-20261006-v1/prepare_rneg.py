"""Identity/as-of/target audit and metadata-only recipe freeze; no learner fits."""
import gzip, json, sys, math
from collections import Counter
from decimal import Decimal as D
import numpy as np
from rneg_io import *

sys.path.insert(0,str(REPO/'research/capital-max3-top3-quality-v3-20261004-v1'))
from preprocessing import predict_saved
sys.path.insert(0,str(V5))
from execution import valid_market

def main():
    PRIVATE.mkdir(exist_ok=True)
    runtime=rows(Q/'CORE_RUNTIME_CAUSAL.jsonl.gz'); stream=rows(SPECTRUM/'source/candidate_stream.jsonl.gz')
    teachers=rows(Q/'TEACHERS_EVALUATION.jsonl.gz'); canonical=rows(SPECTRUM/'evaluation-only/R_SPECTRUM_ROWS.jsonl.gz')
    entries=rows(Q/'FROZEN_ENTRY.jsonl.gz'); books=rows(Q/'MARKET_TEACHER_BOOK.jsonl.gz')
    maps=[]
    for rr in (runtime,stream,teachers,canonical,books):
        assert len({r['entry_id'] for r in rr})==len(rr)
        maps.append({r['entry_id']:r for r in rr})
    rm,sm,tm,lm,bm=maps; em={r['watch_key']:r for r in entries if r['entry_status']=='FIRST_ENTRY'}
    assert len(runtime)==1600 and len(stream)==1039 and set(sm)==set(lm)
    assert sha(Q/'CORE_RUNTIME_CAUSAL.jsonl.gz')=='827abcf716c9203a70bc766783948a6be3cee3428abf6a772d1c3495096fd197'
    assert sha(SPECTRUM/'source/candidate_stream.jsonl.gz')=='c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4'
    assert sha(SPLIT_PATH)=='e83291b8706c48a4e496739219f1a645246b73be28f2195bebfaeb6614a12274'
    split=read(SPLIT_PATH); assert sorted({r['session'] for r in runtime})==split['all58']
    core=read(REPO/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/CORE_FEATURE_MANIFEST.json')
    assert sha(REPO/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/CORE_FEATURE_MANIFEST.json')=='3aa3abd322e239d27776dfde896d93e38c4e84602ddbf0f9d6a6451865ba55f2'
    old_model=read(HL/'models/HL0_BLOCK_01.json')
    numeric=old_model['preprocessing']['numeric_fields']; categorical=old_model['preprocessing']['categorical_fields']
    assert len(numeric)==27 and len(categorical)==7
    assert all(set(r['numeric'])==set(numeric) and set(r['categorical'])==set(categorical) for r in runtime)
    grid_path=next((DATA/'entry_base').rglob('PERSISTENT_GRID.jsonl.gz'))
    matrix_path=next((DATA/'entry_base').rglob('features_numeric.npy'))
    grid_id={}; grid_sessions=[]
    needed={em[k]['first_intent']['row_id'] for k in rm}
    with gzip.open(grid_path,'rt') as f:
        for i,line in enumerate(f):
            g=json.loads(line);grid_sessions.append(g['session'])
            if g['row_id'] in needed:
                assert g['row_id'] not in grid_id;grid_id[g['row_id']]=(i,g)
    matrix=np.load(matrix_path,mmap_mode='r'); assert matrix.shape==(462752,148)
    assert sha(matrix_path)==read(ENTRY/'FEATURE_COMPUTATION_RECEIPT.json')['numeric_sha256']
    p0=read(FREEZE/'P1_Q70_ENTRY_CONTRACT.json')['feature_manifest']['P0_numeric']; assert len(p0)==110
    duplicates={'clockMinute':'entry/intent_clock','activeMinutesSinceSelector':'selector/to_intent_active_delay'}
    additional=['p0/'+k for k in p0 if k not in duplicates]
    original_split=read(ENTRY/'SPLIT_PRECOMMIT.json')['folds']; dependency=[]
    train_cutoffs={}
    for fold in original_split:
        p=next((DATA/'frozen').rglob(f'P1_F{fold["id"]}_train_indices.npy'))
        indices=np.load(p);sessions={grid_sessions[int(i)] for i in indices}
        assert sessions<=set(fold['train']) and sessions.isdisjoint(fold['test'])
        train_cutoffs[fold['id']]=max(sessions)
        dependency.append({'entry_model_fold':fold['id'],'train_cutoff':max(sessions),
            'train_row_N':len(indices),'train_indices_hash':sha(p),'outer_test_teacher_inclusion':0,
            'model_dependencies':'Frozen P1 UPSIDE reuse and corrected QUALITY/ADVERSE; original model audit + saved train IDs',
            'entry_model_parameter_or_selection_exposure':'ITERATIVE_DEVELOPMENT; not removed by temporal teacher exclusion'})
    runtime_out=[]; target_out=[]; joins=[]; zero=Counter();target_difference=0
    for r in runtime:
        key=r['entry_id'];e=em[key];t=tm[key];b=bm[key]
        assert key==r['session']+'|'+r['symbol'] and key==e['watch_key']
        assert e['session']==r['session'] and e['symbol']==r['symbol'] and e['fill_minute']==r['entry_minute']
        assert e['fill_timestamp']==r['entry_timestamp']
        assert float(r['numeric']['entry/p1_score'])==e['first_intent']['score']
        assert float(r['numeric']['entry/p1_threshold'])==e['first_intent']['threshold']
        assert r['numeric']['entry/intent_clock']==e['first_intent']['intent_minute']
        assert train_cutoffs[e['first_intent']['fold']]<r['session']
        prefix_ok=(r['provenance']['max_known_minute'] is not None and r['provenance']['max_known_minute']<=r['entry_minute'])
        src=b.get('entry_actual_source');raw=D(r['raw_reference'])
        current_source_ok=bool(src and src['session']==r['session'] and src['minute']==r['entry_minute'] and D(src['O'])==raw and valid_market(src) and raw.is_finite() and raw>0)
        eligible=r['entry_minute']<920 and current_source_ok
        if key in lm:assert eligible==lm[key]['execution_eligible']
        rank_pass=sm[key]['admission'] if key in sm else None
        snap=grid_id.get(e['first_intent']['row_id']);p0_ok=False;index=None
        rr={**r,'numeric':dict(r['numeric']),'execution_eligible':eligible,'rank_pass':rank_pass,
            'D1_asof_ok':prefix_ok,'D2_asof_ok':False,'feature_as_of':r['entry_timestamp'],
            'max_source_available_at':r['session']+'T'+f'{r["provenance"]["max_known_minute"]//60:02d}:{r["provenance"]["max_known_minute"]%60:02d}:00+09:00' if prefix_ok else None,
            'historical_availability':'HISTORICAL_ASSUMED_AVAILABILITY',
            'input_dependency_train_cutoff':train_cutoffs[e['first_intent']['fold']]}
        if snap:
            index,g=snap
            assert index==e['first_intent']['row_index'] and g['watch_key']==key and g['session']==r['session'] and g['symbol']==r['symbol']
            assert g['intent_minute']==e['first_intent']['intent_minute'] and g['intent_minute']<=r['entry_minute']
            assert g['closed_raw_start']<g['intent_minute'] and g['feature_max_timestamp']==e['first_intent']['intent_timestamp']
            p0_ok=True
            for j,k in enumerate(p0):
                if k not in duplicates:
                    v=float(matrix[index,j]);assert not math.isinf(v)
                    rr['numeric']['p0/'+k]=v if math.isfinite(v) else None
            rr.update(D2_asof_ok=prefix_ok, p0_feature_as_of=g['feature_max_timestamp'], p0_snapshot_row_id=g['row_id'],
                p0_snapshot_row_index=index,p0_snapshot_hash=__import__('hashlib').sha256(matrix[index,:110].tobytes()).hexdigest())
        else:
            for k in additional:rr['numeric'][k]=None
        joins.append({'entry_id':key,'session':r['session'],'D1_asof_ok':prefix_ok,'P0_exact_intent_join':p0_ok,'P0_row_index':index})
        runtime_out.append(rr)
        known=t.get('realized_net_return') is not None and t.get('execution_status')=='COMPLETE' and eligible
        if key in lm:
            known=lm[key]['known'];value=lm[key].get('realized_net_return_ratio_decimal')
            debit=lm[key].get('buy_debit');credit=lm[key].get('sell_credit');exit_kind=lm[key].get('exit_kind')
        else:
            value=t.get('realized_net_return');debit=str(D(t['buy_effective'])*100) if known else None
            credit=str(D(t['sell_effective'])*100) if known else None;exit_kind=t.get('exit_kind')
        if known:
            assert D(debit)==100*raw*D('1.0005')
            assert D(debit)==D(t['buy_effective'])*100 and D(credit)==D(t['sell_effective'])*100
            assert abs(float(D(credit)/D(debit)-1)-t['realized_net_return'])<1e-14
            if key in lm:assert abs(float(value)-t['realized_net_return'])<1e-14
            z=int(D(credit)<D(debit));zero['strict_zero' if D(credit)==D(debit) else 'negative' if z else 'positive']+=1
            target_difference+=int(z!=int(t['realized_net_return']<=0))
        else:z=None;value=None
        target_out.append({'entry_id':key,'session':r['session'],'known':known,'r_original':value,'y_neg':z,
            'buy_debit':debit,'sell_credit':credit,'label_maturity':r['session']+'T'+f'{(t.get("release_minute") or 931)//60:02d}:{(t.get("release_minute") or 931)%60:02d}:00+09:00',
            'exit_kind':exit_kind,'source':'CANONICAL_CAPITAL_R' if key in lm else 'REUSED_TEACHERS_EVALUATION_WARMUP',
            'execution_eligible':eligible})
    coverage=[]
    for block in split['blocks']:
        rr=[r for r in runtime_out if r['session'] in block['test'] and r['execution_eligible']]
        coverage.append({'block':block['block'],'eligible_N':len(rr),'D1_connected_N':sum(r['D1_asof_ok'] for r in rr),
            'D2_connected_N':sum(r['D2_asof_ok'] for r in rr),'D2_connection_rate':sum(r['D2_asof_ok'] for r in rr)/len(rr)})
    d2=bool(additional) and all(x['D2_connection_rate']>=.90 for x in coverage)
    old_predictions={r['entry_id']:r for r in rows(HL/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')};reuse=[];hl_preds=[]
    hashes=read(HL/'MODEL_HASHES.json')
    for block in split['blocks']:
        name=f'HL0_BLOCK_{block["block"]:02d}.json';p=HL/'models'/name;model=read(p)
        assert sha(p)==hashes[name] and model['test_dates']==block['test']
        assert all(rm[k]['session'] in block['train'] for k in model['train_entry_ids'])
        test=[r for r in runtime if r['session'] in block['test']];pred=predict_saved(test,model)
        error=max(abs(float(v)-old_predictions[r['entry_id']]['HL0']['p']) for r,v in zip(test,pred));assert error<=1e-12
        for r,v in zip(test,pred):hl_preds.append({'entry_id':r['entry_id'],'block':block['block'],'score':float(v),'model_hash':sha(p)})
        reuse.append({'block':block['block'],'model_hash':sha(p),'train_N':model['train_N'],'train_ID_hash':__import__('hashlib').sha256(json.dumps(model['train_entry_ids']).encode()).hexdigest(),'train_cutoff':model['train_through'],'prediction_parity_max_abs':error,'new_fit':0})
    gzsave(PRIVATE/'RUNTIME_FEATURES.jsonl.gz',runtime_out,exclusive=True)
    gzsave(PRIVATE/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz',target_out,exclusive=True)
    gzsave(PRIVATE/'HL0_REUSED_OOF.jsonl.gz',hl_preds,exclusive=True)
    gzsave(PRIVATE/'FEATURE_IDENTITY_JOIN.jsonl.gz',joins,exclusive=True)
    save(OUT/'HL0_REUSE_AUDIT.json',{'status':'PASS','fits':0,'models':reuse,'old_target':'R<=0','current_target':'R<0','strict_zero_N':zero['strict_zero'],'target_difference_N':target_difference})
    save(OUT/'RNEG_TARGET_BINDING.json',{'status':'PASS','formula':'sell_credit/buy_debit-1','BUY':'1.0005','SELL':'0.9995','commission':0,'cost_applied_once':True,'known_N':sum(r['known'] for r in target_out),'warmup_known_N':sum(r['known'] and r['session'] in split['warmup20'] for r in target_out),'counts':dict(zero),'canonical_teacher_mismatches':0,'unknown_is_null':True,'new_R_materializations':0})
    save(OUT/'FEATURE_JOIN_COVERAGE.json',{'fixed_before_results':True,'D2_enabled':d2,'additional_numeric_N':len(additional),'duplicates_excluded':duplicates,'blocks':coverage,'identity_mismatch_N':0,'D2_source_status':'DIRECT_FROZEN_RAW_MATRIX_REUSE; no feature regeneration','coverage_contract':'exact Frozen first-intent snapshot available before same Entry quantity decision; source staleness retained'})
    save(OUT/'FEATURE_ASOF_CONTRACT.json',{'status':'PASS_ASSUMED_AVAILABILITY','quantity_decision':'native V5 event t=Frozen fill_minute, after SELL cash release and admission, before occupancy and quantity allocation',
        'CORE':'State closed-bar end<=t; bar end is source raw-start+1. Synchronize state prefix before risk and allocation at same event t.',
        'fill_price':'Only raw open quote at t used by existing V5 to compute lot/debit; Defense inherits that quote availability assumption. No H/L/C/volume of fill bar enters CORE raw-reference delta.',
        'P0':'Exact first_intent.row_id and row_index; raw numeric snapshot at intent, closed raw-start<intent<=fill. No closest-row join; no forward snapshot.',
        'asof_proof':'Frozen extractor assertion max(raw-start)+1<=intent, fixed State raw-start+1 bar-end contract, exact identity and provenance for all1600; prior independent source audit reused',
        'same_time_stage_order':['State prefix closed at t','SELL/cash release','Frozen Entry admission','Defense','V5 occupancy/reserve','V5 allocation','BUY'],
        'historical_actual_arrival':'UNKNOWN','certification':'HISTORICAL_ASSUMED_AVAILABILITY; not live/PIT-certified',
        'numeric_fields':numeric,'categorical_fields':categorical,'additional_D2_fields':additional,
        'learned_feature_dependencies':dependency,'learned_input_outer_test_teacher_reads':0,
        'abstain':'Missing/late mandatory CORE prefix or unavailable exact P0 snapshot => PASS; normal numerical missingness and categories retain train-only UNKNOWN transform',
        'State_ID_semantics_changed':False,'State9_Path_recomputed':False})
    inputs={str(p.relative_to(WORK)):sha(p) for p in [Q/'CORE_RUNTIME_CAUSAL.jsonl.gz',Q/'TEACHERS_EVALUATION.jsonl.gz',Q/'FROZEN_ENTRY.jsonl.gz',Q/'MARKET_TEACHER_BOOK.jsonl.gz',SPECTRUM/'source/candidate_stream.jsonl.gz',SPECTRUM/'evaluation-only/R_SPECTRUM_ROWS.jsonl.gz',grid_path,matrix_path,SPLIT_PATH]}
    save(OUT/'SOURCE_BINDING.json',{'status':'PASS','source_hashes':inputs,'basis_head':read(OUT/'checkpoints/EXECUTION_STARTED.json')['execution_basis_head'],'basis_tree':read(OUT/'checkpoints/EXECUTION_STARTED.json')['execution_basis_tree'],'source_files_immutable':True,'upstream_edits':0})
    save(OUT/'REUSE_MATRIX.json',{'assets':[
        {'asset':'CORE State9/Path','target':'representation','as_of':'closed-bar end<=fill','Entry_connection':'1600 exact','decision':'reuse; existing State not newly introduced'},
        {'asset':'HL0','target':'net R<=0','as_of':'8 past-only folds','Entry_connection':'1039 exact; coefficient parity verified','decision':'reuse reference; no refit','past_AUC':.502645068529545},
        {'asset':'Frozen P0','target':'original Entry context110 numeric','as_of':'exact original first intent<=fill','Entry_connection':'exact row ID/index','decision':'reuse108 nonduplicate direct numeric snapshots'},
        {'asset':'Warmup R','target':'same Capital EXIT/EOD return','as_of':'mature before fold cutoff','Entry_connection':'exact eligible known','decision':'reuse old TEACHERS; canonical overlap debit/credit and R parity'},
        {'asset':'HF1/MRET/MOVE experts','target':'different','decision':'exclude from X and deployment; no rename/blend'},
        {'asset':'old566 features','target':'different lineage','decision':'exclude'},
        {'asset':'V5 RESET20','target':'baseline accounts','decision':'reuse21 planned9complete12coverage unknown; no new Control full replay'}]})
    save(OUT/'PREPARED_INPUT_CONFIG.json',{'D1_numeric':numeric,'categorical':categorical,'D2_numeric':numeric+additional,'D2_enabled':d2,
        'input_hashes':{p.name:sha(p) for p in PRIVATE.glob('*.jsonl.gz')}})
    print(json.dumps({'D2_enabled':d2,'coverage':coverage,'known_training_targets':sum(r['known'] for r in target_out),'HL0_refits':0}))

if __name__=='__main__':main()
