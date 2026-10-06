"""Raw-price independent accounting and paired original-window comparison."""
import sys, csv, importlib.util
from collections import defaultdict,Counter
from decimal import Decimal as D
from statistics import mean,median
from rneg_io import *
sys.path.insert(0,str(REPO/'research/capital-v51-reset20-r5r10-20261006-v1'))
spec=importlib.util.spec_from_file_location('independent_old_accounting',REPO/'research/capital-v51-reset20-r5r10-20261006-v1/accounting_audit.py')
accounting=importlib.util.module_from_spec(spec);spec.loader.exec_module(accounting)

def stats(trades):
    negative=[t for t in trades if D(t['pnl'])<0];positive=[t for t in trades if D(t['pnl'])>0]
    return {'purchase_N':len(trades),'negative_N':len(negative),'positive_N':len(positive),
        'negative_rate':len(negative)/len(trades) if trades else None,
        'negative_pnl_abs_jpy':str(sum((-D(t['pnl']) for t in negative),D(0))),
        'positive_pnl_jpy':str(sum((D(t['pnl']) for t in positive),D(0))),
        'net_pnl_jpy':str(sum((D(t['pnl']) for t in trades),D(0))),
        'RN_tail_loss':{f'RN{k}':{'N':sum(D(t['credit'])/D(t['debit'])-1<=-D(k)/100 for t in trades),
            'loss_jpy':str(sum((-D(t['pnl']) for t in trades if D(t['credit'])/D(t['debit'])-1<=-D(k)/100),D(0)))} for k in (1,3,5,10)}}

def main():
    candidate=read(OUT/'DEFENSE_RESET20_RESULT.json');control=read(REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1/V5_RESET20_RESULT.json')
    control_map={w['window_id']:w for w in control['windows']};stream={r['entry_id']:r for r in rows(SPECTRUM/'source/candidate_stream.jsonl.gz')}
    books={r['entry_id']:r for r in rows(Q/'MARKET_TEACHER_BOOK.jsonl.gz')};labels={r['entry_id']:r for r in rows(PRIVATE/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz')}
    actions={r['entry_id']:r for r in rows(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz')}
    audits=[];paired=[];deltas=[];all_a=[];all_b=[];all_windows=[]
    root=PRIVATE/'runs/V5_RNEG_DEFENSE_V1'
    for w in candidate['windows']:
        wid=w['window_id'];a=control_map[wid];assert a['sessions']==w['sessions'] and a['coverage_complete']==w['coverage_complete']
        audit=accounting.audit_window(w,root/wid,stream,books,labels);audits.append(audit)
        row={'window_id':wid,'start_session':w['start_session'],'end_session':w['end_session'],'V5_status':a['status'],'Defense_status':w['status'],
             'V5_final_jpy':a['final_cash_for_primary'],'Defense_final_jpy':w['final_cash_for_primary'],
             'paired_complete':a['status']==w['status']=='COMPLETE','delta_jpy':None}
        if row['paired_complete']:
            old=rows(RESET/'runs/V5_RESET20'/wid/'TRADES.jsonl.gz');new=rows(root/wid/'TRADES.jsonl.gz')
            oldm={t['entry_id']:t for t in old};newm={t['entry_id']:t for t in new}
            assert len(oldm)==len(old) and len(newm)==len(new)
            row.update(delta_jpy=str(D(w['final_cash_for_primary'])-D(a['final_cash_for_primary'])),V5=stats(old),Defense=stats(new),
                V5_maxDD=a['max_drawdown'],Defense_maxDD=w['max_drawdown'],V5_utilization=a['utilization_mean'],Defense_utilization=w['utilization_mean'],
                V5_occupancy=a['occupancy_mean'],Defense_occupancy=w['occupancy_mean'])
            assert D(w['final_cash_for_primary'])==D('1000000')+sum((D(t['pnl']) for t in new),D(0))
            for key in sorted(set(oldm)|set(newm)):
                x=oldm.get(key);y=newm.get(key)
                category='COMMON_QUANTITY_CHANGE' if x and y and x['quantity']!=y['quantity'] else 'COMMON_IDENTICAL' if x and y else 'V5_ONLY' if x else 'DEFENSE_ONLY'
                deltas.append({'window_id':wid,'entry_id':key,'category':category,'V5_quantity':x['quantity'] if x else 0,'Defense_quantity':y['quantity'] if y else 0,
                    'V5_pnl':x['pnl'] if x else '0','Defense_pnl':y['pnl'] if y else '0',
                    'pnl_difference':str(D(y['pnl'] if y else 0)-D(x['pnl'] if x else 0)),
                    'explicit_VETO':actions[key]['action']=='VETO_THIS_ENTRY'})
            explicit=[t for t in old if actions[t['entry_id']]['action']=='VETO_THIS_ENTRY']
            row['explicit_old_purchase_veto']={'N':len(explicit),'negative_N':sum(D(t['pnl'])<0 for t in explicit),'positive_N':sum(D(t['pnl'])>0 for t in explicit),
                'static_removed_loss_jpy':str(sum((-min(D(t['pnl']),0) for t in explicit),D(0))),
                'static_removed_positive_pnl_jpy':str(sum((max(D(t['pnl']),0) for t in explicit),D(0)))}
            paired.append(row);all_a+=old;all_b+=new
        all_windows.append(row)
    assert all(a['mismatch_N']==0 for a in audits),'INDEPENDENT_NEW_PATH_ACCOUNTING_FAILED'
    save(OUT/'DEFENSE_INDEPENDENT_ACCOUNTING.json',{'exact_jst':now(),'status':'PASS','mismatch_N':0,'audit_code_reused_without_native_execution_import':True,
        'audits':audits,'new_Control_replays':0,'new_market_R_materializations':0,'ending_cash_formula':'1000000 + sum(actual_trade_pnl)','Control_existing_audit_reused':True})
    gzsave(PRIVATE/'PAIRED_TRANSACTION_AND_QUANTITY_DELTA.jsonl.gz',deltas)
    values_a=[D(w['V5_final_jpy']) for w in paired];values_b=[D(w['Defense_final_jpy']) for w in paired];diffs=[b-a for a,b in zip(values_a,values_b)]
    summary_a=stats(all_a);summary_b=stats(all_b)
    def wealth(values):
        return {'min':str(min(values)),'mean':str(mean(values)),'median':str(median(values)),'max':str(max(values)),'two_x_N':sum(v>=2000000 for v in values)} if values else None
    wa=wealth(values_a);wb=wealth(values_b)
    complete=bool(paired)
    loss_better=complete and D(summary_b['negative_pnl_abs_jpy'])<D(summary_a['negative_pnl_abs_jpy']) and summary_b['negative_rate']<summary_a['negative_rate']
    wealth_better=complete and D(wb['median'])>D(wa['median']) and D(wb['mean'])>=D(wa['mean'])
    status='DEFENSE_DEVELOPMENT_PROGRESS_PARTIAL' if loss_better and wealth_better else 'DEFENSE_LOSS_REDUCED_WEALTH_NOT_IMPROVED' if loss_better else 'DEFENSE_REJECTED'
    categories={}
    for cat in ['V5_ONLY','COMMON_IDENTICAL','COMMON_QUANTITY_CHANGE','DEFENSE_ONLY']:
        xs=[r for r in deltas if r['category']==cat]
        categories[cat]={'N':len(xs),'net_pnl_difference_jpy':str(sum((D(r['pnl_difference']) for r in xs),D(0)))}
    explicit=[w['explicit_old_purchase_veto'] for w in paired]
    exp={k:sum(x[k] for x in explicit) for k in ['N','negative_N','positive_N']}
    for k in ['static_removed_loss_jpy','static_removed_positive_pnl_jpy']:exp[k]=str(sum((D(x[k]) for x in explicit),D(0)))
    result={'exact_jst':now(),'status':status,'paired_complete_N':len(paired),'planned_N':len(all_windows),'coverage_unknown_N':sum(w['Defense_status']=='BLOCKED_COVERAGE' for w in all_windows),
        'one_side_incomplete_N':sum((w['V5_status']=='COMPLETE')!=(w['Defense_status']=='COMPLETE') for w in all_windows),
        'comparison_scope':'same completed account windows; overlapping Development sessions, not independent monthly samples',
        'V5_wealth':wa,'Defense_wealth':wb,'V5_trades_overlapping_accounts':summary_a,'Defense_trades_overlapping_accounts':summary_b,
        'wealth_median_difference_jpy':str(D(wb['median'])-D(wa['median'])) if complete else None,
        'paired_difference_median_jpy':str(median(diffs)) if complete else None,
        'paired_win_N':sum(d>0 for d in diffs),'paired_tie_N':sum(d==0 for d in diffs),'paired_loss_N':sum(d<0 for d in diffs),
        'actual_loss_reduction_jpy':str(D(summary_a['negative_pnl_abs_jpy'])-D(summary_b['negative_pnl_abs_jpy'])),
        'actual_positive_pnl_difference_jpy':str(D(summary_b['positive_pnl_jpy'])-D(summary_a['positive_pnl_jpy'])),
        'transaction_delta_decomposition':categories,'explicit_veto_saved_quantities':exp,
        'worst_maxDD_V5':str(max(D(w['V5_maxDD']) for w in paired)) if complete else None,
        'worst_maxDD_Defense':str(max(D(w['Defense_maxDD']) for w in paired)) if complete else None,
        'all_windows':all_windows,'new_Capital_candidates':1,'new_Capital_formal_batches':1,'new_Control_full_replays':0,'productionReady':False,
        'V5_automatic_replacement':False,'all_period_improvement_claim':False}
    save(OUT/'RESET20_COMPARISON.json',result)
    csv_rows=[]
    for w in all_windows:
        row={k:v for k,v in w.items() if not isinstance(v,dict)}
        for family in ['V5','Defense']:
            for k,v in w.get(family,{}).items():
                if not isinstance(v,dict):row[family+'_'+k]=v
        csv_rows.append(row)
    fields=sorted({k for r in csv_rows for k in r})
    with (OUT/'RESET20_ALL21_WINDOWS.csv').open('w') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(csv_rows)
    print(json.dumps({k:v for k,v in result.items() if k not in ['all_windows']},ensure_ascii=False))

if __name__=='__main__':main()
