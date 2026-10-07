"""AD01 post-execution accounting/report compiler; no policy or replay imports.

Fraction arithmetic determines every boundary, identity, and gate. Decimal text
is presentation only. Public artifacts contain aggregates; exact Entry ledgers
and deterministic individual examples stay private. Missing paths stay unknown.
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal, localcontext
from statistics import median
from datetime import date
from collections import defaultdict
import csv, gzip, hashlib, io, json

ROOT = Path(__file__).resolve().parent
PUB, PRI = ROOT/'public', ROOT/'private'
WINDOWS = [f'W{i:02}' for i in range(13,22)]
ARMS = ['E0','H1','H2']
START = F(1000000)
BANDS = ['L5_PLUS','L4_5','L3_4','L2_3','L1_2','L0_1','ZERO','P0_1','P1_2','P2_3','P3_4','P4_5','P5_PLUS','R_UNKNOWN']
CUMULATIVE = ['ALL_MINUS'] + [f'R_LE_MINUS{i}' for i in range(1,6)] + ['ALL_PLUS'] + [f'R_GE_PLUS{i}' for i in range(1,6)]
SD_EXIT = 'SHARP_DROP_FIRST_OBSERVED_EXIT_V0'

def num(value):
    if value is None: return None
    if isinstance(value,F): return value
    d = Decimal(str(value))
    if not d.is_finite(): return None
    return F(d)

def fmt(value):
    if value is None: return None
    if isinstance(value,F):
        with localcontext() as c:
            c.prec = 80
            return format(Decimal(value.numerator)/Decimal(value.denominator),'f')
    return value

def exact(value):
    return {'value':fmt(value),'numerator':str(value.numerator),'denominator':str(value.denominator)} if value is not None else None

def clean(value):
    if isinstance(value,(F,Decimal)): return fmt(num(value))
    if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean(v) for v in value]
    return value

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(clean(value),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_bytes(raw); tmp.replace(path)

def csvsave(path,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    columns=list(dict.fromkeys(k for r in records for k in r))
    if not columns: columns=['status']
    s=io.StringIO(newline=''); w=csv.DictWriter(s,fieldnames=columns,lineterminator='\n');w.writeheader()
    for record in records:
        record=clean(record)
        w.writerow({k:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in record.items()})
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(s.getvalue());tmp.replace(path)

def read(path): return json.loads(path.read_bytes())
def rows(path): return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines() if x]
def pathdata(window,arm):
    p=(ROOT/'baseline/private/runs'/window/'E') if arm=='E0' else PRI/'runs'/window/arm
    if not (p/'RESULT.json').exists(): return None
    return {'result':read(p/'RESULT.json'),**{n:rows(p/(n+'.jsonl.gz')) for n in ['DECISIONS','TRADES','CURVE','INTENTS']}}
def complete(data):
    return bool(data and data['result']['status']=='COMPLETE' and num(data['result'].get('final_equity')) is not None and data['result'].get('unsettled_N',0)==0)
def stats(values):
    if not values: return {k:None for k in ['min','mean','median','max']}
    return dict(zip(['min','mean','median','max'],[min(values),sum(values,F(0))/len(values),median(values),max(values)]))
def inmarket(t): return 540<=t<690 or 750<=t<930
def marketminutes(start,end): return sum(inmarket(t) for t in range(int(start),int(end)))
def bucket(r):
    if r is None:return 'R_UNKNOWN'
    if r<=-5:return 'L5_PLUS'
    for bound,label in [(-4,'L4_5'),(-3,'L3_4'),(-2,'L2_3'),(-1,'L1_2')]:
        if r<=bound:return label
    if r<0:return 'L0_1'
    if r==0:return 'ZERO'
    if r<1:return 'P0_1'
    for bound,label in [(2,'P1_2'),(3,'P2_3'),(4,'P3_4'),(5,'P4_5')]:
        if r<bound:return label
    return 'P5_PLUS'
def ingroup(row,label):
    r=row['R']
    if label in BANDS:return row['bucket']==label
    if r is None:return False
    if label=='ALL_MINUS':return r<0
    if label=='ALL_PLUS':return r>0
    if label.startswith('R_LE_MINUS'):return r<=-int(label[-1])
    if label.startswith('R_GE_PLUS'):return r>=int(label[-1])
    raise ValueError(label)
def enriched(data):
    trades={r['entry_id']:r for r in data['TRADES']}
    assert len(trades)==len(data['TRADES']),'duplicate trade Entry ID'
    funded=[]
    for decision in data['DECISIONS']:
        if decision['reason']!='FUNDED':continue
        t=trades.get(decision['entry_id']); debit=num(decision.get('debit'))
        pnl=num(t.get('pnl')) if t else None
        r=pnl/debit*100 if pnl is not None and debit and debit>0 else None
        funded.append({'entry_id':decision['entry_id'],'session':decision['session'],'quantity':decision['quantity'],
            'entry_minute':decision['minute'],'debit':debit,'R':r,'bucket':bucket(r),'trade':t,'pnl':pnl,
            'cash_minutes':debit*marketminutes(t['entry_minute'],t['release_minute']) if t and debit is not None else None,
            'decision':decision})
    assert len({r['entry_id'] for r in funded})==len(funded),'duplicate funded Entry'
    return funded

def dd(values):
    peak=START; worst=F(0)
    for value in values:
        peak=max(peak,value);worst=max(worst,(peak-value)/peak)
    return worst*100

def loss_metrics(data,funded):
    known=[r for r in funded if r['R'] is not None];minus=[r for r in known if r['R']<0]
    days=[num(d['ending_cash'])-num(d['starting_cash']) for d in data['result']['daily_series'] if d['status']=='COMPLETE']
    mtm=dd([num(c['equity']) for c in data['CURVE']]); eod=dd([num(d['ending_cash']) for d in data['result']['daily_series'] if d['status']=='COMPLETE'])
    met={'funded_N':len(funded),'unique_Entry_N':len({r['entry_id'] for r in funded}),'known_R_N':len(known),'unknown_R_N':len(funded)-len(known),
        'ALL_MINUS_pct_funded':F(len(minus)*100,len(funded)) if funded else None,
        'ALL_MINUS_N':len(minus),'gross_loss_jpy':-sum((r['pnl'] for r in minus),F(0)),
        'gross_positive_jpy':sum((r['pnl'] for r in known if r['pnl']>0),F(0)),
        'realized_PnL_jpy':sum((r['pnl'] for r in known),F(0)),
        'worst_trade_loss_jpy':-min([r['pnl'] for r in minus],default=F(0)),
        'worst_trade_R_pct':min([r['R'] for r in known],default=None),'negative_day_N':sum(v<0 for v in days),
        'known_day_N':len(days),'worst_daily_PnL_jpy':min(days,default=None),
        'minute_MTM_MaxDD_pct':mtm,'EOD_MaxDD_pct':eod,
        'minute_MTM_MaxDD_exact':exact(mtm),'EOD_MaxDD_exact':exact(eod)}
    for k in range(1,6):
        losers=[r for r in known if r['R']<=-k];winners=[r for r in known if r['R']>=k]
        met.update({f'R_LE_MINUS{k}_N':len(losers),f'R_LE_MINUS{k}_gross_loss_jpy':-sum((r['pnl'] for r in losers),F(0)),
            f'R_GE_PLUS{k}_N':len(winners),f'R_GE_PLUS{k}_PnL_jpy':sum((r['pnl'] for r in winners),F(0))})
    return met

def spectra(window,arm,funded):
    out=[];known=[r for r in funded if r['R'] is not None]
    for b in BANDS+CUMULATIVE:
        rr=[r for r in funded if ingroup(r,b)];kk=[r for r in rr if r['R'] is not None]
        out.append({'window_id':window,'arm':arm,'group':b,'band':b,'funded_N':len(rr),'group_type':'EXCLUSIVE' if b in BANDS else 'CUMULATIVE',
            'count_scope':'OVERLAPPING_ACCOUNT_TRADES','total_funded_N':len(funded),'total_unique_Entry_N':len({r['entry_id'] for r in funded}),
            'R_known_denominator_N':len(known),'R_unknown_N':len(funded)-len(known),'group_N':len(rr),
            'pct_all_funded':F(len(rr)*100,len(funded)) if funded else None,'pct_known_R':F(len(kk)*100,len(known)) if known else None,
            'BUY_debit_jpy':sum((r['debit'] for r in rr),F(0)),
            'quantity':sum(r['quantity'] for r in rr),'lots':sum(r['quantity'] for r in rr)//100,
            'positive_PnL_jpy':sum((r['pnl'] for r in kk if r['pnl']>0),F(0)),
            'negative_PnL_abs_jpy':-sum((r['pnl'] for r in kk if r['pnl']<0),F(0)),
            'realized_PnL_jpy':sum((r['pnl'] for r in kk),F(0)) if kk or not rr else None,
            'capital_lock_jpy_market_minutes':sum((r['cash_minutes'] for r in rr if r['cash_minutes'] is not None),F(0)),
            'capital_lock_jpy_minutes':sum((r['cash_minutes'] for r in rr if r['cash_minutes'] is not None),F(0)),
            'capital_lock_jpy_minutes_basis':'EXISTING_NATIVE_MARKET_GRID_330_MINUTES_EXCLUDING_LUNCH',
            'R_median_pct':median([r['R'] for r in kk]) if kk else None})
    return out

def public_example(example):
    if example is None:return None
    return {k:v for k,v in example.items() if k in ['window_id','policy','example_kind','set','miss_reason','direct_guard','rank','R_bucket','difference_fields','contract_same_EXIT','quantity_changed','status']}

def compare(window,policy,baseline,candidate):
    e={r['entry_id']:r for r in enriched(baseline)};h={r['entry_id']:r for r in enriched(candidate)}
    hdec={r['entry_id']:r for r in candidate['DECISIONS']};edec={r['entry_id']:r for r in baseline['DECISIONS']}
    intents={a:defaultdict(list) for a in ['E0',policy]}
    for a,data in [('E0',baseline),(policy,candidate)]:
        for r in data['INTENTS']:
            if r.get('side')=='SELL':intents[a][r['entry_id']].append({k:v for k,v in r.items() if k!='quantity'})
    detail=[];preserve=[];violations=[]
    for key in sorted(set(e)|set(h)):
        er=e.get(key);hr=h.get(key);common=er is not None and hr is not None
        direct=quantity=None;contract=None
        if common and er['trade'] and hr['trade']:
            fields=['buy_effective','sell_effective','entry_minute','release_minute','source_minute','exit_kind','commission']
            differences=[k for k in fields if er['trade'].get(k)!=hr['trade'].get(k)]
            if er['R']!=hr['R']:differences.append('exact_R')
            if intents['E0'][key]!=intents[policy][key]:differences.append('SELL_intent')
            contract=not differences
            if differences:violations.append({'window_id':window,'policy':policy,'entry_id':key,'differences':differences})
            unit_e=num(er['trade']['sell_effective'])-num(er['trade']['buy_effective'])
            unit_h=num(hr['trade']['sell_effective'])-num(hr['trade']['buy_effective'])
            direct=er['quantity']*(unit_h-unit_e);quantity=(hr['quantity']-er['quantity'])*unit_h
            assert direct+quantity==hr['pnl']-er['pnl']
        miss_reason=hdec.get(key,{}).get('reason') if er and not hr else None
        direct_guard=miss_reason=='ADMISSION_QUALITY_RESERVE'
        delta=hr['pnl']-er['pnl'] if common and er['pnl'] is not None and hr['pnl'] is not None else hr['pnl'] if hr and not er else -er['pnl'] if er and not hr and er['pnl'] is not None else None
        detail.append({'window_id':window,'policy':policy,'entry_id':key,'session':(er or hr)['session'],
            'entry_minute':(er or hr)['entry_minute'],'set':'COMMON' if common else 'E0_ONLY' if er else 'H_ONLY',
            'E0_quantity':er['quantity'] if er else 0,'H_quantity':hr['quantity'] if hr else 0,
            'R_E0_pct':er['R'] if er else None,'R_H_pct':hr['R'] if hr else None,'R_bucket':(er or hr)['bucket'],
            'E0_PnL_jpy':er['pnl'] if er else None,'H_PnL_jpy':hr['pnl'] if hr else None,
            'COMMON_direct_EXIT_jpy':direct,'COMMON_quantity_jpy':quantity,'paired_PnL_delta_jpy':delta,
            'contract_same_EXIT':contract,'direct_guard':direct_guard,'miss_reason':miss_reason,
            'E0_reason_for_H_ONLY':edec.get(key,{}).get('reason') if hr and not er else None,
            'rank':(er or hr)['decision']['rank'],'quantity_changed':common and er['quantity']!=hr['quantity']})
    for b in BANDS+CUMULATIVE:
        rr=[r for r in e.values() if ingroup(r,b)]; common=[r for r in rr if r['entry_id'] in h];miss=[r for r in rr if r['entry_id'] not in h]
        direct=[r for r in miss if hdec.get(r['entry_id'],{}).get('reason')=='ADMISSION_QUALITY_RESERVE']
        unknown=[r for r in miss if r['entry_id'] not in hdec or hdec[r['entry_id']].get('reason') is None]
        assert len(rr)==len(common)+len(miss)
        preserve.append({'window_id':window,'policy':policy,'classification':'CAPITAL_FUNDING_PRESERVATION','E0_fixed_R_group':b,
            'group_type':'EXCLUSIVE' if b in BANDS else 'CUMULATIVE','E0_N':len(rr),'COMMON_purchased_N':len(common),'H_not_purchased_N':len(miss),
            'same_purchase_pct':F(len(common)*100,len(rr)) if rr else None,'not_purchased_pct':F(len(miss)*100,len(rr)) if rr else None,
            'direct_guard_reject_N':len(direct),'indirect_path_missed_N':len(miss)-len(direct)-len(unknown),'miss_reason_unknown_N':len(unknown),
            'E0_fixed_missed_PnL_jpy':sum((r['pnl'] for r in miss if r['pnl'] is not None),F(0)),
            'direct_guard_fixed_missed_PnL_jpy':sum((r['pnl'] for r in direct if r['pnl'] is not None),F(0)),
            'COMMON_quantity_PnL_delta_jpy':sum((h[r['entry_id']]['pnl']-r['pnl'] for r in common if h[r['entry_id']]['pnl'] is not None and r['pnl'] is not None),F(0)),
            'fixed_contribution_is_not_account_avoided_profit':True})
    both=complete(baseline) and complete(candidate);known=all(r['paired_PnL_delta_jpy'] is not None for r in detail)
    amount=sum((r['paired_PnL_delta_jpy'] for r in detail if r['paired_PnL_delta_jpy'] is not None),F(0))
    delta=num(candidate['result']['final_equity'])-num(baseline['result']['final_equity']) if both else None
    summary={'window_id':window,'policy':policy,'eligible_exact_identity':both and known,
        'COMMON_N':sum(r['set']=='COMMON' for r in detail),'E0_ONLY_N':sum(r['set']=='E0_ONLY' for r in detail),'H_ONLY_N':sum(r['set']=='H_ONLY' for r in detail),
        'COMMON_direct_EXIT_jpy':sum((r['COMMON_direct_EXIT_jpy'] for r in detail if r['COMMON_direct_EXIT_jpy'] is not None),F(0)),
        'COMMON_quantity_jpy':sum((r['COMMON_quantity_jpy'] for r in detail if r['COMMON_quantity_jpy'] is not None),F(0)),
        'H_ONLY_PnL_jpy':sum((r['H_PnL_jpy'] for r in detail if r['set']=='H_ONLY' and r['H_PnL_jpy'] is not None),F(0)),
        'E0_ONLY_PnL_jpy':sum((r['E0_PnL_jpy'] for r in detail if r['set']=='E0_ONLY' and r['E0_PnL_jpy'] is not None),F(0)),
        'E0_ONLY_direct_guard_N':sum(r['set']=='E0_ONLY' and r['direct_guard'] for r in detail),
        'E0_ONLY_indirect_N':sum(r['set']=='E0_ONLY' and not r['direct_guard'] and r['miss_reason'] is not None for r in detail),
        'E0_ONLY_direct_guard_fixed_PnL_jpy':sum((r['E0_PnL_jpy'] for r in detail if r['set']=='E0_ONLY' and r['direct_guard'] and r['E0_PnL_jpy'] is not None),F(0)),
        'E0_ONLY_indirect_fixed_PnL_jpy':sum((r['E0_PnL_jpy'] for r in detail if r['set']=='E0_ONLY' and not r['direct_guard'] and r['miss_reason'] is not None and r['E0_PnL_jpy'] is not None),F(0)),
        'E0_ONLY_unknown_miss_reason_N':sum(r['set']=='E0_ONLY' and r['miss_reason'] is None for r in detail),
        'decomposed_delta_jpy':amount if both and known else None,'actual_final_delta_jpy':delta,
        'exact_match':amount==delta if both and known else None,'common_EXIT_contract_violations_N':len(violations),
        'attribution':'Accounting identity, not unique causal decomposition'}
    if both and known:assert amount==delta,(window,policy,'PnL identity')
    onlyh=[r for r in h.values() if r['entry_id'] not in e]
    tails=spectra(window,policy,onlyh)
    for r in tails:r['funding_set']='H_ONLY'
    examples=[]
    # Fixed ordering: timestamp, Entry ID; max missed winner / largest loser / worst H-only by actual saved PnL with that stable tie-break.
    eligible=[r for r in detail if r['set']=='E0_ONLY' and r['E0_PnL_jpy'] is not None]
    groups=[('MAXIMUM_E0_WINNER_MISSED',[r for r in eligible if r['E0_PnL_jpy']>0],lambda r:(-r['E0_PnL_jpy'],r['session'],r['entry_minute'],r['entry_id'])),
        ('LARGEST_E0_LOSER_NOT_PURCHASED',[r for r in eligible if r['E0_PnL_jpy']<0],lambda r:(r['E0_PnL_jpy'],r['session'],r['entry_minute'],r['entry_id'])),
        ('WORST_H_ONLY',[r for r in detail if r['set']=='H_ONLY' and r['H_PnL_jpy'] is not None],lambda r:(r['H_PnL_jpy'],r['session'],r['entry_minute'],r['entry_id']))]
    for kind,rr,order in groups:
        examples.append({'example_kind':kind,**min(rr,key=order)} if rr else {'example_kind':kind,'window_id':window,'policy':policy,'status':'NO_ELIGIBLE_EXAMPLE'})
    return preserve,summary,detail,tails,examples,violations

def fixed_global_examples(details):
    examples=[]
    for policy in ['H1','H2']:
        rr=[r for r in details if r['policy']==policy]
        groups=[('MAXIMUM_E0_WINNER_MISSED',[r for r in rr if r['set']=='E0_ONLY' and r['E0_PnL_jpy'] is not None and r['E0_PnL_jpy']>0],lambda r:-r['E0_PnL_jpy']),
            ('LARGEST_E0_LOSER_NOT_PURCHASED',[r for r in rr if r['set']=='E0_ONLY' and r['E0_PnL_jpy'] is not None and r['E0_PnL_jpy']<0],lambda r:r['E0_PnL_jpy']),
            ('WORST_H_ONLY',[r for r in rr if r['set']=='H_ONLY' and r['H_PnL_jpy'] is not None],lambda r:r['H_PnL_jpy'])]
        for kind,cohort,order in groups:
            picked=min(cohort,key=lambda r:(order(r),r['session'],r['entry_minute'],r['entry_id'],r['window_id'])) if cohort else None
            examples.append({'example_kind':kind,**picked} if picked else {'policy':policy,'example_kind':kind,'status':'NO_ELIGIBLE_EXAMPLE'})
    return examples

def preservation_contexts(details,vacancy_examples):
    out=[];grouped=defaultdict(list)
    for row in details:
        if row['set']=='H_ONLY':continue
        arrivals=vacancy_examples[row['window_id']+'_E0']['arrival_records']
        original=next(r for r in arrivals if r['entry_id']==row['entry_id'])
        context=(original['rank'],original['occupancy'],original['sd_seen'],original['time_band'],
            'FIRST_ENTRY' if original['purchase_sequence']==1 else 'SAME_SESSION_LATER',original['post_release_context'],row['R_bucket'])
        grouped[(row['window_id'],row['policy'],context)].append(row)
        grouped[('PRIMARY9_ACCOUNT_SUM',row['policy'],context)].append(row)
    for (window,policy,context),rr in sorted(grouped.items()):
        missed=[r for r in rr if r['set']=='E0_ONLY'];winners=[r for r in missed if r['R_E0_pct'] is not None and r['R_E0_pct']>0]
        out.append({'window_id':window,'policy':policy,'count_scope':'E0_FIXED_FUNDED_ACCOUNT_COHORT','E0_rank':context[0],
            'E0_occupancy':context[1],'E0_SD_release_seen':context[2],'E0_time_band':context[3],'E0_purchase_context':context[4],
            'E0_release_context':context[5],'E0_fixed_R_band':context[6],'E0_N':len(rr),'H_common_N':sum(r['set']=='COMMON' for r in rr),
            'H_not_purchased_N':len(missed),'E0_Winner_not_purchased_N':len(winners),
            'direct_guard_missed_N':sum(r['direct_guard'] for r in missed),'indirect_missed_N':sum(not r['direct_guard'] and r['miss_reason'] is not None for r in missed),
            'unknown_miss_reason_N':sum(r['miss_reason'] is None for r in missed),'unique_E0_Entry_N':len({r['entry_id'] for r in rr}),
            'E0_Winner_missed_fixed_PnL_jpy':sum((r['E0_PnL_jpy'] for r in winners),F(0)),
            'E0_missed_loser_fixed_loss_jpy':-sum((r['E0_PnL_jpy'] for r in missed if r['E0_PnL_jpy'] is not None and r['E0_PnL_jpy']<0),F(0)),
            'not_final_account_avoided_profit':True})
    return out

def divergence(window,policy,e0,h):
    e={r['entry_id']:r for r in e0['DECISIONS']};c={r['entry_id']:r for r in h['DECISIONS']}
    chronological=sorted(set(e)|set(c),key=lambda k:((e.get(k) or c[k])['session'],(e.get(k) or c[k])['minute'],k))
    fields=['reason','quantity','debit','slot_gate_action','slot_gate_reason']
    for key in chronological:
        er=e.get(key,{});hr=c.get(key,{})
        different=[f for f in fields if er.get(f)!=hr.get(f)]
        if different:return {'window_id':window,'policy':policy,'example_kind':'FIRST_CHRONOLOGICAL_DIVERGENCE','entry_id':key,
            'session':(er or hr)['session'],'minute':(er or hr)['minute'],'rank':(er or hr)['rank'],
            'difference_fields':different,'E0_decision':er,'H_decision':hr}
    return None

def summarize_arm(arm,allpaths,metrics):
    measured=[w for w in WINDOWS if complete(allpaths.get((w,arm)))]; full=len(measured)==9
    vals=[num(allpaths[w,arm]['result']['final_equity']) for w in measured]
    mm=[metrics[w,arm] for w in measured]
    ff=[r for w in measured for r in enriched(allpaths[w,arm])]
    subset={'mask':measured,'measured_N':len(measured),'final_equity':stats(vals),'profit':stats([v-START for v in vals]),
        'hit_2m_N':sum(v>=2000000 for v in vals),'red_window_N':sum(v<START for v in vals),
        'gross_loss_jpy':sum((m['gross_loss_jpy'] for m in mm),F(0)),
        'gross_positive_jpy':sum((m['gross_positive_jpy'] for m in mm),F(0)),
        'negative_day_N':sum(m['negative_day_N'] for m in mm),
        'worst_daily_PnL_jpy':min((m['worst_daily_PnL_jpy'] for m in mm if m['worst_daily_PnL_jpy'] is not None),default=None),
        'worst_trade_loss_jpy':max((m['worst_trade_loss_jpy'] for m in mm),default=None),
        'worst_trade_R_pct':min((m['worst_trade_R_pct'] for m in mm if m['worst_trade_R_pct'] is not None),default=None),
        'max_minute_MTM_MaxDD_pct':max((m['minute_MTM_MaxDD_pct'] for m in mm),default=None),
        'max_EOD_MaxDD_pct':max((m['EOD_MaxDD_pct'] for m in mm),default=None),
        'account_trade_N':len(ff),'unique_Entry_N':len({r['entry_id'] for r in ff})}
    for k in range(1,6):
        subset[f'R_LE_MINUS{k}_loss_jpy']=sum((m[f'R_LE_MINUS{k}_gross_loss_jpy'] for m in mm),F(0))
        subset[f'R_LE_MINUS{k}_N']=sum(m[f'R_LE_MINUS{k}_N'] for m in mm)
    return {'arm':arm,'full9_complete':full,'primary_denominator':9,'original_planned_denominator':21,
        'full9':subset if full else None,'measured_subset_auxiliary_only':subset if not full else None,
        'unknown_fixed9':[w for w in WINDOWS if w not in measured],'history12_status':'UNMEASURED_COVERAGE_UNKNOWN'}

def paired_summary(a,b,allpaths):
    mask=[w for w in WINDOWS if complete(allpaths.get((w,a))) and complete(allpaths.get((w,b)))];full=len(mask)==9
    av=[num(allpaths[w,a]['result']['final_equity']) for w in mask];bv=[num(allpaths[w,b]['result']['final_equity']) for w in mask];diff=[x-y for x,y in zip(av,bv)]
    out={'pair':f'{a}_minus_{b}','full9_complete':full,'denominator':9,'mask':mask,'both_known_subset_auxiliary_only':not full,
        'difference_stats':stats(diff) if full else None,'difference_of_medians':median(av)-median(bv) if full else None,
        'median_of_paired_differences':median(diff) if full else None,'difference_of_minima':min(av)-min(bv) if full else None,
        'minimum_paired_difference':min(diff) if full else None,'difference_of_maxima_not_paired_effect':max(av)-max(bv) if full else None,
        'improved_N':sum(v>0 for v in diff) if full else None,'equal_N':sum(v==0 for v in diff) if full else None,'worsened_N':sum(v<0 for v in diff) if full else None}
    if not full:out['auxiliary_subset']={'difference_stats':stats(diff),'improved_N':sum(v>0 for v in diff),'equal_N':sum(v==0 for v in diff),'worsened_N':sum(v<0 for v in diff)}
    return out

def receipt_status(name):
    p=PUB/name
    return read(p).get('status','UNKNOWN') if p.exists() else 'NOT_AVAILABLE'

def classify(policy,summaries,paired,allpaths,violations):
    e=summaries['E0']['full9'];h=summaries[policy]['full9'];p=paired[policy+'_minus_E0']
    sources={n:receipt_status(n) for n in ['E0_PARITY_RECEIPT.json','SYNTHETIC_TEST_RESULTS.json','INDEPENDENT_AUDIT.json','REPORT_METRICS_INDEPENDENT_CHECK.json','REPRODUCTION_RECEIPT.json']}
    full=e is not None and h is not None
    integrity=full and all(v=='PASS' for v in sources.values()) and not violations
    flags={};wealth=None;down=None
    if full:
        wealth=h['final_equity']['median']>e['final_equity']['median'] and p['difference_stats']['mean']>0 and p['difference_stats']['median']>0
        flags={'red_windows_nonincrease':h['red_window_N']<=e['red_window_N'],
            'minimum_final_nondecrease':h['final_equity']['min']>=e['final_equity']['min'],
            'gross_loss_nonincrease':h['gross_loss_jpy']<=e['gross_loss_jpy'],
            'R_LE_MINUS3_loss_nonincrease':h['R_LE_MINUS3_loss_jpy']<=e['R_LE_MINUS3_loss_jpy'],
            'R_LE_MINUS5_loss_nonincrease':h['R_LE_MINUS5_loss_jpy']<=e['R_LE_MINUS5_loss_jpy'],
            'minute_MTM_DD_nonincrease':h['max_minute_MTM_MaxDD_pct']<=e['max_minute_MTM_MaxDD_pct'],
            'EOD_DD_nonincrease':h['max_EOD_MaxDD_pct']<=e['max_EOD_MaxDD_pct']}
        down=all(flags.values())
    semantic_opportunities=sum(r['reason']=='ADMISSION_QUALITY_RESERVE' for w in WINDOWS for r in (allpaths[w,policy]['DECISIONS'] if allpaths.get((w,policy)) else []))
    no_effect=full and semantic_opportunities==0 and all(divergence(w,policy,allpaths[w,'E0'],allpaths[w,policy]) is None for w in WINDOWS)
    status='PARTIAL_INCONCLUSIVE'
    if integrity:
        if no_effect:status='NO_EFFECT'
        elif wealth and down:status='ADMISSION_DEVELOPMENT_PROGRESS_CANDIDATE'
        elif wealth:status='WEALTH_RISK_TRADEOFF_NOT_AUTO_SELECTED'
        elif h['gross_loss_jpy']<e['gross_loss_jpy']:status='LOSS_DEFENSE_ONLY_NO_WEALTH_PROGRESS'
        else:status='ADMISSION_NO_PROGRESS'
    auxiliary={}
    if full:
        for key in ['negative_day_N','worst_daily_PnL_jpy','worst_trade_loss_jpy','worst_trade_R_pct']+[f'R_LE_MINUS{k}_N' for k in range(1,6)]:
            nonworse=None if h[key] is None or e[key] is None else h[key]>=e[key] if key in ['worst_daily_PnL_jpy','worst_trade_R_pct'] else h[key]<=e[key]
            auxiliary[key]={'E0':e[key],'H':h[key],'nonworse':nonworse}
    return {'policy':policy,'status':status,'INTEGRITY':integrity,'INTEGRITY_status':'PASS' if integrity else 'CONTRACT_FAIL' if violations else 'PARTIAL',
        'WEALTH_PROGRESS':wealth,'DOWNSIDE_PRESERVED':down,'downside_flags':flags,'individual_loss_flags':auxiliary,
        'receipt_statuses':sources,'direct_guard_opportunities_N':semantic_opportunities,'loss_defense_classification_basis':'strict reduction of aggregate gross realized loss; all other flags remain explicit',
        'auto_selected':False,'new_OOS':False,'freshValidation':'NOT_RUN'}

def secondary(allpaths):
    data={a:pathdata('CHAIN38',a) for a in ARMS};chain={};legacy=[]
    for a,d in data.items():
        chain[a]={'status':d['result']['status'] if d else 'NOT_MEASURED','final_equity':num(d['result']['final_equity']) if complete(d) else None,
            'market_session_N':len(d['result']['planned_sessions']) if d else 38,'is_one_month_performance':False}
    baseline=data['E0'];sessions=baseline['result']['planned_sessions'] if baseline else []
    for index in range(19):
        rr={'legacy_id':f'L{index+1:02}','start':sessions[index] if len(sessions)>index else None,'end':sessions[index+19] if len(sessions)>index+19 else None,
            'market_session_N':20,'method':'1000000*ending_cash/cash_before_start','is_RESET20':False}
        for a,d in data.items():
            series=d['result']['daily_series'] if d else []
            good=complete(d) and len(series)>=index+20 and all(x['status']=='COMPLETE' for x in series[index:index+20])
            value=START*num(series[index+19]['ending_cash'])/num(series[index]['starting_cash']) if good else None
            rr[a+'_normalized_final']=value;rr[a+'_exact']=exact(value);rr[a+'_status']='COMPLETE' if good else 'UNMEASURED'
        for a in ['H1','H2']:rr[a+'_minus_E0']=rr[a+'_normalized_final']-rr['E0_normalized_final'] if rr[a+'_normalized_final'] is not None and rr['E0_normalized_final'] is not None else None
        legacy.append(rr)
    stats19={a:{'denominator':19,'full19_complete':all(r[a+'_normalized_final'] is not None for r in legacy),
        'normalized_final_stats':stats([r[a+'_normalized_final'] for r in legacy]) if all(r[a+'_normalized_final'] is not None for r in legacy) else None} for a in ARMS}
    return {'CHAIN38':chain,'LEGACY_NORMALIZED20':legacy,'LEGACY_NORMALIZED20_SUMMARIES':stats19,'L02':legacy[1],
        'historical_L02_old_EXIT_final':'1297031.03','historical_L02_saved_E0_final':'1306660.23',
        'secondary_does_not_override_primary':True}

def yen(v):return '未測定' if v is None else f'{Decimal(fmt(v)):,.2f}'
def markdown_table(records,fields):
    header='| '+' | '.join(label for key,label in fields)+' |\n| '+' | '.join('---' for _ in fields)+' |\n'
    return header+'\n'.join('| '+' | '.join(yen(r.get(k)) if isinstance(r.get(k),F) else str(r.get(k)) if r.get(k) is not None else '未測定' for k,label in fields)+' |' for r in records)

def report(table,summaries,paired,classification,cohort,decomps,secondary_result,violations,aggregate_spectrum):
    s=['# AD01：V5 × SHARP_DROP EXIT 空き枠Quality Admission','',
        '100万円・保有ゼロから独立開始した固定20市場営業日9窓。E0は保存済みV5＋新EXIT、H1は全新規AdmissionをS/Aに限定、H2は自armのSD全量決済・資金解放後のみ当日S/Aに限定。窓は重複し、9独立か月や新OOSではありません。','',
        markdown_table(table,[('window_id','窓'),('start','開始'),('end','終了'),('E0_final','E0終点円'),('H1_final','H1終点円'),('H2_final','H2終点円'),('H1_minus_E0','H1−E0円'),('H2_minus_E0','H2−E0円'),('H1_minus_H2','H1−H2円')]),'']
    s+=['## 同じ9窓の資産・対応差','']
    armrows=[]
    for a in ARMS:
        q=summaries[a]['full9'];armrows.append({'arm':a,**(q['final_equity'] if q else {}),'hit':f"{q['hit_2m_N']}/9" if q else '未確定','red':f"{q['red_window_N']}/9" if q else '未確定'})
    s+=[markdown_table(armrows,[('arm','arm'),('median','終点中央値'),('mean','平均'),('min','最小'),('max','最大'),('hit','200万円到達'),('red','赤字窓')]),'','測定済み固定9窓／元予定21窓。W01〜W12はcoverage未確定で未測定を維持。中央値同士の差と対応差中央値、最小値同士の差と最悪対応差を別々に示します。','']
    for policy in ['H1','H2']:
        p=paired[policy+'_minus_E0'];ds=p['difference_stats'] or {}
        s+=[f"{policy}−E0：対応差 min/mean/median/max = {yen(ds.get('min'))} / {yen(ds.get('mean'))} / {yen(ds.get('median'))} / {yen(ds.get('max'))}円。中央値同士の差={yen(p['difference_of_medians'])}円、最小値同士の差={yen(p['difference_of_minima'])}円。改善/同値/悪化={p['improved_N']}/{p['equal_N']}/{p['worsened_N']}窓。",'']
    s+=['旧構造EXIT Cの中央値1,245,688.10円はHISTORICAL_EXIT_COMPARATORです。HのE0改善と旧C超過は別の問いとして保持します。','', '## 損失と口座DD','']
    risk=[]
    for a in ARMS:
        q=summaries[a]['full9'] or {};risk.append({'arm':a,**q})
    s+=[markdown_table(risk,[('arm','arm'),('gross_loss_jpy','総実損円'),('R_LE_MINUS3_loss_jpy','R≤−3%損失円'),('R_LE_MINUS5_loss_jpy','R≤−5%損失円'),('negative_day_N','負け日'),('worst_daily_PnL_jpy','最悪日円'),('max_EOD_MaxDD_pct','最大EOD DD%'),('max_minute_MTM_MaxDD_pct','最大分足MTM DD%')]),'',
        '総実損・大Loser損失・EOD DD・分足MTM DDは別指標。負け日は重複9口座の合計です。最悪取引円/Rとtail件数はTAIL_AND_LOSS_METRICS.csvおよび判定JSONに全保存。','', '## 新EXITの全1%R帯・E0固定cohort','',
        'RETURN_SPECTRUM_BY_WINDOW.csvに排他的14帯と累積ALL_MINUS／−1〜−5%、ALL_PLUS／+1〜+5%を保存。R_UNKNOWNとZEROを独立扱いし、実funded分母とunique Entry分母を明示。E0_FIXED_COHORT_PRESERVATION.csvは元E0購入を固定し、直接Admission拒否、間接経路差、不明理由を分離しています。','']
    bandrows=[]
    for band in BANDS:
        record={'band':band}
        for arm in ARMS:
            source=next((r for r in aggregate_spectrum if r['arm']==arm and r['group']==band),None)
            record[arm+'_N']=source['group_N'] if source and summaries[arm]['full9_complete'] else None
            record[arm+'_PnL']=source['realized_PnL_jpy'] if source and summaries[arm]['full9_complete'] else None
        bandrows.append(record)
    s+=[markdown_table(bandrows,[('band','費用後R帯'),('E0_N','E0 N'),('H1_N','H1 N'),('H2_N','H2 N'),('E0_PnL','E0 PnL円'),('H1_PnL','H1 PnL円'),('H2_PnL','H2 PnL円')]),'']
    winner=[]
    for a in ['H1','H2']:
        for b in ['P5_PLUS','P4_5','P3_4','P2_3','P1_2','P0_1','ZERO']:
            rr=[r for r in cohort if r['policy']==a and r['E0_fixed_R_group']==b]
            known=paired[a+'_minus_E0']['full9_complete']
            winner.append({'arm':a,'group':b,'E0_N':sum(r['E0_N'] for r in rr) if known else None,'missed_N':sum(r['H_not_purchased_N'] for r in rr) if known else None,
                'direct_N':sum(r['direct_guard_reject_N'] for r in rr) if known else None,'fixed_missed_PnL':sum((r['E0_fixed_missed_PnL_jpy'] for r in rr),F(0)) if known else None,
                'common_quantity_delta':sum((r['COMMON_quantity_PnL_delta_jpy'] for r in rr),F(0)) if known else None})
    s+=[markdown_table(winner,[('arm','arm'),('group','元E0帯'),('E0_N','元購入N'),('missed_N','H未購入N'),('direct_N','直接guard N'),('fixed_missed_PnL','未購入元PnL円'),('common_quantity_delta','共通数量PnL差円')]),'',
        '元E0 Loserの未購入PnLは固定台帳の寄与であり、最終口座の回避利益ではありません。H_ONLYの全R分布・大Loser新流入はH_ONLY_RETURN_SPECTRUM.csv。共通EntryのEXIT/R差は性能差として扱わず契約違反とします。','',
        '## 拒否・待機・資金経路','',
        'ADMISSION_REASON_AND_SUPPORT.csvとCAPITAL_LOCK_AND_VACANCY.csvにrank、occupancy、当日SD実解放前後、元14:00/14:30区分、初回／後続購入、通常EXIT後／SD後、拒否後の適格到着・後続購入・終日待機を記録。市場時間は元grid（09:00–11:30、12:30–15:30）で昼休みを除外。待機時間や稼働率だけで成功判定しません。','',
        markdown_table(decomps,[('window_id','窓'),('policy','H'),('COMMON_quantity_jpy','共通数量差円'),('H_ONLY_PnL_jpy','H_ONLY PnL円'),('E0_ONLY_PnL_jpy','E0_ONLY PnL円'),('actual_final_delta_jpy','終点差円'),('exact_match','exact恒等式')]),'',
        '直接EXIT差は0が期待値。数量差＋H_ONLY−E0_ONLYは会計恒等式であり、一意の因果帰属ではありません。最初の差、最大Winner未購入、大Loser未購入、最悪H_ONLYの例は事前固定順でprivate保存。公開版は匿名の分類だけです。','',
        'CHAIN38は38市場sessionの終点で、1か月成績ではありません。CHAIN38_AND_LEGACY20_RESULTS.jsonに全19 LEGACY_NORMALIZED20とL02（2025-06-30〜2025-07-30）を保存。RESET20の代替にせず、SecondaryだけでPrimary悪化を救済しません。','',
        '## 完了・検算・再現・保存状態','']
    s+=[f"{a}：固定9窓の完了={9-len(summaries[a]['unknown_fixed9'])}/9。" for a in ARMS]
    s+=['',f"E0接続検証={receipt_status('E0_PARITY_RECEIPT.json')}、別実装検算={receipt_status('INDEPENDENT_AUDIT.json')}、決定論的再現={receipt_status('REPRODUCTION_RECEIPT.json')}、共通EXIT契約差={len(violations)}件。",
        '計算／公開保存／読戻しは別status。コンパイラ実行時点の保存・実GET状態はCURRENT_STATE.jsonとREADBACK receiptが権威となり、本報告の生成だけで外部保存や読戻しを認定しません。','', '## 判定と次の問い','']
    for a in ['H1','H2']:
        q=classification[a];s+=[f"{a}: **{q['status']}**。INTEGRITY={q['INTEGRITY_status']}、WEALTH_PROGRESS={q['WEALTH_PROGRESS']}、DOWNSIDE_PRESERVED={q['DOWNSIDE_PRESERVED']}。",'']
    good=[a for a in ['H1','H2'] if classification[a]['status']=='ADMISSION_DEVELOPMENT_PROGRESS_CANDIDATE']
    if all(summaries[a]['full9_complete'] for a in ARMS):
        base=summaries['E0']['full9'];h1=summaries['H1']['full9'];h2=summaries['H2']['full9']
        s+=[f"総実損と大Loser損失は両Hで減りましたが、最大分足MTM DDはE0 {yen(base['max_minute_MTM_MaxDD_pct'])}%→H1 {yen(h1['max_minute_MTM_MaxDD_pct'])}%／H2 {yen(h2['max_minute_MTM_MaxDD_pct'])}%へ両方悪化。H1の最小終点は{yen(base['final_equity']['min'])}円→{yen(h1['final_equity']['min'])}円へ低下し、H2の負け日は{base['negative_day_N']}→{h2['negative_day_N']}（+{h2['negative_day_N']-base['negative_day_N']}日）。損失防御の全面PASSとは呼びません。",'']
        s+=[f"H2は終点中央値同士の差が+{yen(paired['H2_minus_E0']['difference_of_medians'])}円でも、対応窓差中央値が{yen(paired['H2_minus_E0']['median_of_paired_differences'])}円のため、事前WEALTH_PROGRESSの同時条件を満たしません。",'']
    if good:s+=['次の問い1つ：この固定Admission候補を研究本線へ採用し、未使用期間で別評価するか。今回の比較では採用しません。']
    else:s+=['次のAdmission情報仮説1つ：購入判断時点で既に確定した直近State9遷移が、固定S/A帯の中で新EXIT下の実現利益を区別する助けになるか。別の事前設計で検証する提案だけを残し、今回は実装・計算しません。']
    s+=['','mainCapital=CAPITAL_MAX3_SLOT_RESERVE_V1、mainExit=SHARP_DROP_FIRST_OBSERVED_EXIT_V0を維持。selectedAdmissionCandidate=null。FIRST LAYER／Ranking／EXIT／sizing変更なし。新policy2個、freshValidation=NOT_RUN、productionReady=false。Safety9すべてfalse。STOP。','']
    (PUB/'REPORT-ja.md').write_text('\n'.join(s))

def compile_all():
    from vacancy_metrics import analyze_vacancy, aggregate_vacancy
    allpaths={};metrics={};table=[];spectrum=[];loss=[];cohort=[];decomps=[];details=[];tails=[];examples=[];violations=[];reason=[];capital=[];vacancy_examples={};first=[]
    vacancy_analyses=defaultdict(list)
    for window in WINDOWS:
        for arm in ARMS:allpaths[window,arm]=pathdata(window,arm)
        source=allpaths[window,'E0'];res=source['result'] if source else {}
        rec={'window_id':window,'start':res.get('start_session'),'end':res.get('end_session'),'market_session_N':20,
            'calendar_span_days':res.get('calendar_span_inclusive_days'),'initial_cash_jpy':START}
        for arm in ARMS:
            data=allpaths[window,arm];ok=complete(data)
            rec[arm+'_status']=data['result']['status'] if data else 'UNMEASURED'
            final=num(data['result']['final_equity']) if ok else None
            rec.update({arm+'_final':final,arm+'_profit':final-START if final is not None else None,
                arm+'_return_pct':(final/START-1)*100 if final is not None else None,
                arm+'_hit_2m':final>=2000000 if final is not None else None,arm+'_red_window':final<START if final is not None else None})
            if not data:continue
            ff=enriched(data);met=loss_metrics(data,ff);metrics[window,arm]=met
            spectrum+=spectra(window,arm,ff);loss.append({'window_id':window,'arm':arm,'status':rec[arm+'_status'],**met})
            rr,cc,ee=analyze_vacancy(window,arm,data,ff);reason+=rr;capital+=cc;vacancy_examples[window+'_'+arm]=ee
            vacancy_analyses[arm].append((rr,cc,ee))
        for a,b in [('H1','E0'),('H2','E0'),('H1','H2')]:rec[a+'_minus_'+b]=rec[a+'_final']-rec[b+'_final'] if rec[a+'_final'] is not None and rec[b+'_final'] is not None else None
        rec['full_three_arm_complete']=all(complete(allpaths[window,a]) for a in ARMS);table.append(rec)
        for arm in ['H1','H2']:
            if source and allpaths[window,arm]:
                pp,ss,dd,tt,ee,vv=compare(window,arm,source,allpaths[window,arm]);cohort+=pp;decomps.append(ss);details+=dd;tails+=tt;examples+=ee;violations+=vv
                d=divergence(window,arm,source,allpaths[window,arm])
                if d:first.append(d)
    for arm,analyses in vacancy_analyses.items():
        measured_N=sum(complete(allpaths[w,arm]) for w in WINDOWS)
        scope='PRIMARY9_ACCOUNT_SUM' if measured_N==9 else 'MEASURED_SUBSET_AUXILIARY_ACCOUNT_SUM'
        for unique in [False,True]:
            rr,cc,ee=aggregate_vacancy(analyses,scope=scope if not unique else scope.replace('ACCOUNT_SUM','UNIQUE_ENTRY_CONTEXT'),unique=unique)
            for r in rr+cc:r.update(fixed_primary_denominator=9,complete_account_N=measured_N,full9_complete=measured_N==9)
            reason+=rr;capital+=cc
    summaries={a:summarize_arm(a,allpaths,metrics) for a in ARMS}
    paired={a+'_minus_'+b:paired_summary(a,b,allpaths) for a,b in [('H1','E0'),('H2','E0'),('H1','H2')]}
    classification={a:classify(a,summaries,paired,allpaths,[r for r in violations if r['policy']==a]) for a in ['H1','H2']}
    historical=[]
    candidates=list((ROOT/'inputs').glob('*COVERAGE*'))+list((ROOT/'baseline').rglob('S6_COVERAGE_AND_WINDOWS.json'))
    original_windows={}
    for p in candidates:
        try:original_windows.update({r['window_id']:r for r in read(p).get('windows',[])})
        except (ValueError,KeyError):pass
    for i in range(1,13):
        w=f'W{i:02}';r=original_windows.get(w,{})
        historical.append({'window_id':w,'start':r.get('start_session'),'end':r.get('end_session'),'status':'UNMEASURED_COVERAGE_UNKNOWN',
            'E0_final':None,'H1_final':None,'H2_final':None,'zero_imputed':False,'calendar_source':'ORIGINAL_S6' if r else 'DATE_UNKNOWN_NO_REGENERATION'})
    secondary_result=secondary(allpaths)
    chain_spectrum=[];chain_loss=[];chain_cohort=[];chain_decomps=[];chain_detail=[];chain_reason=[];chain_capital=[]
    chain_data={a:pathdata('CHAIN38',a) for a in ARMS}
    for arm,data in chain_data.items():
        if not data:continue
        ff=enriched(data);chain_spectrum+=spectra('CHAIN38',arm,ff);chain_loss.append({'window_id':'CHAIN38','arm':arm,'status':data['result']['status'],**loss_metrics(data,ff)})
        rr,cc,ee=analyze_vacancy('CHAIN38',arm,data,ff);chain_reason+=rr;chain_capital+=cc;vacancy_examples['CHAIN38_'+arm]=ee
    for arm in ['H1','H2']:
        if chain_data['E0'] and chain_data[arm]:
            pp,ss,dd,tt,ee,vv=compare('CHAIN38',arm,chain_data['E0'],chain_data[arm]);chain_cohort+=pp;chain_decomps.append(ss);chain_detail+=dd
            if vv:violations+=vv
    csvsave(PUB/'CHAIN38_RETURN_SPECTRUM.csv',chain_spectrum);csvsave(PUB/'CHAIN38_TAIL_AND_LOSS_METRICS.csv',chain_loss)
    csvsave(PUB/'CHAIN38_E0_FIXED_COHORT_PRESERVATION.csv',chain_cohort);csvsave(PUB/'CHAIN38_FUNDING_AND_PNL_DECOMPOSITION.csv',chain_decomps)
    csvsave(PUB/'CHAIN38_ADMISSION_REASON_AND_SUPPORT.csv',chain_reason);csvsave(PUB/'CHAIN38_CAPITAL_LOCK_AND_VACANCY.csv',chain_capital)
    csvsave(PRI/'CHAIN38_FUNDING_AND_PNL_DECOMPOSITION.csv',chain_detail)
    classification={a:classify(a,summaries,paired,allpaths,[r for r in violations if r['policy']==a]) for a in ['H1','H2']}
    examples=fixed_global_examples(details)
    csvsave(PUB/'E0_FIXED_COHORT_VACANCY_CONTEXT.csv',preservation_contexts(details,vacancy_examples))
    aggregate_spectrum=[];unique_spectrum=[]
    for arm in ARMS:
        allfunded=[r for w in WINDOWS if allpaths.get((w,arm)) for r in enriched(allpaths[w,arm])]
        if len([w for w in WINDOWS if complete(allpaths.get((w,arm)))])!=9:
            allfunded=[r for w in WINDOWS if complete(allpaths.get((w,arm))) for r in enriched(allpaths[w,arm])]
        current=spectra('PRIMARY9_ACCOUNT_SUM' if summaries[arm]['full9_complete'] else 'MEASURED_SUBSET_AUXILIARY_ACCOUNT_SUM',arm,allfunded)
        for row in current:row.update(full9_complete=summaries[arm]['full9_complete'],fixed_primary_denominator=9)
        aggregate_spectrum+=current
        for group in BANDS+CUMULATIVE:
            selected=[r for r in allfunded if ingroup(r,group)]
            unique_spectrum.append({'arm':arm,'count_scope':'UNIQUE_MARKET_ENTRY_NO_REPRESENTATIVE_ACCOUNT_QUANTITY',
                'group':group,'group_type':'EXCLUSIVE' if group in BANDS else 'CUMULATIVE','unique_Entry_N':len({r['entry_id'] for r in selected}),
                'unique_funded_denominator_N':len({r['entry_id'] for r in allfunded}),'account_trade_N':len(selected),
                'monetary_quantity_aggregation':'UNDEFINED_FOR_UNIQUE_COHORT_NO_ACCOUNT_SELECTED','full9_complete':summaries[arm]['full9_complete']})
    csvsave(PUB/'PRIMARY9_AGGREGATE_RETURN_SPECTRUM.csv',aggregate_spectrum);csvsave(PUB/'UNIQUE_ENTRY_RETURN_SPECTRUM.csv',unique_spectrum)
    csvsave(PUB/'RESET20_WINDOW_RESULTS.csv',table);save(PUB/'RESET20_ARM_SUMMARIES.json',summaries);save(PUB/'RESET20_PAIRED_DIFFERENCE_SUMMARY.json',paired)
    csvsave(PUB/'HISTORICAL_UNMEASURED_WINDOWS.csv',historical);csvsave(PUB/'RETURN_SPECTRUM_BY_WINDOW.csv',spectrum)
    csvsave(PUB/'E0_FIXED_COHORT_PRESERVATION.csv',cohort);csvsave(PUB/'TAIL_AND_LOSS_METRICS.csv',loss)
    csvsave(PUB/'ADMISSION_REASON_AND_SUPPORT.csv',reason);csvsave(PUB/'BASELINE_VACANCY_DIAGNOSTIC.csv',[r for r in reason if r['arm']=='E0'])
    csvsave(PUB/'CAPITAL_LOCK_AND_VACANCY.csv',capital);csvsave(PUB/'FUNDING_AND_PNL_DECOMPOSITION.csv',decomps)
    csvsave(PUB/'H_ONLY_RETURN_SPECTRUM.csv',tails);csvsave(PRI/'FUNDING_AND_PNL_DECOMPOSITION.csv',details)
    save(PRI/'VACANCY_WAIT_EXAMPLES.json',{key:{k:v for k,v in value.items() if k!='market_curve_records'} for key,value in vacancy_examples.items()});save(PRI/'COMMON_EXIT_CONTRACT_VIOLATIONS.json',violations)
    save(PUB/'COMMON_EXIT_CONTRACT_VIOLATIONS.json',{'count':len(violations),'affected_windows':sorted({r['window_id'] for r in violations})})
    selected_first={a:min([r for r in first if r['policy']==a],key=lambda r:(r['session'],r['minute'],r['entry_id'],r['window_id']),default=None) for a in ['H1','H2']}
    save(PRI/'FIRST_DIVERGENCE.json',{'first_by_policy':selected_first,'fixed_order_examples':examples,'selection_rules':'First difference chronological; maximum missed E0 Winner/largest missed E0 Loser/worst H_ONLY by saved PnL then timestamp then exact Entry ID.'})
    save(PUB/'FIRST_DIVERGENCE.json',{'first_by_policy':{a:public_example(r) for a,r in selected_first.items()},'anonymous_examples':[public_example(r) for r in examples],
        'individual_details_private':True,'chronological_selection':True,'posthoc_rule_changes':0})
    save(PUB/'CHAIN38_AND_LEGACY20_RESULTS.json',secondary_result);save(PUB/'ADMISSION_CLASSIFICATION.json',classification)
    grid_source=ROOT/'native/replay.py';grid_bytes=grid_source.read_bytes()
    inherited_line=next(line.strip() for line in grid_bytes.decode().splitlines() if 'samples=[c for c in primary_curves' in line)
    assert '540<=c[\'minute\']<690 or 750<=c[\'minute\']<930' in inherited_line,'NATIVE_MARKET_GRID_SOURCE_CHANGED'
    save(PUB/'MARKET_TIME_METRIC_CONTRACT.json',{'market_grid_intervals_half_open':[[540,690],[750,930]],'market_minutes_per_complete_session':330,
        'source_path':'research/capital-v5-max3-slot-intelligence-20261004-v1/replay.py','source_commit':'710656491be06235901b45c50a8b5cbd714ba4eb',
        'source_git_blob':hashlib.sha1(b'blob '+str(len(grid_bytes)).encode()+b'\0'+grid_bytes).hexdigest(),'source_sha256':hashlib.sha256(grid_bytes).hexdigest(),
        'source_exact_expression':inherited_line,'includes_market_time_after_1520_until_1530':True,'lunch_excluded':True,
        'trade_lock_definition':'exact funded BUY debit * count(existing market grid intersect [entry_minute, actual_release_minute))',
        'wallclock_lock_if_any':'Not used by AD01 primary capital lock or occupancy; prior historical artifacts remain preserved as prior definitions.',
        'weighted_cash_utilization_ratios':'Exact sum cash/equity and exposure/equity over saved market samples; Decimal80 arithmetic-time-mean display is separately labeled and never used for gates.'})
    proposed=[a for a in ['H1','H2'] if classification[a]['status']=='ADMISSION_DEVELOPMENT_PROGRESS_CANDIDATE']
    if proposed:proposed.sort(key=lambda a:(-summaries[a]['full9']['final_equity']['median'],-paired[a+'_minus_E0']['median_of_paired_differences'],-paired[a+'_minus_E0']['difference_stats']['mean'],summaries[a]['full9']['max_minute_MTM_MaxDD_pct']))
    save(PUB/'ANALYSIS_COMPILATION_RECEIPT.json',{'status':'COMPLETE_FIXED9' if all(r['full_three_arm_complete'] for r in table) else 'PARTIAL_FIXED9',
        'mainCapital':'CAPITAL_MAX3_SLOT_RESERVE_V1','mainExit':SD_EXIT,'selectedAdmissionCandidate':None,'proposedAdmissionCandidate':proposed[0] if proposed else None,
        'firstLayerChanged':False,'rankChanged':False,'exitChanged':False,'sizingFunctionChanged':False,'newAdmissionPolicies':2,
        'existingArtifactsOverwritten':False,'freshValidation':'NOT_RUN','productionReady':False,'public_individual_data':False,
        'decimal_format_is_presentation_only':True,'arithmetic':'Fraction from exact saved decimal money; boundary/identity/classification exact',
        'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'calculation_status':'COMPLETE' if all(r['full_three_arm_complete'] for r in table) else 'PARTIAL','files_saved':'LOCAL_GENERATED','readback_status':'NOT_CERTIFIED_BY_COMPILER'})
    report(table,summaries,paired,classification,cohort,decomps,secondary_result,violations,aggregate_spectrum)
    print(json.dumps({'primary_full9':all(r['full_three_arm_complete'] for r in table),'classifications':{a:r['status'] for a,r in classification.items()},'common_EXIT_violations':len(violations)}))
    return {'summaries':summaries,'paired':paired,'classification':classification}

if __name__=='__main__':compile_all()
