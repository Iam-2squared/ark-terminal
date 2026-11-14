"""Read-only, sealed-spec E0 saved-ledger diagnostics. No runtime/replay imports."""
from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
from statistics import median
from collections import Counter, defaultdict
import json, gzip, csv, hashlib

ROOT=Path(__file__).resolve().parent
PUB=ROOT/'public'
PRI=ROOT/'private'/'baseline_diagnostic'
PUB.mkdir(parents=True,exist_ok=True)
PRI.mkdir(parents=True,exist_ok=True)
D=Decimal
F=Fraction
WINDOWS=[f'W{i}' for i in range(13,22)]
BANDS=['L5_PLUS','L4_5','L3_4','L2_3','L1_2','L0_1','ZERO','P0_1','P1_2','P2_3','P3_4','P4_5','P5_PLUS','R_UNKNOWN']

def rows(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f if line.strip()]

def dec80(value):
    with localcontext() as c:
        c.prec=80
        return str(D(value.numerator)/D(value.denominator))

def exact(value):
    if value is None:return None
    value=F(value)
    return {'numerator':str(value.numerator),'denominator':str(value.denominator),'decimal80':dec80(value)}

def money(value):return str(D(value))

def save(path,value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')

def csvsave(path,data):
    columns=list(dict.fromkeys(k for row in data for k in row))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,columns,lineterminator='\n');writer.writeheader()
        for row in data:
            writer.writerow({k:json.dumps(v,sort_keys=True,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in row.items()})

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

def maxdd(values):
    peak=D(1000000);worst=F(0)
    for value in values:
        peak=max(peak,value)
        worst=max(worst,F(peak-value)/F(peak)*100)
    return worst

def time_band(minute):
    return 'BEFORE_1400' if minute<840 else '1400_TO_1429' if minute<870 else 'FROM_1430'

def group_summary(scope, group, data, unique=False):
    rank,occ,sd,clock=group
    funded=[r for r in data if r['funded']]
    counts=lambda predicate:len({r['entry_id'] for r in data if predicate(r)}) if unique else sum(predicate(r) for r in data)
    row={'window_id':scope,'arm':'E0','count_scope':'UNIQUE_ENTRY_WITHIN_CONTEXT_GROUP' if unique else 'ACCOUNT_ARRIVAL_RECORDS',
         'native_rank':rank,'native_pre_decision_occupancy':occ,'own_confirmed_SD_release_seen_today':sd,'time_band':clock,
         'arrival_N':counts(lambda r:True),'native_gate_visited_N':counts(lambda r:r['native_gate_visited']),
         'native_gate_permit_N':counts(lambda r:r['native_gate_permit']),
         'native_gate_reject_N':counts(lambda r:r['native_gate_visited'] and not r['native_gate_permit']),
         'funded_N':counts(lambda r:r['funded']),
         'native_permit_quantity_zero_N':counts(lambda r:r['native_gate_permit'] and r['quantity']==0),
         'native_permit_sub100_N':counts(lambda r:r['native_gate_permit'] and r['quantity']<100),
         'all_quantity_zero_N':counts(lambda r:r['quantity']==0),
         'funded_first_purchase_in_session_N':counts(lambda r:r['funded'] and r['purchase_sequence']==1),
         'funded_followup_purchase_in_session_N':counts(lambda r:r['funded'] and r['purchase_sequence']>1),
         'funded_normal_exit_already_released_today_N':counts(lambda r:r['funded'] and r['normal_exit_release_seen_today']),
         'ALL_MINUS_N':counts(lambda r:r['funded'] and r['_R'] is not None and r['_R']<0),
         'ALL_PLUS_N':counts(lambda r:r['funded'] and r['_R'] is not None and r['_R']>0)}
    for b in BANDS:row[b+'_N']=counts(lambda r:r['funded'] and r['R_bucket']==b)
    for bound in range(1,6):
        row[f'R_LE_MINUS{bound}_N']=counts(lambda r:r['funded'] and r['_R'] is not None and r['_R']<=-bound)
        row[f'R_GE_PLUS{bound}_N']=counts(lambda r:r['funded'] and r['_R'] is not None and r['_R']>=bound)
    reason_ids=defaultdict(set)
    for r in data:reason_ids[r['reason']].add(r['entry_id'])
    row['quantity_zero_reason_counts']={reason:len(ids) for reason,ids in reason_ids.items() if reason!='FUNDED'} if unique else dict(Counter(r['reason'] for r in data if r['quantity']==0))
    if unique:
        row.update({'quantity':None,'BUY_debit_jpy':None,'positive_PnL_jpy':None,'gross_loss_jpy':None,
                    'net_PnL_jpy':None,'capital_lock_jpy_minutes':None,
                    'unique_money_status':'NOT_DEFINED_ACCOUNT_SIZES_DIFFER; NO_REPRESENTATIVE_ACCOUNT_SELECTED'})
    else:
        row.update({'quantity':sum(r['quantity'] for r in funded),
                    'BUY_debit_jpy':money(sum((r['_debit'] for r in funded),D(0))),
                    'positive_PnL_jpy':money(sum((r['_pnl'] for r in funded if r['_pnl']>0),D(0))),
                    'gross_loss_jpy':money(-sum((r['_pnl'] for r in funded if r['_pnl']<0),D(0))),
                    'net_PnL_jpy':money(sum((r['_pnl'] for r in funded),D(0))),
                    'capital_lock_jpy_minutes':money(sum((r['_lock'] for r in funded),D(0))),
                    'R_median_pct_exact':exact(median([r['_R'] for r in funded if r['_R'] is not None])) if funded else None})
        for bound in range(1,6):
            row[f'R_LE_MINUS{bound}_gross_loss_jpy']=money(-sum((r['_pnl'] for r in funded if r['_R']<=-bound),D(0)))
            row[f'R_GE_PLUS{bound}_PnL_jpy']=money(sum((r['_pnl'] for r in funded if r['_R']>=bound),D(0)))
    return row

def metrics(w, result, decisions, trades, curves, arrivals):
    funded=[r for r in arrivals if r['funded']]
    complete=result['daily_series']
    pnl=sum((D(r['pnl']) for r in trades),D(0))
    final=D(result['final_equity'])
    assert final-D(result['initial_cash'])==pnl,w
    assert sum(r['quantity'] for r in funded)==sum(r['quantity'] for r in trades),w
    assert len(funded)==len(trades)==result['funded_N'],w
    assert result['status']=='COMPLETE' and result['unsettled_N']==0,w
    assert all(d['status']=='COMPLETE' for d in complete),w
    assert D(curves[-1]['equity'])==final,w
    assert sum(t['exit_kind']=='SHARP_DROP_FIRST_OBSERVED_EXIT_V0' for t in trades)==result['SHARP_DROP_fill_N'],w
    vals=[D(d['ending_cash'])-D(d['starting_cash']) for d in complete]
    minute_dd=maxdd([D(c['equity']) for c in curves]);eod_dd=maxdd([D(d['ending_cash']) for d in complete])
    samples=[c for c in curves if 540<=c['minute']<690 or 750<=c['minute']<930]
    occupancy=Counter(c['concurrent'] for c in samples)
    assert len(samples)==330*len(complete),w
    cumulative_debit=sum((D(t['debit']) for t in trades),D(0))
    cumulative_credit=sum((D(t['credit']) for t in trades),D(0))
    cash_weighted=F(sum((D(c['cash']) for c in samples),D(0)))/F(sum((D(c['equity']) for c in samples),D(0)))
    cash_ratios=[F(D(c['cash']))/F(D(c['equity'])) for c in samples]
    with localcontext() as c:
        c.prec=80
        mean_cash=sum((D(x.numerator)/D(x.denominator) for x in cash_ratios),D(0))/len(cash_ratios)
    out={'window_id':w,'arm':'E0','status':result['status'],'session_N':len(complete),
         'initial_cash_jpy':result['initial_cash'],'final_equity_jpy':result['final_equity'],'profit_jpy':money(pnl),
         'return_pct_exact':exact(F(pnl)/F(D(result['initial_cash']))*100),'funded_N':len(funded),
         'arrival_N':len(decisions),'unique_funded_entry_N':len({r['entry_id'] for r in funded}),
         'SHARP_DROP_full_release_N':result['SHARP_DROP_fill_N'],'gross_loss_jpy':money(-sum((r['_pnl'] for r in funded if r['_pnl']<0),D(0))),
         'gross_positive_jpy':money(sum((r['_pnl'] for r in funded if r['_pnl']>0),D(0))),
         'ALL_MINUS_N':sum(r['_R']<0 for r in funded),'ALL_PLUS_N':sum(r['_R']>0 for r in funded),
         'ZERO_N':sum(r['_R']==0 for r in funded),'R_UNKNOWN_N':sum(r['_R'] is None for r in funded),
         'negative_day_N':sum(v<0 for v in vals),'worst_daily_PnL_jpy':money(min(vals)),
         'worst_trade_loss_jpy':money(-min([r['_pnl'] for r in funded]+[D(0)])),
         'worst_trade_R_pct_exact':exact(min(r['_R'] for r in funded)),
         'minute_MTM_MaxDD_pct_exact':exact(minute_dd),'EOD_MaxDD_pct_exact':exact(eod_dd),
         'market_time_samples_N':len(samples),'occupancy_market_minutes':{str(i):occupancy[i] for i in range(4)},
         'market_time_grid':'540<=minute<690 OR 750<=minute<930;330 samples/session',
         'cash_ratio_equity_weighted_mean_exact':exact(cash_weighted),
         'utilization_equity_weighted_mean_exact':exact(1-cash_weighted),
         'cash_ratio_arithmetic_mean_decimal80':str(mean_cash),
         'cash_ratio_arithmetic_mean_status':'80_significant_digit_decimal_evaluation;not_used_for_comparison_gates',
         'cash_ratio_median_exact':exact(median(cash_ratios)),
         'cumulative_BUY_debit_jpy':money(cumulative_debit),'cumulative_SELL_credit_jpy':money(cumulative_credit),
         'round_trip_turnover_jpy':money(cumulative_debit+cumulative_credit),
         'first_purchase_in_session_N':sum(r['purchase_sequence']==1 for r in funded),
         'followup_purchase_in_session_N':sum(r['purchase_sequence']>1 for r in funded),
         'funded_after_own_SD_release_N':sum(r['own_confirmed_SD_release_seen_today'] for r in funded),
         'funded_after_normal_exit_release_N':sum(r['normal_exit_release_seen_today'] for r in funded),
         'quantity_zero_reason_counts':dict(Counter(r['reason'] for r in arrivals if r['quantity']==0))}
    out['return_buckets']={}
    for b in BANDS:
        cohort=[r for r in funded if r['R_bucket']==b]
        out['return_buckets'][b]={'funded_N':len(cohort),'pct_all_funded_exact':exact(F(len(cohort),len(funded))*100),
            'quantity':sum(r['quantity'] for r in cohort),'BUY_debit_jpy':money(sum((r['_debit'] for r in cohort),D(0))),
            'positive_PnL_jpy':money(sum((r['_pnl'] for r in cohort if r['_pnl']>0),D(0))),
            'gross_loss_jpy':money(-sum((r['_pnl'] for r in cohort if r['_pnl']<0),D(0))),
            'net_PnL_jpy':money(sum((r['_pnl'] for r in cohort),D(0))),
            'capital_lock_jpy_minutes':money(sum((r['_lock'] for r in cohort),D(0))),
            'R_median_pct_exact':exact(median([r['_R'] for r in cohort])) if cohort else None}
    for bound in range(1,6):
        losing=[r for r in funded if r['_R']<=-bound];winning=[r for r in funded if r['_R']>=bound]
        out[f'R_LE_MINUS{bound}']={'N':len(losing),'gross_loss_jpy':money(-sum((r['_pnl'] for r in losing),D(0)))}
        out[f'R_GE_PLUS{bound}']={'N':len(winning),'PnL_jpy':money(sum((r['_pnl'] for r in winning),D(0)))}
    return out

def main():
    spec=json.loads((PUB/'SPEC_AD01_PRECOMMIT.json').read_text())
    assert spec['status']=='SEALED_BEFORE_NEW_CANDIDATE_RESULTS'
    stream=rows(ROOT/'inputs'/'candidate_stream')
    native={r['entry_id']:r for r in stream}
    assert len(native)==len(stream)
    allrows=[];diagnostic=[];metrics_by_window=[];source_hashes={}
    for w in WINDOWS+['CHAIN38']:
        path=ROOT/'baseline'/'private'/'runs'/w/'E'
        result=json.loads((path/'RESULT.json').read_text())
        decisions=rows(path/'DECISIONS.jsonl.gz');trades=rows(path/'TRADES.jsonl.gz');curves=rows(path/'CURVE.jsonl.gz')
        for name in ['RESULT.json','DECISIONS.jsonl.gz','TRADES.jsonl.gz','CURVE.jsonl.gz','INTENTS.jsonl.gz']:
            source_hashes[f'{w}/E/{name}']=hashlib.sha256((path/name).read_bytes()).hexdigest()
        subset={r['entry_id'] for r in stream if r['session'] in result['planned_sessions']}
        assert subset=={r['entry_id'] for r in decisions} and len(subset)==len(decisions),w
        trade_map={t['entry_id']:t for t in trades}
        assert len(trade_map)==len(trades),w
        sd=defaultdict(list);normal=defaultdict(list)
        for t in trades:
            (sd if t['exit_kind']=='SHARP_DROP_FIRST_OBSERVED_EXIT_V0' else normal)[t['session']].append(t['release_minute'])
        purchase_seq=Counter();arrivals=[]
        for d in decisions:
            r=native[d['entry_id']]
            assert d['session']==r['session'] and d['minute']==r['entry_minute'] and d['rank']==r['rank'] and d['admission']==r['admission'],w
            funded=d['reason']=='FUNDED';trade=trade_map.get(d['entry_id'])
            assert funded==(trade is not None),w
            if funded:purchase_seq[d['session']]+=1
            debit=D(trade['debit']) if trade else D(0);pnl=D(trade['pnl']) if trade else D(0)
            rp=F(pnl)/F(debit)*100 if trade else None
            occ=d.get('pre_decision_occupancy',len(d['held_before_batch']))
            row={'window_id':w,'entry_id':d['entry_id'],'session':d['session'],'minute':d['minute'],
                 'native_rank':r['rank'],'native_pre_decision_occupancy':occ,
                 'occupancy_source':'SAVED_NATIVE_GATE_AUDIT' if 'pre_decision_occupancy' in d else 'ACTUAL_POSITIONS_GATE_NOT_VISITED',
                 'own_confirmed_SD_release_seen_today':any(m<=d['minute'] for m in sd[d['session']]),
                 'normal_exit_release_seen_today':any(m<=d['minute'] for m in normal[d['session']]),
                 'time_band':time_band(d['minute']),'native_gate_visited':'slot_gate_action' in d,
                 'native_gate_permit':d.get('slot_gate_action')=='ADMIT','native_gate_action':d.get('slot_gate_action','NOT_VISITED'),
                 'native_gate_reason':d.get('slot_gate_reason'),'reason':d['reason'],'funded':funded,
                 'quantity':d['quantity'],'funded_slot':d.get('funded_slot'),
                 'purchase_sequence':purchase_seq[d['session']] if funded else 0,
                 'R_pct_exact':exact(rp),'R_bucket':bucket(rp),'PnL_jpy':money(pnl) if funded else None,
                 'BUY_debit_jpy':money(debit) if funded else None,
                 'release_minute':trade['release_minute'] if trade else None,'exit_kind':trade['exit_kind'] if trade else None,
                 '_R':rp,'_pnl':pnl,'_debit':debit,'_lock':debit*(trade['release_minute']-trade['entry_minute']) if trade else D(0)}
            arrivals.append(row)
        groups=defaultdict(list)
        for row in arrivals:groups[(row['native_rank'],row['native_pre_decision_occupancy'],row['own_confirmed_SD_release_seen_today'],row['time_band'])].append(row)
        diagnostic += [group_summary(w,key,data) for key,data in sorted(groups.items())]
        metrics_by_window.append(metrics(w,result,decisions,trades,curves,arrivals))
        csvsave(PRI/(w+'_ARRIVALS.csv'),[{k:v for k,v in r.items() if not k.startswith('_')} for r in arrivals])
        allrows.extend(arrivals)
    primary=[r for r in allrows if r['window_id'] in WINDOWS]
    groups=defaultdict(list)
    for row in primary:groups[(row['native_rank'],row['native_pre_decision_occupancy'],row['own_confirmed_SD_release_seen_today'],row['time_band'])].append(row)
    diagnostic += [group_summary('PRIMARY9_ACCOUNT_SUM',key,data) for key,data in sorted(groups.items())]
    diagnostic += [group_summary('PRIMARY9_UNIQUE_ENTRY_BY_CONTEXT',key,data,True) for key,data in sorted(groups.items())]
    csvsave(PUB/'BASELINE_VACANCY_DIAGNOSTIC.csv',diagnostic)
    finals=[D(m['final_equity_jpy']) for m in metrics_by_window if m['window_id'] in WINDOWS]
    primary_metrics=[m for m in metrics_by_window if m['window_id'] in WINDOWS]
    aggregate={'complete_primary_windows_N':len(finals),'final_equity_min_jpy':money(min(finals)),
               'final_equity_median_jpy':money(median(finals)),'final_equity_mean_jpy_exact':exact(sum((F(v) for v in finals),F(0))/len(finals)),
               'final_equity_max_jpy':money(max(finals)),'red_window_N':sum(v<D(1000000) for v in finals),
               'two_million_hit_N':sum(v>=D(2000000) for v in finals),
               'account_arrival_records_N':len(primary),'unique_market_arrival_entry_N':len({r['entry_id'] for r in primary}),
               'account_funded_trades_N':sum(r['funded'] for r in primary),
               'unique_market_funded_entry_N':len({r['entry_id'] for r in primary if r['funded']}),
               'gross_loss_jpy':money(sum((D(m['gross_loss_jpy']) for m in primary_metrics),D(0))),
               'gross_positive_jpy':money(sum((D(m['gross_positive_jpy']) for m in primary_metrics),D(0))),
               'ALL_MINUS_N':sum(m['ALL_MINUS_N'] for m in primary_metrics),'ALL_PLUS_N':sum(m['ALL_PLUS_N'] for m in primary_metrics),
               'ZERO_N':sum(m['ZERO_N'] for m in primary_metrics),'R_UNKNOWN_N':sum(m['R_UNKNOWN_N'] for m in primary_metrics),
               'negative_day_N':sum(m['negative_day_N'] for m in primary_metrics),
               'minute_MTM_MaxDD_pct_exact':exact(max(F(int(m['minute_MTM_MaxDD_pct_exact']['numerator']),int(m['minute_MTM_MaxDD_pct_exact']['denominator'])) for m in primary_metrics)),
               'EOD_MaxDD_pct_exact':exact(max(F(int(m['EOD_MaxDD_pct_exact']['numerator']),int(m['EOD_MaxDD_pct_exact']['denominator'])) for m in primary_metrics)),
               'SHARP_DROP_full_release_N':sum(m['SHARP_DROP_full_release_N'] for m in primary_metrics),
               'quantity_zero_reason_counts':dict(Counter(r['reason'] for r in primary if r['quantity']==0)),
               'native_permit_quantity_zero_N':sum(r['native_gate_permit'] and r['quantity']==0 for r in primary)}
    for bound in range(1,6):
        aggregate[f'R_LE_MINUS{bound}']={'N':sum(m[f'R_LE_MINUS{bound}']['N'] for m in primary_metrics),
            'gross_loss_jpy':money(sum((D(m[f'R_LE_MINUS{bound}']['gross_loss_jpy']) for m in primary_metrics),D(0)))}
        aggregate[f'R_GE_PLUS{bound}']={'N':sum(m[f'R_GE_PLUS{bound}']['N'] for m in primary_metrics),
            'PnL_jpy':money(sum((D(m[f'R_GE_PLUS{bound}']['PnL_jpy']) for m in primary_metrics),D(0)))}
    aggregate['return_buckets']={b:{'funded_N':sum(m['return_buckets'][b]['funded_N'] for m in primary_metrics),
        'BUY_debit_jpy':money(sum((D(m['return_buckets'][b]['BUY_debit_jpy']) for m in primary_metrics),D(0))),
        'positive_PnL_jpy':money(sum((D(m['return_buckets'][b]['positive_PnL_jpy']) for m in primary_metrics),D(0))),
        'gross_loss_jpy':money(sum((D(m['return_buckets'][b]['gross_loss_jpy']) for m in primary_metrics),D(0))),
        'net_PnL_jpy':money(sum((D(m['return_buckets'][b]['net_PnL_jpy']) for m in primary_metrics),D(0)))} for b in BANDS}
    unique_groups=defaultdict(list)
    for row in primary:
        if row['funded']:unique_groups[row['entry_id']].append(row)
    unique_buckets=Counter()
    for key,rr in unique_groups.items():
        assert len({r['_R'] for r in rr})==1,'FUNDED_SAME_ENTRY_R_CHANGED'
        unique_buckets[rr[0]['R_bucket']]+=1
    aggregate['unique_funded_entry_return_bucket_N']={b:unique_buckets[b] for b in BANDS}
    save(PUB/'E0_BASELINE_METRICS.json',{'research_id':'AD01','arm':'E0','saved_baseline_only':True,'replay_paths':0,
         'diagnostic_computation_N':1,'new_candidate_results_read':False,'policy_selection_from_diagnostic':False,
         'data_scope':'Previously observed adaptive Development;9 overlapping RESET20 accounts,not independent months or fresh OOS',
         'unique_group_scope':'Unique Entry counts within context groups;same Entry can occur in multiple account contexts. Money/quantity intentionally undefined in unique context rows.',
         'classification':'DIAGNOSTIC_ONLY','primary_windows':WINDOWS,'aggregate_primary9':aggregate,
         'per_window':metrics_by_window,'source_hashes':source_hashes,
         'numeric_contract':'Money exact Decimal;R=pnl/debit*100 exact Fraction;count ratios and drawdowns exact Fraction. decimal80 is display;arithmetic cash ratio mean explicitly approximate at80 significant digits.'})
    save(PRI/'SOURCE_AND_SCHEMA_RECEIPT.json',{'native_stream_sha256':hashlib.sha256((ROOT/'inputs'/'candidate_stream').read_bytes()).hexdigest(),
         'SPEC_sha256':hashlib.sha256((PUB/'SPEC_AD01_PRECOMMIT.json').read_bytes()).hexdigest(),
         'saved_source_hashes':source_hashes,'native_arrival_exact_identity_verified_all_windows':True,
         'SD_flag_definition':'Own saved confirmed full SHARP_DROP release in same session at release_minute<=arrival minute;confirmed fill before buy at same timestamp.',
         'occupancy_definition':'Original saved gate occupancy includes accepted same-batch picks;gate-not-visited C uses actual held_before_batch count and is explicitly labeled.',
         'time_band_definition':['minute<840','840<=minute<870','minute>=870'],
         'diagnostic_rows_N':len(diagnostic),'private_arrival_rows_N':len(allrows)})
    print(json.dumps({'windows_complete':len(finals),'diagnostic_rows':len(diagnostic),'private_arrival_rows':len(allrows),
        'median_final':aggregate['final_equity_median_jpy'],'gross_loss':aggregate['gross_loss_jpy'],
        'MTM_MaxDD_decimal80':aggregate['minute_MTM_MaxDD_pct_exact']['decimal80'],
        'EOD_MaxDD_decimal80':aggregate['EOD_MaxDD_pct_exact']['decimal80'],
        'funded_N':aggregate['account_funded_trades_N'],'unique_funded_N':aggregate['unique_market_funded_entry_N'],
        'native_permit_quantity_zero_N':aggregate['native_permit_quantity_zero_N']},sort_keys=True))

if __name__=='__main__':main()
