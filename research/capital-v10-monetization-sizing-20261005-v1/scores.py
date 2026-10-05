"""Frozen model inference and label-free completed-past empirical percentiles."""
from control import *
from runtime import consensus
import importlib.util
SPEC=importlib.util.spec_from_file_location('v10_frozen_inference',ROOT/'research/capital-v9-quality-aware-max3-integration-20261005-v1/scores.py')
INFER=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(INFER)
def tables():
    train=rows(PRIVATE/'SIZING_TRAIN_SCORE_TABLE.jsonl.gz');tenure=read(B2/'B2_TENURE_LOOKUP_TABLE.json');out={}
    for b in read(SPLIT)['blocks']:
        rr=[r for r in train if r['block']==b['block']]
        out[str(b['block'])]={'training_sessions':b['train'],'test_sessions':b['test'],'tenure':tenure[str(b['block'])],'sessions':{d:[r for r in rr if r['session']==d and r['band']!='P_BELOW'] for d in b['train']},'sorted_train':{f:sorted(r[f] for r in rr) for f in ('pP','q2','q3')}}
    return out
def build():
    receipt=read(OUT/'receipts/M2_COMPLETE_DESIGN_ACTUAL_GET_BEFORE_DIAGNOSTICS_ACTUAL_GET.json');assert receipt['actual_GET_verified'] and str((OUT/'SIZING_DESIGN_PRECOMMIT.json').relative_to(ROOT)) in receipt['paths']
    raw=rows(QUALITY/'inputs/RUNTIME_CAUSAL.jsonl.gz');rm={r['entry_id']:r for r in raw};saved=rows(V9PRIVATE/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz');current={r['entry_id']:dict(r) for r in saved};mapped=rows(MAIN/'private/TRAIN_MAPPED_SCORES.jsonl.gz');training=[];audit=[]
    oldtrain={(r['block'],r['entry_id']):r for r in rows(V9PRIVATE/'QUALITY_TRAIN_SCORE_TABLE.jsonl.gz')}
    delta=0.;ppdelta=0.
    for block in read(SPLIT)['blocks']:
        b=block['block'];pm=read(MAIN/f'inputs/movement/models/MOVE_P_BLOCK_{b:02}.json');models=[read(QUALITY/f'private/models/MOVE_U{h}_BLOCK_{b:02}.json') for h in (2,3)];ids=pm['train_entry_ids'];byid={r['entry_id']:r for r in mapped if r['block']==b};assert set(ids)==set(byid)
        assert all(m['train_entry_ids']==ids and m['preprocessing']==pm['preprocessing'] for m in models)
        pp=INFER.predict([rm[k] for k in ids],pm);qq=[INFER.predict([rm[k] for k in ids],m) for m in models]
        for k,p,a,z in zip(ids,pp,*qq):
            r=byid[k];assert r['session'] in block['train'] and r['session']<min(block['test']);ppdelta=max(ppdelta,abs(p-r['pP']))
            for f,v in [('q2',a),('q3',z)]:delta=max(delta,abs(v-oldtrain[b,k][f]))
            training.append({f:r[f] for f in ('entry_id','session','entry_minute','pP','r','band','block')}|{'q2':a,'q3':z})
        test=[r for r in raw if r['session'] in block['test']];xs=[rm[r['entry_id']] for r in test]
        for h,m in zip((2,3),models):
            for r,q in zip(test,INFER.predict(xs,m)):
                k=r['entry_id'];delta=max(delta,abs(q-current[k][f'q{h}']));current[k][f'q{h}']=q
        for r,p in zip(test,INFER.predict(xs,pm)):ppdelta=max(ppdelta,abs(p-current[r['entry_id']]['pP']))
        audit.append({'block':b,'train_N':len(ids),'strictly_completed_past':True,'model_sha256':{'pP':sha(MAIN/f'inputs/movement/models/MOVE_P_BLOCK_{b:02}.json'),**{f'q{h}':sha(QUALITY/f'private/models/MOVE_U{h}_BLOCK_{b:02}.json') for h in (2,3)}}})
    assert delta<=1e-12 and ppdelta<=1e-12
    training.sort(key=lambda r:(r['block'],r['session'],r['entry_minute'],r['entry_id']));gzsave(PRIVATE/'SIZING_TRAIN_SCORE_TABLE.jsonl.gz',training)
    ts=tables()
    for r in current.values():r.update(consensus(r,ts[str(r['block'])]['sorted_train']))
    cc=sorted(current.values(),key=lambda r:(r['session'],r['entry_minute'],-r['pP'],r['entry_timestamp'],r['symbol'],r['entry_id']));gzsave(PRIVATE/'CURRENT_SIZING_RUNTIME.jsonl.gz',cc)
    save(OUT/'SIZING_PERCENTILE_RUNTIME_FREEZE.json',{'exact_jst':now(),'status':'PASS','current_N':len(cc),'training_N':len(training),'current_and_train_q_delta_vs_v9_max':delta,'pP_reconstruction_delta_max':ppdelta,'pP_ordering':'saved frozen exact authority; inference audit only, no remap','percentile_formula':'(1+count(train<current))/(N+1)','training_resubstitution':True,'training_teacher_fields':[],'test_cross_section':False,'blocks':audit,'runtime_sha256':sha(PRIVATE/'CURRENT_SIZING_RUNTIME.jsonl.gz'),'training_sha256':sha(PRIVATE/'SIZING_TRAIN_SCORE_TABLE.jsonl.gz'),'fits':0,'probability_claim':False,'Safety':SAFETY})
if __name__=='__main__':build()
