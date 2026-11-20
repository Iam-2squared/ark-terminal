"""Source/identity audit. Only whitelisted score/time fields enter COMPOSE."""
import gzip, hashlib, json, math, pathlib, collections
from datetime import datetime
BASE=pathlib.Path(__file__).resolve().parents[2]
OUT=BASE/'resume'; SRC=BASE/'restored'
def pin(b):
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def jl(p):
    b=p.read_bytes();b=gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b
    return [json.loads(s) for s in b.splitlines()]
def keyed(rows):
    z={r['entry_id']:r for r in rows};assert len(z)==len(rows),'DUPLICATE_ID';return z
def pava3(x):
    pools=[]
    for v in x:
        assert math.isfinite(v) and 0<=v<=1
        pools.append([v,1])
        while len(pools)>1 and pools[-2][0]/pools[-2][1]<pools[-1][0]/pools[-1][1]:
            b=pools.pop();a=pools.pop();pools.append([a[0]+b[0],a[1]+b[1]])
    return [a/n for a,n in pools for _ in range(n)]
def main():
    candidate=keyed(jl(SRC/'SHARED/inputs/candidate_stream'))
    runtime=keyed(jl(SRC/'RD01/rd01/private/RUNTIME_INPUTS.jsonl.gz'))
    native_asof=keyed(json.loads((SRC/'RD01/rd01/private/ASOF_ROW_AUDIT.json').read_text()))
    features=keyed(jl(SRC/'S1/FEATURE_ROWS.jsonl.gz'));fb=keyed(jl(SRC/'S1/FEATURE_SOURCE_BINDING.jsonl.gz'))
    ids=set(runtime);assert ids==set(candidate)==set(native_asof) and ids<=set(features)==set(fb) and len(ids)==1039
    split=json.loads((SRC/'SHARED/inputs/split').read_text());blocks={b['block']:b for b in split['blocks']}
    qmaps={};modelpins=[];blocksummary=[];training={};sourcepins=[]
    for n in range(1,9):
        d=SRC/f'B{n:02}/blocks/BLOCK_{n:02}';tm=json.loads((d/'TRAIN_ID_MANIFEST.json').read_text());ps=json.loads((d/'PREDICTION_SEAL.json').read_text())
        assert tm['block']==n and not tm['predict_view_R_U_EXIT_suffix_fields_present'] and not tm['train_view_forbidden_fields_present'] and not ps['eval_outcome_joined_before_seal']
        assert tm['eval_sessions']==blocks[n]['test'] and tm['train_sessions']==blocks[n]['train']
        assert max(tm['train_sessions'])<min(tm['eval_sessions']) and sum(tm['class_counts'])==tm['train_N']
        assert tm['B0_p5']==[(a+.5)/(tm['train_N']+2.5) for a in tm['class_counts']]
        assert pin((d/'TRAIN_ID_MANIFEST.json').read_bytes())==ps['train_manifest']
        assert pin((d/'OOF_PROBABILITIES.jsonl.gz').read_bytes())==ps['predictions']
        oo=jl(d/'OOF_PROBABILITIES.jsonl.gz');ev=set(tm['evaluation_IDs']);assert len(ev)==tm['evaluation_N']
        assert ev=={i for i in ids if runtime[i]['block']==n}
        for method in ['D-LINEAR','D-PRICE','D-FULL']:
            qs=keyed([r for r in oo if r['method']==method]);assert set(qs)==ev
            se=keyed(jl(d/method/'SEALED_ACTIVE_PREDICTIONS.jsonl.gz'))
            assert set(se)==ev and pin((d/method/'SEALED_ACTIVE_PREDICTIONS.jsonl.gz').read_bytes())==ps['models'][method]['prediction']
            model=d/method/'model.pkl';assert pin(model.read_bytes())==ps['models'][method]['model']
            for i,r in qs.items():
                assert r['status']=='ACTIVE' and r['block']==n and r['B0_p5']==tm['B0_p5'] and r['model_hash']==ps['models'][method]['model']['sha256']
                for k in ['p5','q2','q3','q5','qNEG','feature_asof']:assert r[k]==se[i][k],(method,k)
                assert all(math.isfinite(r[k]) and 0<=r[k]<=1 for k in ['q2','q3','q5','qNEG']) and r['q5']<=r['q3']
                assert r['feature_asof']==features[i]['feature_asof']
            qmaps[n,method]=qs
            modelpins.append({'block':n,'method':method,'model':ps['models'][method]['model'],'prediction':ps['models'][method]['prediction'],'train_manifest':ps['train_manifest']})
        hmeta={}
        for head,basekey in [('H2','base2'),('H3','base3'),('H5','base5')]:
            hp=SRC/f'SHARED/inputs/frozen_models/{head}_BLOCK_{n:02}.json';h=json.loads(hp.read_text());dep=json.loads((SRC/f'RD01/rd01/private/base_train_dependencies/{head}_BLOCK_{n:02}.json').read_text())
            metadata=dep['metadata'];assert all(pin(hp.read_bytes())[k]==metadata[k] for k in ['bytes','sha256','git_blob'])
            assert h['block']==n and h['test_dates']==blocks[n]['test'] and h['train_through']==max(blocks[n]['train'])==metadata['train_cutoff']
            assert set(h['train_entry_ids'])==set(dep['train_ids']) and len(h['train_entry_ids'])==h['train_N']
            assert all(i.split('|')[0] in blocks[n]['train'] for i in h['train_entry_ids'])
            assert h['train_through']<min(h['test_dates'])
            for i in ev:
                assert candidate[i][head+'_hash']==metadata['sha256'] and candidate[i][basekey]==h['base_rate']
            hmeta[head]={'model_pin':pin(hp.read_bytes()),'train_cutoff':h['train_through'],'train_ID_N':h['train_N'],'test_sessions':h['test_dates'],'feature_asof':'native candidate provenance max_known_minute','available_at':'ACTUAL_ARRIVAL_UNKNOWN'}
        training[n]={'upside':hmeta,'downside_cutoff':tm['learning_cutoff'],'downside_train_N':tm['train_N'],'B0_p5':tm['B0_p5']}
        blocksummary.append({'block':n,'Entry_N':len(ev),'sessions':len(tm['eval_sessions']),'past_only_train_N':tm['train_N'],'q_methods_verified':3,'H_models_verified':3})
    composed=[];audit=[];mismatches=collections.Counter();lags=collections.Counter()
    for i in sorted(ids):
        c=candidate[i];r=runtime[i];a=native_asof[i];f=features[i];bind=fb[i];n=r['block'];ss,sy=i.split('|')
        assert ss==c['session']==r['session']==f['session'] and sy==str(c['symbol'])==str(r['symbol'])
        assert c['block']==n and ss in blocks[n]['test']
        assert c['entry_timestamp']==r['entry_timestamp']==r['t_rank']==a['t_rank'] and c['entry_minute']==r['entry_minute']==a['fill_minute']
        assert c['provenance']['max_known_minute']<=c['entry_minute'] and not a['late'] and a['max_source_available_at']<=r['t_rank']
        for k in ['ML','m2','m3','m5']:assert c[k]==r[k] and math.isfinite(r[k])
        fit=pava3([c[k] for k in ['p2','p3','p5']]);assert fit==[c[k] for k in ['m2','m3','m5']]
        assert 1>=c['base2']>=c['base3']>=c['base5']>=0 and sum(c[k] for k in ['base2','base3','base5'])>0
        assert sum(fit)/sum(c[k] for k in ['base2','base3','base5'])==r['ML']
        assert c['rank']==r['R0_rank']==('S' if r['ML']>=2 else 'A' if r['ML']>=1.5 else 'B' if r['ML']>=1 else 'C')
        assert r['R0_candidate_order']==[-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'],i]
        for k in ['intent_minute','intent_row_id','intent_row_index','max_raw_available_at','max_state_available_at']:assert f[k]==bind[k]
        tx=f['feature_asof'];assert tx.startswith(ss) and f['intent_row_id']==i+'|'+str(f['intent_minute'])
        assert datetime.fromisoformat(tx).hour*60+datetime.fromisoformat(tx).minute==f['intent_minute']
        assert max(f['max_raw_available_at'],f['max_state_available_at'])<=tx and c['entry_minute']>=f['intent_minute']
        assert c['provenance']['historical_actual_arrival']=='UNKNOWN' and 'ACTUAL_ARRIVAL_UNKNOWN' in f['availability_assumption']
        lag=c['entry_minute']-f['intent_minute'];lags[str(lag)]+=1
        if a['intent_timestamp_minute']!=f['intent_minute']:mismatches['parent_native_intent_field_differs_from_frozen_first_intent']+=1
        risk={}
        for method in ['D-FULL','D-PRICE']:
            q=qmaps[n,method][i];risk[method]={'q3':q['q3'],'q5':q['q5'],'B0_p5':q['B0_p5'],'model_sha256':q['model_hash'],'prediction_feature_asof':q['feature_asof'],'available_at':'ACTUAL_ARRIVAL_UNKNOWN'}
        row={k:c[k] for k in ['entry_id','session','symbol','block','entry_minute','entry_timestamp','p2','p3','p5','base2','base3','base5','m2','m3','m5','ML']}
        row.update({'R0_rank':r['R0_rank'],'R0_candidate_order':r['R0_candidate_order'],'first_intent_t_x':tx,'first_intent_minute':f['intent_minute'],'intent_row_id':f['intent_row_id'],'t_rank':r['t_rank'],'upside_feature_asof':a['max_source_available_at'],'H_source':training[n]['upside'],'downside_train_cutoff':training[n]['downside_cutoff'],'risk':risk,'asof_status':'HISTORICAL_MIXED_ASOF_RESEARCH_ONLY','actual_arrival':'UNKNOWN'})
        composed.append(row);audit.append({'entry_id':i,'session':ss,'symbol':sy,'block':n,'native_t_rank':r['t_rank'],'native_fill_minute':c['entry_minute'],'parent_native_intent_minute':a['intent_timestamp_minute'],'first_intent_t_x':tx,'first_intent_minute':f['intent_minute'],'lag_minutes':lag,'upside_feature_asof':a['max_source_available_at'],'H_sources':training[n]['upside'],'downside_feature_asof':tx,'downside_cutoff':training[n]['downside_cutoff'],'raw_prefix_sha256':bind['raw_prefix_sha256'],'state_prefix_sha256':bind['state_prefix_sha256'],'trace_member':bind['trace_member'],'trace_member_sha256':bind['trace_member_sha256'],'actual_arrival':'UNKNOWN','strict_t_x_certified':False,'strict_failure_reason':'Actual score arrival/availability not certified; native and intent feature clocks preserved'})
    sessions={r['session'] for r in composed};symbols={r['symbol'] for r in composed};assert len(sessions)==38 and len(symbols)==583
    raw=(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in composed)).encode();cp=OUT/'private/COMPOSE_ONLY_INPUTS.jsonl.gz';cp.parent.mkdir(parents=True,exist_ok=True);cp.write_bytes(gzip.compress(raw,mtime=0))
    dump(OUT/'private/ASOF_ROW_AND_SOURCE_AUDIT.json',audit);dump(OUT/'private/MODEL_AND_PREDICTION_PINS.json',modelpins)
    label=SRC/'RD01/rd01/private/EVALUATION_ONLY_R_NEW.jsonl.gz';same=SRC/'S1/EVALUATION_R_NEW_REUSED.jsonl.gz';assert label.read_bytes()==same.read_bytes()
    inp={'status':'PASS','Entry_N':1039,'unique_Entry_N':1039,'Development_sessions':38,'symbols':583,'blocks':8,'duplicate_N':0,'one_to_one_score_join':True,'R_U_outcome_values_read_for_COMPOSE':False,'label_bytes_identical_RD01_RD02':True,'label_pin':pin(label.read_bytes()),'label_ID_and_mask_audit_stage':'EVALUATE after assignment seal','compose_pin':pin(cp.read_bytes()),'old_R0_counts':dict(collections.Counter(r['R0_rank'] for r in composed)),'q_coverage_each_method':1039,'H_score_and_base_exact_match_N':1039,'score_reinference_N':0,'block_summary':blocksummary,'shared_source_restoration':'24 parts / 49 members exact pin PASS'}
    dump(OUT/'public/INPUT_COVERAGE_AND_JOIN_AUDIT.json',inp)
    dump(OUT/'public/SOURCE_BINDING_AND_ASOF_AUDIT.json',{'status':'PASS_HISTORICAL_RESEARCH_SOURCE_VIEW','source_authority_correction_reused':True,'serialization_equivalence_receipt':'SERIALIZATION_EQUIVALENCE_RECEIPT.json','feature_clock_audit_N':1039,'native_minus_first_intent_minutes_histogram':dict(lags),'parent_native_intent_field_differences':dict(mismatches),'H_model_member_pin_check_N':24,'downside_sealed_prediction_pin_check_N':24,'actual_arrival':'UNKNOWN for all rows, inherited source contracts','asof_mode':'HISTORICAL_MIXED_ASOF_RESEARCH_ONLY','strict_t_x_certified_subset_N':0,'strict_subset_audited_N':1039,'strict_failure_reason':'No actual arrival and cross-head score availability certificate; same clock alone is insufficient','BUY_INTENT_DEPLOYABLE':False,'CANDIDATE_FOR_CAPITAL_BRIDGE':False,'future_fields_in_compose':0,'physical_UID_or_mount_blindness':False,'separation':'Separate processes; explicit field whitelist, Python open allowlist and deny canary in assignment; same author already exposed to historical Development reports','model_refit_policy_delta':0})
    print(json.dumps({'input':inp,'lags':dict(lags),'native_intent_differences':dict(mismatches)}))
if __name__=='__main__':main()
