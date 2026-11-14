"""Bounded one-time 1600-entry teacher-blind QA; reuse all C10 matrices."""
import ast,copy,hashlib,os,pathlib,sys
import numpy as np
from common import ROOT,PUB,PRIV,canonical,clock,dump,read,pin,sha,gzrows,seal_rows
from causal_prefix import prefix_view
from ordered_prefix import build_ordered,segment
PARENT=ROOT.parent/'recovery/saved_parent/nc09_c10'

class FuturePayload:
    def __init__(self,m):self.minute=m
    def __getitem__(self,j):
        if j==0:return self.minute
        raise AssertionError('FUTURE_PAYLOAD_READ')

def run():
    assert not (PUB/'C11_FEATURE_SEAL.json').exists(),'NO_DOUBLE_FEATURE_BUILD'
    pre=read(PUB/'C11_PRECOMMIT.json');rb=read(PUB/'C11_PRECOMMIT_READBACK.json');assert rb['status']=='PASS' and rb['before_implementation'] and rb['precommit_sha256']==sha(PUB/'C11_PRECOMMIT.json')
    assert pre['registry']==pin(PUB/'C11_FIELD_REGISTRY.json') and pre['spec']==pin(PUB/'C11_ORDERED_PREFIX_SPEC.json')
    registry=read(PUB/'C11_FIELD_REGISTRY.json');fields=[f['name'] for f in registry['new_fields']]
    assert len(fields)==len(set(fields))==107 and registry['new_encoded_column_N']==214
    inherited=read(PARENT/'public/C10_FIELD_REGISTRY.json');schema=read(PARENT/'private/C08_SCHEMA.json')
    inherited_names={f['name'] for f in inherited['fields']}|set(schema['spec'])
    assert not set(fields)&inherited_names and all(f['alias'] is None for f in registry['new_fields'])
    semantic={'new_fields':107,'new_same_meaning_C06_C10_aliases':0,'C06_clock_bins_rebuilt':0,'C10_features_rebuilt':0,'C10_alias_N_retained':inherited['alias_N'],'decision_before_QA':0}
    for name in ['ordered_prefix.py','causal_prefix.py']:
        tree=ast.parse((ROOT/name).read_text())
        assert not any(isinstance(n,ast.Name) and n.id in ['open','eval','exec','__import__'] for n in ast.walk(tree))
        assert not any(isinstance(n,ast.Attribute) and n.attr in ['fit','partial_fit'] for n in ast.walk(tree))
    source=read(PUB/'SOURCE_PIN.json');assert pin(ROOT/'inputs/TODAY_PREFIX_CACHE.jsonl.gz')==source['prefix_cache_pin']
    parentqa=read(PARENT/'public/C10_CAUSAL_QA.json');assert parentqa['status']=='PASS' and parentqa['all1600_RAW_suffix_cases']==1600 and parentqa['mismatch_N']==0
    allowed={str((ROOT/p).resolve()) for p in ['inputs/TODAY_PREFIX_CACHE.jsonl.gz','inputs/DERIVED_CACHE_SCOPE_PRECOMMIT.json','public/C11_FIELD_REGISTRY.json','public/C11_CAUSAL_QA.json','public/C11_PRECOMMIT.json','ordered_prefix.py','build_features.py','causal_prefix.py']}
    for b in ['S1','S2']:
        allowed.update(str((PARENT/'private/C08'/b/(role+'_ROW_IDS.json')).resolve()) for role in ['FIT','CAL','DEV_COMPARE'])
        allowed.update(str((PARENT/'private/C10_INPUTS'/b/(role+'_MATRIX.npy')).resolve()) for role in ['FIT','CAL','DEV_COMPARE'])
        allowed.add(str((PARENT/'private/C10_INPUTS'/b/'COLUMN_REGISTRY.json').resolve()))
    for p in ['C11_ORDERED_FEATURES_1600.jsonl.gz','C11_CAUSAL_QA_ROWS_1600.jsonl.gz']:allowed.add(str((PRIV/p).resolve()))
    for b in ['S1','S2']:
        for p in ['FIT_MATRIX.npy','CAL_MATRIX.npy','DEV_COMPARE_MATRIX.npy','COLUMN_REGISTRY.json']:allowed.add(str((PRIV/'INPUTS'/b/p).resolve()))
    taskroot=str(ROOT.parent.resolve())+'/'
    def guard(name,args):
        if name!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
        p=str(pathlib.Path(args[0]).resolve());mode=args[1] if len(args)>1 else None;flags=args[2] if len(args)>2 else 0
        writing=isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT))
        if p.startswith(taskroot) and not writing and p not in allowed:raise PermissionError('FEATURE_CAPABILITY_REFUSED:'+p)
    sys.addaudithook(guard)
    denied=[]
    for name in ['CANONICAL_RETURN_ROWS_322.json','RNEG_TARGETED_OUTCOMES_322.json','SIGNS_CAL_DEV.json','EVAL_ROWS.jsonl.gz','C08/S1/FIT_Y_SIGN_ONLY.npy']:
        try:(PARENT/'private'/name).read_bytes();raise AssertionError('OUTCOME_OR_TEACHER_ACCESS_ALLOWED')
        except PermissionError:denied.append(name)
    cases=gzrows(ROOT/'inputs/TODAY_PREFIX_CACHE.jsonl.gz');scopes={r['entry_id']:r for r in read(ROOT/'inputs/DERIVED_CACHE_SCOPE_PRECOMMIT.json')['scope']};assert len(cases)==len(scopes)==1600
    checks=0;out=[];audit=[];native1130=0
    def verify(ok,tag):
        nonlocal checks
        checks+=1
        if not ok:raise AssertionError(tag)
    for c in cases:
        ident=c['identity'];i=ident['entry_id'];bars=c['bars'];cut=ident['cutoff_minute'];scope=scopes[i]
        verify(scope['symbol']==ident['symbol'] and scope['today']==ident['session'] and scope['today_cutoff']==cut,'FROZEN_SCOPE')
        verify(all(b[0]+1<=cut for b in bars),'ENTRY_CUTOFF')
        view=prefix_view(ident,bars);verify(view==bars,'REPAIRED_NATIVE_PREFIX_ORDER')
        case={'identity':ident,'prefix':view};v=build_ordered(case);verify(set(v)==set(fields),'REGISTRY_NAMES')
        legs=segment(case);verify([m for g in legs for m in g['bar_minutes']]==[b[0] for b in bars],'EXACT_PARTITION_NO_FUTURE_HL')
        verify(all(g['start']<g['end'] and g['end']<=cut for g in legs),'BOUNDARY_CAUSAL')
        verify(all(g['chain']<h['chain'] or g['direction']!=h['direction'] for g,h in zip(legs,legs[1:])),'MAXIMAL_PHASES')
        verify(all(g['start']<h['start'] for g,h in zip(legs,legs[1:])),'CHRONOLOGY')
        payload=[FuturePayload(cut),FuturePayload(cut+1),FuturePayload(930),FuturePayload(cut)]
        variants={'delete':bars,'modify':bars+[[cut,1.,1e15,.001,1e10,1e20,1e30]],'reorder':list(reversed(bars+payload)),'duplicate_future':bars+payload}
        for name,raw in variants.items():verify(canonical(build_ordered({'identity':ident,'prefix':prefix_view(ident,raw)}))==canonical(v),'FUTURE_SUFFIX_'+name)
        for n in ['teacher','R','Winner_bucket','EXIT','MFE','MAE','CANONICAL_CAPITAL_R','future_daily_high','future_daily_low']:
            try:build_ordered({**case,n:0});raise AssertionError('UNAUTHORIZED_CASE_ACCEPTED')
            except ValueError:checks+=1
        try:build_ordered({'identity':ident,'prefix':bars+[[cut,1.,1.,1.,1.,0.,0.]]});raise AssertionError('DIRECT_FUTURE_ACCEPTED')
        except ValueError:checks+=1
        if any(b[0]==690 for b in bars):native1130+=1;verify(any(690 in g['bar_minutes'] for g in legs),'NATIVE1130_NOT_ERASED')
        out.append({'entry_id':i,'identity':ident,'numeric':v,'feature_sha256':hashlib.sha256(canonical(v)).hexdigest(),'input_prefix_sha256':c['prefix_sha256']})
        audit.append({'entry_id':i,'future_suffix_variants':list(variants),'partition_N':sum(len(g['bar_minutes']) for g in legs),'phase_count':len(legs),'phase_boundary_PASS':True,'teacher_R_Winner_refused':True,'native_1130_retained':any(b[0]==690 for b in bars),'feature_sha256':out[-1]['feature_sha256']})
    fixture=[]
    def identity(cut):return {'entry_id':'2000-01-10|fixture','session':'2000-01-10','symbol':'fixture','decision_time':f'2000-01-10T{cut//60:02d}:{cut%60:02d}:00+09:00','cutoff_minute':cut}
    def mk(closes,minutes=None):
        minutes=minutes or list(range(540,540+len(closes)));o=100.;bars=[]
        for m,c in zip(minutes,closes):bars.append([m,o,max(o,c),min(o,c),float(c),0.,0.]);o=float(c)
        return {'identity':identity(minutes[-1]+1 if minutes else 540),'prefix':bars}
    for name,closes,directions in [('rise_pullback_rise',[101,102,101,102,103],[1,-1,1]),('rise_flat_rise',[101,101,102],[1,0,1]),('rise_pullback_fail',[102,101,101.5],[1,-1,1]),('drop_rebound',[99,98,99],[-1,1]),('flat',[100,100],[0])]:
        c=mk(closes);g=segment(c);verify([r['direction'] for r in g]==directions,name);v=build_ordered(c)
        if name=='rise_pullback_fail':verify(v['C11.phase5.end_vs_two_back_high']<0,'FAILED_HIGH_RECLAIM')
        if name=='flat':verify(v['C11.phase5.net_log_return']==0 and v['C11.phase5.log1p_volume']==0 and v['C11.phase5.log1p_value']==0,'ZERO_ACTIVITY_FLAT')
        fixture.append({'name':name,'PASS':True})
    c=mk([101,102,103],[689,690,750]);g=segment(c);verify(len(g)==2 and len(g[0]['bar_minutes'])==2 and g[0]['active']==1 and g[1]['chain']!=g[0]['chain'],'NATIVE1130_LUNCH_CHAIN_BREAK');fixture.append({'name':'native1130_lunch','PASS':True})
    c=mk([101,102],[540,542]);verify(len(segment(c))==2,'MISSING_MINUTE_BREAK');fixture.append({'name':'missing_boundary','PASS':True})
    c=mk([101],[690]);v=build_ordered(c);verify(v['C11.phase5.active_minutes']==0 and v['C11.phase5.slope_per_active_minute'] is None and v['C11.phase5.log1p_volume_per_active_minute'] is None,'NATIVE1130_ZERO_ACTIVE');fixture.append({'name':'native1130_zero_active','PASS':True})
    empty=build_ordered({'identity':identity(540),'prefix':[]});verify(empty['C11.phase_count']==0 and all(empty[f'C11.phase{k}.present']==0 for k in range(6)),'EARLY_EMPTY');fixture.append({'name':'early_empty','PASS':True})
    features=seal_rows(PRIV/'C11_ORDERED_FEATURES_1600.jsonl.gz',out);qas=seal_rows(PRIV/'C11_CAUSAL_QA_ROWS_1600.jsonl.gz',audit);by={r['entry_id']:r for r in out};blocks={}
    for block in ['S1','S2']:
        d=PRIV/'INPUTS'/block;d.mkdir(parents=True,exist_ok=True);matrices={}
        for role in ['FIT','CAL','DEV_COMPARE']:
            ids=read(PARENT/'private/C08'/block/(role+'_ROW_IDS.json'));base=np.load(PARENT/'private/C10_INPUTS'/block/(role+'_MATRIX.npy'),allow_pickle=False)
            extra=np.array([[z for name in fields for z in (by[i]['numeric'][name] if by[i]['numeric'][name] is not None else np.nan,float(by[i]['numeric'][name] is None))] for i in ids],dtype=np.float64)
            matrix=np.concatenate([base,extra],axis=1);verify(np.array_equal(matrix[:,:base.shape[1]],base,equal_nan=True),'C10_BASE_BYTE_VALUES_UNCHANGED');np.save(d/(role+'_MATRIX.npy'),matrix,allow_pickle=False);matrices[role+'_MATRIX.npy']=pin(d/(role+'_MATRIX.npy'))
        base_reg=read(PARENT/'private/C10_INPUTS'/block/'COLUMN_REGISTRY.json');reg={'parent':base_reg,'base_column_N':base.shape[1],'new_field_N':107,'new_encoded_column_N':214,'new_fields':fields,'new_columns':[n+s for n in fields for s in ['.value','.missing']],'matrix_N_columns':base.shape[1]+214,'alias_additional_columns':0,'new_preprocessing_fit':0};dump(d/'COLUMN_REGISTRY.json',reg);blocks[block]={'matrices':matrices,'registry':pin(d/'COLUMN_REGISTRY.json'),'column_N':reg['matrix_N_columns']}
    qa={'status':'PASS','clock':clock(),'Entry_N':1600,'mismatch_N':0,'checks':checks,'all1600_future_suffix_mutation_cases':1600,'mutation_modes':['delete','modify','reorder','duplicate_future'],'future_payload_read':0,'native1130_Entry_N':native1130,'capability_refused':denied,'semantic_alias_QA':semantic,'fixtures':fixture,'native_RAW_prefix_equivalence_inherited':{'C10_QA_all1600_PASS':True,'new_RAW_scan':0,'source':'same SHA256-verified repaired C10 prefix cache'},'builder':pin(ROOT/'ordered_prefix.py'),'selector':pin(ROOT/'causal_prefix.py'),'assembly':pin(ROOT/'build_features.py'),'field_registry':pin(PUB/'C11_FIELD_REGISTRY.json'),'row_receipt':qas,'new_fit':0,'new_preprocessing_fit':0,'model_score':0,'REPORT501_prediction':0,'teacher_R_Winner_read':0}
    dump(PUB/'C11_CAUSAL_QA.json',qa);dump(PUB/'C11_FEATURE_SEAL.json',{'clock':clock(),'features':features,'blocks':blocks,'field_registry':pin(PUB/'C11_FIELD_REGISTRY.json'),'QA':pin(PUB/'C11_CAUSAL_QA.json'),'precommit':pin(PUB/'C11_PRECOMMIT.json'),'new_field_N':107,'new_preprocessing_fit':0,'C10_rebuild':0})
    print({'status':'C11_FEATURE_QA_PASS','Entry_N':1600,'checks':checks,'mismatch_N':0,'native1130_Entry_N':native1130,'blocks':{k:v['column_N'] for k,v in blocks.items()}},flush=True)

if __name__=='__main__':run()
