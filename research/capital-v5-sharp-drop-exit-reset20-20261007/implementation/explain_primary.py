"""Sealed-path explanations and fixed-C cohorts; never policy feedback."""
from io_utils import *
from analyze import path,enriched,transition,BANDS
import collections,csv

def main():
    mask=json.loads((PUB/'RESET20_SUMMARY.json').read_text())['mask'];alltrans=[];alldc=[];alltails=[];traces=[];firsts=[];reasonrows=[];unique={'C':{},'E':{}};lock=[]
    for w in mask:
        data={a:path(w,a) for a in ['C','E']};ff={a:enriched(data[a]) for a in ['C','E']};tr,dc,tails=transition(w,ff['C'],ff['E']);alltrans+=tr;alldc+=dc;alltails+=tails
        f={a:{r['entry_id']:r for r in ff[a]} for a in ['C','E']};dec={a:{d['entry_id']:d for d in data[a]['DECISIONS']} for a in ['C','E']};curves={a:{(r['session'],r['minute']):r for r in data[a]['CURVE']} for a in ['C','E']}
        for a in ['C','E']:
            for r in ff[a]:
                item=unique[a].setdefault(r['entry_id'],{'entry_id':r['entry_id'],'session':r['session'],'band':r['bucket'],'R_pct':fmt(r['R']),'windows':[],'quantities':[]})
                assert item['R_pct']==fmt(r['R']);item['windows'].append(w);item['quantities'].append(r['quantity'])
            lock.append({'window_id':w,'arm':a,'capital_lock_jpy_minutes':fmt(sum((r['cash_minutes'] for r in ff[a] if r['cash_minutes'] is not None),D(0)))})
        for r in tr:
            c=f['C'][r['entry_id']];e=f['E'].get(r['entry_id']);money=e['pnl']-c['pnl'] if e and e['pnl'] is not None and c['pnl'] is not None else None
            r['same_ID_actual_PnL_delta_jpy']=fmt(money);r['same_ID_actual_PnL_effect']='E_NOT_PURCHASED' if not e else 'R_UNKNOWN' if money is None else 'IMPROVED' if money>0 else 'EQUAL' if money==0 else 'WORSENED'
        for key in dec['C']:
            c=dec['C'][key];e=dec['E'][key]
            if c['reason']!='FUNDED' and e['reason']!='FUNDED':reasonrows.append({'window_id':w,'entry_id':key,'C_reason':c['reason'],'E_reason':e['reason'],'set':'ALSO_NEITHER'})
        for intent in data['E']['INTENTS']:
            if intent.get('reason')!='SHARP_DROP_FIRST_OBSERVED':continue
            key=intent['entry_id'];item=f['E'][key];trade=item['trade'];day=intent['session'];t=intent['minute'];release=trade['release_minute'];before=curves['E'][day,release-1]
            prior_fills=[r for r in data['E']['TRADES'] if r['session']==day and r['release_minute']==release and r['entry_id']<key]
            before_cash=D(before['cash'])+sum((D(r['credit']) for r in prior_fills),D(0));after_cash=before_cash+D(trade['credit']);slots_before=before['concurrent']-len(prior_fills)
            subsequent=sorted([d for d in data['E']['DECISIONS'] if d['session']==day and d['minute']>=release],key=lambda d:(d['minute'],-d['ML'],-d['m5'],-d['m3'],-d['m2'],d['entry_id']))
            change=next((d for d in subsequent if d['quantity']!=dec['C'][d['entry_id']]['quantity'] or d['reason']!=dec['C'][d['entry_id']]['reason']),None)
            record={'window_id':w,'entry_id':key,'session':day,'events':[{'timestamp':stamp(day,t),'phase_order':2,'event':'FIRST_VALID_POST_FILL_SHARP_DROP_OBSERVATION_AND_LATCHED_SELL_INTENT','cash_and_slot_released':False,'quantity':intent['quantity']},{'timestamp':stamp(day,trade['source_minute']),'phase_order':'source_quote_not_release','event':'ELIGIBLE_RAW_SELL_REFERENCE','sell_effective':trade['sell_effective'],'lineage':trade['lineage']},{'timestamp':stamp(day,release),'phase_order':1,'event':'FILL_ASSUMED_AVAILABLE_RELEASE_BEFORE_BUY_BATCH','cash_before_jpy':fmt(before_cash),'credit_jpy':trade['credit'],'cash_after_jpy':fmt(after_cash),'open_positions_before':slots_before,'open_positions_after':slots_before-1}], 'C_same_ID_trade':f['C'].get(key,{}).get('trade'),'next_funding_difference':{'E':change,'C':dec['C'][change['entry_id']]} if change else None,'event_order_contract':['MTM_UPDATE','SELL_FILL_RELEASE_SORTED_ENTRY_ID','STATE_AND_SELL_INTENT','BUY_BATCH_NATIVE_SCORE_ORDER','CANONICAL_EOD_INTENT','CURVE'],'follow_on_change_is_descriptive_link_not_unique_causal_attribution':True,'actual_receive_time':'UNKNOWN'}
            assert record['events'][0]['cash_and_slot_released'] is False
            assert release>=t and after_cash-before_cash==D(trade['credit'])
            traces.append(record)
        wt=sorted([r for r in traces if r['window_id']==w],key=lambda r:(r['session'],r['events'][0]['timestamp'],r['entry_id']))
        if wt:firsts.append(wt[0])
    csvsave(PRI/'ORIGINAL_C_WINNER_LOSER_TRANSITIONS.csv',alltrans);csvsave(PRI/'ALSO_NEITHER_REASONS.csv',reasonrows);gzsave(PRI/'EARLY_RELEASE_TO_FOLLOWING_BUY_TRACES.jsonl.gz',traces);save(PRI/'UNIQUE_FUNDED_ENTRY_DIAGNOSTICS.json',{a:list(unique[a].values()) for a in ['C','E']});csvsave(PUB/'CAPITAL_LOCK_BY_WINDOW.csv',lock)
    first=min(firsts,key=lambda r:(r['session'],r['events'][0]['timestamp'],r['window_id'],r['entry_id'])) if firsts else None
    save(PRI/'FIRST_DIVERGENCE.json',{'global_first':first,'per_window':firsts,'tie_order':'session,minute,native phase,entry_id; cross-window ties by fixed window ID','selection':'EARLIEST_DIFFERENCE_NOT_BEST_CASE'})
    save(PUB/'FIRST_DIVERGENCE.json',{'status':'FOUND' if first else 'NONE','global_window':first['window_id'] if first else None,'global_session':first['session'] if first else None,'global_timestamp':first['events'][0]['timestamp'] if first else None,'event':'FIRST_SHARP_DROP_SELL_INTENT; cash and slot stay occupied until legal release','per_window':[{'window_id':r['window_id'],'session':r['session'],'timestamp':r['events'][0]['timestamp']} for r in firsts],'private_detail':'FIRST_DIVERGENCE.json and EARLY_RELEASE_TO_FOLLOWING_BUY_TRACES.jsonl.gz','trace_N':len(traces),'source_receive_time':'UNKNOWN'})
    aggregate=[]
    for w in mask+['ALL9_OVERLAPPING_ACCOUNTS']:
        for band in BANDS:
            rr=[r for r in alltrans if r['C_fixed_band']==band and (w.startswith('ALL') or r['window_id']==w)]
            known=[r for r in rr if r['same_ID_EXIT_effect'] in ['IMPROVED','EQUAL','WORSENED']]
            aggregate.append({'window_id':w,'C_fixed_band':band,'C_N':len(rr),'E_purchased_N':sum(r['E_purchased'] for r in rr),'E_not_purchased_N':sum(not r['E_purchased'] for r in rr),'per_unit_EXIT_improved_N':sum(r['same_ID_EXIT_effect']=='IMPROVED' for r in rr),'per_unit_EXIT_equal_N':sum(r['same_ID_EXIT_effect']=='EQUAL' for r in rr),'per_unit_EXIT_worsened_N':sum(r['same_ID_EXIT_effect']=='WORSENED' for r in rr),'actual_PnL_improved_N':sum(r['same_ID_actual_PnL_effect']=='IMPROVED' for r in rr),'actual_PnL_equal_N':sum(r['same_ID_actual_PnL_effect']=='EQUAL' for r in rr),'actual_PnL_worsened_N':sum(r['same_ID_actual_PnL_effect']=='WORSENED' for r in rr),'positive_to_negative_N':sum(r['C_positive_E_negative'] for r in rr),'R_unknown_N':sum(r['same_ID_EXIT_effect']=='R_UNKNOWN' for r in rr),'C_PnL_jpy':fmt(sum((D(r['C_PnL_jpy']) for r in rr),D(0))),'E_COMMON_PnL_jpy':fmt(sum((D(r['E_PnL_jpy']) for r in known),D(0))),'C_ONLY_PnL_funding_change_jpy':fmt(sum((D(r['C_PnL_jpy']) for r in rr if not r['E_purchased']),D(0))),'bucket_retention_does_not_hide_R_damage':True})
    csvsave(PUB/'ORIGINAL_C_WINNER_LOSER_TRANSITIONS.csv',aggregate)
    cohorts=[]
    for k in [1,2,3,4,5]:
        rr=[r for r in alltrans if r['C_R_pct'] is not None and D(r['C_R_pct'])<=-k];ee=[r for r in rr if r['E_purchased'] and r['E_R_pct'] is not None]
        new=[r for r in alltails if r['tail_threshold']==-k]
        cohorts.append({'tail_threshold_pct':-k,'count_scope':'OVERLAPPING9_ACCOUNT_TRADES','C_tail_N':len(rr),'E_not_purchased_N':sum(not r['E_purchased'] for r in rr),'E_purchased_N':sum(r['E_purchased'] for r in rr),'after_purchase_loss_mitigated_R_N':sum(r['same_ID_EXIT_effect']=='IMPROVED' for r in ee),'after_purchase_tail_escape_N':sum(D(r['E_R_pct'])>-k for r in ee),'after_purchase_tail_retained_N':sum(D(r['E_R_pct'])<=-k for r in ee),'E_R_unknown_N':sum(r['E_purchased'] and r['E_R_pct'] is None for r in rr),'new_tail_from_C_outside_N':sum(r['set']=='COMMON_C_OUTSIDE_TAIL' for r in new),'new_tail_from_E_only_N':sum(r['set']=='E_ONLY' for r in new),'new_tail_E_loss_jpy':fmt(-sum((D(r['E_PnL_jpy']) for r in new),D(0)))})
    dcmap={(r['window_id'],r['entry_id']):r for r in alldc}
    rescued=[r for r in alltrans if r['C_fixed_loser'] and r['E_purchased'] and D(dcmap[r['window_id'],r['entry_id']]['COMMON_direct_EXIT_jpy'])>0]
    hurt=[r for r in alltrans if r['C_fixed_winner'] and r['E_purchased'] and D(dcmap[r['window_id'],r['entry_id']]['COMMON_direct_EXIT_jpy'])<0]
    select_rescue=min(rescued,key=lambda r:(-D(dcmap[r['window_id'],r['entry_id']]['COMMON_direct_EXIT_jpy']),r['window_id'],r['entry_id'])) if rescued else None
    select_hurt=min(hurt,key=lambda r:(D(dcmap[r['window_id'],r['entry_id']]['COMMON_direct_EXIT_jpy']),r['window_id'],r['entry_id'])) if hurt else None
    nt=[r for r in alltails if r['tail_threshold']==-3]
    select_new=min(nt,key=lambda r:(D(r['E_PnL_jpy']),D(r['E_R_pct']),r['window_id'],r['entry_id'])) if nt else None
    examples={'selection_rules':{'largest_loser_mitigation':'COMMON C R<0; descending q_C*(u_E-u_C); fixed window/entry ties','largest_winner_damage':'COMMON C R>0; ascending q_C*(u_E-u_C); fixed window/entry ties','worst_new_tail':'E R<=-3; C outside -3 tail or E_ONLY; ascending E actual PnL, E R,window,entry'},'largest_loser_mitigation':{'transition':select_rescue,'accounting':dcmap[select_rescue['window_id'],select_rescue['entry_id']]} if select_rescue else None,'largest_winner_damage':{'transition':select_hurt,'accounting':dcmap[select_hurt['window_id'],select_hurt['entry_id']]} if select_hurt else None,'worst_new_tail':select_new}
    save(PRI/'DETERMINISTIC_SELECTED_EXAMPLES.json',examples)
    winners=[r for r in alltrans if r['C_fixed_winner']];losers=[r for r in alltrans if r['C_fixed_loser']]
    public={'mask':mask,'count_scope':'OVERLAPPING9_PORTFOLIO_ACCOUNTS_NOT_UNIQUE_MARKET_TRADES','fixed_C_winners':{'C_N':len(winners),'E_purchased_N':sum(r['E_purchased'] for r in winners),'E_not_purchased_N':sum(not r['E_purchased'] for r in winners),'per_unit_EXIT_improved_N':sum(r['same_ID_EXIT_effect']=='IMPROVED' for r in winners),'per_unit_EXIT_equal_N':sum(r['same_ID_EXIT_effect']=='EQUAL' for r in winners),'per_unit_EXIT_worsened_N':sum(r['same_ID_EXIT_effect']=='WORSENED' for r in winners),'actual_PnL_improved_N':sum(r['same_ID_actual_PnL_effect']=='IMPROVED' for r in winners),'actual_PnL_equal_N':sum(r['same_ID_actual_PnL_effect']=='EQUAL' for r in winners),'actual_PnL_worsened_N':sum(r['same_ID_actual_PnL_effect']=='WORSENED' for r in winners),'positive_to_negative_N':sum(r['C_positive_E_negative'] for r in winners),'R_unknown_N':sum(r['same_ID_EXIT_effect']=='R_UNKNOWN' for r in winners)},'fixed_C_losers':{'C_N':len(losers),'E_purchased_N':sum(r['E_purchased'] for r in losers),'E_not_purchased_N':sum(not r['E_purchased'] for r in losers)},'tail_transitions':cohorts,'also_neither_reason_pairs':dict(collections.Counter(r['C_reason']+' -> '+r['E_reason'] for r in reasonrows)),'unique_market_Entry_N':{a:len(unique[a]) for a in ['C','E']},'early_release_trace_N':len(traces),'decomposition_sum':{k:fmt(sum((D(r[k]) for r in alldc if r[k] is not None),D(0))) for k in ['COMMON_direct_EXIT_jpy','COMMON_quantity_jpy','E_ONLY_PnL_jpy','C_ONLY_PnL_jpy','paired_PnL_delta_jpy']},'examples_private_hash':pin(PRI/'DETERMINISTIC_SELECTED_EXAMPLES.json'),'examples_redacted':{'largest_loser_mitigation':{'window_id':select_rescue['window_id'],'direct_EXIT_jpy':dcmap[select_rescue['window_id'],select_rescue['entry_id']]['COMMON_direct_EXIT_jpy']} if select_rescue else None,'largest_winner_damage':{'window_id':select_hurt['window_id'],'direct_EXIT_jpy':dcmap[select_hurt['window_id'],select_hurt['entry_id']]['COMMON_direct_EXIT_jpy']} if select_hurt else None,'worst_new_tail':{k:select_new[k] for k in ['window_id','set','E_PnL_jpy']} if select_new else None},'not_unique_causal_attribution':True,'C_ONLY_profit_not_recoverable_profit_claim':True,'potential_U5_U10_not_realized_winners':True}
    save(PUB/'WINNER_LOSER_AND_FUNDING_DIAGNOSTICS.json',public)
    print(json.dumps(public,ensure_ascii=False))
if __name__=='__main__':main()
