"""Separate Decimal/interval implementation. Never imports census.py or computes from its tables."""
import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path

getcontext().prec = 240
D = Decimal
POINTS = [('CAL95','CAL95'),('M80','CAL_MINUS_KEEP_80'),('M60','CAL_MINUS_KEEP_60'),
          ('M40','CAL_MINUS_KEEP_40'),('M20','CAL_MINUS_KEEP_20'),('M10','CAL_MINUS_KEEP_10')]
# Tuple: name, lower, lower inclusive, upper, upper inclusive. This is not an if-chain.
INTERVALS = [('L5_PLUS',None,False,D(-5),True),('L4_5',D(-5),False,D(-4),True),
    ('L3_4',D(-4),False,D(-3),True),('L2_3',D(-3),False,D(-2),True),
    ('L1_2',D(-2),False,D(-1),True),('L0_1',D(-1),False,D(0),False),
    ('ZERO',D(0),True,D(0),True),('P0_1',D(0),False,D(1),False),
    ('P1_2',D(1),True,D(2),False),('P2_3',D(2),True,D(3),False),
    ('P3_4',D(3),True,D(4),False),('P4_5',D(4),True,D(5),False),
    ('P5_PLUS',D(5),True,None,False)]
BANDS = [x[0] for x in INTERVALS]+['R_UNKNOWN']
LEGACY = 'LEGACY_DIAGNOSTIC_ONLY / NEGATIVE_EVIDENCE / NOT_A_NEW_PARENT'

def jread(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def gzread(p):
    with gzip.open(p,'rt',encoding='utf-8') as f: return [json.loads(line) for line in f if line.strip()]

def independently_parse_native(row):
    if row.get('return_available') is False or not row.get('return_available'):
        return None,'FORMAL_R_UNAVAILABLE_SOURCE_REASON_UNSPECIFIED'
    if row.get('R_native_fraction_decimal') is None: return None,'NULL_R_NATIVE'
    try: v=D(str(row['R_native_fraction_decimal']))
    except InvalidOperation: return None,'INVALID_R_NATIVE'
    if v.is_nan(): return None,'NAN_R_NATIVE'
    if not v.is_finite(): return None,'NONFINITE_R_NATIVE'
    return v*100,None

def independent_bin(value):
    if value is None: return 'R_UNKNOWN'
    found=[]
    for name,lo,li,hi,ui in INTERVALS:
        lower=lo is None or value>lo or (li and value==lo)
        upper=hi is None or value<hi or (ui and value==hi)
        if lower and upper: found.append(name)
    if len(found)!=1: raise AssertionError(('NONEXCLUSIVE_BUCKET',str(value),found))
    return found[0]

def pct(x,n):
    return 'N/A' if not n else str((D(x)/D(n)*100).quantize(D('0.000000000001')))

def independent_mass(records):
    negative=D(0);positive=D(0)
    for t in records:
        v=t['value']
        if v is None: continue
        if v.is_signed() and v!=0: negative-=v
        elif v>0: positive+=v
    return negative,positive,positive-negative

def dstats(records,point):
    keep=sum(t['decision'][point]=='KEEP' for t in records)
    drop=sum(t['decision'][point]=='DROP' for t in records)
    n=len(records)
    return {'N':n,'KEEP':keep,'DROP':drop,'decision_UNKNOWN':n-keep-drop,
        'KEEP_rate_pct':pct(keep,n),'DROP_rate_pct':pct(drop,n),'decision_coverage_pct':pct(keep+drop,n)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs',required=True);parser.add_argument('--public',required=True)
    parser.add_argument('--private',required=True);parser.add_argument('--manifest',required=True)
    opts=parser.parse_args();src=Path(opts.inputs);pub=Path(opts.public);private=Path(opts.private)
    errors=[];checks=0
    def check(test,tag):
        nonlocal checks
        checks+=1
        if not test: errors.append(tag)
    sm=jread(opts.manifest)
    for pin in sm['selected_private_sources']:
        rel=pin['member'].removeprefix('c11/private/')
        body=(src/rel).read_bytes()
        check(len(body)==pin['bytes'],'SOURCE_BYTES:'+rel)
        check(hashlib.sha256(body).hexdigest()==pin['sha256'],'SOURCE_SHA256:'+rel)
        check(hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==pin['blob'],'SOURCE_BLOB:'+rel)
    splits=jread(src/'SPLITS_S1_S2.json')
    byblock={b['block']:b for b in splits}
    a=set(byblock['S1']['DEV_COMPARE_Entry_IDs']);b=set(byblock['S2']['DEV_COMPARE_Entry_IDs'])
    check(not(a&b),'CANONICAL_SPLIT_OVERLAP')
    check(len(a)==164 and len(b)==158 and len(a|b)==322,'CANONICAL_SPLIT_COUNTS')
    expected_ids=a|b
    canonical=jread(src/'CANONICAL_RETURN_ROWS_322.json')
    original=jread(src/'RNEG_TARGETED_OUTCOMES_322.json')
    original_map={t['entry_id']:t for t in original}
    identities={t['entry_id']:t for t in jread(src/'SAVED_FROZEN_IDENTITY_322.json')}
    saved=gzread(src/'C11/DEV_SCORES_DECISIONS.jsonl.gz')
    sd={t['entry_id']:t for t in saved}
    check(len(canonical)==len({r['entry_id'] for r in canonical})==322,'CANONICAL_DUPLICATE_IDS')
    check(set(t['entry_id'] for t in canonical)==expected_ids,'CANONICAL_ID_SET')
    check(len(saved)==len(sd)==322 and set(sd)==expected_ids,'DECISION_ID_SET')
    check(len(identities)==322 and set(identities)==expected_ids,'IDENTITY_ID_SET')
    public_seal=jread(pub.parent.parent/'inputs/c11_public/C11_PREDICTION_SEAL.json')
    seal_pin=public_seal['DEV_union_seal'];binary=(src/'C11/DEV_SCORES_DECISIONS.jsonl.gz').read_bytes()
    check(hashlib.sha256(binary).hexdigest()==seal_pin['sha256'] and len(binary)==seal_pin['bytes'],'UNION_PREDICTION_SEAL')
    for block in ['S1','S2']:
        rows=gzread(src/f'C11/{block}/DEV_COMPARE_SCORES_DECISIONS.jsonl.gz')
        check({x['entry_id'] for x in rows}==set(byblock[block]['DEV_COMPARE_Entry_IDs']),'SPLIT_DECISION_ID:'+block)
        for row in rows:
            check(row==sd[row['entry_id']], 'SPLIT_UNION_SAVED_ROW:'+row['entry_id'])
    data=[]
    for t in canonical:
        i=t['entry_id'];block='S1' if i in a else 'S2';s=sd[i];ident=identities[i]
        v,reason=independently_parse_native(t)
        check(t['R_unit']=='percent','R_UNIT:'+i)
        check(t['session']==s['session']==ident['session']==original_map[i]['session'],'SESSION_ID_JOIN:'+i)
        check(s['block']==block,'CANONICAL_BLOCK:'+i)
        if v is not None:
            # Cross-multiplication validates percent ratio without using it to calculate R.
            check(v*D(t['R_pct_denominator'])==D(t['R_pct_numerator']),'EXACT_R_UNIT_CONVERSION:'+i)
            check(D(str(original_map[i]['r_original']))*100==v,'SAVED_SOURCE_R_TOKEN:'+i)
            check(('MINUS' if v<0 else 'PLUS' if v>0 else 'ZERO')==t['sign_status'],'SIGN_CONTRACT:'+i)
        decisions={label:s['decisions'].get(key) if s['decisions'].get(key) in ['KEEP','DROP'] else 'UNKNOWN' for label,key in POINTS}
        data.append({'id':i,'block':block,'session':t['session'],'symbol':ident['symbol'],'value':v,
            'reason':reason,'band':independent_bin(v),'decision':decisions})
    independent_tables={}
    for name in ['ENTRY_EXIT_R_DISTRIBUTION.csv','LEGACY_R_BAND_KEEP_DROP.csv','CUMULATIVE_LOSER_WINNER_KEEP_DROP.csv',
                 'DROP_COMPOSITION.csv','RETURN_MASS_DECOMPOSITION.csv','ACCOUNTING_IDENTITY_CHECK.csv','ALL_KEEP_REFERENCE.csv']:
        independent_tables[name]=[]
    summary=jread(pub/'CENSUS_SUMMARY.json')
    for cohort in ['S1','S2','UNION']:
        ss=[t for t in data if cohort=='UNION' or t['block']==cohort]
        known=sum(t['value'] is not None for t in ss)
        groups={name:[t for t in ss if t['band']==name] for name in BANDS}
        groups['ALL_MINUS']=[t for t in ss if t['value'] is not None and t['value']<0]
        groups['ALL_PLUS']=[t for t in ss if t['value'] is not None and t['value']>0]
        groups['R_KNOWN']=[t for t in ss if t['value'] is not None];groups['TOTAL']=ss
        cumulative={'ALL_MINUS':groups['ALL_MINUS']}
        for k in range(1,6): cumulative['R_LE_NEG'+str(k)]=[t for t in ss if t['value'] is not None and t['value']<=-k]
        cumulative['ALL_PLUS']=groups['ALL_PLUS']
        for k in range(1,6): cumulative['R_GE_POS'+str(k)]=[t for t in ss if t['value'] is not None and t['value']>=k]
        check(sum(len(groups[n]) for n in BANDS)==len(ss),'BUCKET_PARTITION_SUM:'+cohort)
        check(sum(len(groups[n]) for n in BANDS[:6])==len(groups['ALL_MINUS']),'NEGATIVE_PARTITION_SUM:'+cohort)
        check(sum(len(groups[n]) for n in BANDS[7:13])==len(groups['ALL_PLUS']),'POSITIVE_PARTITION_SUM:'+cohort)
        sc=summary['cohorts'][cohort]
        for key,val in {'N':len(ss),'R_known_N':known,'R_unknown_N':len(ss)-known,'ALL_MINUS_N':len(groups['ALL_MINUS']),
                        'ALL_PLUS_N':len(groups['ALL_PLUS']),'ZERO_N':len(groups['ZERO']),
                        'distinct_sessions':len({t['session'] for t in ss}),'distinct_symbols':len({t['symbol'] for t in ss})}.items():
            check(sc[key]==val,'SUMMARY:'+cohort+'/'+key)
        check(sc['sessions']==sorted({t['session'] for t in ss}),'SUMMARY_SESSION_SET:'+cohort)
        for g,rs in groups.items():
            values=sorted(t['value'] for t in rs if t['value'] is not None)
            median='N/A' if not values else values[len(values)//2] if len(values)%2 else sum(values[len(values)//2-1:len(values)//2+1])/2
            neg,pos,net=independent_mass(rs)
            independent_tables['ENTRY_EXIT_R_DISTRIBUTION.csv'].append({'cohort':cohort,'bucket':g,'N':len(rs),'R_known_N':len(values),
                'R_unknown_N':len(rs)-len(values),'share_R_known_pct':'N/A' if g=='R_UNKNOWN' else pct(len(values),known),
                'share_all_entries_pct':pct(len(rs),len(ss)),'distinct_sessions':len({t['session'] for t in rs}),
                'distinct_symbols':len({t['symbol'] for t in rs}),'R_median_pct':median,
                'R_sum_pp':'N/A' if rs and not values else net,'negative_mass_abs_pp':neg,'positive_mass_pp':pos})
            n=len(rs)
            independent_tables['ALL_KEEP_REFERENCE.csv'].append({'cohort':cohort,'point':'ALL_KEEP','bucket':g,'N':n,'KEEP':n,'DROP':0,
                'decision_UNKNOWN':0,'KEEP_rate_pct':pct(n,n),'DROP_rate_pct':pct(0,n),'decision_coverage_pct':pct(n,n)})
        for point,_ in POINTS:
            for g,rs in groups.items():
                stats=dstats(rs,point)
                check(stats['N']==stats['KEEP']+stats['DROP']+stats['decision_UNKNOWN'],'DECISION_PARTITION:'+cohort+'/'+point+'/'+g)
                independent_tables['LEGACY_R_BAND_KEEP_DROP.csv'].append({'cohort':cohort,'point':point,'bucket':g,'diagnostic_labels':LEGACY,**stats})
            for g,rs in cumulative.items():
                stats=dstats(rs,point)
                independent_tables['CUMULATIVE_LOSER_WINNER_KEEP_DROP.csv'].append({'cohort':cohort,'point':point,'group':g,'diagnostic_labels':LEGACY,**stats})
                if g=='ALL_MINUS': bands=BANDS[:6]
                elif g=='ALL_PLUS': bands=BANDS[7:13]
                elif g.startswith('R_LE_NEG'): bands=BANDS[:6-int(g[-1])]
                else: bands=BANDS[7+int(g[-1]):13]
                disjoint=[t for name in bands for t in groups[name]]
                check({t['id'] for t in rs}=={t['id'] for t in disjoint},'CUMULATIVE_BUCKET_IDENTITY:'+cohort+'/'+point+'/'+g)
                check(dstats(disjoint,point)==stats,'CUMULATIVE_BUCKET_COUNTS:'+cohort+'/'+point+'/'+g)
                check(independent_mass(disjoint)==independent_mass(rs),'CUMULATIVE_BUCKET_MASS:'+cohort+'/'+point+'/'+g)
            all_drop=sum(t['decision'][point]=='DROP' for t in ss)
            known_drop=sum(t['value'] is not None and t['decision'][point]=='DROP' for t in ss)
            compgroups={**{n:groups[n] for n in BANDS},'ALL_MINUS':groups['ALL_MINUS'],'R_LE_NEG5':cumulative['R_LE_NEG5'],
                'R_LE_NEG3':cumulative['R_LE_NEG3'],'ALL_PLUS':groups['ALL_PLUS'],'R_GE_POS2':cumulative['R_GE_POS2'],
                'R_GE_POS3':cumulative['R_GE_POS3'],'R_GE_POS5':cumulative['R_GE_POS5'],'TOTAL':ss}
            check(sum(sum(t['decision'][point]=='DROP' for t in groups[n]) for n in BANDS)==all_drop,'DROP_EXCLUSIVE_TOTAL:'+cohort+'/'+point)
            for g,rs in compgroups.items():
                drops=[t for t in rs if t['decision'][point]=='DROP'];kd=sum(t['value'] is not None for t in drops)
                independent_tables['DROP_COMPOSITION.csv'].append({'cohort':cohort,'point':point,'bucket':g,'diagnostic_labels':LEGACY,
                    'DROP_N':len(drops),'all_DROP_N':all_drop,'share_of_all_DROP_pct':pct(len(drops),all_drop),
                    'known_R_DROP_N':kd,'all_known_R_DROP_N':known_drop,'aux_share_of_known_R_DROP_pct':'N/A' if g=='R_UNKNOWN' else pct(kd,known_drop)})
            for g,rs in {**groups,**cumulative}.items():
                n_total,p_total,_=independent_mass(rs)
                parts={'ALL':rs,'KEEP':[t for t in rs if t['decision'][point]=='KEEP'],
                       'DROP':[t for t in rs if t['decision'][point]=='DROP'],
                       'DECISION_UNKNOWN':[t for t in rs if t['decision'][point]=='UNKNOWN']}
                check(len(parts['KEEP'])+len(parts['DROP'])+len(parts['DECISION_UNKNOWN'])==len(rs),'MASS_MASK_COUNT:'+cohort+'/'+point+'/'+g)
                check(tuple(sum(independent_mass(parts[n])[i] for n in ['KEEP','DROP','DECISION_UNKNOWN']) for i in range(3))==independent_mass(rs),
                    'MASS_PARTITION_ADDITIVITY:'+cohort+'/'+point+'/'+g)
                for partition,ls in parts.items():
                    neg,pos,net=independent_mass(ls);kn=sum(t['value'] is not None for t in ls)
                    independent_tables['RETURN_MASS_DECOMPOSITION.csv'].append({'cohort':cohort,'point':point,'group':g,'diagnostic_labels':LEGACY,
                        'decision_partition':partition,'group_N':len(rs),'partition_N':len(ls),'R_known_N':kn,'R_unknown_N':len(ls)-kn,
                        'negative_mass_abs_pp':neg,'positive_mass_pp':pos,'net_R_pp':net,
                        'negative_mass_share_of_group_pct':pct(neg,n_total),'positive_mass_share_of_group_pct':pct(pos,p_total),
                        'mass_unit':'pp-sum','mass_scope':'SAVED_KNOWN_R_ONLY','capitalImprovement':'NOT_EVALUATED'})
            matched=[t for t in ss if t['value'] is not None and t['decision'][point]!='UNKNOWN']
            kp=[t for t in matched if t['decision'][point]=='KEEP'];dp=[t for t in matched if t['decision'][point]=='DROP']
            total=independent_mass(matched)[2];kept=independent_mass(kp)[2];dropped=independent_mass(dp)[2]
            check(kept-total==-dropped,'ACCOUNTING_IDENTITY:'+cohort+'/'+point)
            independent_tables['ACCOUNTING_IDENTITY_CHECK.csv'].append({'cohort':cohort,'point':point,'diagnostic_labels':LEGACY,
                'R_and_decision_known_N':len(matched),'excluded_R_unknown_N':sum(t['value'] is None for t in ss),
                'excluded_R_known_decision_unknown_N':sum(t['value'] is not None and t['decision'][point]=='UNKNOWN' for t in ss),
                'R_sum_KEEP_pp':kept,'R_sum_ALL_KNOWN_DECISION_pp':total,'negative_R_sum_DROP_pp':-dropped,
                'KEEP_minus_ALL_pp':kept-total,'identity_residual_pp':kept-total+dropped,'identity_PASS':True})
    numeric_fields={'N','KEEP','DROP','decision_UNKNOWN','R_known_N','R_unknown_N','share_R_known_pct','share_all_entries_pct',
        'distinct_sessions','distinct_symbols','R_median_pct','R_sum_pp','negative_mass_abs_pp','positive_mass_pp',
        'KEEP_rate_pct','DROP_rate_pct','decision_coverage_pct','DROP_N','all_DROP_N','share_of_all_DROP_pct','known_R_DROP_N',
        'all_known_R_DROP_N','aux_share_of_known_R_DROP_pct','group_N','partition_N','net_R_pp','negative_mass_share_of_group_pct',
        'positive_mass_share_of_group_pct','R_and_decision_known_N','excluded_R_unknown_N','excluded_R_known_decision_unknown_N',
        'R_sum_KEEP_pp','R_sum_ALL_KNOWN_DECISION_pp','negative_R_sum_DROP_pp','KEEP_minus_ALL_pp','identity_residual_pp'}
    compared={}
    for file,expected in independent_tables.items():
        with (pub/file).open(encoding='utf-8',newline='') as f: actual=list(csv.DictReader(f))
        key_fields=['cohort','point','bucket'] if 'bucket' in expected[0] and 'point' in expected[0] else ['cohort','bucket'] if 'bucket' in expected[0] else ['cohort','point','group'] if 'group' in expected[0] else ['cohort','point']
        if 'decision_partition' in expected[0]: key_fields+=['decision_partition']
        ekeys=[tuple(str(r[k]) for k in key_fields) for r in expected]
        akeys=[tuple(r[k] for k in key_fields) for r in actual]
        check(len(ekeys)==len(set(ekeys)),'EXPECTED_KEYS_UNIQUE:'+file)
        check(len(akeys)==len(set(akeys)),'OUTPUT_KEYS_UNIQUE:'+file)
        check(set(ekeys)==set(akeys),'OUTPUT_KEYS_COMPLETE:'+file)
        amap=dict(zip(akeys,actual));cell_n=0
        for key,exp in zip(ekeys,expected):
            act=amap.get(key)
            if act is None: continue
            for field,val in exp.items():
                if field in numeric_fields and str(val)!='N/A':
                    try: ok=D(act[field])==D(val)
                    except (KeyError,InvalidOperation):ok=False
                else:ok=act.get(field)==str(val)
                check(ok,'OUTPUT_VALUE:'+file+'/'+str(key)+'/'+field);cell_n+=1
        compared[file]={'rows':len(expected),'cells_compared':cell_n}
    # Independently derived raw-row masks are also checked against the private join.
    with (private/'ENTRY_R_DECISION_JOIN.jsonl').open(encoding='utf-8') as f: joined=[json.loads(l) for l in f]
    jm={t['entry_id']:t for t in joined}
    check(len(jm)==len(joined)==322 and set(jm)==expected_ids,'PRIVATE_JOIN_ID_SET')
    for t in data:
        x=jm[t['id']]
        check(x['bucket']==t['band'],'PRIVATE_JOIN_BUCKET:'+t['id'])
        check(x['canonical_block']==t['block'],'PRIVATE_JOIN_BLOCK:'+t['id'])
        check(x['symbol']==t['symbol'],'PRIVATE_JOIN_SYMBOL:'+t['id'])
        check(x['decisions']==t['decision'],'PRIVATE_JOIN_DECISIONS:'+t['id'])
        check(x['R_reason']==t['reason'],'PRIVATE_JOIN_R_REASON:'+t['id'])
        check(x['R_pct_exact']=='N/A' if t['value'] is None else D(x['R_pct_exact'])==t['value'],'PRIVATE_JOIN_R_EXACT:'+t['id'])
    receipt={'status':'PASS' if not errors else 'FAIL','author_relation':'same author / separate implementation; not third-party blind audit',
        'computation':'Decimal native fraction * 100; independent interval membership; original source IDs/R/decisions re-read',
        'primary_bucket_imported':False,'primary_aggregates_used_as_computation_input':False,
        'checks':checks,'mismatch_N':len(errors),'errors':errors,'compared_tables':compared,
        'cohort_N':322,'R_known_N':316,'R_unknown_N':6,'saved_operating_points':6,'protected_opened':0,
        'new_fit':0,'inference':0,'threshold_application':0,'capital_evaluated':False}
    (pub/'INDEPENDENT_AUDIT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))
    if errors: raise SystemExit(1)

if __name__=='__main__':main()
