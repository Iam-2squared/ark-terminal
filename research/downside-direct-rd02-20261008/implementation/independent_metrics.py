"""Independent accounting/order/metric implementation; no primary evaluator import."""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,csv,math,hashlib,collections,pickle
import numpy as np
from independent_features import band,cls
ROOT=Path(__file__).resolve().parents[2];W=ROOT/'rd02';V=W/'private';P=W/'public';I=ROOT/'inputs'
METHODS=['D-LINEAR','D-PRICE','D-FULL'];TARGETS=['q5','q3','q2','qNEG'];BANDS=['P5_PLUS','P4_5','P3_4','P2_3','P1_2','P0_1','L0_1','L1_2','L2_3','L3_4','L4_5','L5_PLUS','ZERO','R_UNKNOWN']
def enc(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def gz(p):return [json.loads(x) for x in gzip.decompress(Path(p).read_bytes()).splitlines()]
def predtruth(r,t):return r<0 if t=='qNEG' else r<=-{'q5':5,'q3':3,'q2':2}[t]
def quotient(a,b):return a/b if b else None
def ratio_cell(a,b):return f'{a}/{b} ({100*a/b:.2f}%)' if b else '0/0 (N/A)'
def eq(a,b):
    if a is None or b is None:return a is b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return a==b if isinstance(a,int) and isinstance(b,int) else math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12)
    return a==b
def csvrows(n):return list(csv.DictReader((P/n).open()))
def value(s):
    if s=='':return None
    if s in ['True','False']:return s=='True'
    try:return float(s)
    except ValueError:return s

def definitions(ids,old,q):
    out=[];byblock={b:[i for i in ids if old[i]['block']==b] for b in range(1,9)}
    def emit(table,m,t,rank,group,chosen,pool=None,**extra):out.append({'collection_id':f'C{len(out):04d}','table':table,'method':m,'target':t,'rank':rank,'group':group,'ids':sorted(chosen),'pool_ids':sorted(pool if pool is not None else ids),**extra})
    for r in ['S','A','B','C']:emit('R0_RANK_FULL_12BAND','SAVED_R0','NONE',r,r,[i for i in ids if old[i]['R0_rank']==r])
    for m in METHODS:
        for t in ['q3','q5']:
            available={i for i in ids if q[m][i]['status']=='ACTIVE'};groups=collections.defaultdict(list);wr=collections.defaultdict(list);ff=collections.defaultdict(list);ties={a:{} for a in [10,20]}
            for b,blockids in byblock.items():
                ordered=sorted(set(blockids)&available,key=lambda i:(-q[m][i][t],i));n=len(ordered)
                for k,i in enumerate(ordered):groups[1+(5*k)//n].append(i)
                for percent in [10,20]:
                    count=(percent*n+99)//100;ff[percent].extend(ordered[:count]);ties[percent][str(b)]={'available_N':n,'K':count,'boundary_tie_N':len([i for i in ordered if count and q[m][i][t]==q[m][ordered[count-1]][t]])}
                for rank in ['S','A','B','C']:
                    rr=[i for i in ordered if old[i]['R0_rank']==rank];k=(len(rr)+4)//5;wr[rank,'HIGH_RISK_20'].extend(rr[:k]);wr[rank,'REST_80'].extend(rr[k:]);wr[rank,'UNASSESSED'].extend(i for i in blockids if i not in available and old[i]['R0_rank']==rank)
            for k in range(1,6):emit('RISK_QUINTILE_FULL_12BAND',m,t,'ALL',f'Q{k}',groups[k],available)
            emit('RISK_QUINTILE_FULL_12BAND',m,t,'ALL','UNASSESSED',set(ids)-available)
            for rank in ['S','A','B','C']:
                for group in ['HIGH_RISK_20','REST_80','UNASSESSED']:emit('WITHIN_R0_RANK_RISK_12BAND',m,t,rank,group,wr[rank,group],[i for i in (available if group!='UNASSESSED' else ids) if old[i]['R0_rank']==rank])
            for percent in [10,20]:
                for group,chosen in [('FLAG',ff[percent]),('NOT_FLAGGED',available-set(ff[percent])),('UNASSESSED',set(ids)-available)]:emit('FIXED_RISK_FLAG_TRADEOFF',m,t,'ALL',f'TOP_{percent}_{group}',chosen,available if group!='UNASSESSED' else ids,flag_fraction=percent/100,boundary_ties=ties[percent])
    common={i for i in ids if all(q[m][i]['status']=='ACTIVE' for m in METHODS)}
    for m in METHODS:
        for budget,ranks in [('S',['S']),('SA',['S','A']),('SAB',['S','A','B'])]:
            choices=collections.defaultdict(list);ks={}
            for b,bb in byblock.items():
                aa=set(bb)&common;k=sum(old[i]['R0_rank'] in ranks for i in aa);orig=sum(old[i]['R0_rank'] in ranks for i in bb);ks[str(b)]={'original_K':orig,'common_K':k,'missing_q_K_shrink':orig-k}
                choices['R0_NATIVE'].extend(sorted(aa,key=lambda i:old[i]['R0_candidate_order'])[:k])
                for t in ['q3','q5']:choices[t+'_LOW'].extend(sorted(aa,key=lambda i:(q[m][i][t],i))[:k])
            for order in ['R0_NATIVE','q3_LOW','q5_LOW']:emit('EQUAL_K_SELECTION_12BAND',m,order,budget,order,choices[order],common,K_by_block=ks)
    return out

def run():
    labels={r['entry_id']:r for r in gz(V/'EVALUATION_R_NEW_REUSED.jsonl.gz')};old={r['entry_id']:r for r in gz(I/'rd01/rd01/private/RUNTIME_INPUTS.jsonl.gz')};accounts={r['entry_id']:r for r in gz(V/'INDEPENDENT_RECONSTRUCTED_LABEL_ACCOUNTS.jsonl.gz')};r={i:F(accounts[i]['exact_R']) if accounts[i]['exact_R'] is not None else None for i in labels};ids=sorted(labels)
    for i,a in labels.items():
        if a.get('u_numerator') is not None:
            u=F(int(a['u_numerator']),int(a['u_denominator']))
            for t in [2,3,5,10]:assert a[f'U{t}']==int(u>=t),'U_FLAG_EXACT_DIFF'
        ml=old[i]['ML'];assert old[i]['R0_rank']==('S' if ml>=2 else 'A' if ml>=1.5 else 'B' if ml>=1 else 'C')
    sealed=gz(V/'OOF_PROBABILITIES.jsonl.gz');q={m:{a['entry_id']:a for a in sealed if a['method']==m} for m in METHODS};defs=definitions(ids,old,q);primary=gz(V/'COLLECTION_DEFINITIONS.jsonl.gz');assert defs==primary,'GROUP_K_TIE_MASK_EXACT_DIFF'
    unredacted=gz(V/'UNREDACTED_COLLECTION_DIAGNOSTICS.jsonl.gz');definition_byid={a['collection_id']:a for a in defs};e0=set(read(I/'rd01/rd01/private/E0_SAVED_UNIQUE_IDS.json'))
    masks={('ALL','ALL'):set(ids)}
    for b in range(1,9):masks['BLOCK',str(b)]={i for i in ids if old[i]['block']==b}
    for day in {a['session'] for a in old.values()}:masks['SESSION',day]={i for i in ids if old[i]['session']==day}
    for rank in ['S','A','B','C']:masks['RANK',rank]={i for i in ids if old[i]['R0_rank']==rank}
    masks['EXECUTION_ELIGIBLE','TRUE']={i for i in ids if old[i]['execution_eligible']};masks['R0_PASS','SAB']={i for i in ids if old[i]['R0_rank'] in ['S','A','B']};masks['E0_FUNDED','SAVED']=e0
    aggregate_cache={}
    def aggregate(ii):
        key=tuple(sorted(ii))
        if key in aggregate_cache:return aggregate_cache[key]
        known=[r[i] for i in key if r[i] is not None];cn=collections.Counter(band(r[i]) for i in key);n=len(known);out={'all_N':len(key),'known_N':n,'unknown_N':len(key)-n,'known_coverage':quotient(n,len(key)),'ALL_PLUS':sum(v>0 for v in known),'ALL_MINUS':sum(v<0 for v in known),'ZERO':sum(v==0 for v in known),'small_N':n<10}
        for b in BANDS:out[b+'_n']=cn[b]
        for threshold in range(1,6):out[f'R_GE_P{threshold}_n']=sum(v>=threshold for v in known);out[f'R_LE_M{threshold}_n']=sum(v<=-threshold for v in known)
        pos=sum((v for v in known if v>0),F(0));neg=sum((-v for v in known if v<0),F(0));out.update(positive_mass_pp_sum=float(pos),negative_abs_mass_pp_sum=float(neg),positive_mass_exact=f'{pos.numerator}/{pos.denominator}',negative_abs_mass_exact=f'{neg.numerator}/{neg.denominator}')
        for t in TARGETS:out[t+'_n']=sum(predtruth(v,t) for v in known)
        for name in [f'WINNER{x}' for x in [2,3,4,5]]+[f'U{x}' for x in [2,3,5,10]]:
            hit=sum(r[i] is not None and r[i]>=int(name[6:]) for i in key) if name.startswith('WINNER') else sum(labels[i].get(name)==1 for i in key);kn=n if name.startswith('WINNER') else sum(labels[i].get(name) in [0,1] for i in key);out[name+'_n']=hit;out[name+'_known_N']=kn;out[name+'_density']=quotient(hit,kn)
        aggregate_cache[key]=out;return out
    counter_checks=0
    for a in unredacted:
        d=definition_byid[a['collection_id']];mask=masks[a['scope'],a['scope_value']];chosen=set(d['ids'])&mask;pool=set(d['pool_ids'])&mask;ss=aggregate(chosen);pp=aggregate(pool)
        for k,v in ss.items():assert eq(a[k],v),'COUNTER_OR_MASS_DIFF:'+a['collection_id']+':'+k;counter_checks+=1
        for t in TARGETS:
            expected=F(0)
            for b in range(1,9):
                bs=aggregate([i for i in chosen if old[i]['block']==b]);bp=aggregate([i for i in pool if old[i]['block']==b])
                if bp['known_N']:expected+=F(bs['known_N']*bp[t+'_n'],bp['known_N'])
            checks={t+'_pool_n':pp[t+'_n'],t+'_precision':quotient(ss[t+'_n'],ss['known_N']),t+'_capture':quotient(ss[t+'_n'],pp[t+'_n']),t+'_block_conditioned_random_expected_n':float(expected),t+'_enrichment':float(F(ss[t+'_n'])/expected) if expected else None}
            for k,v in checks.items():assert eq(a[k],v),'TAIL_CAPTURE_EXPECTATION_DIFF:'+k;counter_checks+=1
        for name in [f'WINNER{x}' for x in [2,3,4,5]]+[f'U{x}' for x in [2,3,5,10]]:
            assert a[name+'_pool_n']==pp[name+'_n'] and eq(a[name+'_capture'],quotient(ss[name+'_n'],pp[name+'_n']));counter_checks+=2
    # Verify all public table denominators and exact cell strings separately.
    diagnostics={(a['collection_id'],a['scope'],a['scope_value']):a for a in unredacted};cell_checks=0
    for name in ['R0_RANK_FULL_12BAND','RISK_QUINTILE_FULL_12BAND','WITHIN_R0_RANK_RISK_12BAND','EQUAL_K_SELECTION_12BAND','FIXED_RISK_FLAG_TRADEOFF']:
        for a in csvrows(name+'.csv'):
            s=diagnostics[a['collection_id'],a['scope'],a['scope_value']]
            for b in BANDS:
                den=s['all_N'] if b=='R_UNKNOWN' else s['known_N'];assert a[b]==ratio_cell(s[b+'_n'],den);cell_checks+=1
            assert sum(s[b+'_n'] for b in BANDS if b!='R_UNKNOWN')==s['known_N'] and s['known_N']+s['unknown_N']==s['all_N']
    def score(m,i,t):
        if m=='B0':
            p=q['D-FULL'][i]['B0_p5'];return sum(p[:{'q5':1,'q3':2,'q2':3,'qNEG':4}[t]])
        return q[m][i][t] if q[m][i]['status']=='ACTIVE' else None
    def measures(ii,t,fn):
        ii=[i for i in ii if r[i] is not None and fn(i) is not None];arr=[(fn(i),int(predtruth(r[i],t))) for i in ii];n=len(ii);positive=sum(y for x,y in arr);sess=len({old[i]['session'] for i in ii if predtruth(r[i],t)})
        out={'known_N':n,'positive_n':positive,'positive_cell':ratio_cell(positive,n),'positive_sessions_N':sess,'LOW_SUPPORT':positive<10 or sess<3,'Brier':sum((x-y)**2 for x,y in arr)/n if n else None,'binary_log_loss':-sum(y*math.log(max(1e-15,min(1-1e-15,x)))+(1-y)*math.log(1-max(1e-15,min(1-1e-15,x))) for x,y in arr)/n if n else None,'AUROC':None,'AP':None}
        grouped=collections.defaultdict(lambda:[0,0])
        for x,y in arr:grouped[x][y]+=1
        if 0<positive<n:
            neg_before=0;numerator=0.
            for x,(neg,pos) in sorted(grouped.items()):numerator+=pos*(neg_before+.5*neg);neg_before+=neg
            out['AUROC']=numerator/(positive*(n-positive))
        if positive:
            cum_n=cum_p=0;ap=0.
            for x,(neg,pos) in sorted(grouped.items(),reverse=True):cum_n+=neg+pos;cum_p+=pos;ap+=(cum_p/cum_n)*(pos/positive)
            out['AP']=ap
        return out
    def checkmetric(row,mask,fn):
        z=measures(mask,row['target'],fn)
        if row['method'] in ['HL0','D1','D2']:z['Brier']=z['binary_log_loss']=None
        for k,v in z.items():assert eq(value(row[k]),v),'PROBABILITY_METRIC_DIFF:'+str((row['method'],row['target'],k,value(row[k]),v))
    common=[i for i in ids if all(q[m][i]['status']=='ACTIVE' for m in METHODS)];metric_checks=0
    for a in csvrows('PROBABILITY_METRICS.csv'):
        if a['target']=='5CLASS':
            mask=[i for i in common if r[i] is not None];loss=sum(-math.log(max((q[a['method']][i]['p5'] if a['method']!='B0' else q['D-FULL'][i]['B0_p5'])[cls(r[i])],1e-15)) for i in mask)/len(mask);assert eq(value(a['multiclass_log_loss']),loss)
        else:checkmetric(a,ids if a['mask']=='FULL' else common,lambda i:score(a['method'],i,a['target']))
        metric_checks+=1
    for a in csvrows('BLOCK_SESSION_STABILITY.csv'):checkmetric(a,sorted(masks[a['scope'],a['scope_value']]),lambda i:score(a['method'],i,a['target']));metric_checks+=1
    for a in csvrows('LEAVE_ONE_SESSION_DIAGNOSTIC.csv'):checkmetric(a,[i for i in ids if old[i]['session']!=a['excluded_session']],lambda i:score(a['method'],i,a['target']));metric_checks+=1
    for a in csvrows('LEAVE_ONE_SYMBOL_DIAGNOSTIC.csv'):
        mask=[i for i in ids if sha(old[i]['symbol'].encode())[:12]!=a['excluded_symbol_token']];checkmetric(a,mask,lambda i:score(a['method'],i,a['target']));metric_checks+=1
    oldsealed=gz(I/'rd01/rd01/private/SEALED_PREDICTIONS.jsonl.gz');refs={m:{a['entry_id']:a for a in oldsealed if a['method']==m} for m in ['R1','R2']}
    for a in csvrows('OLD_MODEL_PAIRED_REFERENCE.csv'):
        ref=a['reference'];fn=(lambda i:refs[ref][i].get(a['target'])) if ref in refs else (lambda i:old[i].get(ref));mask=[i for i in common if fn(i) is not None];assert sha(enc(sorted(mask)))==a['mask_hash'];checkmetric(a,mask,fn if a['method']==ref else lambda i:score(a['method'],i,a['target']));metric_checks+=1
    calibration_checks=0
    for a in csvrows('CALIBRATION_DIAGNOSTICS.csv'):
        left,right=a['bin'][1:-1].split(',');lo=float(left);hi=float(right);fn=lambda i:score(a['method'],i,a['target']);ii=[i for i in ids if r[i] is not None and fn(i) is not None and lo<=fn(i) and (fn(i)<hi if a['bin'][-1]==')' else fn(i)<=hi)];n=len(ii);hit=sum(predtruth(r[i],a['target']) for i in ii)
        assert int(a['known_N'])==n and int(a['observed_positive_n'])==hit and a['observed']==ratio_cell(hit,n) and eq(value(a['predicted_mean']),sum(fn(i) for i in ii)/n if n>1 else None);calibration_checks+=1
    model_checks=0
    for b in range(1,9):
        bd=V/'blocks'/f'BLOCK_{b:02d}';tm=read(bd/'TRAIN_ID_MANIFEST.json');cut=tm['learning_cutoff'];alllabels={a['entry_id']:a for a in gz(V/'WARMUP_R_NEW.jsonl.gz')+gz(V/'EVALUATION_R_NEW_REUSED.jsonl.gz')};train_ids=tm['same_method_train_IDs'];train_hash=sha(enc(train_ids));assert len(set(train_ids))==tm['train_N']
        for i in train_ids:assert alllabels[i]['session'] in tm['train_sessions'] and alllabels[i]['label_maturity']<cut and alllabels[i]['known']
        assert tm['class_counts']==[sum(cls(F(int(alllabels[i]['r_numerator']),int(alllabels[i]['r_denominator'])))==k for i in train_ids) for k in range(5)]
        p0=[(n+.5)/(tm['train_N']+2.5) for n in tm['class_counts']]
        for m in METHODS:
            d=bd/m;model=pickle.loads((d/'model.pkl').read_bytes());fit=read(d/'fit_result.json');assert model['train_ID_hash']==train_hash==fit['train_ID_hash'];assert sha(enc(model['preprocessing']))==fit['preprocessing_sha256'];train=gz(d/'TRAIN_ONLY_VIEW.jsonl.gz');test=gz(d/'PREDICT_ONLY_VIEW.jsonl.gz');assert [a['entry_id'] for a in train]==train_ids
            for a in train:assert set(a)=={'entry_id','feature_asof','numeric','categorical','target'}
            for a in test:assert set(a)=={'entry_id','feature_asof','numeric','categorical'}
            for name in ['FIT_WORKER_INPUT_ACCESS_AUDIT.json','PREDICT_WORKER_INPUT_ACCESS_AUDIT.json']:assert read(d/name)['manager_outcome_open_denied'] and not read(d/name)['physical_blindness']
            schema=read(P/'FEATURE_FORMULAS_AND_SCHEMA.json');fields=model['numeric_fields'];assert fields==schema['numeric_column_order'][:45] if m=='D-PRICE' else fields==schema['numeric_column_order']
            matrix=np.asarray([[np.nan if a['numeric'][k] is None else a['numeric'][k] for k in fields] for a in train]);med=np.asarray([np.median(col[np.isfinite(col)]) if np.any(np.isfinite(col)) else 0 for col in matrix.T]);pre=model['preprocessing'];assert med.tolist()==pre['median']
            catkeys=schema['categorical_column_order'] if m!='D-PRICE' else [];cats=np.asarray([[float((a['categorical'].get(k) if a['categorical'].get(k) in schema['vocabulary'][k] else 'UNKNOWN')==v) for k in catkeys for v in schema['vocabulary'][k]] for a in train]);design=np.concatenate([np.where(np.isnan(matrix),med,matrix),np.isnan(matrix).astype(float),cats],axis=1)
            mu=design.mean(axis=0) if m=='D-LINEAR' else np.zeros(design.shape[1]);sd=design.std(axis=0) if m=='D-LINEAR' else np.ones(design.shape[1]);sd[sd==0]=1
            assert mu.tolist()==pre['mean'] and sd.tolist()==pre['scale'] and np.all(np.isnan(matrix),axis=0).tolist()==pre['all_missing_train'];assert all(q[m][i]['B0_p5']==p0 for i in tm['evaluation_IDs']);model_checks+=1
    # Privacy projection retains all exact counters and suppresses each singleton sign mass.
    private_stats={(a['collection_id'],a['scope'],a['scope_value']):a for a in unredacted};privacy_checks=0
    for a in csvrows('UPSIDE_AND_WINNER_PRESERVATION.csv'):
        s=private_stats[a['collection_id'],a['scope'],a['scope_value']]
        for k in ['positive_mass_pp_sum','negative_abs_mass_pp_sum']:
            n=s['ALL_PLUS'] if k.startswith('positive') else s['ALL_MINUS'];assert eq(value(a[k]),s[k] if n>1 else None),'SINGLE_SIGN_MASS_PRIVACY_DIFF'
        privacy_checks+=1
    result={'status':'PASS','author_scope':'SAME_AUTHOR_SEPARATE_IMPLEMENTATION_CROSS_CHECK_NOT_THIRD_PARTY_BLIND_AUDIT','primary_evaluator_bucket_imported':False,'collection_definition_order_ID_K_tie_exact_N':len(defs),'collection_scope_rows_N':len(unredacted),'exact_counter_capture_mass_checks_N':counter_checks,'12band_denominator_cell_checks_N':cell_checks,'probability_metric_rows_N':metric_checks,'calibration_bin_rows_N':calibration_checks,'saved_model_train_preprocessing_worker_audit_N':model_checks,'public_privacy_rows_N':privacy_checks,'metric_tolerance_absolute_relative':1e-12,'integer_ID_bucket_order_hash_tolerance':0,'AUROC_implementation':'pair wins via tied-score counts','AP_implementation':'descending tied-score cumulative precision integral','positive_negative_mass':'exact Fraction pp sums; no yen/Capital conversion','refit_N':0,'physical_blindness':False,'development':'ADAPTIVE_ITERATIVE_DEVELOPMENT','implementation_sha256':sha(Path(__file__).read_bytes())};(P/'INDEPENDENT_METRIC_AUDIT.json').write_bytes(enc(result));print(json.dumps(result))

if __name__=='__main__':
    try:run()
    except Exception as e:
        with (V/'AUDIT_FAILURES.jsonl').open('ab') as f:f.write(enc({'audit':'independent_metrics','error':str(e),'status':'FAIL'}))
        raise
