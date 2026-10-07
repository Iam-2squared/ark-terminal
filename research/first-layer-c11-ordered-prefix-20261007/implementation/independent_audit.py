"""Separate reconstruction: no imports of aggregation, policy, or feature builder."""
import ast,collections,csv,datetime,decimal,gzip,hashlib,json,math,pathlib,pickle,struct
from fractions import Fraction
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=pathlib.Path(__file__).resolve().parent;PUB=ROOT/'public';PRIV=ROOT/'private'
PARENT=ROOT.parent/'recovery/saved_parent/nc09_c10'
checks=0;issues=[]
def verify(ok,tag):
    global checks
    checks+=1
    if not ok:issues.append(tag)
def compact(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in gzip.decompress(p.read_bytes()).splitlines()]
def pin(p):
    b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def stat(rr):
    n=len(rr);k=sum(r['decision']=='KEEP' for r in rr);return {'N':n,'KEEP':k,'DROP':n-k,'KEEP_rate':k/n if n else None,'DROP_rate':(n-k)/n if n else None}
def tau(t):return -math.inf if t.get('sentinel')=='NEGATIVE_INFINITY' else math.inf if t.get('sentinel')=='POSITIVE_INFINITY' else float.fromhex(t['hex'])
POINTS=['ALL_KEEP','CAL95','CAL_MINUS_KEEP_80','CAL_MINUS_KEEP_60','CAL_MINUS_KEEP_40','CAL_MINUS_KEEP_20','CAL_MINUS_KEEP_10']
BANDS=['PLUS_0_1','PLUS_1_2','PLUS_2_3','PLUS_3_4','PLUS_4_5','PLUS_5_PLUS']
CLASSES=['MINUS']+BANDS+['ZERO','UNKNOWN_SIGN','PLUS_RETURN_UNAVAILABLE'];MODELS=['C08','C10','C11'];SCOPES=['S1','S2','S1+S2']
splits=read(PRIV/'SPLITS_S1_S2.json');labels={r['entry_id']:r for r in read(PRIV/'SIGNS_CAL_DEV.json')};native={r['entry_id']:r for r in read(PRIV/'CANONICAL_RETURN_ROWS_322.json')};original={r['entry_id']:r for r in read(PRIV/'RNEG_TARGETED_OUTCOMES_322.json')}
for n in ['SPLITS_S1_S2.json','SIGNS_CAL_DEV.json','CANONICAL_RETURN_ROWS_322.json','RNEG_TARGETED_OUTCOMES_322.json']:
    verify(pin(PRIV/n)==pin(PARENT/'private'/n),'unchanged inherited source '+n)
allids=set().union(*(set(b['DEV_COMPARE_Entry_IDs']) for b in splits));verify(set(native)==set(original)==allids and len(allids)==322,'exact322')
verify(not set(splits[0]['DEV_COMPARE_Entry_IDs'])&set(splits[1]['DEV_COMPARE_Entry_IDs']),'disjoint DEV')
for b in splits:
    for role in ['FIT','CAL','DEV_COMPARE']:
        verify(hashlib.sha256(compact(sorted(b[role+'_Entry_IDs']))).hexdigest()==b[role+'_ID_sha256'],'split '+b['block']+role)
        verify(sorted({i.split('|')[0] for i in b[role+'_Entry_IDs']})==b[role+'_sessions'],'sessions '+b['block']+role)
    verify(max(b['FIT_sessions'])<min(b['CAL_sessions']) and max(b['CAL_sessions'])<min(b['DEV_COMPARE_sessions']),'time order')
value={};bands={};signs={}
for i,r in native.items():
    o=original[i];s='UNKNOWN_SIGN' if labels[i]['sign_status'] in ['UNKNOWN','UNKNOWN_SIGN'] else labels[i]['sign_status'];signs[i]=s
    verify(hashlib.sha256(compact(o)).hexdigest()==labels[i]['source_hash']==r['source_hash'],'source R hash '+i)
    verify(r['sign_status']==labels[i]['sign_status'] and r['R_unit']=='percent','sign/unit '+i)
    if o['known']:
        v=Fraction(decimal.Decimal(o['r_original']))*100;value[i]=v
        verify(v==Fraction(decimal.Decimal(r['R_native_fraction_decimal']))*100==Fraction(int(r['R_pct_numerator']),int(r['R_pct_denominator'])),'exact R fraction '+i)
        bands[i]='MINUS' if v<0 else 'ZERO' if v==0 else BANDS[min(int(v),5)]
        verify((s=='PLUS' and v>0) or (s=='MINUS' and v<0) or (s=='ZERO' and v==0),'sign R consistency '+i)
    else:value[i]=None;bands[i]='UNKNOWN_SIGN';verify(s=='UNKNOWN_SIGN' and not r['return_available'],'unknown separate '+i)
verify(collections.Counter(signs.values())=={'PLUS':144,'MINUS':172,'UNKNOWN_SIGN':6},'population signs')
verify(collections.Counter(bands.values())=={'MINUS':172,'PLUS_0_1':54,'PLUS_1_2':34,'PLUS_2_3':26,'PLUS_3_4':6,'PLUS_4_5':4,'PLUS_5_PLUS':20,'UNKNOWN_SIGN':6},'population bands')

# Independently partition native prefix and reconstruct every new field.
def connected(a,b):return b[0]-a[0]==1 and (540<=a[0]<=690 and 540<=b[0]<=690 or 750<=a[0]<=925 and 750<=b[0]<=925)
fields=[f['name'] for f in read(PUB/'C11_FIELD_REGISTRY.json')['new_fields']]
saved={r['entry_id']:r for r in rows(PRIV/'C11_ORDERED_FEATURES_1600.jsonl.gz')};cases=rows(ROOT/'inputs/TODAY_PREFIX_CACHE.jsonl.gz');verify(len(saved)==len(cases)==1600,'1600 features')
native1130=0
metrics=['present','direction','net_log_return','observed_duration_minutes','active_minutes','gross_log_movement','high_low_log_excursion','slope_per_active_minute','log1p_volume','log1p_value','log1p_volume_per_active_minute','log1p_value_per_active_minute','end_vs_two_back_high','end_vs_two_back_low']
for c in cases:
    bs=c['bars'];i=c['identity']['entry_id'];cut=c['identity']['cutoff_minute'];verify(all(b[0]+1<=cut for b in bs),'prefix before buy '+i)
    if any(b[0]==690 for b in bs):native1130+=1
    groups=[];edges=[];chain=-1
    for k,b in enumerate(bs):
        link=k>0 and connected(bs[k-1],b)
        if not link:chain+=1
        a=bs[k-1][4] if link else b[1];sg=(b[4]>a)-(b[4]<a);e=(k,a,sg,chain)
        if groups and link and edges[-1][2]==sg:groups[-1].append(e)
        else:groups.append([e])
        edges.append(e)
    phases=[]
    for g in groups:
        bb=[bs[e[0]] for e in g];seed=g[0][1];start=bb[0][0];end=bb[-1][0]+1
        duration=max(0,min(end,690)-max(start,540))+max(0,min(end,925)-max(start,750));net=math.log(bb[-1][4]/seed)
        gross=0.
        for e in g:gross+=abs(math.log(bs[e[0]][4]/e[1]))
        hi=max([seed]+[b[2] for b in bb]);lo=min([seed]+[b[3] for b in bb]);vol=sum(b[5] for b in bb);va=sum(b[6] for b in bb)
        older=phases[-2] if len(phases)>=2 and phases[-2]['chain']==g[0][3] else None
        vals=dict(present=1.,direction=float(g[0][2]),net_log_return=net,observed_duration_minutes=float(end-start),active_minutes=float(duration),gross_log_movement=gross,high_low_log_excursion=math.log(hi/lo),slope_per_active_minute=net/duration if duration else None,log1p_volume=math.log1p(vol),log1p_value=math.log1p(va),log1p_volume_per_active_minute=math.log1p(vol/duration) if duration else None,log1p_value_per_active_minute=math.log1p(va/duration) if duration else None,end_vs_two_back_high=math.log(bb[-1][4]/older['high']) if older else None,end_vs_two_back_low=math.log(bb[-1][4]/older['low']) if older else None)
        phases.append({'chain':g[0][3],'high':hi,'low':lo,'values':vals})
    padded=[None]*max(6-len(phases),0)+phases[-6:];want={'C11.phase_count':float(len(phases)),'C11.omitted_phase_count':float(max(len(phases)-6,0)),'C11.chain_count':float(chain+1)}
    for k,g in enumerate(padded):
        vv=g['values'] if g else {n:0. if n=='present' else None for n in metrics};want.update({f'C11.phase{k}.'+n:x for n,x in vv.items()})
    for k in range(1,6):
        a,b=padded[k-1],padded[k];vv={n:None for n in ['same_chain','slope_change','volume_activity_change','value_activity_change']}
        if a and b:
            same=a['chain']==b['chain'];vv['same_chain']=float(same)
            if same:
                for n,src in [('slope_change','slope_per_active_minute'),('volume_activity_change','log1p_volume_per_active_minute'),('value_activity_change','log1p_value_per_active_minute')]:
                    av,bv=a['values'][src],b['values'][src];vv[n]=bv-av if av is not None and bv is not None else None
        want.update({f'C11.transition{k-1}_{k}.'+n:x for n,x in vv.items()})
    verify(set(want)==set(fields)==set(saved[i]['numeric']),'field names '+i)
    for n in fields:verify(want[n]==saved[i]['numeric'][n],'independent feature '+i+n)
    verify(hashlib.sha256(compact(saved[i]['numeric'])).hexdigest()==saved[i]['feature_sha256'],'new feature hash '+i)
verify(native1130==read(PUB/'C11_CAUSAL_QA.json')['native1130_Entry_N']==422,'native1130 count')

pre=read(PUB/'C11_PRECOMMIT.json');verify(pre['options']==read(PARENT/'public/C10_PRECOMMIT.json')['options'],'unchanged HGB7')
verify(read(PUB/'C11_PRECOMMIT_READBACK.json')['precommit_sha256']==pin(PUB/'C11_PRECOMMIT.json')['sha256'],'precommit actual GET')
lock=read(PUB/'C11_IMPLEMENTATION_LOCK.json')
for n,h in lock['implementation_pins'].items():verify(pin(ROOT/n)==h,'unchanged lock '+n)
for n in ['evaluate.py','ordered_prefix.py','operating_policy.py']:
    tree=ast.parse((ROOT/n).read_text());verify(not any(isinstance(x,ast.Attribute) and x.attr in ['fit','partial_fit'] for x in ast.walk(tree)),'non-fit module '+n)
tree=ast.parse((ROOT/'ordered_prefix.py').read_text());verify(not any(isinstance(x,ast.Name) and x.id in ['open','eval','exec','__import__'] for x in ast.walk(tree)),'pure ordered builder')
verify(read(PUB/'C11_SEALED_READBACK.json')['status']=='PASS' and read(PUB/'C11_SEALED_READBACK.json')['before_Winner_join'],'remote seal before join')
completion=read(PRIV/'C11/COMPLETE.json');verify(completion['new_fit']==2 and completion['new_preprocessing_fit']==0 and completion['new_aggressive_thresholds']==10 and completion['new_fixed_CAL95_references']==2,'exact execution')
decisions={};replayN=0;units=0
for b in splits:
    block=b['block'];d=PRIV/'C11'/block;base=PARENT/'private/C08'/block;ps=read(d/'PREDICTION_SEAL.json');meta=read(d/'MODEL.json');th=read(d/'THRESHOLDS.json')
    for n,key in [('MODEL.json','model'),('HGB_MODEL.pkl','pickle'),('THRESHOLDS.json','thresholds'),('CAL_SELECTION_INPUT.json','selection_input')]:verify(pin(d/n)==ps[key],'sealed '+block+n)
    verify(pin(base/'PREPROCESSOR.json')==meta['base_preprocessor'] and pin(base/'COLUMN_SELECTION.json')==meta['base_column_selection'],'preprocess retained '+block)
    fit=read(base/'FIT_SIGN_ONLY_INPUT.json');fitids=read(base/'FIT_ROW_IDS.json');y=np.load(base/'FIT_Y_SIGN_ONLY.npy',allow_pickle=False)
    for r,i,v in zip(fit,fitids,y):verify(r['entry_id']==i and i in b['FIT_Entry_IDs'] and r['y_plus']==int(v) and r['sign_status'] in ['PLUS','MINUS'] and r['label_maturity']<b['FIT_maturity_before'],'FIT sign/maturity '+i)
    with (d/'HGB_MODEL.pkl').open('rb') as f:model=pickle.load(f)
    verify(model.get_params()==pre['options'] and model.classes_.tolist()==[0,1] and model.n_iter_==200,'fitted configuration '+block)
    roledata={}
    for role in ['FIT','CAL','DEV_COMPARE']:
        ids=read(base/(role+'_ROW_IDS.json'));x=np.load(PRIV/'INPUTS'/block/(role+'_MATRIX.npy'),allow_pickle=False);parent=np.load(PARENT/'private/C10_INPUTS'/block/(role+'_MATRIX.npy'),allow_pickle=False)
        verify(pin(PRIV/'INPUTS'/block/(role+'_MATRIX.npy'))==meta['input_matrices'][role+'_MATRIX.npy'],'matrix pin '+role)
        verify(x.shape==(len(ids),parent.shape[1]+214) and np.array_equal(x[:,:parent.shape[1]],parent,equal_nan=True),'C10 matrix unchanged '+role)
        ex=np.array([[v for n in fields for v in (saved[i]['numeric'][n] if saved[i]['numeric'][n] is not None else np.nan,float(saved[i]['numeric'][n] is None))] for i in ids])
        verify(np.array_equal(x[:,parent.shape[1]:],ex,equal_nan=True),'once-only phase encoding '+role)
        if role=='FIT':continue
        rr=rows(d/(role+'_SCORES_DECISIONS.jsonl.gz'));roledata[role]=rr
        verify([r['entry_id'] for r in rr]==ids and set(ids)==set(b[role+'_Entry_IDs']),'CAL DEV IDs '+role)
        verify(pin(d/(role+'_SCORES_DECISIONS.jsonl.gz'))=={k:v for k,v in ps['scores'][role].items() if k!='row_N'},'score seal '+role)
        with threadpool_limits(limits=1):scores=model.decision_function(x)
        units+=1;replayN+=len(rr)
        for e,r in zip(scores,rr):verify(float(e).hex()==r['score_ieee754_hex']==float(r['eta']).hex(),'exact saved model score '+r['entry_id'])
    selection=read(d/'CAL_SELECTION_INPUT.json')['rows'];want=[]
    for r in roledata['CAL']:
        l=labels[r['entry_id']];s=l['sign_status'] if l['sign_status'] in ['PLUS','MINUS'] and l['label_maturity']<b['CAL_maturity_before'] else 'UNKNOWN';want.append({'entry_id':r['entry_id'],'eta':r['eta'],'sign_status':s})
    verify(selection==want and all(set(r)=={'entry_id','eta','sign_status'} for r in selection),'CAL capability '+block)
    plus=sorted(r['eta'] for r in want if r['sign_status']=='PLUS');minus=sorted(r['eta'] for r in want if r['sign_status']=='MINUS')
    for p in POINTS:
        t=-math.inf if p=='ALL_KEEP' else plus[5*len(plus)//100] if p=='CAL95' else math.nextafter(minus[len(minus)-int(p.rsplit('_',1)[1])*len(minus)//100-1],math.inf)
        verify(tau(th[p]['threshold'])==t,'independent threshold '+block+p)
        if math.isfinite(t):verify(struct.pack('>d',t).hex()==th[p]['threshold']['ieee754_binary64_be'],'threshold IEEE754')
        for s in ['PLUS','MINUS','UNKNOWN']:
            rrs=[{'decision':'KEEP' if r['eta'] is None or r['eta']>=t else 'DROP'} for r in want if r['sign_status']==s];verify({k:stat(rrs)[k] for k in ['N','KEEP','DROP']}==th[p]['CAL_counts'][s],'CAL counts '+s)
        for role,rr in roledata.items():
            for r in rr:
                decision='KEEP' if r['eta'] is None or r['eta']>=t else 'DROP';verify(r['decisions'][p]==decision,'fixed KEEP DROP '+role+p+r['entry_id'])
                if role=='DEV_COMPARE':decisions['C11',p,r['entry_id']]={'model':'C11','point':p,'block':block,'entry_id':r['entry_id'],'decision':decision,'eta':r['eta'],'model_sha256':r['model_sha256']}
    verify(ps['clock']['UTC']<read(PUB/'EVALUATION_JOIN_RECEIPT.json')['clock']['UTC'],'seal timestamp before join '+block)
for r in rows(PARENT/'private/EVAL_ROWS.jsonl.gz'):
    if r['model'] in ['C08','C10']:decisions[r['model'],r['point'],r['entry_id']]=r
ev=rows(PRIV/'EVAL_ROWS.jsonl.gz');verify(len(ev)==len(decisions)==3*7*322,'all unique evaluated decisions')
for r in ev:
    i=r['entry_id'];a=decisions[r['model'],r['point'],i]
    for n in ['decision','eta','model_sha256','block']:verify(r[n]==a[n],'unmodified sealed decision '+n)
    verify(r['sign_status']==signs[i] and r['bucket']==bands[i] and r['R_native_fraction_decimal']==native[i]['R_native_fraction_decimal'],'exact post-seal join '+i)
members={};expected={};result=read(PUB/'RESULTS.json')
for m in MODELS:
    for p in POINTS:
        for scope in SCOPES:
            rr=[r for r in ev if r['model']==m and r['point']==p and (scope=='S1+S2' or r['block']==scope)];members[m,p,scope]=rr
            sg={n:stat([r for r in rr if signs[r['entry_id']]==s]) for n,s in [('ALL_PLUS','PLUS'),('ALL_MINUS','MINUS'),('ZERO','ZERO'),('UNKNOWN_SIGN','UNKNOWN_SIGN')]}
            bd={n:stat([r for r in rr if bands[r['entry_id']]==n]) for n in BANDS+['PLUS_RETURN_UNAVAILABLE']}
            cu={str(k):stat([r for r in rr if signs[r['entry_id']]=='PLUS' and value[r['entry_id']] is not None and value[r['entry_id']]>=k]) for k in [1,2,3,5]}
            total=stat(rr);co={n:{'DROP':sum(r['decision']=='DROP' and bands[r['entry_id']]==n for r in rr),'share_of_total_DROP':sum(r['decision']=='DROP' and bands[r['entry_id']]==n for r in rr)/total['DROP'] if total['DROP'] else None,'band_N':sum(bands[r['entry_id']]==n for r in rr),'band_DROP_rate':stat([r for r in rr if bands[r['entry_id']]==n])['DROP_rate']} for n in CLASSES}
            x={'signs':sg,'bands':bd,'cumulative':cu,'total':total,'drop_composition':co};expected[m,p,scope]=x
            verify(x==result[m][p][scope],'all RESULT cells '+str((m,p,scope)))
            verify(sum(v['KEEP'] for v in bd.values())==sg['ALL_PLUS']['KEEP'] and sum(v['DROP'] for v in co.values())==total['DROP'],'exhaustive disjoint bucket sums')
def match(row,want,tag):
    for k,v in want.items():
        a=row[k];verify(a=='' if v is None else a==str(v) if isinstance(v,(str,bool)) else float(a)==v,tag+k)
def csvrows(name):
    with (PUB/name).open() as f:return list(csv.DictReader(f))
for row in csvrows('SIGN_KEEP_DROP.csv'):match(row,expected[row['model'],row['point'],row['scope']]['signs'][row['sign']],'sign CSV ')
for row in csvrows('WINNER_BAND_KEEP_DROP.csv'):match(row,expected[row['model'],row['point'],row['scope']]['bands'][row['band']],'band CSV ')
for row in csvrows('CUMULATIVE_WINNER_KEEP_DROP.csv'):match(row,expected[row['model'],row['point'],row['scope']]['cumulative'][row['R_ge_percent']],'cumulative CSV ')
for row in csvrows('DROP_COMPOSITION.csv'):match(row,expected[row['model'],row['point'],row['scope']]['drop_composition'][row['band']],'composition CSV ')
for row in csvrows('OPERATING_POINT_COMPARISON.csv'):
    x=expected[row['model'],row['point'],row['scope']];match(row,{n+'_'+k:v for n in ['ALL_PLUS','ALL_MINUS'] for k,v in x['signs'][n].items()},'curve CSV ');match(row,{n+'_KEEP':x['bands'][n]['KEEP'] for n in BANDS}|{n+'_N':x['bands'][n]['N'] for n in BANDS},'curve bands ')
pairids={tuple(r[k] for k in ['reference_model','reference_point','new_model','new_point','scope','band']):r for r in read(PRIV/'PAIRED_CHANGE_IDS.json')}
for row in csvrows('PAIRED_CHANGE_COMPARISON.csv'):
    key=tuple(row[k] for k in ['reference_model','reference_point','new_model','new_point','scope','band']);am,ap,bm,bp,scope,band=key
    rr=[r for r in members[bm,bp,scope] if bands[r['entry_id']]==band];ids={n:[] for n in ['KEEP_TO_DROP','DROP_TO_KEEP','STAY_KEEP','STAY_DROP']}
    for r in rr:
        old=decisions[am,ap,r['entry_id']]['decision'];new=r['decision'];ids['STAY_'+new if old==new else old+'_TO_'+new].append(r['entry_id'])
    match(row,{'N':len(rr),**{k:len(v) for k,v in ids.items()},'NET_KEEP_CHANGE':len(ids['DROP_TO_KEEP'])-len(ids['KEEP_TO_DROP'])},'paired counts ')
    for n,v in ids.items():verify(sorted(v)==sorted(pairids[key][n]),'paired exact IDs '+str(key)+n)
pareto=read(PUB/'WINNER_BAND_PARETO.json');candidates=pareto['candidates'];oldc={c['candidate_id']:c for c in read(PARENT/'public/WINNER_BAND_PARETO.json')['candidates']};verify(len(candidates)==28,'retain old21 plus new7')
for c in candidates:
    if c['model']!='C11':
        for k,v in oldc[c['candidate_id']].items():
            if k!='strictly_dominated_by':verify(c[k]==v,'old Pareto frozen '+c['candidate_id']+k)
    else:
        x=expected['C11',c['point'],'S1+S2'];verify(c['MINUS_KEEP']==x['signs']['ALL_MINUS']['KEEP'] and c['ALL_PLUS_KEEP']==x['signs']['ALL_PLUS']['KEEP'] and c['band_KEEP']=={n:x['bands'][n]['KEEP'] for n in BANDS},'new Pareto cells '+c['candidate_id'])
edges=[];ce=[]
for a in candidates:
    for b in candidates:
        if a==b:continue
        if a['MINUS_KEEP']<=b['MINUS_KEEP'] and all(a['band_KEEP'][n]>=b['band_KEEP'][n] for n in BANDS) and (a['MINUS_KEEP']<b['MINUS_KEEP'] or any(a['band_KEEP'][n]>b['band_KEEP'][n] for n in BANDS)):edges.append((a['candidate_id'],b['candidate_id']))
        av=[a['ALL_PLUS_KEEP']]+[a['result']['cumulative'][str(k)]['KEEP'] for k in [1,2,3,5]];bv=[b['ALL_PLUS_KEEP']]+[b['result']['cumulative'][str(k)]['KEEP'] for k in [1,2,3,5]]
        if a['MINUS_KEEP']<=b['MINUS_KEEP'] and all(x>=y for x,y in zip(av,bv)) and (a['MINUS_KEEP']<b['MINUS_KEEP'] or any(x>y for x,y in zip(av,bv))):ce.append((a['candidate_id'],b['candidate_id']))
verify(sorted(edges)==sorted((e['dominator'],e['dominated']) for e in pareto['strict_dominance']),'strict exclusive Pareto reconstruction')
cu=read(PUB/'CUMULATIVE_PARETO.json');verify(sorted(ce)==sorted((e['dominator'],e['dominated']) for e in cu['edges']),'precommitted cumulative Pareto reconstruction')
verify(sorted(pareto['nondominated_ids'])==sorted(c['candidate_id'] for c in candidates if not any(z==c['candidate_id'] for _,z in edges)),'exclusive frontier')
verify(sorted(cu['nondominated_ids'])==sorted(c['candidate_id'] for c in candidates if not any(z==c['candidate_id'] for _,z in ce)),'cumulative frontier')
verify(('C10_CAL_MINUS_KEEP_60','C08_CAL_MINUS_KEEP_60') in edges,'preserve C10 ranking edge')
ledger=read(PUB/'BUDGET_LEDGER.json');verify(ledger['cycles_started']==ledger['cycles_completed']==11 and ledger['model_fit_attempts']==ledger['model_fit_success']==36 and ledger['preprocessing_fits']==30 and ledger['threshold_decisions']==150 and ledger['technical_retries']==0 and ledger['fit_phase_attempts']['report']==6,'final accounting')
oldbudget=read(PARENT/'public/BUDGET_LEDGER.json');verify(ledger['events'][:len(oldbudget['events'])]==oldbudget['events'],'preserve prior budget events')
for name in ['C11_CAUSAL_QA.json','C11_FEATURE_SEAL.json','C11_PREDICTION_SEAL.json']:
    verify(pin(PUB/name)==read(PUB/'PREDICTION_EVIDENCE_MANIFEST.json')['public_artifacts'][name],'stage sealed public '+name)
out={'status':'PASS' if not issues else 'FAIL','checks':checks,'mismatch_N':len(issues),'issues':issues,'separate_implementation_without_main_aggregation_import':True,'independent_feature_Entry_N':1600,'independent_new_numeric_fields':107,'saved_C11_model_score_replay_rows':replayN,'saved_C11_model_score_replay_units':units,'C09_C10_fit_preprocess_score_reexecution':0,'strict_Pareto_edges':edges,'cumulative_Pareto_edge_N':len(ce),'model_fit':0,'threshold_search':0,'REPORT501_new_score':0,'Fresh':0,'OOS':0}
(PUB/'INDEPENDENT_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['issues']},ensure_ascii=False))
if issues:print(json.dumps(issues[:30],ensure_ascii=False));raise SystemExit(1)
