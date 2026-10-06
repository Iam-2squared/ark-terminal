"""Evaluate locked initial OOF and actions; no selection or fitting here."""
from collections import defaultdict, Counter
from fractions import Fraction as F
from decimal import Decimal as D
import csv
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
from rneg_io import *

def metric(rr, key):
    valid=[r for r in rr if r['r'] is not None and r['scores'].get(key) is not None]
    y=[int(r['r']<0) for r in valid];p=[r['scores'][key] for r in valid]
    return {'N':len(valid),'unknown_label_N':sum(r['r'] is None for r in rr),'missing_prediction_N':sum(r['scores'].get(key) is None for r in rr),
        'AUROC':float(roc_auc_score(y,p)) if len(set(y))==2 else None,
        'average_precision':float(average_precision_score(y,p)) if y else None,
        'Brier':float(brier_score_loss(y,p)) if y else None,'log_loss':float(log_loss(y,p,labels=[0,1])) if y else None}

def defense_stats(rr):
    known=[r for r in rr if r['r'] is not None];v=[r for r in known if r['veto']];keep=[r for r in known if not r['veto']]
    neg=sum(r['r']<0 for r in known);pos=sum(r['r']>0 for r in known)
    vp=sum(r['r']>0 for r in v);vn=sum(r['r']<0 for r in v)
    posprofit=sum((max(r['r'],0) for r in known),F(0));removed=sum((max(r['r'],0) for r in v),F(0))
    tail={f'RN{k}':{'population_N':sum(r['r']<=-F(k,100) for r in known),'veto_N':sum(r['r']<=-F(k,100) for r in v)} for k in (1,3,5,10)}
    positive={name:{'population_N':sum(lo<r['r'] and (hi is None or r['r']<hi) for r in known) if lo==0 else sum(lo<=r['r'] and (hi is None or r['r']<hi) for r in known),
        'veto_N':sum(lo<r['r'] and (hi is None or r['r']<hi) for r in v) if lo==0 else sum(lo<=r['r'] and (hi is None or r['r']<hi) for r in v)}
        for name,lo,hi in [('GT0_LT1',F(0),F(1,100)),('GE1_LT3',F(1,100),F(3,100)),('GE3_LT5',F(3,100),F(5,100)),('GE5_LT10',F(5,100),F(10,100)),('GE10',F(10,100),None)]}
    return {'total_N':len(rr),'known_N':len(known),'unknown_N':len(rr)-len(known),
        'veto_all_N':sum(r['veto'] for r in rr),'veto_unknown_R_N':sum(r['veto'] and r['r'] is None for r in rr),
        'negative_N':neg,'positive_N':pos,'veto_negative_N':vn,'veto_positive_N':vp,'veto_precision':vn/len(v) if v else None,
        'negative_veto_recall':vn/neg if neg else None,'remaining_RNEG_rate':sum(r['r']<0 for r in keep)/len(keep) if keep else None,
        'positive_false_veto_rate':vp/pos if pos else None,'positive_unit_profit_removed_rate':float(removed/posprofit) if posprofit else None,
        'non_veto_coverage':1-sum(r['veto'] for r in rr)/len(rr) if rr else None,
        'unit_static_removed_loss':float(sum((-min(r['r'],0) for r in v),F(0))),
        'unit_static_removed_positive_profit':float(removed),'unit_static_net':float(sum((-r['r'] for r in v),F(0))),
        'tails':tail,'positive_bins':positive}

def static_money(trades, actions):
    rr=[r for r in trades if actions[r['entry_id']]['action']=='VETO_THIS_ENTRY'];loss=sum((-min(D(r['pnl']),0) for r in rr),D(0));profit=sum((max(D(r['pnl']),0) for r in rr),D(0))
    return {'veto_trade_N':len(rr),'veto_negative_N':sum(D(r['pnl'])<0 for r in rr),'veto_positive_N':sum(D(r['pnl'])>0 for r in rr),
        'static_removed_loss_jpy':str(loss),'static_removed_positive_pnl_jpy':str(profit),'static_difference_jpy':str(loss-profit),
        'meaning':'Saved original quantities only; NOT actual avoided portfolio losses or constructed new ending wealth'}

def uninformative(rr):
    groups=defaultdict(list)
    for r in rr:
        if r['r'] is not None:groups[(r['block'],r['rank'])].append(r)
    result=[]
    for (b,rank),group in sorted(groups.items()):
        k=sum(r['veto'] for r in group);f=F(k,len(group))
        result.append({'block':b,'rank':rank,'known_N':len(group),'same_veto_N':k,
            'expected_negative_N':float(f*sum(r['r']<0 for r in group)),
            'actual_negative_N':sum(r['veto'] and r['r']<0 for r in group),
            'expected_unit_loss':float(f*sum((-min(r['r'],0) for r in group),F(0))),
            'actual_unit_loss':float(sum((-min(r['r'],0) for r in group if r['veto']),F(0))),
            'expected_unit_profit':float(f*sum((max(r['r'],0) for r in group),F(0))),
            'actual_unit_profit':float(sum((max(r['r'],0) for r in group if r['veto']),F(0)))})
    sums={k:sum(r[k] for r in result) for k in ['expected_negative_N','actual_negative_N','expected_unit_loss','actual_unit_loss','expected_unit_profit','actual_unit_profit']}
    return {'method':'analytic expectation, same veto counts by block/native rank, known-R mask; no random portfolio replay','unknown_R_N':sum(r['r'] is None for r in rr),'groups':result,'total':sums}

def main():
    targets={r['entry_id']:r for r in rows(PRIVATE/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz')}
    actions={r['entry_id']:r for r in rows(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz')}
    pp=rows(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz');pred=defaultdict(dict)
    for r in pp:pred[r['entry_id']][r['recipe']]=r['score'];pred[r['entry_id']]['B0']=r['baseline'] if r['recipe']=='D1' else pred[r['entry_id']].get('B0')
    for r in rows(PRIVATE/'HL0_REUSED_OOF.jsonl.gz'):pred[r['entry_id']]['HL0']=r['score']
    stream=rows(SPECTRUM/'source/candidate_stream.jsonl.gz');rr=[]
    native_trades=rows(SPECTRUM/'source/native_trades.jsonl.gz');funded={r['entry_id'] for r in native_trades}
    for r in stream:
        t=targets[r['entry_id']];rv=F(t['sell_credit'])/F(t['buy_debit'])-1 if t['known'] else None
        rr.append({**r,'r':rv,'scores':pred[r['entry_id']],'execution_eligible':t['execution_eligible'],
            'veto':actions[r['entry_id']]['action']=='VETO_THIS_ENTRY','old_V5_funded':r['entry_id'] in funded})
    masks={'ALL_ENTRY':rr,'EXECUTION_ELIGIBLE':[r for r in rr if r['execution_eligible']],
        'RANK_PASS':[r for r in rr if r['execution_eligible'] and r['admission']],
        'OLD_V5_FUNDED':[r for r in rr if r['old_V5_funded']]}
    recipes=['B0','HL0','D1']+(['D2'] if read(OUT/'PREPARED_INPUT_CONFIG.json')['D2_enabled'] else [])
    output={name:{'metrics':{k:metric(m,k) for k in recipes},'defense':defense_stats(m),'uninformative':uninformative(m)} for name,m in masks.items()}
    for name,m in masks.items():
        output[name]['block_metrics']=[{'block':b,'metrics':{k:metric([r for r in m if r['block']==b],k) for k in recipes},'defense':defense_stats([r for r in m if r['block']==b])} for b in range(1,9)]
    rank=masks['RANK_PASS'];session=[]
    for day in sorted({r['session'] for r in rr}):
        m=[r for r in rank if r['session']==day];session.append({'session':day,'metrics':{k:metric(m,k) for k in recipes},'defense':defense_stats(m)})
    symbols=sorted({r['symbol'] for r in rank});loo=[]
    for symbol in symbols:
        m=[r for r in rank if r['symbol']!=symbol];s=defense_stats(m)
        loo.append({'symbol':symbol,'excluded_N':sum(r['symbol']==symbol for r in rank),
            'remaining_veto_N':s['veto_all_N'],'remaining_unit_net':s['unit_static_net']})
    gzsave(PRIVATE/'SESSION_DIAGNOSTICS.jsonl.gz',session)
    gzsave(PRIVATE/'ALL_SYMBOL_LEAVE_ONE_OUT.jsonl.gz',loo)
    money=[{'scope':'OLD_V5_CHAIN',**static_money(native_trades,actions)}]
    for p in sorted((RESET/'runs/V5_RESET20').glob('W*/COMPLETE.json')):
        w=read(p)
        if w['status']=='COMPLETE':money.append({'scope':p.parent.name,**static_money(rows(p.parent/'TRADES.jsonl.gz'),actions)})
    save(OUT/'LOSS_DEFENSE_DIAGNOSTIC.json',{'exact_jst':now(),'locked_OOF_hash':sha(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz'),
        'locked_action_hash':sha(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz'),'masks':output,'static_money':money,
        'session_dependency':{'sessions':len(session),'unit_net_min':min(s['defense']['unit_static_net'] for s in session),'unit_net_max':max(s['defense']['unit_static_net'] for s in session)},
        'all_symbol_leave_one_out':{'symbol_N':len(loo),'min_remaining_unit_net':min(s['remaining_unit_net'] for s in loo),'max_remaining_unit_net':max(s['remaining_unit_net'] for s in loo),'private_complete_table':True},
        'unknown_dropped_from_runtime':False,'OOF_is':'Repeated Development, not Fresh/OOS','static_is_not_new_portfolio_pnl':True})
    old_veto=sum(r['veto'] for r in masks['OLD_V5_FUNDED'])
    save(OUT/'CAPITAL_CONNECTION_QUALIFICATION.json',{'actual_old_V5_saved_purchase_veto_N':old_veto,
        'active_block_N':read(OUT/'OOF_COMPLETE.json')['active_block_N'],
        'action_support':old_veto>0,'source_asof_status':read(OUT/'FEATURE_ASOF_CONTRACT.json')['status'],
        'candidate':'V5_RNEG_DEFENSE_V1' if old_veto else None,'requires_OOF_policy_audit_PASS':True})
    print(json.dumps({'metrics_ALL':output['ALL_ENTRY']['metrics'],'rank_pass_defense':output['RANK_PASS']['defense'],'old_V5':money[0]},ensure_ascii=False))

if __name__=='__main__':main()
