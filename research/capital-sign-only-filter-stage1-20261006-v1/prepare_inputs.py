"""Bind fixed feature families by producer definitions, never by sign association."""
import pickle
from sign_io import *

def main():
    cfg=read(OLD_OUT/'PREPARED_INPUT_CONFIG.json'); old_rows=rows(OLD/'RUNTIME_FEATURES.jsonl.gz')
    rm={r['entry_id']:r for r in old_rows};split=read(SPLIT)
    assert len(rm)==1600 and len(split['all58'])==58 and len(split['warmup20'])==20 and len(split['OOF38'])==38
    p1deps=read(OLD_OUT/'FEATURE_ASOF_CONTRACT.json')['learned_feature_dependencies']
    # The inherited producer graph was previously independently audited using
    # saved train-index arrays and original grid-session identity. No raw grid is regenerated.
    deps={d['entry_model_fold']:d for d in p1deps}
    entries=rows(REUSE/'authority_data/quality_original/inputs/FROZEN_ENTRY.jsonl.gz')
    em={r['watch_key']:r for r in entries if r['entry_status']=='FIRST_ENTRY'}
    p1_receipts=[]
    for r in old_rows:
        dep=deps[em[r['entry_id']]['first_intent']['fold']]
        assert dep['train_cutoff']==r['input_dependency_train_cutoff']<r['session']
        assert em[r['entry_id']]['first_intent']['score']==r['numeric']['entry/p1_score']
        p1_receipts.append({'entry_id':r['entry_id'],'producer_fold':dep['entry_model_fold'],
                           'producer_cutoff':dep['train_cutoff'],'producer_train_indices_hash':dep['train_indices_hash']})
    quality_audit=read(SCORE/'producer_public/INDEPENDENT_AUDIT.json')
    assert quality_audit['labels_mask_split_preprocessing_coef_snapshot_OOF_mismatch_N']==0
    assert all(c['status']=='PASS' for c in quality_audit['canaries'] if c['name'] in ['train<test','test label leakage0','future High in X=0','PnL in X=0','release in X=0','future bar in X=0','prefix cutoff','prior date','Movement boundary'])
    assert read(SCORE/'producer_public/S9R_CERTIFICATION_DECISION.json')['S9R']=='PASS'
    p5path=SCORE/'capital_v2_private/CORE_P5_SCORE_STREAM.jsonl.gz'
    movepath=SCORE/'quality_original/private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz'
    mretpath=SCORE/'mret/private/CERTIFIED_INDEPENDENT_MRET_OOF_SCORES.jsonl.gz'
    assert sha(p5path)=='a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731'
    assert sha(mretpath)=='90f4dc118b1a688408efade72193c7a7f3a6a74df299336e7ba7615943ad812b'
    p5=rows(p5path);move=rows(movepath);mret=rows(mretpath)
    scores={k:{} for k in ['pP','MOVE_U2','MOVE_U3','MRET']}
    for r in p5:scores['pP'][r['entry_id']]={'block':r['block'],'value':r['pP'],'model_hash':r['P_model_sha256']}
    for r in move:
        assert r['head'] in ['MOVE_U2','MOVE_U3']
        scores[r['head']][r['entry_id']]={'block':r['block'],'value':r['probability']}
    for r in mret:scores['MRET'][r['entry_id']]={'block':r['block'],'value':r['mP']}
    producers=[];score_receipts=[]
    expected=set(r['entry_id'] for r in old_rows if r['session'] in split['OOF38'])
    model_specs={'pP':(SCORE/'capital_v2_private/models','CORE_P'),
                 'MOVE_U2':(SCORE/'quality_original/private/models','MOVE_U2'),
                 'MOVE_U3':(SCORE/'quality_original/private/models','MOVE_U3'),
                 'MRET':(SCORE/'level_0/private/models','MRET')}
    mret_hashes={r['block']:r['model_sha256'] for r in read(SCORE/'producer_public/MRET_COMPLETED_FITS_REUSE_FREEZE.json')['fit_ledger']}
    p5hashes=read(SCORE/'capital_quality_v3_private/SOURCE_MANIFEST.json')
    for name,(directory,prefix) in model_specs.items():
        assert set(scores[name])==expected, name
        for b in split['blocks']:
            path=directory/f'{prefix}_BLOCK_{b["block"]:02d}.json';model=read(path);mh=sha(path)
            assert model['test_dates']==b['test'] and model['train_through']==b['train'][-1]
            ids=model['train_entry_ids'];assert len(ids)==len(set(ids))==model['train_N']
            assert all(rm[k]['session'] in b['train'] and rm[k]['session']<b['test'][0] for k in ids)
            assert set(ids).isdisjoint({k for k,r in rm.items() if r['session'] in b['test']})
            if name=='MRET':assert mh==mret_hashes[b['block']]
            if name=='pP':assert mh==p5hashes['capital_v2_private/models/'+path.name]
            # All saved producer inputs are mechanical prefix features plus
            # the inherited frozen P1 input, whose graph is audited separately.
            fields=model['preprocessing']['numeric_fields']+model['preprocessing']['categorical_fields']
            assert all(k.startswith(('entry/','selector/','state/','path/','movement/')) for k in fields)
            producers.append({'score':name,'block':b['block'],'model_sha256':mh,'train_ID_N':len(ids),
                              'train_ID_hash':digest(ids),'producer_cutoff':model['train_through'],
                              'outer_test_teacher_inclusion_N':0,'new_fit':0,'model_path':str(path.relative_to(WORK)),
                              'source_asof_audit':'reused CORE/Movement prefix canaries and inherited P1 graph',
                              'numerical_operator':'certified independent saved OOF' if name=='MRET' else 'native saved first OOF'})
            for k,r in scores[name].items():
                if r['block']!=b['block']:continue
                assert rm[k]['session'] in b['test'] and model['train_through']<rm[k]['session']
                if name=='pP':assert r['model_hash']==mh
                assert 0<=r['value']<=1
                score_receipts.append({'entry_id':k,'score':name,'producer_block':b['block'],
                                       'producer_cutoff':model['train_through'],'model_hash':mh,
                                       'feature_as_of':rm[k]['entry_timestamp'],'actual_arrival':'UNKNOWN'})
    extra=['score/pP','score/MOVE_U2','score/MOVE_U3','score/MRET']
    # Selector anchor price progress belongs to Selector context, not State.
    # Clock/delay of the Entry itself belongs to PRICE/time. No correlation is inspected.
    cbase=['entry/p1_score','entry/p1_threshold']+[k for k in cfg['D2_numeric'] if k.startswith('selector/')]+[
           'p0/priceVsFirstSelectorPct','p0/knownRefreshCount','p0/activeMinutesSinceLatestSelector']
    bnum=[k for k in cfg['D2_numeric'] if k.startswith(('state/','path/'))]
    anum=[k for k in cfg['D2_numeric'] if k not in set(cbase+bnum)]
    group_specs={
      'SF_A_PRICE':{'numeric':anum,'categorical':[],'enabled':True,'asof_flag':'A_asof_ok'},
      'SF_B_STATE':{'numeric':bnum,'categorical':cfg['categorical'],'enabled':True,'asof_flag':'B_asof_ok'},
      'SF_C_SCORE':{'numeric':cbase+extra,'categorical':[],'enabled':True,'asof_flag':'C_asof_ok'},
      'SF_D_UNION':{'numeric':cfg['D2_numeric']+extra,'categorical':cfg['categorical'],'enabled':True,'asof_flag':'D_asof_ok'}}
    assert len(set(anum+bnum+cbase+extra))==len(cfg['D2_numeric'])+4
    features=[]
    for recipe in RECIPES[:3]:
        for kind in ['numeric','categorical']:
            for k in group_specs[recipe][kind]:
                is_score=k.startswith('score/') or k.startswith('entry/p1_')
                producer='saved first-OOF producer' if k.startswith('score/') else 'Frozen P1 first-intent' if k.startswith('entry/p1_') else 'Frozen P0 first-intent snapshot' if k.startswith('p0/') else 'CORE closed State/Path prefix' if recipe=='SF_B_STATE' else 'CORE frozen Entry/Selector projection'
                definition='stored '+k+'; read/join only; no new market calculation'
                features.append({'column':k,'kind':kind,'family':recipe,'producer':producer,
                                 'definition':definition,'learned':is_score,
                                 'source_definition':'price_features.py:compute' if k.startswith('p0/') else 'saved producer preprocessing' if k.startswith('score/') else 'core_features.py:project',
                                 'asof':'first intent <= decision' if k.startswith('p0/') or k.startswith('entry/p1_') else 'closed prefix or saved score <= original fill decision',
                                 'selection_basis':'producer metadata/code semantics; no outcomes or correlations',
                                 'duplicate_of':None})
    runtime=[]
    for r in old_rows:
        rr={k:r[k] for k in ['entry_id','session','entry_timestamp','entry_minute','execution_eligible','rank_pass','feature_as_of','max_source_available_at','input_dependency_train_cutoff','p0_feature_as_of','p0_snapshot_hash','historical_availability']}
        rr['numeric']={k:r['numeric'][k] for k in cfg['D2_numeric']};rr['categorical']=r['categorical'].copy()
        for name in scores:rr['numeric']['score/'+name]=scores[name].get(r['entry_id'],{}).get('value')
        prefix=bool(r['D1_asof_ok'] and r['max_source_available_at']<=r['entry_timestamp'])
        p0=bool(r['D2_asof_ok'] and r['p0_feature_as_of']<=r['entry_timestamp'])
        p1=bool(r['input_dependency_train_cutoff']<r['session'])
        rr.update(A_asof_ok=prefix and p0,B_asof_ok=prefix,C_asof_ok=prefix and p0 and p1,D_asof_ok=prefix and p0 and p1)
        runtime.append(rr)
    assert all(r['D_asof_ok'] for r in runtime),'MANDATORY_SOURCE_ASOF_BLOCKED'
    gzsave(PRIVATE/'INPUT_ROWS.jsonl.gz',runtime,exclusive=True)
    gzsave(PRIVATE/'SCORE_LINEAGE_ROWS.jsonl.gz',score_receipts,exclusive=True)
    gzsave(PRIVATE/'P1_LINEAGE_ROWS.jsonl.gz',p1_receipts,exclusive=True)
    # Reference adapters expose only identities, probabilities, and lineage.
    oldpred=rows(OLD/'INITIAL_OOF_PREDICTIONS.jsonl.gz');hlpred=rows(OLD/'HL0_REUSED_OOF.jsonl.gz')
    gzsave(PRIVATE/'REFERENCE_OOF.jsonl.gz',[{'entry_id':r['entry_id'],'block':r['block'],'recipe':'OLD_'+r['recipe'],'score_neg':r['score'],
            'model_prediction_valid':r['can_veto'],'model_hash':r['model_hash'],'original_prediction_status':r['prediction_status']} for r in oldpred]+
           [{'entry_id':r['entry_id'],'block':r['block'],'recipe':'HL0','score_neg':r['score'],'model_prediction_valid':rm[r['entry_id']]['D1_asof_ok'],
             'model_hash':r['model_hash'],'original_prediction_status':'REUSED_INITIAL_OOF'} for r in hlpred],exclusive=True)
    spectrum=REUSE/'authority_data/spectrum/Ark_Capital_Full_R_Spectrum_Anatomy_20261006_PRIVATE/source/native_trades.jsonl.gz'
    # Identity-only membership view. Economic values never leave this adapter.
    funded={r['entry_id'] for r in rows(spectrum)};assert len(funded)==150
    gzsave(PRIVATE/'AUXILIARY_MEMBERSHIP.jsonl.gz',[{'entry_id':r['entry_id'],'rank_pass':bool(r['rank_pass']),'old_V5_purchased':r['entry_id'] in funded} for r in runtime],exclusive=True)
    save(OUT/'FEATURE_FAMILY_MAP.json',{'fixed_before_new_model_results':True,'recipes':group_specs,'features':features,'unresolved_columns':[],
         'union_order':'inherited D2 numeric order, then pP/MOVE_U2/MOVE_U3/MRET; inherited categorical order',
         'duplicates_removed':{'clockMinute':'entry/intent_clock','activeMinutesSinceSelector':'selector/to_intent_active_delay'},
         'new_market_feature_batches':0,'raw_old566_import':0,'HL0_D1_D2_stacking':0})
    save(OUT/'ASOF_AND_SCORE_LINEAGE.json',{'status':'PASS_HISTORICAL_ASSUMED_AVAILABILITY','historical_actual_arrival':'UNKNOWN',
         'live_PIT_certified':False,'decision':'original fill, before quantity and before Rank/Reserve/holding/cash selection',
         'availability_order':'closed State prefix + frozen first-intent snapshot; inherited raw fill OPEN quote assumption; no fill H/L/C/volume',
         'source_asof_checks_N':len(runtime),'asof_failures_N':0,'P1_dependencies':p1deps,'score_producers':producers,
         'score_rows':len(score_receipts),'warmup_extra_score_rows_missing':len([r for r in runtime if r['session'] in split['warmup20']]),
         'warmup_rebackscore':0,'in_sample_score_substitution':0,'producer_new_fits':0,
         'outer_test_in_producer_training':0,'score_recovery_status':'COMPLETE_ONE_MANIFEST_DIRECTED_RECOVERY; all four optional scores authenticated',
         'old_quality_baseline_incident':'preserved; baseline file integrity failed in old cycle, while producer label/mask/split/preprocessing/coef/OOF mismatch=0; no baseline file reused',
         'inherited_feature_audit_sha256':sha(OLD_OUT/'FEATURE_ASOF_CONTRACT.json'),
         'quality_producer_audit_sha256':sha(SCORE/'producer_public/INDEPENDENT_AUDIT.json'),
         'mret_cert_decision_sha256':sha(SCORE/'producer_public/S9R_CERTIFICATION_DECISION.json')})
    source_paths=[OLD/'RUNTIME_FEATURES.jsonl.gz',OLD/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz',OLD/'INITIAL_OOF_PREDICTIONS.jsonl.gz',OLD/'HL0_REUSED_OOF.jsonl.gz',SPLIT,p5path,movepath,mretpath,spectrum]
    public_origins=[p for d in ['research/capital-rneg-defense-reuse-20261006-v1','research/persistent-watchlist-uptrend-first-entry-20261003-v2','research/capital-max3-upward-staircase-v4-20261004-v1','research/capital-v5-max3-slot-intelligence-20261004-v1'] for p in (REPO/d).glob('*.py')]
    save(OUT/'SOURCE_BINDING.json',{'status':'PASS','execution_basis_head':read(OUT/'CURRENT_STATE.json')['execution_basis_head'],
      'execution_basis_tree':read(OUT/'CURRENT_STATE.json')['execution_basis_tree'],
      'design_basis_head':'6f3a09e4800a1cccbf359364c9acc9ba1f05e8dc',
      'private_sources':{str(p.relative_to(WORK)):sha(p) for p in source_paths},
      'frozen_code_hashes':{str(p.relative_to(REPO)):sha(p) for p in public_origins},
      'immutable_old_RNEG_evidence':{str(p.relative_to(REPO)):sha(p) for p in OLD_OUT.rglob('*') if p.is_file()},
      'new_view_input_hashes':{p.name:sha(p) for p in PRIVATE.glob('*.jsonl.gz')},
      'recovered_archive_hashes':{'old_RNEG':'a70abbbb2e4d9933d7a6479dff4e1081b07627ccaad5c3eeb2c3132e5312f47d','Quality_v3':'32fd8aecf83a57c564fa32806d7fc65b0fdc57393e6623597fbf747e76ac3db1','Main_handoff':'e9178ce4d57760f5c4176c0538eb69beccefadf9d29768c9f20f75bf18108c8c'},
      'source_recovery_missing':[],'new_provider_calls':0,'upstream_edits':0})
    ledger=read(OLD_OUT/'FIT_LEDGER.json')['ledger'];reuse=[]
    for recipe in RECIPES:
        spec=group_specs[recipe]
        matching=[old for old in ['D1','D2'] if spec['numeric']==cfg[old+'_numeric'] and spec['categorical']==cfg['categorical']]
        reuse.append({'recipe':recipe,'numeric_N':len(spec['numeric']),'categorical_N':len(spec['categorical']),
                      'column_signature':digest(spec),'equivalent_old_recipe':matching[0] if matching else None,
                      'planned_new_fits':0 if matching else 8,'planned_reuse_fits':8 if matching else 0,
                      'why':'different precommitted information subset/addition; same sign target, masks, preprocessing and learner' if not matching else 'exact inherited column order; verify each fold input signature before reuse'})
    save(OUT/'REUSE_MATRIX.json',{'new_fit_max':32,'planned_new_fits':sum(r['planned_new_fits'] for r in reuse),'recipes':reuse,
      'old_D1_D2_training_hashes':[{'recipe':r['recipe'],'block':r['block'],'training_input_hash':r['training_input_hash'],'model_hash':r['model_hash']} for r in ledger],
      'old_sign_target_already_used':True,'references':['B0','HL0','OLD_D1','OLD_D2'],'old_reference_refits':0,
      'SF_D_versus_OLD_D2':'same original135 numeric+7 categorical plus four authenticated saved scores; different input signature, not a renamed D2',
      'sign_view_change_alone_justifies_refit':False})
    print(canonical({'families':{k:[len(v['numeric']),len(v['categorical'])] for k,v in group_specs.items()},'extra_scores':list(scores),'planned_fits':32,'score_producers':len(producers)}))

if __name__=='__main__':main()
