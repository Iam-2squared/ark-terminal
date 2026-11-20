"""Separate outcome evaluator; consumes only a GitHub-readback sealed assignment."""
import csv,gzip,hashlib,io,json,pathlib,sys,collections
from fractions import Fraction as F
from decimal import Decimal,localcontext
METHODS=['R0_4','U7','G7_FULL','B7_FULL','G7_PRICE','B7_PRICE'];GRADES='SABCDEF';TH=[2,3,5,10]
BANDS=['R_GE_P5','R_P4_P5','R_P3_P4','R_P2_P3','R_P1_P2','R_P0_P1','R_M1_0','R_M2_M1','R_M3_M2','R_M4_M3','R_M5_M4','R_LE_M5','ZERO','R_UNKNOWN']
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def jwrite(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def gzrows(p):return [json.loads(x) for x in gzip.decompress(p.read_bytes()).splitlines()]
def number(x):
    if x is None:return 'N/A'
    with localcontext() as c:
        c.prec=60;v=Decimal(x.numerator)/Decimal(x.denominator) if isinstance(x,F) else Decimal(str(x));return format(v.quantize(Decimal('0.000000000001')),'f')
def pct(n,d):return number(F(n*100,d)) if d else 'N/A'
def band(x):
    if x is None:return 'R_UNKNOWN'
    if x==0:return 'ZERO'
    if x>0:
        for b,name in [(5,'R_GE_P5'),(4,'R_P4_P5'),(3,'R_P3_P4'),(2,'R_P2_P3'),(1,'R_P1_P2')]:
            if x>=b:return name
        return 'R_P0_P1'
    for b,name in [(-1,'R_M1_0'),(-2,'R_M2_M1'),(-3,'R_M3_M2'),(-4,'R_M4_M3'),(-5,'R_M5_M4')]:
        if x>b:return name
    return 'R_LE_M5'
def normalized(labels,assign):
    assert len(labels)==1039 and len({r['entry_id'] for r in labels})==1039
    out={}
    for l in labels:
        i=l['entry_id'];a=assign[i];assert l['session']==a['session'] and l['block']==a['block'];assert l['r_namespace']=='R_NEW_SHARP_DROP_FIRST_OBSERVED_EXIT_V0_PCT_100SHARE'
        r=F(int(l['r_numerator']),int(l['r_denominator'])) if l['known'] else None
        assert (r is None)==(l['r_numerator'] is None)
        u=F(int(l['u_numerator']),int(l['u_denominator'])) if l['u_numerator'] is not None else None
        for t in TH:
            assert l['U'+str(t)] is None if u is None else bool(l['U'+str(t)])==(u>=t)
        out[i]={'R':r,'U':u,'session':a['session'],'symbol':a['symbol'],'block':a['block'],'U_flags':{t:l['U'+str(t)] for t in TH},'label_source':l['label_source'],'exit_kind':l['exit_kind'],'unknown_reason':l['unknown_reason']}
    assert set(out)==set(assign) and sum(l['R'] is not None for l in out.values())==1016
    return out
def metrics(ids,L,full=True):
    rows=[L[i] for i in sorted(ids)];r=sorted(x['R'] for x in rows if x['R'] is not None);N=len(rows);K=len(r);unknown=N-K;uc={t:sum(x['U_flags'][t] is not None for x in rows) for t in TH};ut={t:sum(x['U_flags'][t] is True for x in rows) for t in TH};globalU={t:sum(x['U_flags'][t] is True for x in L.values()) for t in TH}
    med=(r[(K-1)//2]+r[K//2])/2 if K else None;pos=sum((x for x in r if x>0),F(0));neg=-sum((x for x in r if x<0),F(0));net=pos-neg
    z={'N':N,'R_known_N':K,'R_unknown_N':unknown,'R_coverage_pct':pct(K,N),'R_unknown_pct':pct(unknown,N),'U_known_N':sum(x['U'] is not None for x in rows),'session_N':len({x['session'] for x in rows}),'symbol_N':len({x['symbol'] for x in rows}),'PLUS_n':sum(x>0 for x in r),'MINUS_n':sum(x<0 for x in r),'R_GE_P2_n':sum(x>=2 for x in r),'R_GE_P3_n':sum(x>=3 for x in r),'R_GE_P4_n':sum(x>=4 for x in r),'R_GE_P5_n':sum(x>=5 for x in r),'R_LE_M2_n':sum(x<=-2 for x in r),'R_LE_M3_n':sum(x<=-3 for x in r),'R_LE_M5_n':sum(x<=-5 for x in r),'mean_R':number(net/K) if K else 'N/A','median_R':number(med),'positive_mass_pp':number(pos),'negative_abs_mass_pp':number(neg),'net_pp_sum':number(net)}
    for k in ['PLUS','MINUS','R_GE_P2','R_GE_P3','R_GE_P4','R_GE_P5','R_LE_M2','R_LE_M3','R_LE_M5']:
        z[k+'_N']=K;z[k+'_pct']=pct(z[k+'_n'],K);z[k+'_nN_pct']=str(z[k+'_n'])+'/'+str(K)+' ('+z[k+'_pct']+'%)' if K else '0/0 (N/A)'
    for t in TH:
        z.update({f'U{t}_n':ut[t],f'U{t}_N':uc[t],f'U{t}_pct':pct(ut[t],uc[t]),f'U{t}_capture_pct':pct(ut[t],globalU[t]),f'U{t}_global_n':globalU[t],f'U{t}_nN_pct':str(ut[t])+'/'+str(uc[t])+' ('+pct(ut[t],uc[t])+'%)' if uc[t] else '0/0 (N/A)'})
    if full:
        counts=collections.Counter(band(x['R']) for x in rows);assert sum(counts[b] for b in BANDS[:-1])==K and counts['R_UNKNOWN']==unknown
        for b in BANDS:
            d=N if b=='R_UNKNOWN' else K;n=counts[b];z.update({b+'_band_n':n,b+'_band_N':d,b+'_band_pct':pct(n,d),b+'_band_nN_pct':str(n)+'/'+str(d)+' ('+pct(n,d)+'%)' if d else '0/0 (N/A)'})
    return z
def exactmass(ids,L):
    v=[L[i]['R'] for i in ids if L[i]['R'] is not None];p=sum((x for x in v if x>0),F(0));n=-sum((x for x in v if x<0),F(0));return p,n,p-n
def csvbytes(rows):
    fields=list(dict.fromkeys(k for r in rows for k in r));out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);return out.getvalue().encode()
def evaluate(A,L,C):
    ids=set(A);ordered={m:{b:[i for i in sorted(ids,key=lambda i:A[i]['methods'][m].get('block_order',10**9)) if A[i]['block']==b and A[i]['methods'][m]['available']] for b in range(1,9)} for m in METHODS}
    sizes={k:{b:sum(A[i]['block']==b and A[i]['methods']['R0_4']['grade'] in gs for i in ids) for b in range(1,9)} for k,gs in [('K43','S'),('K197','SA'),('K494','SAB')]};assert [sum(sizes[k].values()) for k in sizes]==[43,197,494]
    natural={m:{b:sum(A[i]['block']==b and A[i]['methods'][m]['grade']=='S' for i in ids) for b in range(1,9)} for m in METHODS[1:]}
    def top(m,s):return set(i for b in range(1,9) for i in ordered[m][b][:s[b]])
    for s in [*sizes.values(),*natural.values()]:
        for b in range(1,9):assert ordered['R0_4'][b][:s[b]]==ordered['U7'][b][:s[b]]
    def select(d):
        m=d['method'];kind=d['kind'];s=set()
        if kind=='grade':s={i for i in ids if A[i]['methods'][m]['grade']==d['grade']}
        elif kind=='cumulative':s={i for i in ids if A[i]['methods'][m]['grade'] in d['grades']}
        elif kind=='transition':s={i for i in ids if A[i]['methods'][d['from_method']]['grade']==d['from_grade'] and A[i]['methods'][m]['grade']==d['to_grade']}
        elif kind=='equalK':s=top(m,sizes[d['K']])
        elif kind=='newS_K':s=top(m,natural[d['anchor']])
        elif kind=='diagnostic':
            s={i for i in ids if A[i]['methods'][m]['grade']==d['grade']}
            if d['risk']=='RELATIVE_HIGH':s={i for i in s if A[i]['methods'][m]['r3']>1 or A[i]['methods'][m]['r5']>1}
            elif d['risk']=='RELATIVE_NOT_HIGH':s={i for i in s if A[i]['methods'][m]['r3']<=1 and A[i]['methods'][m]['r5']<=1}
            else:s={i for i in s if A[i]['methods'][m]['downshift']>0}
        elif kind=='oldS_move':s={i for i in ids if A[i]['methods']['R0_4']['grade']=='S' and A[i]['methods'][m]['grade']==d['grade']}
        else:raise ValueError(kind)
        if 'group' in d:
            g,v=d['group'],d['value']
            if g=='block':s={i for i in s if A[i]['block']==int(v)}
            elif g=='session':s={i for i in s if A[i]['session']==v}
            elif g=='symbol':s={i for i in s if str(A[i]['symbol'])==v}
            elif g=='asof':s={i for i in s if (C[i]['entry_minute']==C[i]['first_intent_minute'])==(v=='SAME_CLOCK')}
            elif g=='leave_one_block_out':s={i for i in s if A[i]['block']!=int(v)}
            elif g=='leave_one_session_out':s={i for i in s if A[i]['session']!=v}
        return s
    tables=collections.defaultdict(list);catalog=[];special={}
    def add(table,d,extra=None,full=True):
        s=select(d);key=f'{table}:{len(tables[table])}';row={'row_key':key,**d,**metrics(s,L,full)}
        row.update(extra or {});tables[table].append(row);catalog.append({'row_key':key,'table':table,'selection':d,'full_metrics':full,'entry_ids':sorted(s),'extra':extra or {}});return s,row
    for m in METHODS:
        gs='SABC' if m=='R0_4' else GRADES
        for g in [*gs,'RANK_UNAVAILABLE']:
            s,row=add('OLD_R0_4GRADE_FULL_12BAND.csv' if m=='R0_4' else 'NEW_7GRADE_FULL_12BAND.csv',{'method':m,'kind':'grade','grade':g})
            if m!='R0_4':add('NEW_7GRADE_SUMMARY.csv',{'method':m,'kind':'grade','grade':g},{'support':'NO_S_FOR_THIS_DESIGN' if g=='S' and not s else 'LOW_SUPPORT_S' if g=='S' and (len(s)<10 or row['session_N']<5) else 'DESCRIPTIVE'},full=False)
        cum=['S','SA','SAB','SABC'] if m=='R0_4' else ['S','SA','SAB','SABC','SABCD','SABCDE','SABCDEF']
        for g in cum:add('CUMULATIVE_7GRADE_12BAND.csv',{'method':m,'kind':'cumulative','grades':g})
    for m in METHODS[1:]:
        for old in 'SABC':
            for g in GRADES:
                d={'method':m,'kind':'transition','from_method':'R0_4','from_grade':old,'to_grade':g};s=select(d);rn=sum(A[i]['methods']['R0_4']['grade']==old for i in ids);cn=sum(A[i]['methods'][m]['grade']==g for i in ids);add('OLD4_TO_NEW7_TRANSITIONS.csv',d,{'row_pct':pct(len(s),rn),'column_pct':pct(len(s),cn),'row_N':rn,'column_N':cn})
        for g in GRADES:add('OLD_S43_MOVEMENT_AND_OUTCOMES.csv',{'method':m,'kind':'oldS_move','grade':g})
    for m in METHODS[2:]:
        for old in GRADES:
            for g in GRADES:
                d={'method':m,'kind':'transition','from_method':'U7','from_grade':old,'to_grade':g};s=select(d);assert not s or GRADES.index(g)>=GRADES.index(old);rn=sum(A[i]['methods']['U7']['grade']==old for i in ids);cn=sum(A[i]['methods'][m]['grade']==g for i in ids);add('U7_TO_RISK7_TRANSITIONS.csv',d,{'row_pct':pct(len(s),rn),'column_pct':pct(len(s),cn),'row_N':rn,'column_N':cn})
    trade=[];paired=[]
    for k in sizes:
        baseline=top('U7',sizes[k]);bm=metrics(baseline,L);bp,bn,bt=exactmass(baseline,L)
        for m in METHODS:
            s,row=add('EQUAL_K_OLD_S_SA_SAB_12BAND.csv',{'method':m,'kind':'equalK','K':k},{'requested_K':sum(sizes[k].values()),'K_shortfall':sum(sizes[k].values())-len(top(m,sizes[k]))});assert row['K_shortfall']==0
            lost=baseline-s;new=s-baseline;lm=metrics(lost,L);nm=metrics(new,L);p,n,t=exactmass(s,L)
            ex={'reference':'U7','lost_ID_N':len(lost),'new_ID_N':len(new),'delta_R_unknown_N':row['R_unknown_N']-bm['R_unknown_N'],'delta_R_LE_M3_n':row['R_LE_M3_n']-bm['R_LE_M3_n'],'delta_R_LE_M5_n':row['R_LE_M5_n']-bm['R_LE_M5_n'],'delta_positive_mass_pp':number(p-bp),'delta_negative_abs_mass_pp':number(n-bn),'delta_net_pp_sum':number(t-bt),'unknown_event_delta_worst':nm['R_unknown_N'],'unknown_event_delta_best':-lm['R_unknown_N'],'unknown_mass_sensitivity':'UNBOUNDED_WITHOUT_R_LIMITS' if lm['R_unknown_N']+nm['R_unknown_N'] else 'PAIRED_UNKNOWNS_CANCEL'}
            for metric in ['R_GE_P2_n','R_GE_P5_n','U5_n','U10_n']:
                ex[metric+'_retention_pct']=pct(row[metric],bm[metric]);ex['lost_'+metric]=lm[metric];ex['new_'+metric]=nm[metric]
            for metric in ['PLUS_n','MINUS_n','R_LE_M3_n','R_LE_M5_n','R_unknown_N']:ex['lost_'+metric]=lm[metric];ex['new_'+metric]=nm[metric]
            ex['lost_positive_mass_pp']=lm['positive_mass_pp'];ex['new_positive_mass_pp']=nm['positive_mass_pp'];ex['positive_mass_retention_pct']=number(p/bp*100) if bp else 'N/A'
            add('WINNER_AND_BIG_LOSER_TRADEOFF.csv',{'method':m,'kind':'equalK','K':k},ex,full=False);paired.append({'method':m,'K':k,'lost':sorted(lost),'new':sorted(new)})
    for anchor in METHODS[1:]:
        for m in METHODS:add('EQUAL_K_NEW_S_SIZE_12BAND.csv',{'method':m,'kind':'newS_K','anchor':anchor},{'requested_K':sum(natural[anchor].values()),'K_shortfall':sum(natural[anchor].values())-len(top(m,natural[anchor]))})
    for m in METHODS[2:]:
        for g in GRADES:
            for risk in ['RELATIVE_HIGH','RELATIVE_NOT_HIGH','RISK_DOWNGRADE']:add('HIGH_UPSIDE_HIGH_RISK_DIAGNOSTICS.csv',{'method':m,'kind':'diagnostic','grade':g,'risk':risk},full=False)
    sessions=sorted({A[i]['session'] for i in ids});symbols=sorted({str(A[i]['symbol']) for i in ids})
    for m in METHODS:
        gs='SABC' if m=='R0_4' else GRADES
        for group,values in [('block',range(1,9)),('session',sessions),('asof',['SAME_CLOCK','LATER_NATIVE_CLOCK'])]:
            for v in values:
                for g in gs:add('BLOCK_SESSION_AND_ASOF_STABILITY.csv',{'method':m,'kind':'grade','grade':g,'group':group,'value':str(v)},full=False)
        for k in sizes:
            for group,values in [('block',range(1,9)),('session',sessions),('leave_one_block_out',range(1,9)),('leave_one_session_out',sessions),('asof',['SAME_CLOCK','LATER_NATIVE_CLOCK'])]:
                for v in values:add('FIXED_K_AND_LEAVE_ONE_OUT_STABILITY.csv',{'method':m,'kind':'equalK','K':k,'group':group,'value':str(v)},full=False)
        for sy in symbols:
            for k in sizes:add('private/SYMBOL_FIXED_K_STABILITY.csv',{'method':m,'kind':'equalK','K':k,'group':'symbol','value':sy},full=False)
    screens={};Achecks={'U7_R0_exact_complete_order_and_all_block_K':True,'low_ML_S_promotion_N':0,'risk_upgrade_N':0,'high_ML_over_one_downshift_N':0}
    for m in METHODS[2:]:
        ms={}
        for k in ['K197','K494']:
            bs=top('U7',sizes[k]);s=top(m,sizes[k]);v=metrics(s,L);b=metrics(bs,L);p,n,t=exactmass(s,L);bp,bn,bt=exactmass(bs,L)
            bc={'R_LE_M3_reduction_at_least_1':v['R_LE_M3_n']<=b['R_LE_M3_n']-1,'R_LE_M5_nonincrease':v['R_LE_M5_n']<=b['R_LE_M5_n'],'negative_abs_mass_decrease':n<bn,'net_pp_sum_nonworse':t>=bt}
            cc={}
            for metric,num,den in [('R_GE_P5_n',85,100),('U10_n',85,100),('R_GE_P2_n',80,100),('U5_n',80,100)]:cc[metric+'_preserved']=None if not b[metric] else v[metric]*den>=b[metric]*num
            cc['positive_mass_preserved']=None if not bp else p*100>=bp*90
            lost=bs-s;new=s-bs;unknownlost=sum(L[i]['R'] is None for i in lost);unknownnew=sum(L[i]['R'] is None for i in new)
            ms[k]={'B':bc,'B_PASS':all(bc.values()),'C':cc,'C_PASS':all(x is True for x in cc.values()),'unknown_baseline':b['R_unknown_N'],'unknown_method':v['R_unknown_N'],'unknown_R_event_delta_worst':unknownnew,'unknown_R_event_delta_best':-unknownlost,'unknown_mass_bound':'UNBOUNDED' if unknownlost+unknownnew else 'PAIRED_UNKNOWNS_CANCEL','baseline':{q:b[q] for q in ['N','R_LE_M3_n','R_LE_M5_n','R_GE_P2_n','R_GE_P5_n','U5_n','U10_n','positive_mass_pp','negative_abs_mass_pp','net_pp_sum']},'method':{q:v[q] for q in ['N','R_LE_M3_n','R_LE_M5_n','R_GE_P2_n','R_GE_P5_n','U5_n','U10_n','positive_mass_pp','negative_abs_mass_pp','net_pp_sum']}}
        ms['B_BOTH_K_PASS']=all(ms[k]['B_PASS'] for k in ['K197','K494']);ms['C_BOTH_K_PASS']=all(ms[k]['C_PASS'] for k in ['K197','K494']);ms['A_B_C_SCREEN_PASS']=ms['B_BOTH_K_PASS'] and ms['C_BOTH_K_PASS'];screens[m]=ms
    decision='NO_INCREMENT' if not any(screens[m]['A_B_C_SCREEN_PASS'] for m in ['G7_FULL','B7_FULL']) else 'INCONCLUSIVE_LOW_SUPPORT'
    result={'decision':decision,'A':Achecks,'candidates':screens,'screen_research_only':True,'HARD_INTEGRITY':'PENDING_INDEPENDENT_AUDIT_AND_REPRODUCTION','asof_mode':'HISTORICAL_MIXED_ASOF_RESEARCH_ONLY','BUY_INTENT_DEPLOYABLE':False,'CANDIDATE_FOR_CAPITAL_BRIDGE':False,'selectedNewRank':None,'mainRank':'SAVED_R0','K_per_block':sizes,'new_S_K_per_block':natural,'R_known_N':1016,'R_unknown_N':23,'tail_R_LE_M5_N':sum(l['R'] is not None and l['R']<=-5 for l in L.values()),'U_known_N':sum(l['U'] is not None for l in L.values()),'CapitalReplay':0,'winner_counts_do_not_equal_upside_label_counts':True,'unknown_mass_not_imputed':True}
    return dict(tables),catalog,paired,result
def main():
    base=pathlib.Path(__file__).resolve().parents[1];mode=sys.argv[1] if len(sys.argv)>1 else 'evaluate';out=base/('reproduction/evaluation' if mode=='reproduce' else 'evaluation');out.mkdir(parents=True,exist_ok=True)
    gate=json.loads((base/'cache/ASSIGNMENT_ACTUAL_GET_PASS.json').read_text());assert gate['status']=='EXACT_GET_PASS';assignment=base/'private/SEALED_RANK_ASSIGNMENTS.jsonl.gz';assert pin(assignment.read_bytes())==gate['assignment_pin']
    A={r['entry_id']:r for r in gzrows(assignment)};C={r['entry_id']:r for r in gzrows(base/'private/COMPOSE_ONLY_INPUTS.jsonl.gz')};label=base.parent/'restored/RD01/rd01/private/EVALUATION_ONLY_R_NEW.jsonl.gz';pre=json.loads((base/'public/PRECOMMIT_RG01.json').read_text());assert pin(label.read_bytes())==pre['label_pin'];L=normalized(gzrows(label),A)
    tables,catalog,paired,result=evaluate(A,L,C)
    manifest=[]
    for name,rows in tables.items():
        b=csvbytes(rows);dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b);manifest.append({'path':name,'rows':len(rows),**pin(b)})
    for name,rows in [('SCOPE_SELECTIONS.jsonl.gz',catalog),('PAIRED_LOST_AND_NEW_IDS.jsonl.gz',paired)]:
        b=gzip.compress((''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in rows)).encode(),mtime=0);(out/'private'/name).write_bytes(b)
    jwrite(out/'SCREEN_RESULTS_PRE_AUDIT.json',result);jwrite(out/'TABLE_MANIFEST.json',manifest)
    source={'known':1016,'unknown':23,'U_known':result['U_known_N'],'EXIT_namespace':'R_NEW_SHARP_DROP_FIRST_OBSERVED_EXIT_V0_PCT_100SHARE','ID_session_block_exact_match_N':1039,'duplicate_N':0,'label_pin':pin(label.read_bytes()),'R_UNKNOWN_not_imputed':True,'U_mask_independently_verified_N':1039,'label_source_counts':dict(collections.Counter(l['label_source'] for l in L.values())),'exit_kind_counts':dict(collections.Counter(l['exit_kind'] for l in L.values()))}
    jwrite(out/'OUTCOME_JOIN_AUDIT.json',source)
    old=next(r for r in tables['OLD_R0_4GRADE_FULL_12BAND.csv'] if r['grade']=='S');assert old['N']==43 and old['PLUS_n']==10 and old['MINUS_n']==33 and old['R_GE_P5_n']==3 and old['R_LE_M3_n']==3
    print(json.dumps({'decision':result['decision'],'tables':len(manifest),'rows':sum(r['rows'] for r in manifest),'tail_N':result['tail_R_LE_M5_N'],'U_known_N':result['U_known_N'],'old_S':{k:old[k] for k in ['N','PLUS_n','MINUS_n','R_LE_M3_n','R_LE_M5_n','R_GE_P5_n','mean_R']},'primary_screen':{m:{k:result['candidates'][m][k] for k in ['B_BOTH_K_PASS','C_BOTH_K_PASS']} for m in ['G7_FULL','B7_FULL']}}))
if __name__=='__main__':main()
