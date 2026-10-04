"""D10 independent engine. Imports no primary runtime/replay/evaluator code.

Raw score/book/arrival/model bytes are shared immutable inputs. Accounting,
causal features, inference, allocation and evaluation are independently written.
Probability/float tolerance is 1e-12; quantities and Decimal money are exact.
No fitting, teacher generation, control replay, policy changes or orders.
"""
import csv, gzip, hashlib, json, math, sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D, ROUND_FLOOR
from statistics import mean, median
from control import ROOT, WORK, OUT, now, save, sha

PROFILE='COUNTERFACTUAL_SLOT_VALUE_V6_MAX3'
PRIVATE=WORK/'capital_v6_slot_private'
INPUTS=WORK/'source_main'
TOL=1e-12
FORBIDDEN={'replay','common','features','slot_runtime','slot_model','allocation','execution','staircase',
           'teacher_oracle','teachers','teachers_certified','train_slot','evaluate'}
MISMATCH=[]
CHECKS=Counter()

def check(group,condition,detail):
    CHECKS[group]+=1
    if not condition:
        MISMATCH.append({'group':group,'detail':detail})

def close(a,b):
    if a is None or b is None:
        return a is b
    return abs(float(a)-float(b))<=TOL

def loadrows(p):
    return [json.loads(line) for line in gzip.open(p,'rt')]

def order(r):
    return (-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'])

def market_valid(row,auction=False):
    try:
        if not row.get('lineage'):
            return False
        o,h,l,c,v,a=[D(str(row[k])) for k in ['O','H','L','C','Vo','Va']]
        if not all(x.is_finite() and x>0 for x in (o,h,l,c,v,a)):
            return False
        return l<=min(o,c)<=max(o,c)<=h and (not auction or o==h==l==c)
    except (ValueError,TypeError,KeyError):
        return False

def release(book,eod=False):
    if eod:
        regular=sorted([r for r in book['market'] if r.get('session')==book['session'] and 920<=r['minute']<925 and market_valid(r)],key=lambda r:r['minute'])
        auction=[r for r in book['market'] if r.get('session')==book['session'] and r['minute']==930 and market_valid(r,True)]
        source=regular[0] if regular else auction[0] if auction else None
        if source is None:
            return None
        return {'kind':'EOD_REGULAR' if regular else 'EOD_EXACT_1530_AUCTION','source_minute':source['minute'],
                'release_minute':source['minute']+1,'price':D(str(source['O'] if regular else source['C']))*D('.9995'),'lineage':source['lineage']}
    x=book['frozen_exit']
    if x['sell_status']!='FILLED':
        return None
    clock=datetime.fromisoformat(x['sell_source_assumed_available_at'])
    known=clock.hour*60+clock.minute
    if known>920:
        return None
    source=next((r for r in book['market'] if r['minute']==x['sell_minute']),None)
    assert source is not None and market_valid(source),'INDEPENDENT_FROZEN_EXECUTION_LINEAGE_FAILURE'
    reference=source['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else source['C']
    price=D(str(reference))*D('.9995')
    check('source_exit_price',price==D(x['sell_price_decimal']),book['entry_id'])
    return {'kind':'FROZEN_EXIT_V3','source_minute':source['minute'],'release_minute':known,'price':price,'lineage':source['lineage']}

def active(t):
    return t-540-(0 if t<=690 else t-690 if t<750 else 60)

def features(row,held,pending,cash,equity,history,batch_size,index,table):
    t=row['entry_minute'];occupants=list(held.values())+pending;n=len(occupants)
    x={'active_minute':active(t),'active_minutes_remaining':active(920)-active(t),
       'm2':row['m2'],'m3':row['m3'],'m5':row['m5'],'ML':row['ML'],'batch_size':batch_size,
       'batch_order_index':index,'minimum_lot_equity_ratio':float(D(row['raw_reference'])*D('1.0005')*100/equity),
       'cash_equity_ratio':float(cash/equity),'open_count':n,'free_slots':3-n}
    for field in ('ML','m5','age'):
        v=[active(t)-active(p['entry_minute']) if field=='age' else p[field] for p in occupants]
        for kind in ('min','mean','max'):
            x[f'held_{field}_{kind}']=(min(v) if kind=='min' else max(v) if kind=='max' else mean(v)) if v else None
    for rank in ('S','A','B'):
        x[f'held_{rank}_count']=sum(p['rank']==rank for p in occupants)
    for kind in ('admitted','Aplus','B'):
        hs=[r for r in history if r['admission'] and (kind=='admitted' or kind=='Aplus' and r['rank'] in ('S','A') or kind=='B' and r['rank']=='B')]
        for minutes in (15,30,60):
            x[f'{kind}_last{minutes}']=sum(active(t)-minutes<=active(r['entry_minute'])<=active(t) for r in hs)
        if kind in ('admitted','Aplus'):
            x['cumulative_'+kind]=len(hs)
            x['minutes_since_'+kind]=active(t)-max(active(r['entry_minute']) for r in hs) if hs else None
    c=table['minute_counts'][str(t)];train=table['training_session_N']
    x.update(expected_remaining_Aplus=c[2]/train,P_remaining_Aplus_ge1=c[0]/train,
             P_remaining_Aplus_ge2=c[1]/train,expected_remaining_admission_pass=c[3]/train,
             B_median_ML=table['B_median'],B_p75_ML=table['B_p75'])
    return {'numeric':x,'categorical':{'rank':row['rank']}}

def probability(f,model):
    pre=model['preprocessing'];raw=[f['numeric'][k] for k in pre['numeric_fields']]
    vector=[((0. if v is None else float(v))-mu)/sd for v,mu,sd in zip(raw,pre['numeric_mean'],pre['numeric_std'])]
    vector += [1. if v is None else 0. for v in raw]
    for k in pre['categorical_fields']:
        vector += [1. if f['categorical'][k]==z else 0. for z in pre['vocabulary'][k]]
    assert len(vector)==len(model['coef'])
    z=math.fsum(v*c for v,c in zip(vector,model['coef']))+model['intercept']
    if z>=0:
        return 1./(1.+math.exp(-z))
    e=math.exp(z)
    return e/(1.+e)

def allocate(picked,equity,exposure,cash,held):
    caps={'S':D('.45'),'A':D('.35'),'B':D('.25')};base={'S':D('.68'),'A':D('.56'),'B':D('.44')}
    ranks=[p['band'] for p in held.values()]+[r['capacity_band'] for r in picked]
    best=min(ranks,key=lambda b:('S','A','B').index(b));target=min(D('.92'),base[best]+D('.055')*(len(ranks)-1))
    budget=min(cash,max(D(0),equity*target-exposure));weight=sum(D(str(r['capital_score'])) for r in picked)
    free_cash=cash;free_budget=budget;out=[]
    for r in picked:
        b=r['capacity_band'];lot=D(r['raw_reference'])*D('1.0005')*100
        desired=budget*D(str(r['capital_score']))/weight;cap=equity*caps[b]
        lots=max(0,int((min(desired,cap,free_cash)/lot).to_integral_value(rounding=ROUND_FLOOR)))
        debit=lots*lot;free_cash-=debit;free_budget-=debit
        out.append({'quantity':lots*100,'first_pass_quantity':lots*100,'water_fill_lots':0,'debit':debit,
            'lot_debit':lot,'equity_cap':cap,'liquidity_cap':None,'desired':desired,'band':b,
            'target_utilization':target,'batch_equity':equity,'batch_budget':budget})
    rounds=0
    while True:
        updated=False
        for a in out:
            if a['first_pass_quantity']<100:
                continue
            lot=a['lot_debit']
            if lot<=free_cash and lot<=free_budget and a['debit']+lot<=a['equity_cap']:
                a['quantity']+=100;a['debit']+=lot;a['water_fill_lots']+=1
                free_cash-=lot;free_budget-=lot;updated=True
        if not updated:
            break
        rounds+=1
    for a in out:
        a.update(water_fill_rounds=rounds,budget_unspent=free_budget)
    return out

def engine(scores,books,models,tables):
    all_decisions=[];all_trades=[];frames=[];daily=[];intents=[];cash=D(1000000)
    for day in sorted({r['session'] for r in scores}):
        opening=cash;original_pool=cash;recycled_pool=D(0);recycled_used=D(0);held={};sell_events=defaultdict(list)
        candidates=[r for r in scores if r['session']==day];events=defaultdict(list)
        for r in candidates:
            events[r['entry_minute']].append(r)
        cash_min=cash;max_open=0
        for minute in range(540,932):
            for i,p in held.items():
                known=[r for r in books[i]['market'] if r.get('session')==day and p['entry_minute']<=r['minute'] and r['minute']+1<=minute and market_valid(r)]
                if known:
                    mark=max(known,key=lambda r:r['minute']);p['mark']=D(str(mark['C']));p['mark_known_minute']=mark['minute']+1
            for i,source in sorted(sell_events.pop(minute,[]),key=lambda v:v[0]):
                p=held.pop(i);credit=p['quantity']*source['price'];debit=p['quantity']*p['buy']
                cash+=credit;recycled_pool+=credit
                all_trades.append({'entry_id':i,'session':day,'quantity':p['quantity'],'entry_minute':p['entry_minute'],
                    'release_minute':minute,'source_minute':source['source_minute'],'exit_kind':source['kind'],
                    'buy_effective':p['buy'],'sell_effective':source['price'],'debit':debit,'credit':credit,
                    'pnl':credit-debit,'net_return':float(credit/debit-1),'lineage':source['lineage'],'commission':0})
            batch=sorted(events[minute],key=order);eligible=[]
            for r in batch:
                d={'entry_id':r['entry_id'],'session':day,'minute':minute,'quantity':0,'reason':None,
                   'rank':r['rank'],'held_before_batch':sorted(held)}
                all_decisions.append(d)
                if minute>=920:
                    d['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
                elif not r['admission']:
                    d['reason']='UPWARD_BELOW_BASELINE'
                elif any(p['symbol']==r['symbol'] for p in held.values()):
                    d['reason']='SYMBOL_ALREADY_OPEN'
                else:
                    eligible.append((r,d))
            picked=[]
            for r,d in eligible:
                pending=[v for v,_ in picked];occ=len(held)+len(pending)
                eq=cash+sum((p['quantity']*p['mark'] for p in held.values()),D(0))
                hs=[v for v in candidates if v['entry_minute']<minute or v['entry_minute']==minute and order(v)<order(r)]
                d.update(pre_decision_occupancy=occ,p_accept=None,slot_features=None,
                         occupant_ids=sorted(held)+[v['entry_id'] for v in pending],
                         pending_ids=[v['entry_id'] for v in pending],causal_cash=cash,causal_equity=eq,
                         history_ids=[v['entry_id'] for v in hs],batch_size=len(batch),batch_order_index=batch.index(r),
                         held_causal={k:{f:p[f] for f in ('symbol','entry_minute','ML','m5','rank','quantity','buy','mark','mark_known_minute','band')} for k,p in held.items()})
                if occ==3:
                    d.update(reason='MAX_POSITION_CAP',slot_gate_action='REJECT',slot_gate_reason='MAX_POSITION_CAP')
                    continue
                if occ:
                    f=features(r,held,pending,cash,eq,hs,len(batch),batch.index(r),tables[str(r['block'])]);p=probability(f,models[str(r['block'])])
                    d.update(slot_features=f,p_accept=p)
                    if p<.5:
                        d.update(reason='SLOT_RESERVE_REJECT',slot_gate_action='REJECT',slot_gate_reason='SLOT_RESERVE_REJECT')
                        continue
                d.update(slot_gate_action='ADMIT',slot_gate_reason='SLOT_VALUE_ACCEPT' if occ else 'SLOT1_NO_MODEL_ACCEPT',slot_admission_index=occ+1)
                picked.append((r,d))
            if picked:
                eq=cash+sum((p['quantity']*p['mark'] for p in held.values()),D(0))
                assignments=allocate([r for r,d in picked],eq,eq-cash,cash,held)
                for (r,d),a in zip(picked,assignments):
                    d.update(a,cash_before=cash)
                    q=a['quantity']
                    if q<100:
                        d['reason']='CASH_OR_LOT_CONSTRAINED'
                        continue
                    cost=q*D(r['raw_reference'])*D('1.0005');assert cost==a['debit'] and cost<=cash
                    cash-=cost;cash_min=min(cash_min,cash);used=min(original_pool,cost);original_pool-=used
                    recycled=cost-used;recycled_pool-=recycled;recycled_used+=recycled
                    assert cash>=0 and recycled_pool>=0
                    d.update(reason='FUNDED',funded_slot=len(held)+1,recycled_cash_used=recycled)
                    i=r['entry_id'];held[i]={'symbol':r['symbol'],'entry_minute':minute,'ML':r['ML'],'m5':r['m5'],
                        'rank':r['rank'],'quantity':q,'buy':D(r['raw_reference'])*D('1.0005'),
                        'mark':D(r['raw_reference']),'mark_known_minute':minute,'band':r['capacity_band']}
                    max_open=max(max_open,len(held));assert len(held)<=3 and q%100==0
                    book=books[i];assert book['capture_complete'] and book['entry_actual_source'] and book['session']==day
                    source=release(book)
                    if source:
                        assert source['release_minute']>minute
                        sell_events[source['release_minute']].append((i,source))
            if minute==920:
                for i,p in sorted(held.items()):
                    authority=books[i]['limit_up_authority']
                    limit_up=bool(authority and authority.get('status')=='LIMIT_UP_CONFIRMED' and authority.get('authoritative_price_limit_source') and authority.get('causal_exchange_status') and authority.get('session')==day and authority.get('known_minute',9999)<=920 and authority.get('observed_minute',9999)<=920)
                    intents.append({'entry_id':i,'session':day,'minute':920,'side':'SELL','quantity':p['quantity'],
                        'sor':True,'order_type':'MARKET','condition':'DAY','transmitted':False,
                        'limit_up_status':'LIMIT_UP_CONFIRMED' if limit_up else 'LIMIT_UP_UNKNOWN'})
                    source=release(books[i],True);assert source is not None,'INDEPENDENT_EOD_BLOCKED'
                    sell_events[source['release_minute']].append((i,source))
            eq=cash+sum((p['quantity']*p['mark'] for p in held.values()),D(0))
            frames.append({'session':day,'minute':minute,'equity':eq,'cash':cash,'exposure':eq-cash,
                'utilization':float((eq-cash)/eq),'concurrent':len(held),'known_marks':{i:p['mark_known_minute'] for i,p in held.items()}})
        assert not held,'INDEPENDENT_UNRESOLVED_HOLDINGS'
        daily.append({'session':day,'starting_cash':opening,'ending_cash':cash,'daily_return':float(cash/opening-1),
            'cash_min':cash_min,'max_concurrent':max_open,'recycled_cash_used':recycled_used})
    return all_decisions,all_trades,frames,daily,intents

def main():
    check('primary_import_guard',not FORBIDDEN.intersection(sys.modules),'beginning')
    assert not (OUT/'INDEPENDENT_AUDIT.json').exists(),'INDEPENDENT_AUDIT_ALREADY_EXISTS'
    freeze=json.loads((OUT/'SCORE_ACTION_FREEZE.json').read_text());support=json.loads((OUT/'TEACHER_CENSUS_SUPPORT_GATE.json').read_text())
    precommit=json.loads((OUT/'SLOT_MODEL_PRECOMMIT.json').read_text());models={}
    for b,h in freeze['models'].items():
        p=OUT/'models'/f'SLOT_MODEL_BLOCK_{int(b):02d}.json';check('model_identity',sha(p)==h,b);model=json.loads(p.read_text());models[b]=model
        block=support['blocks'][int(b)-1]
        check('teacher_support_identity',model['teacher_sha256']==block['teacher_sha256'] and model['train_N']==block['unique_examples'] and model['ACCEPT_N']==block['ACCEPT'] and model['RESERVE_N']==block['RESERVE'],b)
        check('preprocessing_identity',model['preprocessing']['numeric_fields']==precommit['numeric_features'] and model['preprocessing']['categorical_fields']==precommit['categorical_features'],b)
        check('frozen_training_only',max(model['train_sessions'])<min(model['test_sessions']) and model['within_block_refit']==model['winner_fit']==0 and model['threshold']==.5,b)
    scores=loadrows(INPUTS/'capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
    books={r['entry_id']:r for r in loadrows(INPUTS/'inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
    tables=json.loads((ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/ARRIVAL_TABLE.json').read_text())
    identities=json.loads((INPUTS/'capital_staircase_v4_private/MODEL_HASHES.json').read_text())
    for r in scores:
        check('winner_rank_identity',all(r[f'H{h}_hash']==identities[f'H{h}_BLOCK_{r["block"]:02d}.json'] for h in (2,3,5)) and r['rank']==('S' if r['ML']>=2 else 'A' if r['ML']>=1.5 else 'B' if r['ML']>=1 else 'C') and r['admission']==(r['ML']>=1),r['entry_id'])
    ds,ts,frames,daily,intents=engine(scores,books,models,tables)
    primary=loadrows(PRIVATE/f'{PROFILE}_DECISIONS.jsonl.gz');primary_by_id={r['entry_id']:r for r in primary}
    check('decision_count_and_order',[d['entry_id'] for d in ds]==[d['entry_id'] for d in primary],'1039')
    decimal_fields={'debit','lot_debit','equity_cap','desired','target_utilization','batch_equity','batch_budget','budget_unspent','cash_before','recycled_cash_used'}
    for d in ds:
        i=d['entry_id'];actual=primary_by_id[i]
        for field in ['reason','quantity','rank','held_before_batch','pre_decision_occupancy','slot_gate_action','slot_gate_reason','slot_admission_index','funded_slot','first_pass_quantity','water_fill_lots','water_fill_rounds','band','liquidity_cap']:
            check('action_occupancy_allocation',d.get(field)==actual.get(field),(i,field,d.get(field),actual.get(field)))
        for field in decimal_fields:
            if field in d:
                check('exact_decimal_allocation',field in actual and d[field]==D(actual[field]),(i,field))
        check('probability',close(d.get('p_accept'),actual.get('p_accept')),i)
        expected_feature=d.get('slot_features');observed=actual.get('slot_features')
        if expected_feature is None:
            check('causal_features',observed is None,i)
        else:
            check('causal_features',observed is not None and set(observed['numeric'])==set(expected_feature['numeric']) and observed['categorical']==expected_feature['categorical'],i)
            if observed is not None:
                for key,value in expected_feature['numeric'].items():
                    check('causal_features',close(value,observed['numeric'].get(key)),(i,key))
        state=actual.get('causal_slot_state')
        if 'causal_cash' in d:
            check('causal_state',state is not None and D(state['cash'])==d['causal_cash'] and D(state['equity'])==d['causal_equity'] and state['pending_ids']==d['pending_ids'] and state['history_ids']==d['history_ids'] and state['batch_size']==d['batch_size'] and state['batch_order_index']==d['batch_order_index'],i)
            for key,p in d['held_causal'].items():
                observed_held=state['held'].get(key,{})
                for field,value in p.items():
                    check('causal_held_marks',D(observed_held[field])==value if isinstance(value,D) else observed_held.get(field)==value,(i,key,field))
    primary_trades=loadrows(PRIVATE/f'{PROFILE}_TRADES.jsonl.gz')
    check('trade_count_order',[t['entry_id'] for t in ts]==[t['entry_id'] for t in primary_trades],'trade count')
    for t,a in zip(ts,primary_trades):
        for field in t:
            value=t[field];actual=a[field]
            check('BUY_SELL_source_money',value==D(actual) if isinstance(value,D) else close(value,actual) if field=='net_return' else value==actual,(t['entry_id'],field))
    primary_frames=loadrows(PRIVATE/f'{PROFILE}_CURVE.jsonl.gz')
    check('frame_count',len(frames)==len(primary_frames),'14896')
    for f,a in zip(frames,primary_frames):
        for field in f:
            value=f[field];actual=a[field]
            check('MTM_cash_equity',value==D(actual) if isinstance(value,D) else close(value,actual) if field=='utilization' else value==actual,(f['session'],f['minute'],field))
    check('EOD_intents',intents==loadrows(PRIVATE/f'{PROFILE}_INTENTS.jsonl.gz'),'exact intents')
    result=json.loads((OUT/'MAIN_REPLAY_RESULT.json').read_text());economics=json.loads((OUT/'ECONOMIC_RESULT.json').read_text())['economics']
    for d,a in zip(daily,result['daily_series']):
        for field in d:
            value=d[field];actual=a[field]
            check('daily_accounting',value==D(actual) if isinstance(value,D) else close(value,actual) if field=='daily_return' else value==actual,(d['session'],field))
    returns=[d['daily_return'] for d in daily];rolls=[float(daily[i+19]['ending_cash']/daily[i]['starting_cash']) for i in range(19)]
    peak=D(1000000);maxdd=D(0)
    for f in frames:
        peak=max(peak,f['equity']);maxdd=max(maxdd,(peak-f['equity'])/peak)
    utilization=[f['utilization'] for f in frames if 540<=f['minute']<690 or 750<=f['minute']<930]
    expected={'daily_geometric':math.expm1(mean(math.log1p(r) for r in returns)),'daily_arithmetic':mean(returns),
        'daily_median':median(returns),'rolling20_N':19,'rolling20_min':min(rolls),'rolling20_mean':mean(rolls),
        'rolling20_median':median(rolls),'rolling20_max':max(rolls),'rolling20_2x_N':sum(r>=2 for r in rolls),
        'final_equity':float(daily[-1]['ending_cash']),'final_return':float(daily[-1]['ending_cash']/D(1000000)-1),
        'max_drawdown':float(maxdd),'utilization_mean':mean(utilization),'utilization_median':median(utilization),
        'mean_idle_cash_fraction':mean(1-v for v in utilization),'cash_minimum':float(min(d['cash_min'] for d in daily)),
        'turnover_cash_jpy':float(sum((t['debit']+t['credit'] for t in ts),D(0))),
        'capital_recycling_used_jpy':float(sum((d['recycled_cash_used'] for d in daily),D(0))),
        'capital_recycling_closed_N':len(ts),'funded_N':sum(d['reason']=='FUNDED' for d in ds),'avg_funded_per_session':len(ts)/38}
    for field,value in expected.items():
        check('economic_summary',close(value,economics.get(field)),field)
    for i,value in enumerate(rolls):
        check('rolling20',close(value,result['rolling20_windows'][i]['growth_multiple']),i)
    labels={r['entry_id']:r for r in loadrows(INPUTS/'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
    scores_by_id={r['entry_id']:r for r in scores};funded={d['entry_id'] for d in ds if d['reason']=='FUNDED'}
    d8=json.loads((OUT/'FALSE_RESERVE_BAD_FILL_ORACLE_GAP.json').read_text());metrics={}
    for k,denom,ceiling in [(5,113,104),(10,47,47)]:
        ids={i for i,r in scores_by_id.items() if r['admission'] and labels[i]['potential_return']>=k/100}
        reasons=Counter(d['reason'] for d in ds if d['entry_id'] in ids)
        f,m,r,c=[reasons.get(key,0) for key in ['FUNDED','MAX_POSITION_CAP','SLOT_RESERVE_REJECT','CASH_OR_LOT_CONSTRAINED']]
        values={'rank_pass':len(ids),'funded':f,'MAX3_miss':m,'reserve_rejected':r,'Net_Slot_Miss':m+r,'cash_lot':c,'Oracle_recovery':f/ceiling,'Oracle_gap':ceiling-f}
        metrics[f'U{k}']=values
        check('U5_U10_conservation',f+m+r+c==denom,(k,values))
        for field,value in values.items():
            check('U5_U10_reasons_Oracle_gap',close(value,d8['metrics'][f'U{k}'][field]),(k,field))
    u5={i for i,r in scores_by_id.items() if r['admission'] and labels[i]['potential_return']>=.05}
    false=[d for d in ds if d['entry_id'] in u5 and d['reason']=='SLOT_RESERVE_REJECT']
    physically=sum(sum((D(scores_by_id[i]['raw_reference'])*D('1.0005')*100 for i in d['pending_ids']+[d['entry_id']]),D(0))<=d['causal_cash'] for d in false)
    bad={d['entry_id'] for d in ds if d['entry_id'] in u5 and d['reason']=='MAX_POSITION_CAP' and any(labels[i]['potential_return']<.02 for i in d['occupant_ids'])}
    bad_actual={d['entry_id'] for d in ds if d['entry_id'] in u5 and d['reason']=='MAX_POSITION_CAP' and any(i in funded and labels[i]['potential_return']<.02 for i in d['occupant_ids'])}
    for field,value in {'FALSE_RESERVE_U5':len(false),'FALSE_RESERVE_U5_ONE_LOT_FUNDABLE':physically,'BAD_FILL_BLOCKED_U5':len(bad),'BAD_FILL_BLOCKED_U5_ACTUAL_FUNDED':len(bad_actual)}.items():
        check('false_reserve_bad_fill',value==d8[field],field)
    check('below2_contamination',close(sum(labels[i]['potential_return']<.02 for i in funded)/len(funded),d8['quality']['below2_rate']),'below2')
    daily_csv=list(csv.DictReader((OUT/'ASSET_CURVE_DAILY.csv').open()))
    v5=json.loads((OUT/'V5_CONTROL_ORACLE_FREEZE.json').read_text())['Control'];v5days={d['session']:d for d in v5['daily_series']}
    for d,c in zip(daily,daily_csv):
        check('asset_curve_csv',d['session']==c['session'] and d['ending_cash']==D(c['ending_equity']) and close(d['daily_return'],c['v6_daily_return']) and close(d['daily_return']-v5days[d['session']]['daily_return'],c['paired_daily_delta']),d['session'])
    full=loadrows(PRIVATE/'FULL_DECISION_LEDGER.jsonl.gz')
    for d,a in zip(full,primary):
        i=d['entry_id'];b=str(scores_by_id[i]['block'])
        check('full_ledger_model_identity',d['slot_model_sha256']==freeze['models'][b] and d['runtime_threshold']==.5 and all(d[k]==v for k,v in a.items()),i)
    check('primary_import_guard',not FORBIDDEN.intersection(sys.modules),'end')
    summary={'exact_jst':now(),'status':'PASS' if not MISMATCH else 'MISMATCH_STOP','mismatch_N':len(MISMATCH),
        'check_N':sum(CHECKS.values()),'checks_by_group':dict(CHECKS),'mismatches':MISMATCH,
        'Main_replay_count':1,'independent_replay_count':1,'Slot_fits_existing':8,'Slot_additional_fit':0,
        'teacher_regeneration':0,'control_replay':0,'retune':0,'tolerance':{'float_probability_features':TOL,'Decimal_money':'exact','quantity':'exact'},
        'independent_engine_sha256':sha(Path(__file__)),'primary_runtime_imports':[],
        'shared_inputs_only':['D6 frozen Slot models','v4 score stream','v5 frozen Arrival Table','D1 execution book','existing evaluator labels'],
        'independence_limit':'Same immutable source bytes and frozen coefficients; audit checks implementation/accounting consistency, not external truth or fresh OOS validity.',
        'economics':expected,'metrics':metrics,'FALSE_RESERVE_U5':len(false),'FALSE_RESERVE_U5_ONE_LOT_FUNDABLE':physically,
        'BAD_FILL_BLOCKED_U5':len(bad),'BAD_FILL_BLOCKED_U5_ACTUAL_FUNDED':len(bad_actual)}
    save(OUT/'INDEPENDENT_AUDIT.json',summary)
    witness=[{'entry_id':d['entry_id'],'reason':d['reason'],'quantity':d['quantity'],'p_accept':d.get('p_accept'),
        'occupancy':d.get('pre_decision_occupancy'),'slot_features':d.get('slot_features'),
        'occupant_ids':d.get('occupant_ids'),'pending_ids':d.get('pending_ids'),'model_block':scores_by_id[d['entry_id']]['block']} for d in ds]
    with (PRIVATE/'INDEPENDENT_V6_LEDGER.jsonl.gz').open('xb') as f:
        f.write(gzip.compress(('\n'.join(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False) for x in witness)+'\n').encode(),mtime=0))
    print(json.dumps({k:summary[k] for k in ['status','mismatch_N','check_N','checks_by_group','economics','metrics']}))
    if MISMATCH:
        raise SystemExit(2)

if __name__=='__main__':
    main()
