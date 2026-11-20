"""Replay only the two new arms on immutable frozen P1_Q70 fills."""
import collections
from exit_common import *

def next_sell(a,day,t):
    x=a[(a[:,0]>=t)&np.isin(a[:,0],sell_starts(day))]
    if len(x): return int(x[0,0]),float(x[0,1]),'NEXT_AVAILABLE_REGULAR_RAW_OPEN'
    x=a[a[:,0]==close_minute(day)]
    if len(x) and close_minute(day)>=t:return close_minute(day),float(x[-1,4]),'PREPLANNED_CLOSING_AUCTION_CLOSE'
    return None,None,'SOURCE_UNAVAILABLE'

def baseline(e,a,indices,grid,pred,fold,meta):
    counter=0;previous=None;trace=[];intent=None;reason='SESSION_CLOSE'
    for i in indices:
        r=grid[i];t=r['intent_minute']
        if t<=e['fill_minute']:continue
        p=float(pred[i]);assert math.isfinite(p)
        assert r['closed_raw_start']+1==t and r['feature_max_timestamp']<=r['intent_timestamp']
        m=meta[i];assert m['state_as_of_minute'] is None or m['state_as_of_minute']<=t
        if previous is None or t!=previous+1 or (previous<=690 and t>=751):counter=0
        counter=counter+1 if p<=0 else 0
        trace.append({'row_index':int(i),'decision_minute':t,'prediction':p,'nonpositive_counter':counter,'fold':int(fold[i]),'feature_max_timestamp':r['feature_max_timestamp'],'state_as_of_minute':m['state_as_of_minute'],'formal_primary':m['formal_primary'],'source_status':m['source_status']})
        previous=t
        if counter>=2:intent=t;reason='CONTINUATION_VALUE_NONPOSITIVE_TWICE';break
    if intent is None:intent=900 if e['session']<'2024-11-05' else 925
    minute,raw,kind=next_sell(a,e['session'],intent)
    return {'arm':'STATE_EXIT','watch_key':e['watch_key'],'session':e['session'],'symbol':e['symbol'],'entry_minute':e['fill_minute'],'entry_fill_price':e['fill_price'],'entry_first_intent_row_index':e['first_intent']['row_index'],'entry_fold':e['first_intent']['fold'],'exit_intent_minute':intent,'exit_reason':reason,'sell_minute':minute,'sell_timestamp':stamp(e['session'],minute) if minute is not None else None,'sell_reference_price':raw,'sell_fill_price':sell_price(raw) if raw is not None else None,'fill_kind':kind,'exit_status':'SELL_FILLED' if raw is not None else 'UNRESOLVED_SOURCE','decision_N':len(trace),'decision_after_sell':0,'reentry_calls':0,'Hard1_trigger':False,'Hard1_trigger_kind':None,'Hard1_line_raw':e['fill_price']*.99},trace

def hard_arm(base,trace,a,day):
    h=dict(base);h['arm']='STATE_EXIT_HARD1';line=base['Hard1_line_raw'];hit=None
    for row in a:
        m=int(row[0])
        if m<base['entry_minute'] or m not in sell_starts(day):continue
        # A pending/fresh canonical market sell at this open closes first.
        if base['sell_minute'] is not None and m>=base['sell_minute']:break
        if row[1]<=line:hit=(m,float(row[1]),'GAP_OPEN_AT_OR_BELOW_LINE');break
        if row[3]<=line:hit=(m,line,'INTRABAR_LOW_TOUCH');break
    if hit:
        m,raw,kind=hit
        cutoff=(lambda x:x['decision_minute']<m) if kind.startswith('GAP') else (lambda x:x['decision_minute']<=m)
        trace=[x for x in trace if cutoff(x)]
        h.update(Hard1_trigger=True,Hard1_trigger_kind=kind,exit_intent_minute=None,exit_reason='HARD1_STANDING_RISK_LINE',sell_minute=m,sell_timestamp=stamp(day,m),sell_reference_price=raw,sell_fill_price=sell_price(raw),fill_kind='OHLC_STOP_PROXY',exit_status='SELL_FILLED',decision_N=len(trace))
    return h,trace

def evaluate(r,e,a):
    fill=e['fill_price'];m=r['sell_minute'];day=e['session']
    r.update(entry_observed_MFE_pct=e['remaining_upside_pct'],entry_remaining_source_complete=e['remaining_source_complete'],selector_observed_MFE_pct=e['selector_to_high_pct'])
    if m is None:
        r.update(realized_return_pct=None,held_observed_MFE_pct=None,Peak_Giveback_pp=None,opportunity_giveback_pp=None,MFE_realization_pct=None,holding_active_min=None,execution_path_complete=False,missing_eligible_regular_bars_N=None)
    else:
        ret=100*(r['sell_fill_price']/fill-1);held=a[(a[:,0]>e['fill_minute'])&(a[:,0]<m)]
        peak=max([fill]+list(held[:,2]));hmfe=100*(peak/fill-1);mfe=e['remaining_upside_pct']
        scheduled=[x for x in sell_starts(day) if e['fill_minute']<=x<m];missing=set(scheduled)-set(map(int,a[:,0]))
        r.update(realized_return_pct=ret,held_observed_MFE_pct=hmfe,Peak_Giveback_pp=hmfe-ret,opportunity_giveback_pp=mfe-ret if mfe is not None else None,MFE_realization_pct=100*ret/mfe if mfe is not None and mfe>0 else None,holding_active_min=active_elapsed(day,e['fill_minute'],m),execution_path_complete=not missing,missing_eligible_regular_bars_N=len(missing))
    future=a[a[:,0]>m] if m is not None else np.empty((0,7));same=a[a[:,0]==m] if m is not None else np.empty((0,7))
    latermax=float(max(future[:,2])) if len(future) else None
    future_scheduled=sorted(regular(day)+[690,close_minute(day)])
    future_missing=[x for x in future_scheduled if m is not None and x>m and x not in set(map(int,a[:,0]))]
    r['post_sell_remaining_source_complete']=m is not None and not future_missing
    r['strictly_after_sell_observed_High_pct']=100*(latermax/fill-1) if latermax is not None else None
    for level in (3,5):
        target=fill*(1+level/100)
        r[f'later_winner_{level}_observed']=bool(latermax is not None and latermax>=target)
        r[f'later_winner_{level}_status']='OBSERVED_HIT' if r[f'later_winner_{level}_observed'] else 'KNOWN_NO_HIT' if r['post_sell_remaining_source_complete'] else 'UNKNOWN_INCOMPLETE_SOURCE'
        r[f'stop_bar_only_winner_{level}_order_ambiguous']=bool(r['Hard1_trigger'] and len(same) and same[0,2]>=target and not r[f'later_winner_{level}_observed'])
    return r

def run():
    assert not (HERE/'STATE_EXIT_RECORDS.jsonl.gz').exists(),'NO_REPLAY_REGENERATION'
    assert read(HERE/'FIT_LEDGER.json')['fits_completed']==5
    grid=list(lines(ENTRY/'PERSISTENT_GRID.jsonl.gz'));meta=list(lines(ENTRY/'STATE_FEATURE_METADATA.jsonl.gz'));entries=[r for r in lines(ENTRY/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'];assert len(entries)==1600
    source=read(SOURCE);bywatch=collections.defaultdict(list)
    with np.load(HERE/'PRIVATE_INPUTS/exit_oof.npz') as z:
        pred=np.full(len(grid),np.nan);fold=np.zeros(len(grid),int);pred[z['row_indices']]=z['predictions'];fold[z['row_indices']]=z['fold']
    for i,r in enumerate(grid):
        if r['canonical']:bywatch[r['watch_key']].append(i)
    base_records=[];hard_records=[];traces=[]
    for e in entries:
        a=clean(source[e['watch_key']]['today']);b,bt=baseline(e,a,bywatch[e['watch_key']],grid,pred,fold,meta);h,ht=hard_arm(b,bt,a,e['session'])
        base_records.append(evaluate(b,e,a));hard_records.append(evaluate(h,e,a))
        for arm,trace in (('STATE_EXIT',bt),('STATE_EXIT_HARD1',ht)):
            traces.append({'arm':arm,'watch_key':e['watch_key'],'decisions':trace,'decision_after_sell':0,'Entry_repeated':0,'Reentry':0})
    write_lines(HERE/'STATE_EXIT_RECORDS.jsonl.gz',base_records);write_lines(HERE/'STATE_EXIT_HARD1_RECORDS.jsonl.gz',hard_records);write_lines(HERE/'EXIT_DECISION_TRACES.jsonl.gz',traces)
    paired=[]
    for b,h in zip(base_records,hard_records):
        known=b['realized_return_pct'] is not None and h['realized_return_pct'] is not None
        paired.append({'watch_key':b['watch_key'],'session':b['session'],'paired_known':known,'STATE_EXIT_return_pct':b['realized_return_pct'],'STATE_EXIT_HARD1_return_pct':h['realized_return_pct'],'delta_return_pp':h['realized_return_pct']-b['realized_return_pct'] if known else None,'Hard1_trigger':h['Hard1_trigger'],'saved_negative_loss':bool(known and h['Hard1_trigger'] and b['realized_return_pct']<0 and h['realized_return_pct']>b['realized_return_pct']),'both_execution_path_complete':b['execution_path_complete'] and h['execution_path_complete'],'entry_observed_MFE_pct':b['entry_observed_MFE_pct'],'later_winner_3_cut':h['Hard1_trigger'] and h['later_winner_3_observed'],'later_winner_5_cut':h['Hard1_trigger'] and h['later_winner_5_observed'],'reentry':0})
    write_lines(HERE/'PAIRED_EXIT_DELTAS.jsonl.gz',paired)
    write(HERE/'TWO_ARM_REPLAY_RECEIPT.json',{'saved_at_jst':now(),'Frozen_Entry_N':1600,'sessions':len(set(e['session'] for e in entries)),'arms':{'STATE_EXIT':{'N':len(base_records),'filled_N':sum(r['exit_status']=='SELL_FILLED' for r in base_records),'records_sha256':sha(HERE/'STATE_EXIT_RECORDS.jsonl.gz')},'STATE_EXIT_HARD1':{'N':len(hard_records),'filled_N':sum(r['exit_status']=='SELL_FILLED' for r in hard_records),'records_sha256':sha(HERE/'STATE_EXIT_HARD1_RECORDS.jsonl.gz')}},'paired_known_N':sum(p['paired_known'] for p in paired),'OOF_lineage_sha256':sha(HERE/'OOF_LINEAGE_RECEIPT.json'),'traces_sha256':sha(HERE/'EXIT_DECISION_TRACES.jsonl.gz'),'Hard1_extra_fit':0,'old_EXIT_replay':0,'Entry_regeneration':0,'Reentry':0,'Capital':0,'Portfolio_Replay':0,'orders':0,'provider':0,'protected':0,'safety':SAFETY})
    print(json.dumps({'new_arms_replayed':2,'frozen_entries':1600,'paired_known':sum(p['paired_known'] for p in paired),'Hard1_trigger_N':sum(h['Hard1_trigger'] for h in hard_records)}),flush=True)
if __name__=='__main__':run()
