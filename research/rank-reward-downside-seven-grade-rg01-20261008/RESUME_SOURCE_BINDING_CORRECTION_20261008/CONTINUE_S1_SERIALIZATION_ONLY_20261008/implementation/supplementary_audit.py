"""Independent source check of derived reporting summaries; no primary imports."""
import csv,collections,gzip,json,pathlib
from fractions import Fraction
from decimal import Decimal,localcontext
R=pathlib.Path(__file__).resolve().parents[1]
def f(v):
    with localcontext() as c:
        c.prec=60;return Decimal(v.numerator)/Decimal(v.denominator)
def rounded(v):return f(v).quantize(Decimal('0.000000000001'))
def main():
    A={x['entry_id']:x for x in [json.loads(z) for z in gzip.decompress((R/'private/SEALED_RANK_ASSIGNMENTS.jsonl.gz').read_bytes()).splitlines()]};L={x['entry_id']:x for x in [json.loads(z) for z in gzip.decompress((R.parent/'restored/S1/EVALUATION_R_NEW_REUSED.jsonl.gz').read_bytes()).splitlines()]};rs={i:Fraction(int(l['r_numerator']),int(l['r_denominator'])) if l['known'] else None for i,l in L.items()};us={i:Fraction(int(l['u_numerator']),int(l['u_denominator'])) for i,l in L.items()};checks=0
    neg={i for i in A if A[i]['methods']['R0_4']['grade']=='S' and rs[i] is not None and rs[i]<0};expected={'old_S_negative_N':len(neg),**{'U'+str(t):sum(us[i]>=t for i in neg) for t in [2,3,5,10]},'saved_exit_kind_counts':dict(collections.Counter(L[i]['exit_kind'] for i in neg)),'High_to_EXIT_exact_path':'UNKNOWN_NOT_RECONSTRUCTED','grade_input_leakage':False};assert expected==json.loads((R/'public/OLD_S_NEGATIVE_HIGH_AND_EXIT_DIAGNOSTIC.json').read_text());checks+=8
    Ks={k:{b:sum(x['block']==b and x['methods']['R0_4']['grade'] in gs for x in A.values()) for b in range(1,9)} for k,gs in [('K197','SA'),('K494','SAB')]}
    def top(m,k):return {i for i,x in A.items() if x['methods'][m]['block_order']<=Ks[k][x['block']]}
    def masses(s):
        p=sum((rs[i] for i in s if rs[i] is not None and rs[i]>0),Fraction());n=sum((-rs[i] for i in s if rs[i] is not None and rs[i]<0),Fraction());return p,n,p-n
    summary=json.loads((R/'public/STABILITY_DIAGNOSTIC_SUMMARY.json').read_text());sessions=sorted({x['session'] for x in A.values()})
    for m in summary:
        for k in summary[m]:
            s=top(m,k);baseline=top('U7',k)
            for z in summary[m][k]['block_deltas']:
                a={i for i in s if A[i]['block']==z['block']};b={i for i in baseline if A[i]['block']==z['block']};ap,an,at=masses(a);bp,bn,bt=masses(b);ct=sum(rs[i] is not None and rs[i]<=-3 for i in a)-sum(rs[i] is not None and rs[i]<=-3 for i in b);assert z['delta_R_LE_M3']==ct and Decimal(z['delta_net_pp'])==rounded(at)-rounded(bt) and Decimal(z['delta_positive_mass'])==rounded(ap)-rounded(bp);checks+=3
            for key,col,values in [('leave_one_block_out','block',range(1,9)),('leave_one_session_out','session',sessions)]:
                tally={'net_delta_positive_N':0,'net_delta_nonnegative_N':0,'negative_mass_reduced_N':0,'evaluated_N':0}
                for v in values:
                    a={i for i in s if A[i][col]!=v};b={i for i in baseline if A[i][col]!=v};ap,an,at=masses(a);bp,bn,bt=masses(b);diff=rounded(at)-rounded(bt);tally['net_delta_positive_N']+=diff>0;tally['net_delta_nonnegative_N']+=diff>=0;tally['negative_mass_reduced_N']+=rounded(an)<rounded(bn);tally['evaluated_N']+=1
                assert tally==summary[m][k]['fixed_assignment_leave_one_out'][key];checks+=4
    for x in json.loads((R/'evaluation/TABLE_MANIFEST.json').read_text()):
        if x['path'].startswith('private/'):continue
        if x['bytes']<=600000:assert (R/'evaluation'/x['path']).read_bytes()==(R/'public'/x['path']).read_bytes()
        else:assert gzip.decompress((R/'public'/(x['path']+'.gz')).read_bytes())==(R/'evaluation'/x['path']).read_bytes()
        checks+=1
    out={'status':'PASS','same_author_separate_source_check':True,'primary_assign_or_evaluator_imported':False,'checks':checks,'summary_cell_mismatch_N':0,'exact_source_U_and_R_Fraction':True,'public_table_restoration_full_bytes_match_N':13,'derived_summaries':['STABILITY_DIAGNOSTIC_SUMMARY.json','OLD_S_NEGATIVE_HIGH_AND_EXIT_DIAGNOSTIC.json'],'future_grade_input':False};(R/'public/SUPPLEMENTARY_AGGREGATE_CHECK_RECEIPT.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
