"""P2b: eight fixed past-only screens. No fit, rescore, historical policy path or retuning."""
from context import *
from fractions import Fraction
from decimal import Decimal
from datetime import datetime, timedelta
from collections import Counter
import numpy as np

TARGETS=('U5','U10','U3','Weak','realized_nonpositive')

def f(x):return Fraction(Decimal(str(x)))
def fs(x):return str(x.numerator)+'/'+str(x.denominator)

def maturity(teacher):
    """Conservative semantic label-availability bound under the inherited closed-bar contract."""
    if not teacher or not teacher.get('capture_complete') or teacher.get('strictly_after_entry_before_1520') is not True:
        return None,'POTENTIAL_HORIZON_OR_CAPTURE_UNCERTIFIED'
    if teacher.get('execution_status')!='COMPLETE' or teacher.get('release_minute') is None or not teacher.get('source_lineage'):
        return None,'REALIZED_OUTCOME_OR_SOURCE_UNKNOWN'
    if not 0<=teacher['release_minute']<=931 or teacher.get('source_minute') is None:
        return None,'LABEL_RELEASE_BOUND_UNCERTIFIED'
    # The certified Potential horizon ends strictly before15:20; frozen/EOD settlement
    # finishes by15:31. Use15:31 for BOTH labels, never a guessed actual provider arrival.
    return teacher['session']+'T15:31:00+09:00',None

def join_row(row,teachers,outcomes,first_session):
    key=row['entry_id'];t=teachers.get(key);o=outcomes.get(key)
    available,reason=maturity(t)
    rec=row|{'label_maturity_bound':available,'known':False,'unknown_reason':reason,
        'maturity_contract':'inherited assumed closed-bar/session-complete contract, not actual historical feed receipt'}
    if available is None:return rec
    cutoff=first_session+'T09:00:00+09:00'
    if datetime.fromisoformat(available)>=datetime.fromisoformat(cutoff):
        return rec|{'unknown_reason':'LABEL_NOT_MATURED_BEFORE_BLOCK'}
    if t['session']!=row['session'] or not o or o.get('frozen_execution_status')!='COMPLETE':
        return rec|{'unknown_reason':'IDENTITY_OR_ORIGINAL_OUTCOME_UNKNOWN'}
    if o.get('potential_pct') is None or o.get('frozen_realized_net_return_cell') is None:
        return rec|{'unknown_reason':'TARGET_UNKNOWN'}
    potential=f(o['potential_pct']);net=f(o['frozen_realized_net_return_cell'])
    if t.get('potential_return') is None or t.get('realized_net_return') is None:
        return rec|{'unknown_reason':'ORIGINAL_TEACHER_TARGET_UNKNOWN'}
    assert f(t['realized_net_return'])==net,'SAVED_NET_RETURN_COPY_MISMATCH'
    # Potential decimal in the authority is the original saved potential cell *100.
    assert f(t['potential_return'])*100==potential,'SAVED_POTENTIAL_COPY_MISMATCH'
    return rec|{'known':True,'unknown_reason':None,'potential_pct_exact':fs(potential),'net_return_exact':fs(net),
        'targets':{'U5':potential>=5,'U10':potential>=10,'U3':potential>=3,'Weak':potential<2,'realized_nonpositive':net<=0},
        'label_source_lineage':t['source_lineage'],'teacher_source_minute':t['source_minute'],'teacher_release_minute':t['release_minute']}

def cohort(records):
    known=[r for r in records if r['known']]
    counts={k:sum(r['targets'][k] for r in known) for k in TARGETS}
    return {'total_N':len(records),'known_N':len(known),'unknown_N':len(records)-len(known),
        'distinct_sessions':len({r['session'] for r in records}),'known_distinct_sessions':len({r['session'] for r in known}),
        'distinct_blocks':len({r['block'] for r in records}),'target_counts':counts,
        'target_denominators':{k:len(known) for k in TARGETS},
        'rates_exact':{k:fs(Fraction(v,len(known))) if known else None for k,v in counts.items()},
        'unknown_reasons':dict(Counter(r['unknown_reason'] for r in records if not r['known']))}

def screen(block,frame,S,F,bootstrap_counts=None):
    """Only already restricted prior rows. Used by synthetic cases without market/source imports."""
    sc,fc=cohort(S),cohort(F);complete=not sc['unknown_N'] and not fc['unknown_N']
    need={'S_N':max(0,10-sc['total_N']),'S_sessions':max(0,10-sc['distinct_sessions']),
          'S_blocks':max(0,2-sc['distinct_blocks']),'F_N':max(0,20-fc['total_N']),
          'F_sessions':max(0,8-fc['distinct_sessions']),'S_U5':max(0,2-sc['target_counts']['U5']),
          'S_U10':max(0,1-sc['target_counts']['U10'])}
    H={'H0':complete,'H1':all(v==0 for v in need.values()),'H2':False,'H3':False,'H4':False,'H5':False,'H6':False}
    metrics={'mean_S_net_return_exact':None,'mean_S_net_return':None,'leave_one_session_means_exact':{},
        'bootstrap_CI95':None,'bootstrap_valid_N':0,'H5_details':{},'H6_details':{}}
    boot_rows=[];boot_values=[]
    if complete and S:
        returns={r['session']:Fraction(r['net_return_exact']) for r in S}
        assert len(returns)==len(S),'MORE_THAN_ONE_PROPOSAL_PER_SESSION'
        total=sum(returns.values(),Fraction(0));avg=total/len(S)
        metrics['mean_S_net_return_exact']=fs(avg);metrics['mean_S_net_return']=float(avg);H['H2']=avg>0
        loo={s:fs((total-v)/(len(S)-1)) for s,v in returns.items()} if len(S)>1 else {}
        metrics['leave_one_session_means_exact']=loo;H['H4']=bool(loo) and all(Fraction(v)>0 for v in loo.values())
        assert set(returns).issubset(frame)
        x=np.array([float(returns.get(s,Fraction(0))) for s in frame],dtype=np.float64)
        generator=np.random.Generator(np.random.PCG64(571005310+block)) if bootstrap_counts is None else None
        for i in range(1999):
            if bootstrap_counts is None:
                draw=generator.integers(0,len(frame),size=len(frame));counts=np.bincount(draw,minlength=len(frame))
            else:counts=np.array(bootstrap_counts[i],dtype=np.int64)
            assert int(sum(counts))==len(frame)
            stat=float(np.dot(counts,x)/len(frame));assert np.isfinite(stat)
            boot_rows.append({'block':block,'resample':i,'frame':frame,'counts':counts.tolist(),'mean':stat})
            boot_values.append(stat)
        lo,hi=np.percentile(boot_values,[2.5,97.5],method='linear')
        metrics.update(bootstrap_CI95=[float(lo),float(hi)],bootstrap_valid_N=len(boot_values),
            frame_N=len(frame),nonzero_proposal_session_N=len(S),empty_proposal_session_N=len(frame)-len(S),
            session_proxy_values=[{'session':s,'net_return_exact':fs(returns.get(s,Fraction(0)))} for s in frame])
        H['H3']=bool(len(boot_values)==1999 and lo>0)
        if F:
            for target in ('U5','U10','U3'):
                a,b=sc['target_counts'][target],fc['target_counts'][target]
                ok=a*len(F)>=b*len(S)
                metrics['H5_details'][target]={'S_positive_N':a,'S_den':len(S),'F_positive_N':b,'F_den':len(F),'pass':ok}
            H['H5']=all(d['pass'] for d in metrics['H5_details'].values())
            for target in ('Weak','realized_nonpositive'):
                a,b=sc['target_counts'][target],fc['target_counts'][target]
                ok=a*len(F)<=b*len(S)
                metrics['H6_details'][target]={'S_positive_N':a,'S_den':len(S),'F_positive_N':b,'F_den':len(F),'pass':ok}
            H['H6']=all(d['pass'] for d in metrics['H6_details'].values())
    if block==1:
        H['H0']=False;status='COLD_ABSTAIN'
    elif not complete:status='UNKNOWN_ABSTAIN'
    elif all(H.values()):status='PAST_QUALIFIED'
    else:status='PAST_SCREEN_FAIL'
    return {'block':block,'status':status,'PAST_QUALIFIED':status=='PAST_QUALIFIED','Hi':H,'S':sc,'F':fc,
        'support_shortfalls':need,'failed_Hi':[k for k,v in H.items() if not v],
        'metrics':metrics,'frame_sessions':frame,'frame_hash':digest(frame),'S_ids':[r['entry_id'] for r in S],
        'F_ids':[r['entry_id'] for r in F],'S_hash':digest(S),'F_hash':digest(F),
        'bootstrap':{'seed':571005310+block,'generator':'PCG64','resamples':1999,'method':'linear','unit':'session_proxy',
           'interpretation':'standalone proposal support; not portfolio daily return'}},boot_rows

def main():
    freeze=json.loads((OUT/'PAST_PROPOSAL_MANIFEST.json').read_text())
    receipt=json.loads((OUT/'receipts/P2A_MANIFEST_ACTUAL_GET.json').read_text())
    assert receipt['actual_GET_before_new_label_join'] and receipt['manifest_body']==freeze
    sp=PRIVATE/'PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz';assert sha(sp)==freeze['S_artifact_sha256']
    S=[json.loads(s) for s in gzip.open(sp,'rt')];assert digest(S)==freeze['S_canonical_identity_hash']
    split=read('split');block_of={s:b['block'] for b in split['blocks'] for s in b['test']}
    F=[{'entry_id':r['entry_id'],'session':r['session'],'block':block_of[r['session']],
        'quantity':r['quantity'],'pnl':r['pnl'],'trade_source':'V5_NATIVE_ACTUAL_FUNDED'} for r in read('native_trades')]
    # New outcome joins begin only after the above S identity/hash actual-GET check.
    teachers={r['entry_id']:r for r in read('teachers')};outcomes=read('outcomes')
    all_tables=[];all_joined=[];all_counts=[];dependencies=[]
    for b in split['blocks']:
        number=b['block'];first=min(b['test']);frame=[s for s in split['OOF38'] if block_of[s]<number]
        pastS=[r for r in S if r['block']<number];pastF=[r for r in F if r['block']<number]
        assert all(r['session'] in frame for r in pastS+pastF)
        js=[join_row(r,teachers,outcomes,first) for r in pastS]
        jf=[join_row(r,teachers,outcomes,first) for r in pastF]
        table,counts=screen(number,frame,js,jf)
        table.update(first_current_block_session=first,table_available_before=first+'T09:00:00+09:00',
            original_prior_blocks=list(range(1,number)),original_block_split_hash=sha(INPUT/ROLES['split']),
            proposal_manifest_sha256=sha(OUT/'PAST_PROPOSAL_MANIFEST.json'),
            original_input_hashes={role:sha(INPUT/ROLES[role]) for role in ('packet','reference32','proposals','teachers','outcomes','native_trades')},
            current_or_future_outcome_inputs=0,warmup_OOF_samples=0,training_resub_OOF_samples=0)
        all_tables.append(table);all_counts+=counts
        for label,joined in [('S',js),('F',jf)]:
            for r in joined:
                all_joined.append({'target_block':number,'cohort':label,**r})
                dependencies.append({'target_block':number,'entry_id':r['entry_id'],'original_OOF_block':r['block'],
                    'session':r['session'],'label_maturity_bound':r['label_maturity_bound'],'known':r['known'],
                    'prior_block_only':r['block']<number,'matured_before_current_block':r['known']})
    counts_path=gzsave('PAST_BOOTSTRAP_SESSION_COUNTS.jsonl.gz',all_counts)
    join_path=gzsave('PAST_SUPPORT_JOINED_ROWS.jsonl.gz',all_joined)
    dag_path=gzsave('PAST_TEMPORAL_DEPENDENCIES.jsonl.gz',dependencies)
    save('TEMPORAL_DAG.json',{'schema':'V5_R_PAST_OOF_QUALIFICATION_DAG_V1','exact_jst':now(),
        'edges':[['original past fitted head','saved original-block OOF score'],['completed-training references','original-block rational rank'],
          ['original native snapshot plus score/rank','outcome-blind first fundable S identity'],
          ['matured prior-block outcome plus fixed S/F','past-only qualification table b'],['table b plus current causal state','current action b']],
        'forbidden_edges':[['current/future outcome','table b'],['training resubstitution labels','past OOF performance sample'],
          ['future execution availability','BUY selection'],['protected100 IDs','runtime policy']],
        'dependency_artifact':'private/PAST_TEMPORAL_DEPENDENCIES.jsonl.gz','dependency_sha256':sha(dag_path),
        'label_maturity_basis':{'potential':'saved teachers strictly_after_entry_before_1520=True, capture_complete=True',
           'realized':'saved COMPLETE, source lineage and release_minute<=931; Frozen EXIT/EOD original execution module',
           'conservative_bound':'original session15:31 assumed source availability, before later block09:00',
           'existing_completed_past_certificate':'R1 CAUSAL_SOURCE_REVIEW + Bridge TEMPORAL_DEPENDENCY_DAG hash/body reuse',
           'actual_historical_feed_delivery':'UNKNOWN; no independent provider timing claim'},
        'second_stage_outcome_based_artifact':True,'new_fit':0,'fresh_OOS_claim':False})
    qualification={'schema':'V5_R_PAST_QUALIFICATION_BY_BLOCK_V1','exact_jst':now(),'tables':all_tables,
        'PAST_QUALIFIED_block_N':sum(t['PAST_QUALIFIED'] for t in all_tables),
        'table_generation_N':len(all_tables),'policy_cutoffs_unchanged':True,
        'bootstrap_counts_artifact':'private/PAST_BOOTSTRAP_SESSION_COUNTS.jsonl.gz','bootstrap_counts_sha256':sha(counts_path),
        'joined_artifact':'private/PAST_SUPPORT_JOINED_ROWS.jsonl.gz','joined_sha256':sha(join_path),
        'proposal_collection_population_N':len(S),'new_portfolio_replays':0,
        'primary_status_if_pre_main_pass':'PAST_SUPPORT_NOT_ESTABLISHED' if not any(t['PAST_QUALIFIED'] for t in all_tables) else 'CONTINUE_TO_PREMAIN_FIRST_DIVERGENCE'}
    save('PAST_QUALIFICATION_BY_BLOCK.json',qualification)
    checkpoint('P2','PAST_TABLES_FIXED',{'table_N':8,'qualified_block_N':qualification['PAST_QUALIFIED_block_N'],
         'by_block':[{'block':t['block'],'S_N':t['S']['total_N'],'F_N':t['F']['total_N'],'failed_Hi':t['failed_Hi']} for t in all_tables]},
         'Independent quantity/table/bootstrap verification and all28 synthetic cases; no Replay before all pre-main gates')
    print(json.dumps({'qualified_block_N':qualification['PAST_QUALIFIED_block_N'],
      'tables':[{'block':t['block'],'status':t['status'],'S_N':t['S']['total_N'],'F_N':t['F']['total_N'],
       'mean':t['metrics']['mean_S_net_return'],'CI95':t['metrics']['bootstrap_CI95'],'fail':t['failed_Hi'],
       'unknown_S':t['S']['unknown_N'],'unknown_F':t['F']['unknown_N']} for t in all_tables]}))

if __name__=='__main__':main()
