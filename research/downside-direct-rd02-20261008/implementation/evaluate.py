"""Frozen RD02 diagnostics. No fitting, policy search, or rank replacement."""
import csv, io, math, collections
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score
from common import *

TARGETS=['q5','q3','q2','qNEG']
TABLES=['R0_RANK_FULL_12BAND','RISK_QUINTILE_FULL_12BAND','WITHIN_R0_RANK_RISK_12BAND','EQUAL_K_SELECTION_12BAND','FIXED_RISK_FLAG_TRADEOFF']

def ratio(n,d):return n/d if d else None
def cell(n,d):return f'{n}/{d} ({100*n/d:.2f}%)' if d else '0/0 (N/A)'
def exact(x):return str(x.numerator)+'/'+str(x.denominator)
def dumpcsv(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for r in data for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
def truth(r,t):return r<=-5 if t=='q5' else r<=-3 if t=='q3' else r<=-2 if t=='q2' else r<0

def load_data(probability_path=None):
    pred=rows(probability_path or PRIVATE/'OOF_PROBABILITIES.jsonl.gz')
    if probability_path is None:assert pin(PRIVATE/'OOF_PROBABILITIES.jsonl.gz')==read(PRIVATE/'ALL_PREDICTIONS_SEAL.json')['predictions']
    labels={r['entry_id']:r for r in rows(PRIVATE/'EVALUATION_R_NEW_REUSED.jsonl.gz')}
    old={r['entry_id']:r for r in rows(INPUT/'rd01/rd01/private/RUNTIME_INPUTS.jsonl.gz')}
    assert labels.keys()==old.keys() and len(labels)==1039
    returns={i:unpack(l) for i,l in labels.items()}
    assert sum(r is not None for r in returns.values())==1016
    by={m:{r['entry_id']:r for r in pred if r['method']==m} for m in METHODS}
    for m,q in by.items():
        assert q.keys()==labels.keys()
        for i,r in q.items():
            assert r['block']==labels[i]['block']
            if r['status']=='ACTIVE':
                p=r['p5'];assert len(p)==5 and abs(sum(p)-1)<=2e-15
                assert 0<=r['q5']<=r['q3']<=r['q2']<=r['qNEG']<=1
                assert r['q5']==p[0] and r['q3']==p[0]+p[1] and r['q2']==p[0]+p[1]+p[2]
    return labels,old,returns,by

def stats(ids,pool,labels,old,returns):
    rr=[returns[i] for i in ids if returns[i] is not None]
    counts=collections.Counter(bucket(returns[i]) for i in ids)
    out={'all_N':len(ids),'known_N':len(rr),'unknown_N':len(ids)-len(rr),'known_coverage':ratio(len(rr),len(ids)),
         'ALL_PLUS':sum(r>0 for r in rr),'ALL_MINUS':sum(r<0 for r in rr),'ZERO':sum(r==0 for r in rr)}
    for b in BANDS:out[b+'_n']=counts[b]
    for x in range(1,6):out[f'R_GE_P{x}_n']=sum(r>=x for r in rr);out[f'R_LE_M{x}_n']=sum(r<=-x for r in rr)
    pos=sum((r for r in rr if r>0),Fraction(0));neg=-sum((r for r in rr if r<0),Fraction(0))
    out.update(positive_mass_pp_sum=float(pos),negative_abs_mass_pp_sum=float(neg),positive_mass_exact=exact(pos),negative_abs_mass_exact=exact(neg))
    for t,thr in [('q5',5),('q3',3),('q2',2),('qNEG',0)]:
        hit=sum(truth(r,t) for r in rr);whole=[returns[i] for i in pool if returns[i] is not None];total=sum(truth(r,t) for r in whole)
        expected=Fraction(0)
        for b in range(1,9):
            pr=[returns[i] for i in pool if old[i]['block']==b and returns[i] is not None]
            k=sum(old[i]['block']==b and returns[i] is not None for i in ids)
            if pr:expected+=Fraction(k*sum(truth(r,t) for r in pr),len(pr))
        out.update({t+'_n':hit,t+'_pool_n':total,t+'_precision':ratio(hit,len(rr)),t+'_capture':ratio(hit,total),t+'_block_conditioned_random_expected_n':float(expected),t+'_enrichment':float(Fraction(hit)/expected) if expected else None})
    for name,test in [(f'WINNER{x}',lambda i,x=x:returns[i] is not None and returns[i]>=x) for x in [2,3,4,5]]+[(f'U{x}',lambda i,x=x:labels[i].get(f'U{x}')==1) for x in [2,3,5,10]]:
        known=lambda i:returns[i] is not None if name.startswith('WINNER') else labels[i].get(name) in [0,1]
        hit=sum(test(i) for i in ids);total=sum(test(i) for i in pool);kn=sum(known(i) for i in ids)
        out.update({name+'_n':hit,name+'_known_N':kn,name+'_pool_n':total,name+'_capture':ratio(hit,total),name+'_density':ratio(hit,kn)})
    out['small_N']=len(rr)<10
    out['mass_unit']='EQUAL_WEIGHT_PP_SUM_NOT_YEN_NOT_CAPITAL'
    return out

def publicstats(s):
    z={k:v for k,v in s.items() if not k.endswith('_exact')}
    reasons=[]
    if s['ALL_PLUS']<=1:z['positive_mass_pp_sum']=None;reasons.append('SINGLE_POSITIVE_R_MASS_PRIVATE')
    if s['ALL_MINUS']<=1:z['negative_abs_mass_pp_sum']=None;reasons.append('SINGLE_NEGATIVE_R_MASS_PRIVATE')
    z['continuous_suppression']=';'.join(reasons)
    return z

def build_collections(labels,old,by):
    allids=sorted(labels);blocks={b:[i for i in allids if old[i]['block']==b] for b in range(1,9)};out=[]
    def add(table,method,t,rank,group,ids,pool=None,**extra):
        z={'collection_id':f'C{len(out):04d}','table':table,'method':method,'target':t,'rank':rank,'group':group,'ids':sorted(ids),'pool_ids':sorted(pool if pool is not None else allids),**extra};out.append(z)
    for rank in ['S','A','B','C']:add(TABLES[0],'SAVED_R0','NONE',rank,rank,[i for i in allids if old[i]['R0_rank']==rank])
    for m in METHODS:
        for t in ['q3','q5']:
            active={i for i in allids if by[m][i]['status']=='ACTIVE'};qs={q:[] for q in range(1,6)}
            within={(r,g):[] for r in ['S','A','B','C'] for g in ['HIGH_RISK_20','REST_80','UNASSESSED']}
            flags={a:[] for a in [.1,.2]};ties={a:{} for a in [.1,.2]}
            for b,ids in blocks.items():
                seq=sorted((i for i in ids if i in active),key=lambda i:(-by[m][i][t],i))
                for j,i in enumerate(seq):qs[1+5*j//len(seq)].append(i)
                for a in [.1,.2]:
                    k=math.ceil(a*len(seq));flags[a]+=seq[:k];ties[a][str(b)]={'available_N':len(seq),'K':k,'boundary_tie_N':sum(by[m][i][t]==by[m][seq[k-1]][t] for i in seq) if k else 0}
                for rank in ['S','A','B','C']:
                    rs=[i for i in seq if old[i]['R0_rank']==rank];k=math.ceil(.2*len(rs));within[(rank,'HIGH_RISK_20')]+=rs[:k];within[(rank,'REST_80')]+=rs[k:];within[(rank,'UNASSESSED')]+=[i for i in ids if old[i]['R0_rank']==rank and i not in active]
            for q in range(1,6):add(TABLES[1],m,t,'ALL',f'Q{q}',qs[q],active)
            add(TABLES[1],m,t,'ALL','UNASSESSED',set(allids)-active)
            for (rank,g),ids in within.items():add(TABLES[2],m,t,rank,g,ids,[i for i in active if old[i]['R0_rank']==rank] if g!='UNASSESSED' else [i for i in allids if old[i]['R0_rank']==rank])
            for a,ids in flags.items():
                for g,ii in [('FLAG',ids),('NOT_FLAGGED',active-set(ids)),('UNASSESSED',set(allids)-active)]:add(TABLES[4],m,t,'ALL',f'TOP_{int(100*a)}_{g}',ii,active if g!='UNASSESSED' else allids,flag_fraction=a,boundary_ties=ties[a])
    common={i for i in allids if all(by[m][i]['status']=='ACTIVE' for m in METHODS)}
    for m in METHODS:
        for budget,ranks in [('S',['S']),('SA',['S','A']),('SAB',['S','A','B'])]:
            selected={k:[] for k in ['R0_NATIVE','q3_LOW','q5_LOW']};ks={}
            for b,ids in blocks.items():
                pool=[i for i in ids if i in common];orig=sum(old[i]['R0_rank'] in ranks for i in ids);k=sum(old[i]['R0_rank'] in ranks for i in pool)
                ks[str(b)]={'original_K':orig,'common_K':k,'missing_q_K_shrink':orig-k}
                selected['R0_NATIVE']+=sorted(pool,key=lambda i:old[i]['R0_candidate_order'])[:k]
                for t in ['q3','q5']:selected[t+'_LOW']+=sorted(pool,key=lambda i:(by[m][i][t],i))[:k]
            for order,ids in selected.items():add(TABLES[3],m,order,budget,order,ids,common,K_by_block=ks)
    return out

def met(ids,t,score,returns,labels):
    ids=[i for i in ids if returns[i] is not None and score(i) is not None];q=np.asarray([score(i) for i in ids]);y=np.asarray([int(truth(returns[i],t)) for i in ids]);n=len(ids);pos=int(y.sum());sessions={labels[i]['session'] for i in ids if truth(returns[i],t)}
    clip=np.clip(q,1e-15,1-1e-15)
    return {'known_N':n,'positive_n':pos,'positive_cell':cell(pos,n),'positive_sessions_N':len(sessions),'LOW_SUPPORT':pos<10 or len(sessions)<3,'Brier':float(np.mean((q-y)**2)) if n else None,'binary_log_loss':float(np.mean(-(y*np.log(clip)+(1-y)*np.log(1-clip)))) if n else None,'AUROC':float(roc_auc_score(y,q)) if 0<pos<n else None,'AP':float(average_precision_score(y,q)) if pos and n else None}

def evaluate(output,probability_path=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);labels,old,returns,by=load_data(probability_path);ids=sorted(labels);collections_=build_collections(labels,old,by);e0=set(read(INPUT/'rd01/rd01/private/E0_SAVED_UNIQUE_IDS.json'))
    scopes=[('ALL','ALL',set(ids))]+[('BLOCK',str(b),{i for i in ids if old[i]['block']==b}) for b in range(1,9)]+[('SESSION',d,{i for i in ids if old[i]['session']==d}) for d in sorted({r['session'] for r in old.values()})]+[('RANK',r,{i for i in ids if old[i]['R0_rank']==r}) for r in ['S','A','B','C']]+[('EXECUTION_ELIGIBLE','TRUE',{i for i in ids if old[i]['execution_eligible']}),('R0_PASS','SAB',{i for i in ids if old[i]['R0_rank'] in ['S','A','B']}),('E0_FUNDED','SAVED',e0)]
    canonical_rows=[];tabledata={t:[] for t in TABLES};diagnostics=[];unredacted=[]
    for c in collections_:
        meta={k:c[k] for k in ['collection_id','table','method','target','rank','group']}
        for scope,value,mask in scopes:
            selected=set(c['ids'])&mask;pool=set(c['pool_ids'])&mask;s=stats(sorted(selected),sorted(pool),labels,old,returns);m={**meta,'scope':scope,'scope_value':value}
            unredacted.append({**m,**s});pub=publicstats(s);diagnostics.append({**m,**pub})
            if scope not in ['ALL','BLOCK']:continue
            row={**m,'all_N':s['all_N'],'known_N':s['known_N'],'known_coverage':s['known_coverage'],'small_N':s['small_N']}
            for band in BANDS:
                den=s['all_N'] if band=='R_UNKNOWN' else s['known_N'];row[band]=cell(s[band+'_n'],den)
                if scope=='ALL':canonical_rows.append({**m,'band':band,'n':s[band+'_n'],'N':den,'percent':100*s[band+'_n']/den if den else None,'cell':cell(s[band+'_n'],den),'R_known_N':s['known_N'],'all_N':s['all_N']})
            for k in ['ALL_PLUS','ALL_MINUS']+[f'R_GE_P{x}_n' for x in range(1,6)]+[f'R_LE_M{x}_n' for x in range(1,6)]:row[k]=cell(s[k],s['known_N'])
            for k in ['positive_mass_pp_sum','negative_abs_mass_pp_sum','continuous_suppression']:row[k]=pub[k]
            tabledata[c['table']].append(row)
    for t,data in tabledata.items():dumpcsv(output/(t+'.csv'),data)
    dumpcsv(output/'CANONICAL_12BAND_CELLS.csv',canonical_rows)
    # A single canonical collection table supplies all counters, capture, return
    # mass, block-conditioned random expectations and day/block/rank breakdowns.
    dumpcsv(output/'UPSIDE_AND_WINNER_PRESERVATION.csv',diagnostics)
    gzsave(PRIVATE/'COLLECTION_DEFINITIONS.jsonl.gz',collections_) if probability_path is None else gzsave(output/'COLLECTION_DEFINITIONS.jsonl.gz',collections_)
    gzsave(PRIVATE/'UNREDACTED_COLLECTION_DIAGNOSTICS.jsonl.gz',unredacted) if probability_path is None else gzsave(output/'UNREDACTED_COLLECTION_DIAGNOSTICS.jsonl.gz',unredacted)
    common=[i for i in ids if all(by[m][i]['status']=='ACTIVE' for m in METHODS)]
    methods=METHODS+['B0'];metrics=[];cal=[];stability=[];loo=[];symbol_loo=[]
    def score(m,i,t):
        if m=='B0':
            p=by['D-FULL'][i]['B0_p5'];return p[0] if t=='q5' else p[0]+p[1] if t=='q3' else p[0]+p[1]+p[2] if t=='q2' else sum(p[:4])
        return by[m][i][t] if by[m][i]['status']=='ACTIVE' else None
    for m in methods:
        for t in TARGETS:
            for name,mask in [('FULL',ids),('METHOD_COMMON',common)]:metrics.append({'method':m,'target':t,'mask':name,'mask_ID_N':len(mask),**met(mask,t,lambda i:score(m,i,t),returns,labels)})
            for scope,v,mask in scopes:
                if scope=='ALL':continue
                stability.append({'method':m,'target':t,'scope':scope,'scope_value':v,'mask_ID_N':len(mask),**met(sorted(mask),t,lambda i:score(m,i,t),returns,labels)})
            for d in sorted({r['session'] for r in old.values()}):
                mask=[i for i in ids if old[i]['session']!=d];loo.append({'method':m,'target':t,'excluded_session':d,**met(mask,t,lambda i:score(m,i,t),returns,labels)})
            for sym in sorted({r['symbol'] for r in old.values()}):
                mask=[i for i in ids if old[i]['symbol']!=sym];symbol_loo.append({'method':m,'target':t,'excluded_symbol_token':sha(sym.encode())[:12],**met(mask,t,lambda i:score(m,i,t),returns,labels)})
            edges=[0,.01,.02,.05,.10,.20,.40,1] if t in ['q3','q5'] else [0,.05,.10,.20,.40,.60,1]
            for j,(lo,hi) in enumerate(zip(edges,edges[1:])):
                ii=[i for i in ids if returns[i] is not None and score(m,i,t) is not None and lo<=score(m,i,t) and (score(m,i,t)<hi if j<len(edges)-2 else score(m,i,t)<=hi)]
                n=len(ii);hit=sum(truth(returns[i],t) for i in ii)
                cal.append({'method':m,'target':t,'bin':f'[{lo},{hi}'+(']' if j==len(edges)-2 else ')'),'known_N':n,'predicted_mean':sum(score(m,i,t) for i in ii)/n if n>1 else None,'observed_positive_n':hit,'observed':cell(hit,n),'observed_rate':ratio(hit,n),'sessions_N':len({old[i]['session'] for i in ii}),'LOW_SUPPORT':n<10,'continuous_suppression':'SINGLETON_MEAN' if n==1 else ''})
    for m in methods:
        jj=[i for i in common if returns[i] is not None];p=[by[m][i]['p5'] if m!='B0' else by['D-FULL'][i]['B0_p5'] for i in jj]
        metrics.append({'method':m,'target':'5CLASS','mask':'METHOD_COMMON','mask_ID_N':len(common),'known_N':len(jj),'multiclass_log_loss':float(np.mean([-math.log(max(a[target(returns[i])],1e-15)) for i,a in zip(jj,p)]))})
    dumpcsv(output/'PROBABILITY_METRICS.csv',metrics);dumpcsv(output/'CALIBRATION_DIAGNOSTICS.csv',cal);dumpcsv(output/'BLOCK_SESSION_STABILITY.csv',stability);dumpcsv(output/'LEAVE_ONE_SESSION_DIAGNOSTIC.csv',loo);dumpcsv(output/'LEAVE_ONE_SYMBOL_DIAGNOSTIC.csv',symbol_loo)
    refs=rows(INPUT/'rd01/rd01/private/SEALED_PREDICTIONS.jsonl.gz');ref={m:{r['entry_id']:r for r in refs if r['method']==m} for m in ['R1','R2']};paired=[];oldflag=[]
    for refm in ['R1','R2','HL0','D1','D2']:
        for t in (['q5','q3','qNEG'] if refm in ['R1','R2'] else TARGETS):
            fn=(lambda i:ref[refm][i].get(t)) if refm in ['R1','R2'] else (lambda i:old[i].get(refm))
            mask=[i for i in common if fn(i) is not None];known=[i for i in mask if returns[i] is not None]
            for m in methods+[refm]:
                z=met(known,t,fn if m==refm else lambda i:score(m,i,t),returns,labels)
                if m in ['HL0','D1','D2']:z['Brier']=z['binary_log_loss']=None
                paired.append({'reference':refm,'method':m,'target':t,'paired_ID_N':len(mask),'mask_hash':sha(canonical(sorted(mask))),'asof':'LATER_ASOF_REFERENCE; BUY_INTENT and native fill information sets/train support differ',**z})
            if t in ['q5','q3']:
                for a in [.1,.2]:
                    for m in METHODS+[refm]:
                        ff=[]
                        for b in range(1,9):
                            bb=[i for i in mask if old[i]['block']==b];k=math.ceil(a*len(bb));ff+=sorted(bb,key=lambda i:(-(fn(i) if m==refm else score(m,i,t)),i))[:k]
                        oldflag.append({'reference':refm,'method':m,'target':t,'top_fraction':a,'paired_ID_N':len(mask),**publicstats(stats(ff,mask,labels,old,returns))})
    dumpcsv(output/'OLD_MODEL_PAIRED_REFERENCE.csv',paired);dumpcsv(output/'OLD_MODEL_PAIRED_FLAG_DIAGNOSTICS.csv',oldflag)
    # Saved RD01/R0 count parity is exact; the label bytes are reused unchanged.
    rank_counts={r:sum(old[i]['R0_rank']==r for i in ids) for r in ['S','A','B','C']};assert rank_counts=={'S':43,'A':154,'B':297,'C':545}
    get=lambda m,t:next(z for z in metrics if z['method']==m and z['target']==t and z['mask']=='METHOD_COMMON')
    comparisons={t:{m:{k:get(m,t)[k]-get('B0',t)[k] if get(m,t)[k] is not None and get('B0',t)[k] is not None else None for k in ['Brier','binary_log_loss','AUROC','AP']} for m in METHODS} for t in TARGETS}
    direction=[]
    for b in range(1,9):
        aa=next(z for z in stability if z['scope']=='BLOCK' and z['scope_value']==str(b) and z['method']=='D-FULL' and z['target']=='q3');bb=next(z for z in stability if z['scope']=='BLOCK' and z['scope_value']==str(b) and z['method']=='B0' and z['target']=='q3')
        direction.append({'block':b,'q3_Brier_better':aa['Brier']<bb['Brier'],'q3_log_loss_better':aa['binary_log_loss']<bb['binary_log_loss']})
    selectivity=[]
    for t in ['q3','q5']:
        for a in [10,20]:
            d=next(z for z in diagnostics if z['scope']=='ALL' and z['table']==TABLES[4] and z['method']=='D-FULL' and z['target']==t and z['group']==f'TOP_{a}_FLAG')
            selectivity.append({'target':t,'top_percent':a,'tail_enrichment':d[t+'_enrichment'],'tail_recall':d[t+'_capture'],'U5_damage':d['U5_capture'],'U10_damage':d['U10_capture'],'R_GE_P2_damage':d['WINNER2_capture'],'R_GE_P5_damage':d['WINNER5_capture'],'passes':d[t+'_enrichment'] is not None and d[t+'_enrichment']>1 and all(d[t+'_capture'] is not None and d[k] is not None and d[t+'_capture']>d[k] for k in ['U5_capture','U10_capture','WINNER2_capture'])})
    screen=all(comparisons['q3']['D-FULL'][k]<0 for k in ['Brier','binary_log_loss']) and all(comparisons['q5']['D-FULL'][k]<=0 for k in ['Brier','binary_log_loss']) and sum(z['q3_Brier_better'] and z['q3_log_loss_better'] for z in direction)>4
    summary={'unique_ID_N':1039,'known_R_N':1016,'unknown_R_N':23,'sessions':38,'rank_counts':rank_counts,'tail_known_counts':{t:get('D-FULL',t)['positive_n'] for t in TARGETS},'effective_prediction_N':{m:sum(by[m][i]['status']=='ACTIVE' for i in ids) for m in METHODS},'unassessed_N':{m:sum(by[m][i]['status']!='ACTIVE' for i in ids) for m in METHODS},'fallback_N':0,'q3_block_proper_score_direction':direction,'D_FULL_prediction_screen':screen,'D_FULL_selectivity':selectivity,'D_FULL_selectivity_screen':all(z['passes'] for z in selectivity),'differences_vs_B0':comparisons,'calibrated_probability_certified':False,'asof_reference':'RD01/R0/HL0/D1/D2 native fill LATER_ASOF_REFERENCE; stricter RD02 BUY_INTENT and warmup train support differ','development':'ADAPTIVE_ITERATIVE_DEVELOPMENT; no Fresh/OOS claim','integrity_status':'AUDIT_PENDING','CapitalReplay':0,'capitalImprovement':'NOT_EVALUATED','model_primary':'D-FULL','newChampion':None,'mainRank':'SAVED_R0','selectedNewRank':None}
    save(output/'EVALUATION_SUMMARY.json',summary)
    save(output/'EVALUATION_MASKS_AND_PRIVACY.json',{'all_unique_ID_N':1039,'known_N':1016,'unknown_N':23,'common_prediction_ID_N':len(common),'effective_model_coverage':'ACTIVE only; B0/fallback not included','selection_labels_used':False,'selection_rule_authority':'frozen original sections9/10/11','unknown_selection':'decide K and ID before R-known exclusion','random_expectation':'analytic block-conditioned expectation on R-known subset','same_budget':'post-hoc fixed block counts; not runtime gate','public_continuous_statistics':'singleton mean and return masses suppressed; exact counts retained; full values private','U_mask':'U known including R unknown; observed return mask separately R known','model_family_N':3,'new_calibration_fit_N':0,'symbol_loo':'all observed symbols; no selective removal; symbol labels hashed in public','physical_blindness':False})
    from publication_layout import project
    project(output,PRIVATE/'FULL_AGGREGATE_PAYLOADS' if probability_path is None else output.parent/'private/FULL_AGGREGATE_PAYLOADS')
    return summary

if __name__=='__main__':
    import sys
    z=evaluate(PUB if len(sys.argv)==1 else sys.argv[1],None if len(sys.argv)<3 else Path(sys.argv[2]));print(json.dumps({k:z[k] for k in ['unique_ID_N','effective_prediction_N','D_FULL_prediction_screen','D_FULL_selectivity_screen']}))
