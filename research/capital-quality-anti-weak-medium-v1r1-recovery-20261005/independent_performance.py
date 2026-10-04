"""One independent complete performance package; no primary implementation imports."""
import ast
from independent_io import *
import independent_stats as stats

def main():
    claimed('PERFORMANCE_INDEPENDENT_EXECUTION_CLAIM',[OUT/'INDEPENDENT_PERFORMANCE_AUDIT.json',PRIVATE/'INDEPENDENT_PERFORMANCE_FULL.json.gz'])
    assert load(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json')['status']=='PASS'
    data,saved_dec=source_rows();dec=stats.deciles(data);assert dec==saved_dec
    auth=load(OUT/'PRIVATE_PACK_AUTHENTICATION.json');assert auth['mismatch_N']==0
    for x in auth['transport_members']:assert sha(OLD_WORK/x['path'])==x['sha256']
    pred=rows(OLD_WORK/'private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz');pm={(p['head'],p['entry_id']):p for p in pred}
    assert len(pred)==len(pm)==2078
    common={r['entry_id'] for r in data}
    for h in ['MOVE_U2','MOVE_U3']:
        ids={p['entry_id'] for p in pred if p['head']==h};assert len(ids)==1039 and len(ids-common)==11 and not common-ids
    for r in data:
        for h in ['MOVE_U2','MOVE_U3']:
            p=pm[(h,r['entry_id'])];assert p['session']==r['session'] and p['block']==r['block']
            assert math.isfinite(p['probability']) and 0<=p['probability']<=1;r[h]=p['probability']
    expected_row=b''.join(canon(r) for r in data);assert expected_row==gzip.decompress((PRIVATE/'QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz').read_bytes())
    names=['CORE_H2','CORE_H3','pP','legacy_ML','MOVE_U2','MOVE_U3']
    mm={s:stats.quality(data,s) for s in names}
    cc={t:{s:stats.conditional(data,s,t,dec) for s in names} for t in ['U2','U3']}
    bb={};samples={};draw_hashes={}
    for h,c,t in [('MOVE_U2','CORE_H2','U2'),('MOVE_U3','CORE_H3','U3')]:
        print(json.dumps({'independent_bootstrap_started':h,'resamples':1999,'seed':5701005}),flush=True)
        bb[h],draw_hashes[h],samples[h]=stats.bootstrap(data,h,c,t,dec)
        print(json.dumps({'independent_bootstrap_complete':h}),flush=True)
    assert len(set(draw_hashes.values()))==1
    a=stats.gates(mm,cc['U2'],bb['MOVE_U2'],'MOVE_U2','CORE_H2','U2','A')
    b=stats.gates(mm,cc['U3'],bb['MOVE_U3'],'MOVE_U3','CORE_H3','U3','M')
    ordinal={s:stats.ordinal(data,s) for s in ['CORE_H2','CORE_H3','pP','MOVE_U2','MOVE_U3']}
    guards={};p=mm['pP']['top'][2]
    for h in ['MOVE_U2','MOVE_U3']:
        q=mm[h]['top'][2];b5=q['U5_capture']>=p['U5_capture'];b10=q['U10_capture']>=p['U10_capture']
        guards[h]={'budget':.3,'selected_N':q['selected_N'],'U5_capture':q['U5_capture'],'U10_capture':q['U10_capture'],
            'pP_U5_capture':p['U5_capture'],'pP_U10_capture':p['U10_capture'],'U5_preserved':b5,'U10_preserved':b10,
            'status':'BIG_WINNER_PRESERVING' if b5 and b10 else 'PARTIAL' if b5 or b10 else 'NOT_PRESERVING','diagnostic_only':True}
    sessions=sorted({r['session'] for r in data})
    primary={'N':1028,'metrics':mm,'AntiWeak':a,'MediumPlus':b,'bootstrap':bb,
        'session_draw_stream_sha256':next(iter(draw_hashes.values())),
        'session_order_sha256':hashlib.sha256(canon(sessions)).hexdigest(),
        'integrity_status':'PENDING_INDEPENDENT_PERFORMANCE_AUDIT','realized_PnL':'diagnostic only',
        'candidate_budgets_fixed':True,'combined_score_created':0,'newFits':0,'CapitalReplay':0,'MAX3Replay':0}
    expected={'primary':primary,'conditional':cc,'ordinal':ordinal,'guards':guards,'provisional_decision':stats.decision(a,b)}
    full=json.loads(gzip.decompress((PRIVATE/'PERFORMANCE_FULL.json.gz').read_bytes()))
    errors,maxdiff=difference(full,expected);assert not errors,errors[:30]
    ps=json.loads(gzip.decompress((PRIVATE/'BOOTSTRAP_RESAMPLE_VALUES.json.gz').read_bytes()))
    sample_errors,sample_diff=difference(ps,samples);assert not sample_errors,sample_errors[:30]
    drawfile=gzip.decompress((PRIVATE/'BOOTSTRAP_SESSION_DRAWS.jsonl.gz').read_bytes())
    assert hashlib.sha256(drawfile).hexdigest()==primary['session_draw_stream_sha256']
    root=load(OUT/'PERFORMANCE_ARTIFACT_ROOT.json')
    for x in root['private_artifacts']:
        path=WORK/x['path'];body=gzip.decompress(path.read_bytes())
        assert sha(path)==x['sha256'] and hashlib.sha256(body).hexdigest()==x['uncompressed_sha256']
        if x['schema']=='canonical JSON':assert body==canon(json.loads(body))
        else:assert body==b''.join(canon(json.loads(s)) for s in body.splitlines())
    for path,h in root['public_sha256'].items():assert sha(OUT/path)==h
    public_cond=load(OUT/'P_P_CONDITIONAL_INCREMENTAL.json')['results']
    er,d=difference(public_cond,strip_groups(cc));assert not er;maxdiff=max(maxdiff,d)
    er,d=difference(load(OUT/'PRIMARY_QUALITY_EVAL.json'),primary);assert not er;maxdiff=max(maxdiff,d)
    er,d=difference(load(OUT/'ORDINAL_QUALITY.json')['results'],ordinal);assert not er;maxdiff=max(maxdiff,d)
    er,d=difference(load(OUT/'BIG_WINNER_PRESERVATION.json')['guards'],guards);assert not er;maxdiff=max(maxdiff,d)
    # Recreate fixed-budget CSV rows independently, comparing every count/rate.
    import csv
    with (OUT/'FIXED_BUDGET_QUALITY.csv').open(newline='') as f:table=list(csv.DictReader(f))
    assert len(table)==18
    for row in table:
        top=next(x for x in mm[row['score']]['top'] if x['fraction']==float(row['fraction']))
        for k,v in row.items():
            if k!='score':assert abs(float(v)-float(top[k]))<=1e-12
    imports=[]
    for file in ['independent_performance.py','independent_io.py','independent_stats.py']:
        for n in ast.walk(ast.parse((CODE/file).read_text())):
            if isinstance(n,ast.Import):imports += [x.name for x in n.names]
            if isinstance(n,ast.ImportFrom):imports.append(n.module)
    assert not any(x in ['control','sources','baseline_rebuild','metrics','evaluate','performance','train_heads','sklearn'] for x in imports)
    fp=compress(PRIVATE/'INDEPENDENT_PERFORMANCE_FULL.json.gz',expected)
    sb=compress(PRIVATE/'INDEPENDENT_BOOTSTRAP_VALUES.json.gz',samples)
    result={'exact_jst':now(),'status':'PASS','N':1028,'mismatch_N':0,'float_tolerance':1e-12,
        'max_abs_float_difference':max(maxdiff,sample_diff),'primary_trainer_evaluator_metrics_imports':0,
        'source_identity_labels_mask_split_mismatch_N':0,'quality_block_Top_Bottom_conditional_session_ordinal_NDCG_mismatch_N':0,
        'bootstrap_resample_value_mismatch_N':0,'bootstrap_interval_mismatch_N':0,'session_draw_stream_mismatch_N':0,
        'session_draw_stream_sha256':primary['session_draw_stream_sha256'],'gates_status_selected_heads_mismatch_N':0,
        'independent_decision':expected['provisional_decision'],'independent_gate_U2':a,'independent_gate_U3':b,
        'independent_full_artifact':fp,'independent_bootstrap_artifact':sb,'newFits':0,'auditRefits':0,
        'independent_performance_packages':1,'seed':5701005,'resamples_per_head':1999,'cluster_unit':'session'}
    save(OUT/'INDEPENDENT_PERFORMANCE_AUDIT.json',result)
    checkpoint('R10_FULL_INDEPENDENT_PERFORMANCE_AUDIT',result,'R11 final integrity/canaries and exact old decision contract; R12 fixed STOP without integration')
    print(json.dumps({'status':'PASS','mismatch_N':0,'max_float':result['max_abs_float_difference'],
        'decision':expected['provisional_decision'],'newFits':0}),flush=True)

if __name__=='__main__':main()
