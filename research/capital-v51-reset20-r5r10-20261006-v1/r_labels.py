"""Evaluation-only fixed execution labels; never imported by allocation."""
from decimal import Decimal as D
from fractions import Fraction as F
from collections import Counter
import sys
from io_utils import *
sys.path.insert(0,str(REPO/'research/capital-v5-max3-slot-intelligence-20261004-v1'))
from execution import BUY,SELL,valid_market,frozen_execution,eod_source

def classify(debit,credit):
    if debit is None or credit is None:return {'R5':None,'R10':None,'Loser':None,'net_bin':'UNKNOWN'}
    debit=F(debit);credit=F(credit);assert debit>0
    r=credit/debit-1
    return {'R5':r>=F(5,100),'R10':r>=F(10,100),'Loser':r<=0,'net_bin':'LE0' if r<=0 else 'GT0_LT5' if r<F(5,100) else 'GE5_LT10' if r<F(10,100) else 'GE10','r_net_fraction':[r.numerator,r.denominator],'r_net_ratio_decimal':str(D(r.numerator)/D(r.denominator))}

def entry_eligible(r,b):
    try:
        source=b.get('entry_actual_source') if b else None
        return r['entry_minute']<920 and D(r['raw_reference']).is_finite() and D(r['raw_reference'])>0 and source is not None and valid_market(source) and source['session']==r['session'] and source['minute']==r['entry_minute'] and D(source['O'])==D(r['raw_reference'])
    except (ValueError,KeyError,TypeError):return False

def materialize(r,b,teacher,contract):
    eligible=entry_eligible(r,b)
    out={k:r[k] for k in ['entry_id','session','symbol','entry_minute','block']}
    out.update(rank=r['rank'],rank_pass=r['admission'],execution_eligible=eligible,U5=bool(teacher['label_bigwinner5']) if teacher else None,U10=bool(teacher['label_bigwinner10']) if teacher else None,Weak=teacher['potential_return']<.02 if teacher else None,potential_return_original=teacher['potential_return'] if teacher else None,structural_exit_v3=({k:b['frozen_exit'].get(k) for k in ['sell_status','sell_price_decimal','sell_source','sell_source_assumed_available_at']} if b else None),structural_teacher_return=teacher.get('realized_net_return') if teacher else None,exit_policy_hash=contract['exit_policy_hash'],BUY_factor=str(BUY),SELL_factor=str(SELL),reference_quantity=100,known=False,buy_debit=None,sell_credit=None)
    src=None;reason=None
    if not eligible:reason='ENTRY_EXECUTION_INELIGIBLE'
    elif not b['capture_complete']:reason='CAPTURE_INCOMPLETE'
    else:
        try:src=frozen_execution(b) or eod_source(b['market'],r['session'])
        except (AssertionError,KeyError,ValueError):reason='FIXED_SOURCE_CONTRACT_MISMATCH'
        if src and (src.get('blocked') or src['release_minute']<=r['entry_minute']):reason=src.get('blocked','EXIT_ORDER_INVALID');src=None
        elif src is None and reason is None:reason='EXIT_EOD_SOURCE_UNKNOWN'
    if src and not reason:
        debit=D(r['raw_reference'])*BUY*100;credit=D(src['price'])*100
        raw_sell=next(x for x in b['market'] if x['minute']==src['source_minute'] and x['session']==r['session'])
        price_source=b['frozen_exit']['sell_source'] if src['kind']=='FROZEN_EXIT_V3' else 'REGULAR_RAW_OPEN' if src['kind']=='EOD_REGULAR' else 'EXACT_1530_RAW_CLOSE'
        out.update(known=True,buy_debit=str(debit),sell_credit=str(credit),exit_kind=src['kind'],price_source=price_source,source_minute=src['source_minute'],release_minute=src['release_minute'],sell_assumed_available_minute=src['release_minute'],buy_source_minute=b['entry_actual_source']['minute'],buy_assumed_available_at=r['entry_timestamp'],historical_actual_arrival='UNKNOWN_ASSUMED_INHERITED_CONTRACT',source_lineage=src['lineage'],cost_basis='raw buy*1.0005; raw sell*0.9995; effective values used once; commission0',holding_minutes=src['release_minute']-r['entry_minute'],reference_net_pnl=str(credit-debit),reference_capital_minutes=str(debit*(src['release_minute']-r['entry_minute'])))
    out.update(classify(out['buy_debit'],out['sell_credit']),unknown_reason=reason)
    assert out['R10'] is not True or out['R5'] is True
    assert out['U10'] is not True or out['U5'] is True
    return out

def main():
    destination=PRIVATE/'evaluation-only/R_LABELS.jsonl.gz'
    if destination.exists():raise RuntimeError('Labels already materialized: reuse stored artifact')
    stream=rows(INPUTS/'candidate_stream');books={b['entry_id']:b for b in rows(INPUTS/'books')};teachers={r['entry_id']:r for r in rows(INPUTS/'teachers')};contract=read(OUT/'R_LABEL_CONTRACT.json')
    labels=[materialize(r,books.get(r['entry_id']),teachers.get(r['entry_id']),contract) for r in stream]
    write_rows(destination,labels)
    cens=[]
    for mask,ls in [('all_frozen_entries',labels),('rank_pass',[r for r in labels if r['rank_pass']]),('execution_eligible',[r for r in labels if r['execution_eligible']]),('rank_pass_and_eligible',[r for r in labels if r['rank_pass'] and r['execution_eligible']])]:
        known=[r for r in ls if r['known']]
        cross={u:{k:sum(r[u] is True and r[k] is True for r in known) for k in ['R5','R10','Loser']} for u in ['U5','U10','Weak']}
        cens.append({'mask':mask,'N':len(ls),'known_N':len(known),'unknown_N':len(ls)-len(known),'unknown_rate':(len(ls)-len(known))/len(ls) if ls else None,'bins':dict(Counter(r['net_bin'] for r in ls)),'R5_N':sum(r['R5'] is True for r in ls),'R10_N':sum(r['R10'] is True for r in ls),'U5_N':sum(r['U5'] is True for r in ls),'U10_N':sum(r['U10'] is True for r in ls),'cross':cross})
    save(OUT/'R_LABEL_CENSUS.json',{'exact_jst':now(),'unit':'unique Frozen Entry identity','universe':'Original OOF38 fixed stream, unchanged; all1600 teachers retained read-only, training rows not counted as evaluation opportunities','materialization_N':1,'census':cens,'unknown_reasons':dict(Counter(r['unknown_reason'] for r in labels if not r['known'])),'exit_kinds':dict(Counter(r['exit_kind'] for r in labels if r['known'])),'private_artifact':{'path':'capital_v51_private/evaluation-only/R_LABELS.jsonl.gz','sha256':sha(destination),'bytes':destination.stat().st_size}})
    print(cens)

if __name__=='__main__':main()
