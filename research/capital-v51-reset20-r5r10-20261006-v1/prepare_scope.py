"""Freeze calendar windows and diagnostic masks before any result computation."""
from datetime import date,timedelta
from collections import Counter
from decimal import Decimal as D
from io_utils import *

def main():
    binding=read(INPUTS/'RESOLVED_INPUTS.json');split=read(INPUTS/'split')
    stream=rows(INPUTS/'candidate_stream');runtime=rows(INPUTS/'core_runtime');books=rows(INPUTS/'books')
    assert sha(INPUTS/'core_runtime')=='827abcf716c9203a70bc766783948a6be3cee3428abf6a772d1c3495096fd197'
    assert sha(INPUTS/'split')=='e83291b8706c48a4e496739219f1a645246b73be28f2195bebfaeb6614a12274'
    assert sorted({r['session'] for r in runtime})==split['all58']
    assert sorted({r['session'] for r in stream})==split['OOF38']
    assert len({r['entry_id'] for r in stream})==len(stream)
    block={s:b['block'] for b in split['blocks'] for s in b['test']}
    assert all(r['block']==block[r['session']] for r in stream)
    table=read(INPUTS/'arrival')
    assert all(table[str(b['block'])]['training_sessions']==b['train'] and max(b['train'])<min(b['test']) for b in split['blocks'])
    holidays={'2025-07-21':'海の日','2025-08-11':'山の日'}
    authority=[{'url':'https://www.jpx.co.jp/faq/others_general.html','role':'TSE cash equities closed weekends/national holidays','retrieval':'actual search 2026-10-06 JST'}, {'url':'https://eco.mtk.nao.ac.jp/koyomi/yoko/2025/rekiyou251.html','role':'Official 2025 national holiday dates'}]
    all_days=[];start=date.fromisoformat(split['all58'][0]);end=date.fromisoformat(split['all58'][-1]);cur=start
    cands=Counter(r['session'] for r in stream);rt=Counter(r['session'] for r in runtime);bd=Counter(b['session'] for b in books)
    for n in range((end-start).days+1):
        cur=start+timedelta(days=n);s=cur.isoformat();closed=cur.weekday()>=5 or s in holidays
        status='MARKET_CLOSED' if closed else 'COMPLETE_WITH_CANDIDATES' if s in rt else 'UNKNOWN_REASON'
        all_days.append({'session':s,'market_session':not closed,'status':status,'runtime_candidate_N':rt[s],'OOF_candidate_N':cands[s],'book_N':bd[s],'completeness_basis':'Inherited authenticated fixed candidate stream and execution books' if s in rt else 'No completed zero-entry/source-universe receipt found' if not closed else holidays.get(s,'WEEKEND')})
    audit_paths=[]
    for p in sorted((ROOT/'sources/coverage_meta').glob('*.json')):
        audit_paths.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'conclusion':'Metadata checked; no end-to-end Frozen Entry zero receipt for both missing dates'})
    calendar=[r['session'] for r in all_days if r['market_session'] and split['OOF38'][0]<=r['session']<=split['OOF38'][-1]]
    statuses={r['session']:r['status'] for r in all_days};windows=[]
    for i in range(len(calendar)-19):
        sessions=calendar[i:i+20];missing=[s for s in sessions if statuses[s] not in ['COMPLETE_WITH_CANDIDATES','COMPLETE_ZERO_ENTRY']]
        windows.append({'window_id':f'W{i+1:02d}','mode':'RESET20_CASH1M','sessions':sessions,'start_session':sessions[0],'end_session':sessions[-1],'calendar_contiguous':True,'coverage_complete':not missing,'coverage_blocked_sessions':missing})
    obj={'schema':'ARK_COVERAGE_WINDOWS_V1','exact_jst':now(),'fixed_before_results':True,'calendar_authority':authority,'market':'TSE CASH EQUITIES','calendar_method':'Weekdays excluding official Japanese national holidays; no Entry-derived calendar','source_period':[split['all58'][0],split['all58'][-1]],'OOF_period':[calendar[0],calendar[-1]],'old_split_preserved':True,'training_sessions_N':20,'old_OOF_sessions_N':38,'calendar_OOF_sessions_N':len(calendar),'days':all_days,'focused_missing':[{ 'session':s,'status':statuses[s],'source_evidence':'2025-07-14 is mentioned in inherited V4 manifest, insufficient to prove Frozen Entry zero or pipeline omission' if s=='2025-07-14' else 'No authoritative source completeness/omission proof recovered','needed':'Day-specific source/universe coverage + completed frozen Selector/Entry processing/zero or exclusion receipt'} for s in ['2025-07-11','2025-07-14']],'searched_paths':audit_paths,'archive_metadata_index_sha256':sha(INPUTS/'ARCHIVE_MEMBER_INDEX.json'),'search_closed':True,'window_N':len(windows),'coverage_complete_window_N':sum(w['coverage_complete'] for w in windows),'windows':windows,'selected_session_diagnostic':'NOT_NEEDED_NO_GAP_WINDOW_PROMOTION','statistical_independence':False}
    save(OUT/'COVERAGE_AND_WINDOWS.json',obj)
    contract={'schema':'ARK_R_LABEL_CONTRACT_V1','exact_jst':now(),'materializations_max':1,'evaluation_only':True,'unit':'ratio','reference_quantity':100,'formula':'sell_credit / buy_debit - 1','classification_exact':'Fraction/Decimal original debit and credit; R5 credit*100>=debit*105; R10 credit*100>=debit*110; Loser credit<=debit','R5_boundary_inclusive':True,'R10_boundary_inclusive':True,'unknown':'null; never false/Loser','U_authority':'Existing teachers.potential_return and label_bigwinner5/10; strictly later actual High before15:20/raw Entry reference; alias only','capital_EXIT':'Native frozen_execution if release<=920, otherwise native EOD source, including native source/lineage fail-closed contract','structural_EXIT_return':'Preserve separately; not relabeled as Capital return','BUY_factor':'1.0005','SELL_factor':'0.9995','commission':0,'fee_deduction':'Effective prices already include cost; no second deduction','eligibility_mask':'entry_minute<920, finite positive bound raw reference, valid entry_actual_source with same session/minute and raw O matching reference. Excludes no future source or outcome','rank_pass_mask':'native admission/ML>=1','score_heads':['pP/MOVE_P5','MOVE_U2','MOVE_U3','MRET'],'direction':'Original higher score direction for all heads','score_buckets':'Existing training strict-less r/rM rank, split at inherited1/2; V5 native S/A/B/C separate; no test quantiles','score_mask':'known Capital R label AND matched existing precomputed OOF expert score; census/eligible/rankpass masks separately','aggregation':'Pooled unique-Entry AUROC + fixed forward block and session AUROC/rates, arithmetic mean available session AUROC; no bootstrap or independent-window CI','score_calibration_claim':False,'MRET_absolute_loss_defense':'INCONCLUSIVE','quantity_contract':'Inherited raw price x effective cost x quantity, no liquidity price impact or quantity-varying commission; historical liquidity remains diagnostic','source_hashes':{k:v['sha256'] for k,v in binding['resolved'].items()},'exit_policy_hash':sha(REPO/'research/capital-v5-max3-slot-intelligence-20261004-v1/execution.py')}
    save(OUT/'R_LABEL_CONTRACT.json',contract)
    update=read(OUT/'START_AND_INPUT_BINDING.json');update['resolved_inputs']=binding;update['split_and_schedule_verified']=True
    save(OUT/'START_AND_INPUT_BINDING.json',update)
    print({'planned_windows':len(windows),'coverage_complete':sum(w['coverage_complete'] for w in windows),'missing_days':[r['session'] for r in all_days if r['status']=='UNKNOWN_REASON']})

if __name__=='__main__':main()
