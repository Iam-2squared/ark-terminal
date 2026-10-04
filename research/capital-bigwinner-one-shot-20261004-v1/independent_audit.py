"""Independent Fraction replay and scalar scoring; imports no Primary logic.

Shared I/O limitation: both implementations use the same original provider cache,
Frozen Entry/State/Path/EXIT lineage and fixed fitted logistic coefficients.
This verifies causal projection/accounting agreement, not external market truth.
"""
from collections import defaultdict,Counter
from datetime import datetime
from fractions import Fraction as F
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import median
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
P=ROOT.parent/'bigwinner_private'
OUT=ROOT/'docs/evidence/capital-bigwinner-one-shot-20261004-v1'

def read(path):return [json.loads(r) for r in gzip.open(path,'rt')]
def output(path,value):
    with Path(path).open('x') as file:json.dump(value,file,indent=2,sort_keys=True);file.write('\n')
def minute(t):
    t=datetime.fromisoformat(t)
    return t.hour*60+t.minute
def actual(row,auction=False):
    try:
        if not row.get('lineage'):return False
        o,h,l,c,v,a=[F(str(row[k])) for k in ('O','H','L','C','Vo','Va')]
        return min(o,h,l,c,v,a)>0 and l<=min(o,c) and max(o,c)<=h and (not auction or o==h==l==c)
    except Exception:return False

def independent_features(e,trace):
    t=e['fill_minute']
    past=[]
    for row in trace:
        if row['bar_end_minute']<=t:past.append(row)
    def observed(row):
        return (row['state']['current_semantics_observed'] and row['state']['observed_at']==row['state']['as_of']
                and row['state']['numeric_status']=='ACCEPTED' and row['path']['Primary_or_null'] is not None)
    latest=past[-1] if past else None
    known=bool(latest and observed(latest));s=latest['state'] if latest else {};p=latest['path'] if latest else {}
    intent=e['first_intent'];unknown='__UNKNOWN__'
    numeric={
        'entry/p1_score':intent.get('score'),'entry/p1_threshold':intent.get('threshold'),
        'entry/intent_clock':intent.get('intent_minute'),'entry/fill_clock':t,
        'entry/intent_to_fill_active_delay':e.get('intent_to_fill_active_delay'),
        'selector/first_clock':e.get('selector_minute'),'selector/to_intent_active_delay':e.get('selector_to_intent_active_delay'),
        'selector/to_entry_active_delay':e.get('selector_to_entry_active_delay'),
        'selector/raw_entry_vs_first_price_pct':float((F(str(e['fill_price']))/F('1.0005')/F(str(e['selector_price']))-1)*100),
        'state/observed':int(known),'state/context_direction':p.get('context_direction') if known else None,
        'state/local_direction':p.get('local_direction') if known else None,
        'state/fast_applicable':int(p.get('fast_applicable_to_primary',False)) if known else None,
        'state/stop_count':(s.get('stop') or {}).get('count') if known else None,
        'path/dwell_observed_bars':p.get('dwell_observed_bars') if known else None,
        'path/dwell_scheduled_bars':p.get('dwell_scheduled_bars') if known else None,
    }
    changes=[];breaks=losses=0
    for row in past:
        for event in row.get('path_events',[]):
            if event['event_type']=='TRANSITION':changes.append(row['bar_end_minute'])
            elif event['event_type']=='SEGMENT_BREAK':breaks+=1
            elif event['event_type']=='OBSERVATION_LOST':losses+=1
    numeric.update({'path/transitions_total':len(changes),'path/segment_breaks_total':breaks,
        'path/observation_losses_total':losses,'path/observed_prefix_rows':sum(observed(row) for row in past),
        'path/last_transition_age_minutes':t-changes[-1] if changes else None})
    for width in (15,30,60):
        numeric[f'path/transitions_{width}m']=sum(t-width<m<=t for m in changes)
        numeric[f'path/observed_rows_{width}m']=sum(t-width<row['bar_end_minute']<=t and observed(row) for row in past)
    start=len(past)
    if known:
        start=len(past)-1
        while start>0:
            a,b=past[start-1],past[start]
            if not observed(a) or a['path']['causal_segment_id']!=b['path']['causal_segment_id'] or a['path']['scheduled_t']+1!=b['path']['scheduled_t']:break
            start-=1
    seq=[]
    for row in past[start:]:
        if not seq or row['path']['Primary_or_null']!=seq[-1]:seq.append(row['path']['Primary_or_null'])
    categories={'state/current_primary':p.get('Primary_or_null') if known else unknown,
        'state/activity':s.get('activity',unknown),'state/basis':s.get('basis',unknown),
        'state/direction_basis':s.get('direction_basis',unknown) if known else unknown,
        'state/fast':str(p.get('fast')) if known and p.get('fast') is not None else unknown,
        'state/numeric_status':s.get('numeric_status',unknown),
        'path/last3_connected_primary':'>'.join(seq[-3:]) if seq else unknown}
    return numeric,categories

def independent_liquidity(r,calendar,source):
    prior=sorted(d for d in calendar if d<r['session'])[-20:]
    history=[]
    for d in prior:
        h=source.get((d,r['symbol']))
        if not h or not h.get('daily') or not h.get('minute_source') or not h.get('daily_source'):continue
        if not h['minute_source'].get('terminal_pagination_proven') or not h['minute_source'].get('date_scope_complete') or not h['daily_source'].get('date_scope_complete'):continue
        try:value=F(str(h['daily']['Va']))
        except Exception:continue
        if value>=0:history.append((value,F(len(h['active_windows']),65)))
    if len(history)<10:return False,'LIQUIDITY_UNKNOWN',None
    value=median([h[0] for h in history]);coverage=median([h[1] for h in history])
    ok=100*F(r['raw_reference'])<=value*F(1,200) and coverage>=F(3,5)
    return ok,'LIQUIDITY_ELIGIBLE' if ok else 'LIQUIDITY_HARD_GATE_REJECT',value/100

def scalar_probability(r,model,manifest):
    numeric=[r['numeric'][k] for k in manifest['numeric']]
    values=[float(v) if v is not None else 0.0 for v in numeric]+[float(v is None) for v in numeric]
    prep=model['preprocessing']
    values=[(x-m)/s for x,m,s in zip(values,prep['numeric_mean'],prep['numeric_scale'])]
    for key in manifest['categorical']:
        vocab=prep['categorical_train_vocab'][key]
        c=r['categorical'][key]
        if c not in vocab:c='__UNKNOWN__'
        values.extend(float(c==v) for v in vocab)
    z=math.fsum(x*w for x,w in zip(values,model['coef']))+model['intercept']
    return 1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))

def replay(n,stream,books):
    days=sorted({r['session'] for r in stream});capital=F(1000000);chain=True
    ds=[];ts=[];frames=[];daily=[]
    caps={'S':F(45,100),'A':F(35,100),'B':F(25,100)}
    utilbase={'S':F(68,100),'A':F(56,100),'B':F(44,100)}
    for day in days:
        opening=capital if chain else F(1000000);cash=opening;held={};scheduled=defaultdict(list);blocked=[]
        event=defaultdict(list)
        for r in stream:
            if r['session']==day:event[r['entry_minute']].append(r)
        for t in range(540,932):
            for key,pos in held.items():
                while pos['cursor']<len(pos['closed_feed']) and pos['closed_feed'][pos['cursor']][0]<=t:
                    pos['mark']=pos['closed_feed'][pos['cursor']][1]
                    pos['cursor']+=1
            for key,fill in sorted(scheduled.pop(t,[])):
                assert key in held
                if fill is None:blocked.append(key);continue
                pos=held.pop(key);credit=pos['q']*fill['price'];cash+=credit
                ts.append({'entry_id':key,'quantity':pos['q'],'release_minute':t,
                           'debit':str(pos['q']*pos['buy']),'credit':str(credit),'exit_kind':fill['kind']})
            ranked=sorted(event[t],key=lambda r:(-r['p_bigwinner5'],r['entry_timestamp'],r['symbol']))
            choices=[]
            for r in ranked:
                record={'entry_id':r['entry_id'],'quantity':0,'reason':None};ds.append(record)
                if t>=920:record['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
                elif not r['liquidity']['eligible']:record['reason']=r['liquidity']['reason']
                elif r['rank']=='C':record['reason']='BELOW_BIGWINNER_BASE_RATE'
                elif r['rank'] not in caps:record['reason']='SCORE_INPUT_UNKNOWN'
                elif any(pos['symbol']==r['symbol'] for pos in held.values()):record['reason']='SYMBOL_ALREADY_OPEN'
                else:choices.append((r,record))
            selected=choices[:max(0,n-len(held))]
            for r,record in choices[len(selected):]:record['reason']='MAX_POSITION_CAP'
            if selected:
                exposed=sum(pos['q']*pos['mark'] for pos in held.values());equity=cash+exposed
                ranks=[pos['rank'] for pos in held.values()]+[r['rank'] for r,record in selected]
                best=sorted(ranks,key=lambda rk:('S','A','B').index(rk))[0]
                target=min(F(92,100),utilbase[best]+F(55,1000)*(len(ranks)-1))
                budget=min(cash,max(F(0),equity*target-exposed))
                total=sum(F(str(r['p_bigwinner5'])) for r,record in selected)
                for r,record in selected:
                    desired=budget*F(str(r['p_bigwinner5']))/total
                    ceiling=equity*caps[r['rank']];capacity=F(r['liquidity']['capacity'])
                    per_share=F(r['raw_reference'])*F(10005,10000)
                    q=int(min(desired,ceiling,capacity,cash)/(per_share*100))*100
                    if q<100:
                        record['reason']='CAPITAL_SKIP_LIQUIDITY_OR_LOT' if capacity<100*per_share else 'CASH_OR_LOT_CONSTRAINED'
                        continue
                    record.update(quantity=q,reason='FUNDED',debit=str(per_share*q));cash-=per_share*q
                    key=r['entry_id'];held[key]={'symbol':r['symbol'],'q':q,'buy':per_share,'anchor':F(r['raw_reference']),
                        'mark':F(r['raw_reference']),'rank':r['rank'],'start':t}
                    assert cash>=0 and len(held)<=n
                    book=books[key];x=book['frozen_exit']
                    held[key]['closed_feed']=sorted((row['minute']+1,F(row['C'])) for row in book['market'] if row['session']==day and row['minute']>=t and actual(row))
                    held[key]['cursor']=0
                    if not book['capture_complete'] or not book['entry_actual_source']:blocked.append(key)
                    if x['sell_status']=='FILLED' and minute(x['sell_source_assumed_available_at'])<=920:
                        release=minute(x['sell_source_assumed_available_at'])
                        source=next((row for row in book['market'] if row['minute']==x['sell_minute']),None)
                        fill=None
                        if source and actual(source):
                            price=F(source['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else source['C'])*F(9995,10000)
                            assert price==F(x['sell_price_decimal'])
                            fill={'price':price,'kind':'FROZEN_EXIT_V3'}
                        scheduled[release].append((key,fill))
            if t==920:
                for key,pos in held.items():
                    available=[row for row in books[key]['market'] if row['session']==day and 920<=row['minute']<925 and actual(row)]
                    if available:
                        s=min(available,key=lambda row:row['minute']);price=F(s['O'])*F(9995,10000);kind='EOD_REGULAR'
                    else:
                        auction=[row for row in books[key]['market'] if row['session']==day and row['minute']==930 and actual(row,True)]
                        if not auction:blocked.append(key);continue
                        s=auction[0];price=F(s['C'])*F(9995,10000);kind='EOD_EXACT_1530_AUCTION'
                    scheduled[s['minute']+1].append((key,{'price':price,'kind':kind}))
            eq=cash+sum(pos['q']*pos['mark'] for pos in held.values())
            frames.append({'session':day,'minute':t,'cash':str(cash),'equity':str(eq),'concurrent':len(held)})
        complete=not blocked and not held
        daily.append({'session':day,'ending_cash':str(cash) if complete else None,
                      'primary_chain':chain,'complete':complete})
        if chain and complete:capital=cash
        elif chain:chain=False
    return ds,ts,frames,daily

def main():
    manifest=json.load(open(OUT/'FEATURE_LIQUIDITY_MANIFEST.json'))
    runtime=read(P/'RUNTIME_CAUSAL.jsonl.gz');stream=read(P/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')
    pointer=json.load(open(P/'FINAL_SOURCE_POINTER.json'))
    books={r['entry_id']:r for r in read(P/pointer['market_book'])}
    teachers={r['entry_id']:r for r in read(P/pointer['teachers'])}
    entries={r['watch_key']:r for r in read(ROOT.parent/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
    source={}
    for name in ('bigwinner_source','bigwinner_supplement'):
        data=json.load(gzip.open(ROOT.parent/f'work_inputs/{name}/SAVED_SOURCE_PRIVATE.json.gz','rt'))
        for r in data:source[r['session'],r['symbol']]=r
    scope=json.load(open(Path(__file__).parent/'SOURCE_RECOVERY_SCOPE.json'))
    calendar=set(scope['required_prior_dates']+scope['entry_cohort_dates'])
    counts=Counter();mismatches=[]
    def check(kind,ok):
        counts[kind]+=1
        if not ok:mismatches.append(kind)
    for r in runtime:
        e=entries[r['entry_id']]
        trace=read(ROOT.parent/f"work_inputs/exit_v2/FULL_TRACE/{r['session']}_{r['symbol']}.jsonl.gz")
        num,cat=independent_features(e,trace)
        for k,v in num.items():
            primary=r['numeric'][k]
            check('causal_numeric',v==primary if v is None or primary is None else abs(float(v)-float(primary))<1e-12)
        check('causal_categories',cat==r['categorical'])
        ok,reason,cap=independent_liquidity(r,calendar,source)
        check('liquidity_gate',ok==r['liquidity']['eligible'] and reason==r['liquidity']['reason'])
        check('liquidity_capacity',cap is None and r['liquidity']['capacity'] is None or cap is not None and cap==F(r['liquidity']['capacity']))
        future=[v for v in books[r['entry_id']]['market'] if r['entry_minute']<v['minute']<920 and actual(v)]
        best=max([F(v['H']) for v in future],default=F(r['raw_reference']))
        y=int(best/F(r['raw_reference'])-1>=F(5,100)) if future and best/F(r['raw_reference'])-1>=F(5,100) else 0 if books[r['entry_id']]['capture_complete'] else None
        check('teacher_primary',y==teachers[r['entry_id']]['label_bigwinner5'])
    models={i:json.load(open(P/'models'/f'BLOCK_{i:02d}.json')) for i in range(1,9)}
    max_score_diff=0
    for r in stream:
        predicted=scalar_probability(r,models[r['block']],manifest)
        diff=abs(predicted-r['p_bigwinner5']);max_score_diff=max(max_score_diff,diff)
        check('scalar_score',diff<1e-12)
        lift=predicted/models[r['block']]['base_rate']
        rk='S' if lift>=2 else 'A' if lift>=1.5 else 'B' if lift>=1 else 'C'
        check('rank',rk==r['rank'])
    for model in models.values():
        training=[r for r in runtime if r['session']<=model['train_through'] and r['entry_minute']<920 and teachers[r['entry_id']]['label_bigwinner5'] is not None]
        check('temporal_base_rate',sum(teachers[r['entry_id']]['label_bigwinner5'] for r in training)/len(training)==model['base_rate'])
        check('temporal_boundary',max(r['session'] for r in training)<min(model['test_dates']))
        a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in manifest['numeric']] for r in training])
        a=np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
        std=a.std(axis=0);std[std==0]=1
        check('training_only_means',np.max(np.abs(a.mean(axis=0)-model['preprocessing']['numeric_mean']))<1e-12)
        check('training_only_scales',np.max(np.abs(std-model['preprocessing']['numeric_scale']))<1e-12)
        for key in manifest['categorical']:
            check('training_only_vocab',sorted({r['categorical'][key] or '__UNKNOWN__' for r in training}|{'__UNKNOWN__'})==model['preprocessing']['categorical_train_vocab'][key])
    for n in (3,4,5):
        ds,ts,cs,daily=replay(n,stream,books)
        pds=read(P/f'MAX{n}_DECISIONS.jsonl.gz');pts=read(P/f'MAX{n}_TRADES.jsonl.gz');pcs=read(P/f'MAX{n}_CURVE.jsonl.gz')
        check('decision_count',len(ds)==len(pds))
        for a,b in zip(ds,pds):
            check('funding_decision',all(a[k]==b[k] for k in ('entry_id','quantity','reason')))
            if a['quantity']:check('BUY_debit',F(a['debit'])==F(b['debit']))
        check('closed_trade_count',len(ts)==len(pts))
        for a,b in zip(ts,pts):
            check('SELL_event',all(a[k]==b[k] for k in ('entry_id','quantity','release_minute','exit_kind')))
            check('trade_cash',F(a['debit'])==F(b['debit']) and F(a['credit'])==F(b['credit']))
        check('curve_count',len(cs)==len(pcs))
        for a,b in zip(cs,pcs):
            check('exact_cash_equity',F(a['cash'])==F(b['cash']) and F(a['equity'])==F(b['equity']) and a['concurrent']==b['concurrent'])
        primary=json.load(open(P/f'MAX{n}_RESULT.json'))['daily_series']
        for a,b in zip(daily,primary):
            check('daily_endpoint',a['primary_chain']==b['primary_chain'] and ((a['ending_cash'] is None and b['ending_cash'] is None) or a['ending_cash'] is not None and b['ending_cash'] is not None and F(a['ending_cash'])==F(b['ending_cash'])))
        output(P/f'MAX{n}_INDEPENDENT_ENDPOINTS.json',daily)
    report={'status':'PASS' if not mismatches else 'FAIL','mismatch_N':len(mismatches),
        'mismatch_categories':dict(Counter(mismatches)),'checks_N':sum(counts.values()),'checks':dict(counts),
        'independent_replay_profiles':3,'independent_model_refits':0,'max_scalar_score_abs_difference':max_score_diff,
        'Primary_logic_imported':False,'cash_arithmetic':'Independent exact Fraction; cash/equity/debit/credit compared as exact rational equality.',
        'shared_io_limit':'Same provider cache and Frozen Entry/State/Path/EXIT plus fixed8 fitted model coefficients. Implementation agreement is not independent external source or production certification.',
        'future_suffix_inputs_to_runtime':False,'productionReady':False}
    output(OUT/'INDEPENDENT_AUDIT.json',report)
    print(json.dumps(report))
    assert not mismatches,'PRIMARY_INDEPENDENT_MISMATCH'

if __name__=='__main__':main()
