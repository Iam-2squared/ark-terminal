"""Evaluation-only algebra over saved R and V5 ledgers. No market engine imports."""
from pathlib import Path
from collections import Counter, defaultdict
from fractions import Fraction as F
from decimal import Decimal, localcontext
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse, csv, gzip, hashlib, json, math, statistics

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO.parent
OLD = REPO / 'docs/evidence/capital-v51-reset20-r5r10-20261006-v1'
OUT = REPO / 'docs/evidence/capital-full-r-spectrum-20261006-v1'
PRIVATE = ROOT / 'capital_r_spectrum_private'
PREVIOUS_PRIVATE = ROOT / 'capital_v51_private'
HEADS = {'pP/MOVE_P5':'pP', 'MOVE_U2':'q2', 'MOVE_U3':'q3', 'MRET':'mP'}
COUNTS = dict(derived_label_batches=1, new_fits=0, refits=0, calibration=0,
              new_Capital_candidates=0, new_Capital_replays=0,
              R_market_EXIT_rematerializations=0, provider_requests=0,
              protected_partition_openings=0, orders=0, main_merge=0,
              force_push=0, Claude=0)

def now(): return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def rows(path): return [json.loads(x) for x in gzip.open(path, 'rt') if x.strip()]
def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    content=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
    if len(content)>80000:
        content=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    path.write_text(content+'\n')
def write_rows(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(('\n'.join(json.dumps(x, sort_keys=True,
                          allow_nan=False) for x in value)+'\n').encode(), mtime=0))
def decimal(x):
    if isinstance(x, F):
        with localcontext() as c:
            c.prec=60
            return str(Decimal(x.numerator)/Decimal(x.denominator))
    return str(x)
def rational(x): return [x.numerator, x.denominator]
def rate(n,d): return n/d if d else None
def csv_file(path, data, fields=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(data[0])
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in data:
            w.writerow({k:json.dumps(r[k],sort_keys=True) if isinstance(r.get(k),(dict,list)) else r.get(k) for k in fields})
def exact_stats(values):
    values=sorted(values); n=len(values)
    if not n: return {'N':0,'unit':'percent','mean':None,'median':None,'min':None,'max':None,'quantiles':{}}
    def quantile(q):
        pos=(n-1)*q; lo=pos.numerator//pos.denominator; frac=pos-lo
        return values[lo]+frac*(values[min(lo+1,n-1)]-values[lo])
    qs={str(k):decimal(100*quantile(F(k,100))) for k in [1,5,10,25,50,75,90,95,99]}
    return {'N':n,'unit':'percent','mean':decimal(100*sum(values,F(0))/n),
            'median':qs['50'],'min':decimal(100*values[0]),'max':decimal(100*values[-1]),'quantiles':qs,
            'mean_ratio_exact':rational(sum(values,F(0))/n),'median_ratio_exact':rational(quantile(F(1,2)))}
def event(value, label):
    if value is None: return None
    if label=='R0PLUS': return value>=0
    if label=='RPOS': return value>0
    if label=='RNEG': return value<0
    if label=='ZERO': return value==0
    if label=='Loser': return value<=0
    if label.startswith('RN'): return value<=F(-int(label[2:]),100)
    return value>=F(int(label[1:]),100)
def labels_for(values):
    positive=max(10, math.floor(max(values)*100))
    negative=max(10, math.floor(-min(values)*100))
    return ['R0PLUS','RPOS','ZERO','RNEG','Loser'] + [f'R{k}' for k in range(1,positive+1)] + [f'RN{k}' for k in range(1,negative+1)]
def derive_once():
    dest=PRIVATE/'evaluation-only/R_SPECTRUM_ROWS.jsonl.gz'
    receipt=PRIVATE/'DERIVATION_COMPLETE.json'
    source=PREVIOUS_PRIVATE/'evaluation-only/R_LABELS.jsonl.gz'
    source_sha=sha(source); contract_sha=sha(OUT/'R_SPECTRUM_CONTRACT.json')
    if dest.exists() or receipt.exists():
        assert dest.exists() and receipt.exists(), 'PARTIAL_DERIVATION_REQUIRES_TECHNICAL_RECEIPT'
        meta=read(receipt)
        assert meta['source_sha256']==source_sha and meta['contract_sha256']==contract_sha
        assert sha(dest)==meta['output_sha256']
        return rows(dest), meta
    started=PRIVATE/'DERIVATION_STARTED.json'
    resumed=started.exists()
    if resumed:
        previous=read(started)
        assert previous['source_sha256']==source_sha and previous['contract_sha256']==contract_sha
        assert previous.get('technical_resume_N',0)==0, 'DERIVATION_RESUME_BUDGET_EXHAUSTED'
        previous.update(technical_resume_N=1,resume_jst=now(),
                        reason='Unknown rows omit optional EXIT metadata; preserve null. No completed derived output existed.')
        save(started,previous)
    original=rows(source); values=[F(*r['r_net_fraction']) for r in original if r['known']]
    labels=labels_for(values); lower=math.floor(min(values)*100); upper=math.floor(max(values)*100)
    if not resumed:
        save(started,{'exact_jst':now(),'source_sha256':source_sha,
             'contract_sha256':contract_sha,'derived_batch_N':1,'market_EXIT_replays':0})
    derived=[]
    for r in original:
        value=F(*r['r_net_fraction']) if r['known'] else None
        events={k:event(value,k) for k in labels}
        assert events['R5']==r['R5'] and events['R10']==r['R10'] and events['Loser']==r['Loser']
        d={k:r[k] for k in ['entry_id','session','symbol','block','entry_minute','known',
          'execution_eligible','rank_pass','rank','U5','U10','unknown_reason']}
        d.update({k:r.get(k) for k in ['exit_kind','release_minute','source_minute',
                  'price_source','cost_basis','buy_debit','sell_credit']})
        d.update(realized_net_return_exact=rational(value) if value is not None else None,
                 realized_net_return_ratio_decimal=decimal(value) if value is not None else None,
                 bucket_pp_lower=math.floor(value*100) if value is not None else None,events=events)
        derived.append(d)
    write_rows(dest,derived)
    meta={'schema':'ARK_R_SPECTRUM_DERIVATION_V1','exact_jst':now(),
          'source_sha256':source_sha,'contract_sha256':contract_sha,'output_sha256':sha(dest),
          'derived_batch_N':1,'N':len(derived),'known_N':len(values),'unknown_N':len(derived)-len(values),
          'bucket_lower_min':lower,'bucket_lower_max':upper,'labels':labels,
          'market_EXIT_rematerializations':0,'new_Capital_replays':0,'technical_resume_N':int(resumed)}
    save(receipt,meta)
    return derived,meta
def source_data():
    binding=read(OUT/'START_AND_SOURCE_BINDING.json'); refs=binding['source_refs']
    paths={k:Path(v['local_path']) for k,v in refs['inputs'].items()}
    scores_path=next(Path(v['local_path']) for v in refs['expert_score_sources'] if Path(v['local_path']).name=='c7e10944822c_CURRENT_MRET_CAP_RUNTIME.jsonl.gz')
    return binding,paths,scores_path
def universe():
    data=rows(PRIVATE/'evaluation-only/R_SPECTRUM_ROWS.jsonl.gz')
    meta=read(PRIVATE/'DERIVATION_COMPLETE.json')
    assert sha(PRIVATE/'evaluation-only/R_SPECTRUM_ROWS.jsonl.gz')==meta['output_sha256']
    return data,meta
def join(data,decisions,trades):
    lm={r['entry_id']:r for r in data}; dm={r['entry_id']:r for r in decisions};tm={r['entry_id']:r for r in trades}
    assert len(lm)==len(data) and len(dm)==len(decisions) and len(tm)==len(trades)
    assert set(dm)<=set(lm) and set(tm)=={k for k,d in dm.items() if d['reason']=='FUNDED'}
    for k,t in tm.items():
        assert lm[k]['known'] and dm[k]['quantity']==t['quantity'] and Decimal(dm[k]['debit'])==Decimal(t['debit'])
        assert F(Decimal(t['credit']))/F(Decimal(t['debit']))-1==F(*lm[k]['realized_net_return_exact'])
        assert Decimal(t['credit'])-Decimal(t['debit'])==Decimal(t['pnl'])
    return lm,dm,tm
def populations(data,dm):
    masks={'ALL_FROZEN_ENTRY':data,'EXECUTION_ELIGIBLE':[r for r in data if r['execution_eligible']],
           'RANK_PASS_EXECUTION_ELIGIBLE':[r for r in data if r['execution_eligible'] and r['rank_pass']],
           'V5_FUNDED':[r for r in data if dm[r['entry_id']]['reason']=='FUNDED'],
           'V5_NOT_FUNDED':[r for r in data if dm[r['entry_id']]['reason']!='FUNDED']}
    for key,reason in [('V5_RESERVE_REJECT','SLOT_RESERVE_REJECT'),('V5_MAX3_FULL','MAX_POSITION_CAP'),('V5_CASH_OR_LOT','CASH_OR_LOT_CONSTRAINED')]:
        masks[key]=[r for r in data if dm[r['entry_id']]['reason']==reason]
    for reason in sorted({d['reason'] for d in dm.values()}-{'FUNDED','SLOT_RESERVE_REJECT','MAX_POSITION_CAP','CASH_OR_LOT_CONSTRAINED'}):
        masks['NATIVE_REASON_'+reason]=[r for r in data if dm[r['entry_id']]['reason']==reason]
    return masks
def summary_count(rr,dm,tm):
    funded=[r for r in rr if r['entry_id'] in tm];eligible=[r for r in rr if r['execution_eligible']]
    reasons=Counter(dm[r['entry_id']]['reason'] for r in rr if r['entry_id'] not in tm)
    return {'candidate_N':len(rr),'eligible_N':len(eligible),
            'rank_pass_N':sum(r['rank_pass'] for r in rr),
            'rank_pass_eligible_N':sum(r['rank_pass'] and r['execution_eligible'] for r in rr),
            'funded_N':len(funded),'funded_shares':sum(tm[r['entry_id']]['quantity'] for r in funded),
            'funded_rate_all':rate(len(funded),len(rr)),'funded_rate_eligible':rate(len(funded),len(eligible)),
            'missed_N':len(rr)-len(funded),'missed_eligible_N':len(eligible)-len(funded),
            'missed_actual_recoverable_shares':None,
            'miss_reason_N':dict(reasons),'distinct_sessions':len({r['session'] for r in rr}),
            'distinct_symbols':len({r['symbol'] for r in rr})}
def census(rr,dm,tm,meta):
    known=[r for r in rr if r['known']]
    buckets=[]
    for k in range(meta['bucket_lower_min'],meta['bucket_lower_max']+1):
        selected=[r for r in known if r['bucket_pp_lower']==k]
        buckets.append({'bucket_pp_lower':k,'bucket_pp_upper':k+1,**summary_count(selected,dm,tm)})
    unknown=[r for r in rr if not r['known']]
    return {'N':len(rr),'known_N':len(known),'unknown_N':len(unknown),
            'continuous_return':exact_stats([F(*r['realized_net_return_exact']) for r in known]),
            'cumulative':[{ 'label':label,'event_N':sum(r['events'][label] for r in known),
                 'known_N':len(known),'unknown_N':len(unknown),
                 'event_rate':rate(sum(r['events'][label] for r in known),len(known)),
                 **summary_count([r for r in known if r['events'][label]],dm,tm)} for label in meta['labels']],
            'buckets':buckets,'unknown_mask':summary_count(unknown,dm,tm)}
def flow_summary(trades,dm):
    debit=sum((Decimal(t['debit']) for t in trades),Decimal(0)); credit=sum((Decimal(t['credit']) for t in trades),Decimal(0))
    holdings=[t['release_minute']-t['entry_minute'] for t in trades]
    returns=[F(Decimal(t['credit']))/F(Decimal(t['debit']))-1 for t in trades]
    return {'trade_N':len(trades),'shares':sum(t['quantity'] for t in trades),
            'buy_debit_jpy':str(debit),'sell_credit_jpy':str(credit),
            'realized_pnl_jpy':str(credit-debit),
            'debit_weighted_return_ratio_exact':rational(F(credit)/F(debit)-1) if debit else None,
            'debit_weighted_return_pct':decimal(100*(F(credit)/F(debit)-1)) if debit else None,
            'trade_mean_return_pct':decimal(100*sum(returns,F(0))/len(returns)) if returns else None,
            'holding_minutes_total':sum(holdings),'holding_minutes_mean':statistics.mean(holdings) if holdings else None,
            'capital_minutes_jpy':str(sum((Decimal(t['debit'])*(t['release_minute']-t['entry_minute']) for t in trades),Decimal(0))),
            'funded_slot_N':dict(Counter(str(dm[t['entry_id']]['funded_slot']) for t in trades)),
            'entry_hour_N':dict(Counter(f"{t['entry_minute']//60:02d}:00" for t in trades)),
            'recycled_cash_used_jpy':str(sum((Decimal(dm[t['entry_id']]['recycled_cash_used']) for t in trades),Decimal(0))),
            'native_pre_decision_occupancy_N':dict(Counter(str(dm[t['entry_id']]['pre_decision_occupancy']) for t in trades)),
            'concurrent_after_own_BUY_N':dict(Counter(str(dm[t['entry_id']]['funded_slot']) for t in trades))}
def capital_flow(data,dm,tm,meta):
    lm={r['entry_id']:r for r in data}
    buckets=[]; all_trades=list(tm.values()); total=sum((Decimal(t['debit']) for t in all_trades),Decimal(0))
    for k in range(meta['bucket_lower_min'],meta['bucket_lower_max']+1):
        tt=[tm[r['entry_id']] for r in data if r['entry_id'] in tm and r['bucket_pp_lower']==k]
        f=flow_summary(tt,dm)
        f.update(bucket_pp_lower=k,bucket_pp_upper=k+1,debit_share=rate(float(f['buy_debit_jpy']),float(total)))
        buckets.append(f)
    cumulative=[]
    for label in meta['labels']:
        tt=[tm[r['entry_id']] for r in data if r['entry_id'] in tm and r['events'][label]]
        f=flow_summary(tt,dm);f.update(label=label,debit_share=rate(float(f['buy_debit_jpy']),float(total)));cumulative.append(f)
    facets={}
    for key,fn,values in [('funded_slot',lambda t:str(dm[t['entry_id']]['funded_slot']),['1','2','3']),
                          ('entry_hour',lambda t:f"{t['entry_minute']//60:02d}:00",sorted({f"{t['entry_minute']//60:02d}:00" for t in all_trades})),
                          ('pre_decision_occupancy',lambda t:str(dm[t['entry_id']]['pre_decision_occupancy']),['0','1','2']),
                          ('native_rank',lambda t:dm[t['entry_id']]['rank'],['S','A','B','C']),
                          ('capital_allocation_band',lambda t:dm[t['entry_id']]['band'],['S','A','B'])]:
        facet=[]
        for v in values:
            for k in range(meta['bucket_lower_min'],meta['bucket_lower_max']+1):
                tt=[t for t in all_trades if fn(t)==v and lm[t['entry_id']]['bucket_pp_lower']==k]
                facet.append({'facet':v,'bucket_pp_lower':k,**flow_summary(tt,dm)})
        facets[key]=facet
    return {'total':flow_summary(all_trades,dm),'buckets':buckets,'cumulative':cumulative,
            'near_zero_0_to_1':next(f for f in buckets if f['bucket_pp_lower']==0),
            'facets':facets,'flow_unit_note':'Repeated BUY debit is turnover, not simultaneous cash. Original chain account only. Each trade classified by its quantity-specific exact credit/debit return; reference equality verified.'}
def miss_reasons(data,dm,meta):
    groups={'SLOT_RESERVE_REJECT':'Reserve','MAX_POSITION_CAP':'MAX3','CASH_OR_LOT_CONSTRAINED':'cash/lot',
            'CAPITAL_EOD_ENTRY_CUTOFF':'cutoff','UPWARD_BELOW_BASELINE':'rank/admission','SYMBOL_ALREADY_OPEN':'same-symbol'}
    cumulative=[]
    for label in meta['labels']:
        selected=[r for r in data if r['known'] and r['events'][label] and dm[r['entry_id']]['reason']!='FUNDED']
        native=Counter(dm[r['entry_id']]['reason'] for r in selected); grouped=Counter()
        for reason,n in native.items():grouped[groups.get(reason,'other')]+=n
        cumulative.append({'label':label,'missed_N':len(selected),'eligible_missed_N':sum(r['execution_eligible'] for r in selected),
             'grouped_reasons':{k:grouped[k] for k in ['Reserve','MAX3','cash/lot','cutoff','rank/admission','same-symbol','other']},
             'native_reasons':dict(native),'actual_recovery_shares':None})
    unknown=Counter(dm[r['entry_id']]['reason'] for r in data if not r['known'] and dm[r['entry_id']]['reason']!='FUNDED')
    return {'cumulative':cumulative,'unknown_by_native_reason':dict(unknown),
            'standalone_missed_profit_sum':'NOT_COMPUTED_NOT_COUNTERFACTUAL_WEALTH',
            'unfunded_shares':'No actual funded quantity; no portfolio recovery quantity inferred'}
def checkpoint(event_name,completed,next_step,details):
    derivation=read(PRIVATE/'DERIVATION_COMPLETE.json')
    COUNTS.update(derivation_logical_starts=1,derivation_successful_outputs=1,
                  derivation_technical_resume_N=derivation['technical_resume_N'],
                  derivation_failed_incomplete_attempts=derivation['technical_resume_N'])
    state=read(OUT/'CURRENT_STATE.json');state.update(exact_jst=now(),status=event_name,completed=completed,
        not_executed=['New model fit','New Capital policy/replay','V5.2 implementation','Market/EXIT rematerialization'],
        counts=COUNTS,next=next_step,details=details)
    save(OUT/'CURRENT_STATE.json',state)
    event_row={**state,'event':event_name}
    save(OUT/'checkpoints'/f'{event_name}.json',event_row)
    with (OUT/'WORK_STATUS_LOG.jsonl').open('a') as f:f.write(json.dumps(event_row,ensure_ascii=False)+'\n')
def census_phase():
    data,meta=derive_once();binding,paths,score_path=source_data()
    decisions=rows(paths['native_decisions']);trades=rows(paths['native_trades'])
    lm,dm,tm=join(data,decisions,trades);assert set(lm)==set(dm)
    global next_r; next_r=lm
    assert len(data)==1039 and sum(r['known'] for r in data)==1016
    assert sum(r['execution_eligible'] for r in data)==1028
    assert sum(r['execution_eligible'] and r['rank_pass'] for r in data)==494
    assert len(tm)==150 and sum(r['known'] and r['rank_pass'] for r in data)==492
    assert sum(r['events']['R5'] is True and r['rank_pass'] for r in data)==34
    assert sum(r['events']['R10'] is True and r['rank_pass'] for r in data)==16
    assert sum(lm[k]['events']['R5'] for k in tm)==19 and sum(lm[k]['events']['R10'] for k in tm)==11
    pops=populations(data,dm); result={k:census(rr,dm,tm,meta) for k,rr in pops.items()}
    save(OUT/'R_FULL_CENSUS.json',{'schema':'ARK_R_FULL_CENSUS_V1','exact_jst':now(),'unit':'Unique original OOF Frozen Entry','grid':meta,
         'populations':result,'existing_certified_census_match':True})
    csv_file(OUT/'R_FULL_CENSUS.csv',[{'population':name,**b} for name,z in result.items() for b in z['buckets']]+[
             {'population':name,'bucket_pp_lower':'UNKNOWN','bucket_pp_upper':None,**z['unknown_mask']} for name,z in result.items()])
    groups={'ALL_KNOWN_U5':[r for r in data if r['U5'] is True],
            'U5_NOT_U10':[r for r in data if r['U5'] is True and r['U10'] is False],
            'U10':[r for r in data if r['U10'] is True],
            'NON_U5':[r for r in data if r['U5'] is False],
            'U_UNKNOWN':[r for r in data if r['U5'] is None or r['U10'] is None]}
    cross={k:census(rr,dm,tm,meta) for k,rr in groups.items()}
    save(OUT/'U_R_CROSS.json',{'schema':'ARK_U_OPPORTUNITY_TO_R_REALIZATION_V1','exact_jst':now(),
         'overlap_note':'ALL_KNOWN_U5 includes U10; U5_NOT_U10/U10/NON_U5/U_UNKNOWN form the exclusive U partition. R unknown is separate.',
         'groups':cross,'not_prediction_accuracy':True})
    csv_file(OUT/'U_R_CROSS.csv',[{'U_group':name,'R_known_N':z['known_N'],'R_unknown_N':z['unknown_N'],**b} for name,z in cross.items() for b in z['buckets']])
    flow=capital_flow(data,dm,tm,meta)
    save(OUT/'V5_R_CAPITAL_FLOW.json',{'schema':'ARK_V5_R_FLOW_V1','exact_jst':now(),'account':'Original V5 chain reused, no replay',**flow})
    csv_file(OUT/'V5_R_CAPITAL_FLOW.csv',flow['buckets'])
    miss=miss_reasons(data,dm,meta);save(OUT/'V5_R_MISS_REASONS.json',{'schema':'ARK_V5_R_MISS_V1','exact_jst':now(),**miss})
    csv_file(OUT/'V5_R_MISS_REASONS.csv',miss['cumulative'])
    reset=read(OLD/'V5_RESET20_RESULT.json');windows=[]
    for w in reset['windows']:
        base={k:w[k] for k in ['window_id','start_session','end_session','status','coverage_complete','calendar_contiguous','execution_complete','final_cash_for_primary']}
        if w['status']!='COMPLETE':
            windows.append({**base,'R_flow':None});continue
        dest=PREVIOUS_PRIVATE/'runs/V5_RESET20'/w['window_id'];ds=rows(dest/'DECISIONS.jsonl.gz');ts=rows(dest/'TRADES.jsonl.gz')
        pool=[r for r in data if r['session'] in w['sessions']];wl,wd,wt=join(pool,ds,ts)
        next_r=wl;wf=capital_flow(pool,wd,wt,meta)
        assert Decimal(w['final_cash_for_primary'])==Decimal('1000000')+Decimal(wf['total']['realized_pnl_jpy'])
        windows.append({**base,'R_flow':wf})
    next_r=lm
    joined=[]
    for w in windows:
        if w['R_flow'] is None: continue
        f=w['R_flow']; cm={x['label']:x for x in f['cumulative']}
        joined.append({'window_id':w['window_id'],'final_cash_jpy':w['final_cash_for_primary'],
             'buy_debit_jpy':f['total']['buy_debit_jpy'],'pnl_jpy':f['total']['realized_pnl_jpy'],
             **{f'{label}_debit_share':cm[label]['debit_share'] for label in ['RNEG','R3','R5','R10']},
             'R0_to_1_debit_share':f['near_zero_0_to_1']['debit_share']})
    def corr(key):
        x=[r[key] for r in joined];y=[float(r['final_cash_jpy']) for r in joined]
        if len(set(x))<2:return None
        return statistics.correlation(x,y)
    correlations={key:corr(key) for key in ['RNEG_debit_share','R3_debit_share','R5_debit_share','R10_debit_share','R0_to_1_debit_share']}
    # Facet tables are original-chain anatomy; reset accounts need only per-bucket flows.
    for w in windows:
        if w['R_flow'] is not None:w['R_flow'].pop('facets')
    save(OUT/'RESET20_R_FLOW.json',{'schema':'ARK_SAVED_RESET20_R_FLOW_V1','exact_jst':now(),'planned_N':21,'complete_N':9,'blocked_coverage_N':12,
         'windows':windows,'descriptive_correlations':correlations,'overlap_note':'Nine overlapping saved accounts, not independent market samples; no CI/significance or gain claim','new_replays':0})
    csv_file(OUT/'RESET20_R_FLOW.csv',joined)
    checkpoint('CENSUS_AND_CAPITAL_FLOW_COMPLETE',['Source binding/contract fixed','Mechanical derived labels once','Full census/U cross/native flow/miss reasons','Saved reset account join'],
               'Save census checkpoint; then analyze existing score curves and independent raw-debit/credit audit',
               {'known_N':meta['known_N'],'unknown_N':meta['unknown_N'],'grid':[meta['bucket_lower_min'],meta['bucket_lower_max']],
                'original_funded_N':150,'reset_complete_N':9,'original_debit':flow['total']['buy_debit_jpy'],'original_pnl':flow['total']['realized_pnl_jpy']})
    print(json.dumps({'phase':'census','grid':meta,'all_return':result['ALL_FROZEN_ENTRY']['continuous_return'],
                      'cumulative':{x['label']:x['event_N'] for x in result['ALL_FROZEN_ENTRY']['cumulative']},'U_groups':{k:[z['N'],z['known_N'],z['unknown_N']] for k,z in cross.items()},
                      'funded_total':flow['total']},ensure_ascii=False))
def auc(pairs):
    n1=sum(y for s,y in pairs);n0=len(pairs)-n1
    if not n1 or not n0:return None
    groups=defaultdict(lambda:[0,0])
    for s,y in pairs:groups[s][int(y)]+=1
    lower0=0;twice=0
    for s,(zero,one) in sorted(groups.items()):twice+=one*(2*lower0+zero);lower0+=zero
    return twice/(2*n0*n1)
def score_phase():
    data,meta=universe();binding,paths,score_path=source_data()
    lm,dm,tm=join(data,rows(paths['native_decisions']),rows(paths['native_trades']))
    scores={r['entry_id']:r for r in rows(score_path)};assert set(scores)==set(lm)
    assert all(scores[k]['session']==lm[k]['session'] and scores[k]['block']==lm[k]['block'] and scores[k]['entry_minute']==lm[k]['entry_minute'] for k in lm)
    assert all(math.isfinite(s[f]) for s in scores.values() for f in HEADS.values())
    write_rows(PRIVATE/'evaluation-only/ENTRY_JOINED_ANATOMY.jsonl.gz',
               [{**r,'causal_scores':scores[r['entry_id']],
                 'native_decision':dm[r['entry_id']],
                 'actual_funded_trade':tm.get(r['entry_id'])} for r in data])
    pops=populations(data,dm); names=['EXECUTION_ELIGIBLE','RANK_PASS_EXECUTION_ELIGIBLE','V5_FUNDED']
    # Public old evidence summarizes sessions; authenticated private support has the full table.
    old=read(OLD/'CAPITAL_DIAGNOSTIC.json')
    old['new_R_score_support']=read(PREVIOUS_PRIVATE/'evaluation-only/SCORE_SUPPORT_FULL.json')
    pooled=[];strata=[];buckets=[]
    numeric_labels=[k for k in meta['labels'] if k not in ['R0PLUS','RPOS','ZERO','RNEG','Loser']]
    reuse_N=0;new_auc_N=0
    for name in names:
        original=pops[name];known=[r for r in original if r['known']]
        oldmask={'EXECUTION_ELIGIBLE':'eligible','RANK_PASS_EXECUTION_ELIGIBLE':'eligible_rankpass'}.get(name)
        for label in numeric_labels:
            selected=[r for r in known if r['events'][label]]; non=[r for r in known if not r['events'][label]]
            for head,col in HEADS.items():
                reuse=label in ['R5','R10'] and oldmask is not None
                if reuse:
                    authority=old['new_R_score_support'][oldmask][head][label]
                    assert authority['N']==len(known) and authority['positive_N']==len(selected)
                    value=authority['AUROC'];reuse_N+=1
                else:value=auc([(scores[r['entry_id']][col],r['events'][label]) for r in known]);new_auc_N+=1
                pooled.append({'population':name,'head':head,'label':label,'N':len(known),'unknown_N':len(original)-len(known),
                  'positive_N':len(selected),'negative_N':len(non),'event_rate':rate(len(selected),len(known)),
                  'raw_direction_AUROC':value,'prior_AUROC_reused':reuse,
                  'event_score_mean':statistics.mean(scores[r['entry_id']][col] for r in selected) if selected else None,
                  'nonevent_score_mean':statistics.mean(scores[r['entry_id']][col] for r in non) if non else None})
            for dimension in ['block','session']:
                for value in sorted({r[dimension] for r in original}):
                    rr=[r for r in known if r[dimension]==value]; allrr=[r for r in original if r[dimension]==value]
                    z={'population':name,'dimension':dimension,'stratum':value,'label':label,'known_N':len(rr),'unknown_N':len(allrr)-len(rr),
                       'positive_N':sum(r['events'][label] for r in rr),'event_rate':rate(sum(r['events'][label] for r in rr),len(rr))}
                    for head,col in HEADS.items():
                        if label in ['R5','R10'] and oldmask is not None:
                            oldrows=old['new_R_score_support'][oldmask][head][label]['by_'+dimension]
                            a=next((x for x in oldrows if x[dimension]==value),None)
                            av=a['AUROC'] if a else None;reuse_N+=1
                            if a:assert a['N']==len(rr) and a['positive_N']==z['positive_N']
                        else:av=auc([(scores[r['entry_id']][col],r['events'][label]) for r in rr]);new_auc_N+=1
                        z[head+'_AUROC']=av
                    strata.append(z)
        for bucket_kind,fn in [('native_rank',lambda r:r['rank']),('pP_native_band',lambda r:scores[r['entry_id']]['band']),
                                ('pP_training_rank_half',lambda r:'HIGH' if scores[r['entry_id']]['r']>=.5 else 'LOW'),
                                ('MRET_training_rank_half',lambda r:'HIGH' if scores[r['entry_id']]['rM']>=.5 else 'LOW')]:
            for bucket in sorted({fn(r) for r in original}):
                rr=[r for r in known if fn(r)==bucket];allrr=[r for r in original if fn(r)==bucket]
                for label in numeric_labels:
                    buckets.append({'population':name,'bucket_kind':bucket_kind,'bucket':bucket,'label':label,
                         'N':len(allrr),'known_N':len(rr),'unknown_N':len(allrr)-len(rr),
                         'event_N':sum(r['events'][label] for r in rr),'event_rate':rate(sum(r['events'][label] for r in rr),len(rr))})
    save(OUT/'SCORE_R_SPECTRUM.json',{'schema':'ARK_EXISTING_CAUSAL_SCORE_R_CURVES_V1','exact_jst':now(),'heads':HEADS,
         'direction':'Original higher score, RN not inverted','pooled':pooled,'fixed_buckets':buckets,
         'strata_file':'SCORE_R_STRATA.csv','strata_row_N':len(strata),'score_quantile_splits':0,
         'new_fit_N':0,'prior_R5_R10_AUROC_cells_reused':reuse_N,'new_descriptive_AUROC_cells':new_auc_N,
         'MRET_absolute_loss_defense':'INCONCLUSIVE','productionReady':False})
    csv_file(OUT/'SCORE_R_SPECTRUM.csv',pooled);csv_file(OUT/'SCORE_R_STRATA.csv',strata);csv_file(OUT/'SCORE_R_FIXED_BUCKETS.csv',buckets)
    checkpoint('SCORE_AND_CAPITAL_ANATOMY_COMPLETE',['Exact spectrum/census/U cross/native flow/misses','Saved reset flow join','All existing raw-score directions and inherited strata/buckets'],
               'Complete independent R audit, full charts and maximum-one design-only mechanism assessment',
               {'score_curve_rows':len(pooled),'strata_rows':len(strata),'fixed_bucket_rows':len(buckets),'prior_AUROC_cells_reused':reuse_N,'new_descriptive_AUROC_cells':new_auc_N})
    print(json.dumps({'phase':'scores','pooled_curve_rows':len(pooled),'strata_rows':len(strata),'fixed_bucket_rows':len(buckets),
                      'eligible_curve':[x for x in pooled if x['population']=='EXECUTION_ELIGIBLE' and x['label'] in ['R1','R2','R3','R4','R5','R10','RN1','RN2','RN3','RN5','RN10']]}))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['census','scores']);args=parser.parse_args()
    if args.phase=='census':census_phase()
    else:score_phase()
