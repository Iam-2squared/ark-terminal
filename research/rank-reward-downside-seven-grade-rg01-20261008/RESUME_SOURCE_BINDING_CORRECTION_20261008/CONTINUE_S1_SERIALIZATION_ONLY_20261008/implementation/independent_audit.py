"""Same-author separate implementation; imports neither primary rank nor evaluator."""
import collections,csv,gzip,hashlib,json,math,pathlib
from decimal import Decimal,localcontext
from fractions import Fraction
M=['R0_4','U7','G7_FULL','B7_FULL','G7_PRICE','B7_PRICE'];G='SABCDEF';T=[2,3,5,10]
BN=['R_GE_P5','R_P4_P5','R_P3_P4','R_P2_P3','R_P1_P2','R_P0_P1','R_M1_0','R_M2_M1','R_M3_M2','R_M4_M3','R_M5_M4','R_LE_M5','ZERO','R_UNKNOWN']
def readrows(p):return [json.loads(s) for s in gzip.decompress(p.read_bytes()).splitlines()]
def f(x):
    if x is None:return 'N/A'
    with localcontext() as c:
        c.prec=60
        v=Decimal(x.numerator)/Decimal(x.denominator) if isinstance(x,Fraction) else Decimal(str(x))
        return format(v.quantize(Decimal('0.000000000001')),'f')
def rate(n,d):return f(Fraction(100*n,d)) if d else 'N/A'
def seven(v):
    if not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:return None
    return 6-sum(v>=z for z in [.75,1.,1.25,1.5,2.,2.5])
def rband(v):
    if v is None:return 'R_UNKNOWN'
    intervals=[('R_GE_P5',lambda x:x>=5),('R_P4_P5',lambda x:4<=x<5),('R_P3_P4',lambda x:3<=x<4),('R_P2_P3',lambda x:2<=x<3),('R_P1_P2',lambda x:1<=x<2),('R_P0_P1',lambda x:0<x<1),('R_M1_0',lambda x:-1<x<0),('R_M2_M1',lambda x:-2<x<=-1),('R_M3_M2',lambda x:-3<x<=-2),('R_M4_M3',lambda x:-4<x<=-3),('R_M5_M4',lambda x:-5<x<=-4),('R_LE_M5',lambda x:x<=-5),('ZERO',lambda x:x==0)]
    matches=[name for name,test in intervals if test(v)];assert len(matches)==1;return matches[0]
def calc(c,q):
    score=c['ML'];u=seven(score);tail=[-score,-c['m5'],-c['m3'],-c['m2'],c['entry_timestamp'],c['symbol'],c['entry_id']]
    d={'R0_4':{'grade':c['rank'],'grade_index':'SABC'.index(c['rank']),'order_key':tail},'U7':{'grade':G[u],'grade_index':u,'order_key':[u]+tail}}
    for suffix in ['FULL','PRICE']:
        p=q['D-'+suffix];b5=p['B0_p5'][0];b3=sum(p['B0_p5'][:2]);v3=p['q3']/b3;v5=p['q5']/b5
        risky=v3>1 or v5>1;down=(risky if u==0 else min(v3,v5)>=1.5);g=min(u+int(down),6)
        d['G7_'+suffix]={'grade':G[g],'grade_index':g,'order_key':[g]+tail,'r3':v3,'r5':v5,'downshift':g-u}
        excess=[max(0.,min(2.,v-1)) for v in [v3,v5]];discount=min(.30,excess[0]*.12+excess[1]*.06);effective=score*(1.-discount);cap=1 if score>=2 else 2;g=min(seven(effective),u+cap,6)
        if u==0 and risky and g==0:g=1
        d['B7_'+suffix]={'grade':G[g],'grade_index':g,'order_key':[g,-effective]+tail,'r3':v3,'r5':v5,'downshift':g-u,'penalty':discount,'effective_ML':effective,'max_downshift':cap}
    return d
def aggregate(ids,L,full):
    records=[L[i] for i in sorted(ids)];vals=[x['r'] for x in records if x['r'] is not None];n=len(records);k=len(vals);u=n-k;p=sum((v for v in vals if v>0),Fraction());neg=sum((-v for v in vals if v<0),Fraction());net=p-neg;s=sorted(vals);med=(s[(k-1)//2]+s[k//2])/2 if k else None
    d={'N':n,'R_known_N':k,'R_unknown_N':u,'R_coverage_pct':rate(k,n),'R_unknown_pct':rate(u,n),'U_known_N':sum(x['u'] is not None for x in records),'session_N':len(set(x['session'] for x in records)),'symbol_N':len(set(x['symbol'] for x in records)),'mean_R':f(net/k) if k else 'N/A','median_R':f(med),'positive_mass_pp':f(p),'negative_abs_mass_pp':f(neg),'net_pp_sum':f(net)}
    counts={'PLUS':sum(v>0 for v in vals),'MINUS':sum(v<0 for v in vals)}
    for t in [2,3,4,5]:counts['R_GE_P'+str(t)]=sum(v>=t for v in vals)
    for t in [2,3,5]:counts['R_LE_M'+str(t)]=sum(v<=-t for v in vals)
    for label,num in counts.items():d.update({label+'_n':num,label+'_N':k,label+'_pct':rate(num,k),label+'_nN_pct':str(num)+'/'+str(k)+' ('+rate(num,k)+'%)' if k else '0/0 (N/A)'})
    for t in T:
        nk=sum(x['u'] is not None for x in records);yes=sum(x['u'] is not None and x['u']>=t for x in records);all_yes=sum(x['u'] is not None and x['u']>=t for x in L.values());label='U'+str(t);d.update({label+'_n':yes,label+'_N':nk,label+'_pct':rate(yes,nk),label+'_capture_pct':rate(yes,all_yes),label+'_global_n':all_yes,label+'_nN_pct':str(yes)+'/'+str(nk)+' ('+rate(yes,nk)+'%)' if nk else '0/0 (N/A)'})
    if full:
        counts=collections.Counter(rband(x['r']) for x in records)
        for b in BN:
            denom=n if b=='R_UNKNOWN' else k;num=counts[b];d.update({b+'_band_n':num,b+'_band_N':denom,b+'_band_pct':rate(num,denom),b+'_band_nN_pct':str(num)+'/'+str(denom)+' ('+rate(num,denom)+'%)' if denom else '0/0 (N/A)'})
    return d
def mass(s,L):
    p=Fraction();n=Fraction()
    for i in s:
        x=L[i]['r']
        if x is not None:
            if x>0:p+=x
            else:n-=x
    return p,n,p-n
def main():
    root=pathlib.Path(__file__).resolve().parents[1];src=root.parent/'restored';evaldir=root/'evaluation';C={r['entry_id']:r for r in readrows(src/'SHARED/inputs/candidate_stream')};A={r['entry_id']:r for r in readrows(root/'private/SEALED_RANK_ASSIGNMENTS.jsonl.gz')};Fmeta={r['entry_id']:r for r in readrows(root/'private/COMPOSE_ONLY_INPUTS.jsonl.gz')};Q={};score_checks=0
    for b in range(1,9):
        for m in ['D-FULL','D-PRICE']:
            d=src/f'B{b:02}/blocks/BLOCK_{b:02}';tm=json.loads((d/'TRAIN_ID_MANIFEST.json').read_text());qs=readrows(d/m/'SEALED_ACTIVE_PREDICTIONS.jsonl.gz')
            for r in qs:Q[r['entry_id'],m]={**r,'B0_p5':tm['B0_p5']}
    predicted={};float_max_ULP=0.;reasons_checked=0
    for i,c in C.items():
        # Recheck PAVA with an independent merge representation.
        pools=[(c['p2'],1),(c['p3'],1),(c['p5'],1)];j=0
        while j<len(pools)-1:
            if pools[j][0]/pools[j][1]<pools[j+1][0]/pools[j+1][1]:
                pools[j:j+2]=[(pools[j][0]+pools[j+1][0],pools[j][1]+pools[j+1][1])];j=max(j-1,0)
            else:j+=1
        mm=[total/count for total,count in pools for _ in range(count)];assert mm==[c['m2'],c['m3'],c['m5']] and sum(mm)/(c['base2']+c['base3']+c['base5'])==c['ML'];score_checks+=1
        dm=calc(c,{m:Q[i,m] for m in ['D-FULL','D-PRICE']});predicted[i]=dm
        for m,d in dm.items():
            saved=A[i]['methods'][m]
            for key,v in d.items():
                if isinstance(v,float):
                    diff=abs(v-saved[key])/math.ulp(v) if v else abs(v-saved[key]);float_max_ULP=max(float_max_ULP,diff);assert diff<=2,(i,m,key)
                else:assert v==saved[key],(i,m,key)
            assert saved['available'] is True
            if m.startswith('G7'):
                g=dm['U7']['grade_index'];delta=d['downshift'];expect='S_OR_GT_1_DOWN_ONE' if g==0 and delta else 'NON_S_AND_GE_1_5_DOWN_ONE' if delta else 'UNCHANGED';assert saved['reason']==expect
            elif m.startswith('B7'):assert saved['reason']==('CONTINUOUS_RISK_PENALTY_WITH_FIXED_DOWNSHIFT_CAP' if d['downshift'] else 'GRADE_UNCHANGED_EFFECTIVE_ML_ORDER')
            reasons_checked+=1
    orders={};n_positions=0
    for m in M:
        complete=sorted(C,key=lambda i:predicted[i][m]['order_key']);counts=collections.Counter();orders[m]={b:[] for b in range(1,9)}
        for pos,i in enumerate(complete,1):
            b=C[i]['block'];counts[b]+=1;assert A[i]['methods'][m]['global_order']==pos and A[i]['methods'][m]['block_order']==counts[b];orders[m][b].append(i);n_positions+=1
    K={k:{b:sum(C[i]['block']==b and C[i]['rank'] in grades for i in C) for b in range(1,9)} for k,grades in [('K43','S'),('K197','SA'),('K494','SAB')]};S={m:{b:sum(C[i]['block']==b and predicted[i][m]['grade']=='S' for i in C) for b in range(1,9)} for m in M[1:]}
    assert [sum(K[x].values()) for x in K]==[43,197,494]
    for sizes in [*K.values(),*S.values()]:
        for b in range(1,9):assert orders['U7'][b][:sizes[b]]==orders['R0_4'][b][:sizes[b]]
    def top(m,z):return set(i for b in range(1,9) for i in orders[m][b][:z[b]])
    rawlabels=readrows(src/'S1/EVALUATION_R_NEW_REUSED.jsonl.gz');L={}
    for l in rawlabels:
        i=l['entry_id'];r=Fraction(int(l['r_numerator']),int(l['r_denominator'])) if l['known'] else None;u=Fraction(int(l['u_numerator']),int(l['u_denominator'])) if l['u_numerator'] is not None else None
        assert l['session']==C[i]['session'] and l['block']==C[i]['block'] and i not in L
        for t in T:assert l['U'+str(t)]==(None if u is None else u>=t)
        L[i]={'r':r,'u':u,'session':C[i]['session'],'symbol':C[i]['symbol'],'block':C[i]['block']}
    assert set(L)==set(C) and sum(r['r'] is not None for r in L.values())==1016
    def subset(d):
        m=d['method'];kind=d['kind']
        if kind in ['grade','cumulative','diagnostic']:
            allowed=[d['grade']] if 'grade' in d else list(d['grades']);s={i for i in C if predicted[i][m]['grade'] in allowed}
        elif kind=='transition':s={i for i in C if predicted[i][m]['grade']==d['to_grade'] and predicted[i][d['from_method']]['grade']==d['from_grade']}
        elif kind=='equalK':s=top(m,K[d['K']])
        elif kind=='newS_K':s=top(m,S[d['anchor']])
        elif kind=='oldS_move':s={i for i in C if C[i]['rank']=='S' and predicted[i][m]['grade']==d['grade']}
        else:raise AssertionError(kind)
        if kind=='diagnostic':
            if d['risk']=='RELATIVE_HIGH':s={i for i in s if max(predicted[i][m]['r3'],predicted[i][m]['r5'])>1}
            elif d['risk']=='RELATIVE_NOT_HIGH':s={i for i in s if max(predicted[i][m]['r3'],predicted[i][m]['r5'])<=1}
            else:s={i for i in s if predicted[i][m]['grade_index']>predicted[i]['U7']['grade_index']}
        if 'group' in d:
            group,v=d['group'],d['value']
            if group in ['block','session','symbol']:s={i for i in s if str(C[i][group])==v}
            elif group=='asof':s={i for i in s if (C[i]['entry_minute']==Fmeta[i]['first_intent_minute'])==(v=='SAME_CLOCK')}
            elif group.startswith('leave_one_'):key='block' if group=='leave_one_block_out' else 'session';s={i for i in s if str(C[i][key])!=v}
        return s
    table_rows={};cells=0;scopes=0;extra_cells=0
    for x in json.loads((evaldir/'TABLE_MANIFEST.json').read_text()):
        with (evaldir/x['path']).open(newline='') as fh:rr=list(csv.DictReader(fh))
        assert len(rr)==x['rows'];table_rows[x['path']]={r['row_key']:r for r in rr}
    for cat in readrows(evaldir/'private/SCOPE_SELECTIONS.jsonl.gz'):
        d=cat['selection'];s=subset(d);assert sorted(s)==cat['entry_ids'];row=table_rows[cat['table']][cat['row_key']];z=aggregate(s,L,cat['full_metrics']);extra={};table=cat['table']
        if table=='NEW_7GRADE_SUMMARY.csv':extra['support']='NO_S_FOR_THIS_DESIGN' if d['grade']=='S' and not s else 'LOW_SUPPORT_S' if d['grade']=='S' and (len(s)<10 or z['session_N']<5) else 'DESCRIPTIVE'
        if d['kind']=='transition':
            rn=sum(predicted[i][d['from_method']]['grade']==d['from_grade'] for i in C);cn=sum(predicted[i][d['method']]['grade']==d['to_grade'] for i in C);extra.update({'row_N':rn,'column_N':cn,'row_pct':rate(len(s),rn),'column_pct':rate(len(s),cn)})
        if table in ['EQUAL_K_OLD_S_SA_SAB_12BAND.csv','EQUAL_K_NEW_S_SIZE_12BAND.csv']:
            n=sum((K[d['K']] if d['kind']=='equalK' else S[d['anchor']]).values());extra.update({'requested_K':n,'K_shortfall':n-len(s)})
        if table=='WINNER_AND_BIG_LOSER_TRADEOFF.csv':
            bs=top('U7',K[d['K']]);lost=bs-s;new=s-bs;b=aggregate(bs,L,False);lm=aggregate(lost,L,False);nm=aggregate(new,L,False);p,n,t=mass(s,L);bp,bn,bt=mass(bs,L)
            extra={'reference':'U7','lost_ID_N':len(lost),'new_ID_N':len(new),'delta_R_unknown_N':z['R_unknown_N']-b['R_unknown_N'],'delta_R_LE_M3_n':z['R_LE_M3_n']-b['R_LE_M3_n'],'delta_R_LE_M5_n':z['R_LE_M5_n']-b['R_LE_M5_n'],'delta_positive_mass_pp':f(p-bp),'delta_negative_abs_mass_pp':f(n-bn),'delta_net_pp_sum':f(t-bt),'unknown_event_delta_worst':nm['R_unknown_N'],'unknown_event_delta_best':-lm['R_unknown_N'],'unknown_mass_sensitivity':'UNBOUNDED_WITHOUT_R_LIMITS' if lm['R_unknown_N']+nm['R_unknown_N'] else 'PAIRED_UNKNOWNS_CANCEL'}
            for metric in ['R_GE_P2_n','R_GE_P5_n','U5_n','U10_n']:extra[metric+'_retention_pct']=rate(z[metric],b[metric]);extra['lost_'+metric]=lm[metric];extra['new_'+metric]=nm[metric]
            for metric in ['PLUS_n','MINUS_n','R_LE_M3_n','R_LE_M5_n','R_unknown_N']:extra['lost_'+metric]=lm[metric];extra['new_'+metric]=nm[metric]
            extra['lost_positive_mass_pp']=lm['positive_mass_pp'];extra['new_positive_mass_pp']=nm['positive_mass_pp'];extra['positive_mass_retention_pct']=f(p/bp*100) if bp else 'N/A'
        assert {k:str(v) for k,v in extra.items()}=={k:str(v) for k,v in cat['extra'].items()},(table,cat['row_key'],'extra')
        for k,v in {**d,**z,**extra}.items():assert row[k]==str(v),(table,cat['row_key'],k,row[k],v);cells+=1
        scopes+=1;extra_cells+=len(extra)
    screen=json.loads((evaldir/'SCREEN_RESULTS_PRE_AUDIT.json').read_text());assert screen['K_per_block']=={k:{str(b):v for b,v in K[k].items()} for k in K}
    for m in M[2:]:
        for k in ['K197','K494']:
            bs=top('U7',K[k]);s=top(m,K[k]);b=aggregate(bs,L,False);z=aggregate(s,L,False);p,n,t=mass(s,L);bp,bn,bt=mass(bs,L)
            bc={'R_LE_M3_reduction_at_least_1':z['R_LE_M3_n']<b['R_LE_M3_n'],'R_LE_M5_nonincrease':z['R_LE_M5_n']<=b['R_LE_M5_n'],'negative_abs_mass_decrease':n<bn,'net_pp_sum_nonworse':t>=bt};cc={metric+'_preserved':None if not b[metric] else Fraction(z[metric],b[metric])>=Fraction(pct_,100) for metric,pct_ in [('R_GE_P5_n',85),('U10_n',85),('R_GE_P2_n',80),('U5_n',80)]};cc['positive_mass_preserved']=None if not bp else p/bp>=Fraction(9,10)
            assert screen['candidates'][m][k]['B']==bc and screen['candidates'][m][k]['C']==cc
            assert screen['candidates'][m][k]['B_PASS']==all(bc.values()) and screen['candidates'][m][k]['C_PASS']==all(x is True for x in cc.values())
    fixture=json.loads((root/'public/BOUNDARY_AND_SEPARATION_TEST_RECEIPT.json').read_text());assert fixture['status']=='PASS'
    result={'status':'PASS','audit_type':'same-author separate implementation cross-check','third_party_independent':False,'primary_assign_or_evaluator_imported':False,'source_pava_ML_recalculated_N':score_checks,'grade_and_order_key_method_N':len(A)*6,'global_and_block_positions_compared_N':n_positions,'reason_fields_compared_N':reasons_checked,'table_N':len(table_rows),'table_row_and_scope_ID_sets_compared_N':scopes,'table_cell_compared_N':cells,'extra_cells_compared_N':extra_cells,'mismatch_N':0,'cell_tolerance':0,'grade_boundary_epsilon':0,'floating_score_max_observed_ULP':float_max_ULP,'floating_score_allowed_ULP':2,'outcome_Fraction_classification':True,'source_q_from_original_saved_prediction_members':True,'fixed_screen_independent_check':'PASS','fixture_receipt':'BOUNDARY_AND_SEPARATION_TEST_RECEIPT.json'}
    (root/'public/INDEPENDENT_RECALC_RECEIPT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
