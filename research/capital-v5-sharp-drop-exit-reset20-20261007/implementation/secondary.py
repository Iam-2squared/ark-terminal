"""Original chained selected-session normalization, never a RESET20 replay."""
from io_utils import *
from analyze import path,stats,enriched,loss_metrics,spectrum,transition
from statistics import median
from datetime import date

def main():
    p={a:path('CHAIN38',a) for a in ['C','E']}
    old=json.loads((ROOT/'inputs/v5/native_result').read_text())
    split=json.loads((ROOT/'inputs/v5/split').read_text());ss=split['OOF38']
    out=[]
    for i,saved in enumerate(old['rolling20_windows']):
        assert saved['start_session']==ss[i] and saved['end_session']==ss[i+19]
        r={'metric_label':'LEGACY_NORMALIZED20','window_id':'L%02d'%(i+1),'original_window_array_index':i,'start_session':ss[i],'end_session':ss[i+19],'selected_session_N':20,'calendar_span_inclusive_days':(date.fromisoformat(ss[i+19])-date.fromisoformat(ss[i])).days+1,'sessions':ss[i:i+20],'independent_cash_reset':False,'continuous_market20_claim':False,'saved_C_amount_float_reference':str(saved['amount_from_1m'])}
        for a in ['C','E']:
            daily=p[a]['result']['daily_series'] if p[a] else []
            valid=len(daily)>i+19 and all(d['status']=='COMPLETE' for d in daily[:i+20])
            r[a+'_status']='COMPLETE' if valid else 'UNMEASURED_AFTER_CHAIN_BLOCK'
            start=D(daily[i]['starting_cash']) if valid else None;end=D(daily[i+19]['ending_cash']) if valid else None
            r[a+'_chain_starting_cash_jpy']=fmt(start);r[a+'_chain_ending_cash_jpy']=fmt(end)
            r[a+'_normalized_final_jpy']=fmt(D(1000000)*(end/start)) if valid else None
        r['paired_complete']=r['C_status']==r['E_status']=='COMPLETE'
        r['E_minus_C_normalized_jpy']=fmt(D(r['E_normalized_final_jpy'])-D(r['C_normalized_final_jpy'])) if r['paired_complete'] else None
        if r['C_status']=='COMPLETE':
            # The old saved report used IEEE float normalization. Exact money comes from its unchanged ledger.
            native_float_amount=1000000*float(D(r['C_chain_ending_cash_jpy'])/D(r['C_chain_starting_cash_jpy']))
            assert native_float_amount.hex()==float(saved['amount_from_1m']).hex()
            r['C_native_saved_float_formula_exact']=True
        out.append(r)
    complete=[r for r in out if r['paired_complete']]
    best=max(range(len(out)),key=lambda i:old['rolling20_windows'][i]['amount_from_1m'])
    result={'metric_label':'LEGACY_NORMALIZED20','planned19':19,'paired_complete_N':len(complete),'unknown_N':19-len(complete),'formula':'1000000 * (chain window ending_cash / chain window starting_cash)','not_independent_reset':True,'original_selected_sessions_include_unevaluated_market_dates':True,'missing_evaluation_dates':['2025-07-11','2025-07-14'],'paired_mask':[r['window_id'] for r in complete],'old_best_window_selected_by_old_C_only':out[best],'float_saved_reference_is_unchanged':True,'reported_exact_normalization_uses_pinned_money':True,'paired_delta_stats':stats([D(r['E_minus_C_normalized_jpy']) for r in complete])}
    for a in ['C','E']:
        values=[D(r[a+'_normalized_final_jpy']) for r in complete];result[a+'_normalized_stats']=stats(values)
        result[a+'_extreme_window_ids']={k:[r['window_id'] for r in complete if D(r[a+'_normalized_final_jpy'])==f(values)] if values else [] for k,f in [('min',min),('max',max)]}
        result[a+'_median_window_ids']=[r['window_id'] for r in complete if D(r[a+'_normalized_final_jpy'])==median(values)] if values else []
    result['difference_of_medians_jpy']=fmt(median([D(r['E_normalized_final_jpy']) for r in complete])-median([D(r['C_normalized_final_jpy']) for r in complete])) if complete else None
    result['median_of_paired_differences_jpy']=fmt(median([D(r['E_minus_C_normalized_jpy']) for r in complete])) if complete else None
    result['CHAIN38']={'metric_label':'CHAIN38','start_session':ss[0],'end_session':ss[-1],'selected_session_N':38,'calendar_span_inclusive_days':(date.fromisoformat(ss[-1])-date.fromisoformat(ss[0])).days+1,'initial_cash_jpy':'1000000','monthly_result_claim':False,'C':p['C']['result'] if p['C'] else None,'E':p['E']['result'] if p['E'] else None,'E_minus_C_jpy':fmt(D(p['E']['result']['final_equity'])-D(p['C']['result']['final_equity'])) if all(p[a] and p[a]['result']['status']=='COMPLETE' for a in ['C','E']) else None}
    # Public chain daily summaries are already redacted in the path status.
    status=json.loads((PUB/'CHAIN38_PATH_STATUS.json').read_text())
    for a in ['C','E']:result['CHAIN38'][a]=status['arms'].get(a)
    save(PUB/'CHAIN38_AND_LEGACY20_RESULTS.json',result);csvsave(PUB/'LEGACY20_PAIRED_WINDOWS.csv',out)
    loss=[];sp=[]
    if all(p.values()):
        fc={a:enriched(p[a]) for a in ['C','E']}
        for a in ['C','E']:loss.append({'window_id':'CHAIN38','arm':a,**loss_metrics(p[a],fc[a])});sp+=spectrum('CHAIN38',a,fc[a])
        tr,dc,tail=transition('CHAIN38',fc['C'],fc['E']);csvsave(PRI/'CHAIN38_ORIGINAL_C_TRANSITIONS.csv',tr);csvsave(PRI/'CHAIN38_FUNDING_DECOMPOSITION.csv',dc);csvsave(PRI/'CHAIN38_NEW_TAIL_ENTRANTS.csv',tail)
        total=sum((D(x['paired_PnL_delta_jpy']) for x in dc if x['paired_PnL_delta_jpy'] is not None),D(0))
        if result['CHAIN38']['E_minus_C_jpy'] is not None:assert total==D(result['CHAIN38']['E_minus_C_jpy'])
    csvsave(PUB/'CHAIN38_RETURN_SPECTRUM.csv',sp);csvsave(PUB/'CHAIN38_TAIL_AND_LOSS_METRICS.csv',loss)
    print(json.dumps({k:result[k] for k in ['paired_complete_N','old_best_window_selected_by_old_C_only','C_normalized_stats','E_normalized_stats']},ensure_ascii=False))
if __name__=='__main__':main()
