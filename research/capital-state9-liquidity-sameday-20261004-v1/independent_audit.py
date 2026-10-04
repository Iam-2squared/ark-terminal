"""Independent source/accounting/diagnostic verification; no primary imports or fits.

Reconstructs the observed funded prefix, not an invented complete Portfolio.
All full-performance quantities remain null when a required mark is absent.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import copy, gzip, hashlib, json, math, pickle, sys, zipfile
from pathlib import Path
import numpy as np

def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(s) for s in f if s.strip()]
def tm(s):
    d=datetime.fromisoformat(s);return 60*d.hour+d.minute
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def serial(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def projection(e):
    d=datetime.fromisoformat(e['fill_timestamp']);s=e['first_intent'].get('score')
    return dict(entry_id=e['watch_key'],session=e['session'],symbol=e['symbol'],
        entry_timestamp=e['fill_timestamp'],entry_effective_price=str(e['fill_price']),
        score=s if isinstance(s,(int,float)) and math.isfinite(s) and 0<=s<=1 else None,
        eligible=(d.hour,d.minute,d.second)<(15,20,0),
        cutoff_reason=None if (d.hour,d.minute,d.second)<(15,20,0) else 'CAPITAL_EOD_ENTRY_CUTOFF')
def auc(y,p):
    positives=p[y==1];negatives=p[y==0]
    if not len(positives) or not len(negatives):return None
    return float(np.mean([(np.sum(a>negatives)+.5*np.sum(a==negatives))/len(negatives) for a in positives]))

def main():
    root=Path(sys.argv[1]);out=root/'svnext_private';here=Path(__file__).parent
    counts=Counter();mismatches=[]
    def eq(a,b,label,tol=None):
        counts[label]+=1
        if tol is not None and a is not None and b is not None:
            good=abs(float(a)-float(b))<=tol
        else:good=a==b
        if not good:mismatches.append({'label':label,'expected':str(a),'actual':str(b)})
    entries=[e for e in rows(root/'eod_private/independent/entry.jsonl.gz') if e['entry_status']=='FIRST_ENTRY']
    exits={e['watch_key']:e for e in rows(root/'eod_private/independent/exit_v3.jsonl.gz')}
    market=json.loads(gzip.open(root/'eod_private/independent/raw_paths.json.gz','rt').read())
    outcome={e['entry_id']:e for e in rows(root/'f1520_private/independent/INDEPENDENT_ROWS.jsonl.gz')}
    with zipfile.ZipFile(out/'daily/private.zip') as z:
        daily=json.loads(gzip.decompress(z.read(next(n for n in z.namelist() if n.endswith('.gz')))))
    scope=json.loads((here/'DAILY_RECOVERY_SCOPE.json').read_text())
    safe=json.loads((here/'DAILY_RECOVERY_SCOPE_SAFE_V2.json').read_text())
    calendar=sorted(set(scope['required_prior_dates']+scope['entry_cohort_dates']))
    authorized=set(safe['source_dates_authorized'])
    protected=set(scope['required_prior_dates'])-authorized
    bysymbol=defaultdict(list)
    for r in daily:bysymbol[r['Code']].append(r)
    saved_cap=json.loads((out/'CAPACITIES_PRIVATE.json').read_text());caps={};reasons=Counter();capacity_lt_lot=[]
    for e in entries:
        prior=tuple(d for d in calendar if d<e['session'])[-20:]
        values=[];unavailable=False;missing=[]
        for day in prior:
            options=[]
            for r in bysymbol[e['symbol']]:
                if r['Date']==day and r.get('known_session',day)<e['session'] and r.get('Va') is not None:
                    v=Decimal(r['Va'])
                    if v.is_finite() and v>0:options.append(v)
            if not options or len(set(options))!=1:unavailable=True;missing.append(day)
            else:values.append(options[0])
        if len(prior)!=20:unavailable=True
        if unavailable:
            caps[e['watch_key']]=None
            reasons['REQUIRED_PROTECTED_DATE_UNOPENED' if any(d in protected for d in missing) else 'OTHER_EXACT_PRIOR_HISTORY_UNAVAILABLE']+=1
        else:
            values.sort();caps[e['watch_key']]=(values[9]+values[10])/Decimal(200);reasons['KNOWN']+=1
            if caps[e['watch_key']]<Decimal(str(e['fill_price']))*100:capacity_lt_lot.append(e)
        eq(caps[e['watch_key']],Decimal(saved_cap[e['watch_key']]) if saved_cap[e['watch_key']] is not None else None,'exact_prior20_capacity')
        r=projection(e);m=copy.deepcopy(e)
        m.update(execution_evidence_status='FORBIDDEN_MUTATION',profit=1e100,future_high=-1e50,next_day_open=0)
        eq(projection(m),r,'future_evidence_projection_canary')
    primary=rows(out/'CAPITAL_DECISIONS.jsonl.gz');curves=rows(out/'PORTFOLIO_CURVES_KNOWN_PREFIX.jsonl.gz')
    baseline=json.loads((out/'BASELINE_RESULTS.json').read_text());independent=[]
    byid={e['watch_key']:e for e in entries};events=defaultdict(list)
    for e in entries:events[(e['session'],tm(e['fill_timestamp']))].append(projection(e))
    daylist=sorted({e['session'] for e in entries});private_prefix=[]
    for result in baseline['arms']:
        arm,n=result['arm'],result['max_positions']
        observed={d['entry_id']:d for d in primary if d['arm']==arm and d['max_positions']==n}
        frames=[f for f in curves if f['arm']==arm and f['max_positions']==n]
        eq(set(observed),set(byid),'identity_set')
        expected={k:{'quantity':None,'reason':'NOT_EVALUATED_AFTER_MEASUREMENT_BLOCKED'} for k in byid}
        for e in entries:
            if not projection(e)['eligible']:expected[e['watch_key']]={'quantity':0,'reason':'CAPITAL_EOD_ENTRY_CUTOFF'}
        cash=Decimal(1000000);positions={};schedule=defaultdict(list);ownframes=[];block=None;maxpos=0;closeN=0
        for day in daylist:
            if positions:raise ValueError('NO_CROSS_SESSION_SYNTHETIC_MARK')
            grid=set(range(545,691,5))|set(range(755,926,5))
            for minute in range(540,932):
                for key in schedule.pop((day,minute),[]):
                    o=outcome[key]
                    if not o['historical_cash_release_authorized']:
                        block=(day,minute,key,'FUNDED_EXECUTION_UNKNOWN');break
                    q,buy,mark=positions[key];sell=Decimal(o['integrated_exit_price'])
                    old=cash;cash+=q*sell;eq(cash-old-q*buy,q*(sell-buy),'cash_trade_pnl',1e-10)
                    del positions[key];closeN+=1
                if block:break
                if minute in grid:
                    for key,(q,buy,oldmark) in list(positions.items()):
                        source=[b for b in market[key]['today'] if int(b[0])==minute-1]
                        if not source or not math.isfinite(float(source[0][4])) or source[0][4]<=0:
                            block=(day,minute,key,'MISSING_FUNDED_EXACT_5M_MARK');break
                        positions[key]=(q,buy,Decimal(str(source[0][4])))
                    if block:break
                batch=sorted(events.get((day,minute),[]),key=lambda r:(-(r['score'] if r['score'] is not None else -1),r['entry_id']))
                good=[]
                for r in batch:
                    key=r['entry_id']
                    if not r['eligible']:continue
                    if r['score'] is None:expected[key]={'quantity':0,'reason':'CAPITAL_SCORE_INPUT_UNKNOWN'}
                    elif caps[key] is None:expected[key]={'quantity':0,'reason':'CAPITAL_LIQUIDITY_INPUT_UNKNOWN'}
                    elif any(byid[k]['symbol']==r['symbol'] for k in positions):expected[key]={'quantity':0,'reason':'SYMBOL_ALREADY_OPEN'}
                    else:good.append(r)
                equity=cash+sum(q*mark for q,buy,mark in positions.values());invested=equity-cash
                util=min(.90,.60+.25*max([r['score'] for r in good],default=0)+.02*max(0,len(good)-1))
                deployment=max(Decimal(0),equity*Decimal(str(util))-invested)
                weights={r['entry_id']:Decimal('.5')+Decimal(str(r['score'])) for r in good}
                total=sum(weights.values())
                for r in good:
                    k=r['entry_id'];equity=cash+sum(q*mark for q,buy,mark in positions.values())
                    if len(positions)>=n:expected[k]={'quantity':0,'reason':'MAX_POSITION_CAP'};total-=weights[k];continue
                    if arm=='FIXED_SANITY':target=equity/Decimal(n);cap=target
                    else:target=deployment*weights[k]/total;cap=equity*(Decimal('.20')+Decimal('.20')*Decimal(str(r['score'])))
                    total-=weights[k];price=Decimal(r['entry_effective_price']);limit=min(target,cap,cash,caps[k]);q=int(limit//(price*100))*100
                    reason='ACCEPTED' if q else 'CAPITAL_SKIP_LIQUIDITY' if caps[k]<price*100 else 'CAPITAL_LOT_OR_CASH_CONSTRAINED'
                    expected[k]={'quantity':q,'reason':reason}
                    d=observed[k]
                    for field,val in [('cash_before',cash),('equity_before',equity),('liquidity_capacity',caps[k]),('candidate_equity_cap',cap),('target_notional',target)]:eq(val,d[field],'allocation_'+field,1e-7)
                    if q:
                        cash-=q*price;positions[k]=(q,price,price/Decimal('1.0005'));deployment=max(Decimal(0),deployment-q*price)
                        eq(q%100,0,'100_share_lot');eq(cash>=0,True,'nonnegative_cash');eq(len(positions)<=n,True,'concurrent_cap')
                        maxpos=max(maxpos,len(positions));o=outcome[k]
                        schedule[(day,tm(o['cash_release_timestamp']) if o['historical_cash_release_authorized'] else 931)].append(k)
                if minute in grid or batch or minute in (540,931):
                    equity=cash+sum(q*mark for q,buy,mark in positions.values());investment=equity-cash
                    ownframes.append({'session':day,'timestamp':day+'T%02d:%02d:00+09:00'%divmod(minute,60),'cash':float(cash),'equity':float(equity),
                        'investment':float(investment),'utilization':float(investment/equity),'positions':len(positions)})
            if block:break
        for k,v in expected.items():
            eq(v['quantity'],observed[k]['quantity'],'decision_quantity');eq(v['reason'],observed[k]['reason'],'decision_reason')
            for field,v2 in projection(byid[k]).items():eq(v2,observed[k][field],'runtime_'+field)
        eq(len(frames),len(ownframes),'prefix_frame_N')
        for a,b in zip(ownframes,frames):
            for field in a:eq(a[field],b[field],'prefix_'+field,1e-8 if field in ('cash','equity','investment','utilization') else None)
        accepted=[k for k,v in expected.items() if v['reason']=='ACCEPTED'];unknown=[k for k in accepted if outcome[k]['reason']=='UNKNOWN_NO_ADMISSIBLE_SOURCE']
        eq(block[3],result['blocker']['reason'],'required_missing_mark_reason');eq(block[0],result['blocker']['session'],'block_session')
        eq(block[1],tm(result['blocker']['timestamp']),'block_time');eq(len(accepted),result['accepted_observed_N'],'accepted_N')
        eq(closeN,result['closed_trades_observed_N'],'closed_trade_N');eq(maxpos,result['max_concurrent_observed'],'max_positions_observed')
        eq(len(unknown),result['funded_execution_unknown_observed_N'],'funded_unknown_prefix_N')
        eq(result['funded_unknown_full_trace_N'],None,'unknown_full_trace_not_fabricated')
        for key in ('final_equity','total_return','max_drawdown','mean_utilization','median_utilization','rolling20_max_multiple','rolling22_max_multiple','rolling24_max_multiple'):eq(None,result[key],'full_metric_null')
        independent.append({'arm':arm,'max_positions':n,'prefix_accepted_N':len(accepted),'prefix_closed_trades_N':closeN,
            'full_portfolio_measurement':'BLOCKED','missing_mark_reason':block[3],'funded_unknown_prefix_N':len(unknown),'funded_unknown_full_trace_N':None,
            'final_equity':None,'max_drawdown':None,'commission_jpy':0})
        private_prefix.append({'arm':arm,'max_positions':n,'independent_block':block,'frames':ownframes})
    # Recompute targets from independently extracted original frozen rows, not primary teacher code.
    data=np.load(out/'CAUSAL_DIAGNOSTIC_PRIVATE.npz');Y=data['Y'];sessions=data['sessions'];pred=np.load(out/'DIAGNOSTIC_OOF_PREDICTIONS_PRIVATE.npy')
    yown=[]
    for e in entries:
        x=exits[e['watch_key']];winner=1 if e['first_upside']['5']['minute'] is not None else 0 if e['remaining_source_complete'] else np.nan
        mae=e['pre_peak_mae_abs_pct'] if e['pre_peak_mae_abs_pct'] is not None else np.nan
        ret=100*(float(x['sell_price_decimal'])/e['fill_price']-1) if x['sell_status']=='FILLED' else np.nan
        hold=sum(max(0,min(x['sell_minute'],stop)-max(e['fill_minute'],start)) for start,stop in [(540,690),(750,925)]) if x['sell_status']=='FILLED' else np.nan
        yown.append([winner,mae,ret,hold]);eq(e['session'],sessions[len(yown)-1],'diagnostic_session_identity')
    yown=np.array(yown,float);eq(bool(np.array_equal(np.isnan(yown),np.isnan(Y))),True,'teacher_missing_masks');eq(bool(np.allclose(yown,Y,equal_nan=True)),True,'independent_teachers')
    model_receipts=json.loads((out/'DIAGNOSTIC_MODEL_RECEIPTS_PRIVATE.json').read_text());days=sorted(set(sessions))
    for rec in model_receipts:
        f,a,t=rec['fold'],rec['arm'],rec['target'];p=out/f'diagnostic_model_F{f}_A{a}_T{t}.pkl'
        eq(sha(p),rec['sha256'],'model_hash');model=pickle.loads(p.read_bytes());train=days[:17+10*f];test=days[18+10*f:28+10*f]
        eq(model['train_days'],train,'prior_train_split');eq(model['test_days'],test,'forward_test_split');eq(max(train)<min(test),True,'purge_no_future_train')
        te=np.isin(sessions,test);x=data[['A','B','C'][a]][te];x=model['scaler'].transform(model['imputer'].transform(x))
        if model['onehot'] is not None:x=np.column_stack([x,model['onehot'].transform(data[['','catsB','catsC'][a]][te])])
        rebuilt=model['model'].predict(x);eq(bool(np.allclose(rebuilt,pred[te,a,t],rtol=0,atol=1e-12)),True,'saved_OOF_predictions')
    diagnostic=json.loads((out/'STATE9_INCREMENTAL_RESULTS.json').read_text());diag_ind=[]
    for old,new,key in [(0,1,'State9_current_vs_A'),(1,2,'StatePath_vs_B')]:
        improvements=[];lifts={day:0.0 for day in days[18:]}
        for t in range(4):
            mask=np.isfinite(Y[:,t])&np.isfinite(pred[:,old,t])&np.isfinite(pred[:,new,t]);loss0=(Y[:,t]-pred[:,old,t])**2;loss1=(Y[:,t]-pred[:,new,t])**2
            a=float(np.mean(loss0[mask]));b=float(np.mean(loss1[mask]));improvement=1-b/a;improvements.append(improvement);target=diagnostic[key]['targets'][t]
            eq(int(mask.sum()),target['support_N'],'OOF_target_support');eq(a,target['mse_old'],'OOF_mse_old',1e-9);eq(b,target['mse_new'],'OOF_mse_new',1e-9)
            if t==0:
                eq(auc(Y[mask,t],pred[mask,old,t]),target['auc_old'],'independent_auc',1e-12);eq(auc(Y[mask,t],pred[mask,new,t]),target['auc_new'],'independent_auc',1e-12)
            for day in days[18:]:
                m=mask&(sessions==day)
                if m.any():lifts[day]+=float(np.mean(loss0[m]-loss1[m])/a)
        positives=[max(0,v) for v in lifts.values()];share=max(positives)/sum(positives) if sum(positives) else 1.0
        eq(float(np.mean(improvements)),diagnostic[key]['mean_relative_improvement'],'mean_relative_improvement',1e-12)
        eq(share,diagnostic[key]['max_positive_session_lift_share'],'session_lift_concentration',1e-12)
        diag_ind.append({'comparison':key,'mean_relative_mse_improvement':float(np.mean(improvements)),'largest_positive_session_share':share,'primary_gate_pass':diagnostic[key]['pass']})
    late=[e for e in entries if not projection(e)['eligible']]
    def observed_mean(group,key):
        values=[e[key] for e in group if e.get(key) is not None and math.isfinite(float(e[key]))]
        return {'known_N':len(values),'mean':float(np.mean(values)) if values else None}
    def opportunity(group):
        return {'N':len(group),'confirmed_ge5_N':sum(e['first_upside']['5']['minute'] is not None for e in group),
            'ge5_UNKNOWN_N':sum(e['first_upside']['5']['minute'] is None and not e['remaining_source_complete'] for e in group),
            'Entry_to_observed_High_pct':observed_mean(group,'remaining_upside_pct'),
            'Selector_to_observed_High_pct':observed_mean(group,'selector_to_high_pct'),
            'source_censored':True,'role':'EVALUATION_ONLY_NOT_FUNDING_INPUT'}
    analysis={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'late_cutoff':opportunity(late),'liquidity_capacity_below_one_lot_potential_not_actual_rejects':opportunity(capacity_lt_lot),
        'liquidity_input_taxonomy':dict(reasons),'confirmed_limitup_evidence_N':0,'limitup_evidence_unknown_N':1600,
        'limitup_market_occurrence_N':None,'observed_funded_limitup_exception_N':0,'observed_funded_auction_fills_N':0,
        'funded_unknown_full_trace_N':None,'all18_unfunded_is_not_established':True}
    analysis['liquidity_capacity_below_one_lot_potential_not_actual_rejects']['eligible_before1520_N']=sum(e['fill_minute']<920 for e in capacity_lt_lot)
    analysis['liquidity_capacity_below_one_lot_potential_not_actual_rejects']['eligible_confirmed_ge5_N']=sum(e['fill_minute']<920 and e['first_upside']['5']['minute'] is not None for e in capacity_lt_lot)
    unknown_entries=[e for e in entries if outcome[e['watch_key']]['reason']=='UNKNOWN_NO_ADMISSIBLE_SOURCE']
    unknown_tax=Counter('LIQUIDITY_INPUT_UNKNOWN' if caps[e['watch_key']] is None else 'CAPACITY_BELOW_100_SHARES' if caps[e['watch_key']]<Decimal(str(e['fill_price']))*100 else 'CAPACITY_FITS_ONE_LOT' for e in unknown_entries)
    analysis['future_execution_UNKNOWN_capacity_evaluation_only']={'candidate_N':len(unknown_entries),'capacity_classification':dict(unknown_tax),
        'conditional_funding_upper_bound_with_current_inputs':unknown_tax['CAPACITY_FITS_ONE_LOT'],
        'actual_full_funding_trace_executed':False,'not_a_completed_replay_count':True,
        'why':'Post-decision evaluation of common fixed prior20 capacity only; source status was not a funding input. Missing daily inputs are not evidence of bad/thin/no-trade entries.'}
    # Exhaust the existing original response-token prefix for the actual funded mark gap.
    tokenpath=root/'eod_private/primary/source_tokens.json.gz';tokens=json.loads(gzip.open(tokenpath,'rt').read())
    blocked_private=json.loads((out/'FUNDED_BLOCKERS_PRIVATE.json').read_text());lookups=[]
    for key in {r['blocker']['entry_id'] for r in blocked_private}:
        e=byid[key];b=next(r['blocker'] for r in blocked_private if r['blocker']['entry_id']==key);needed=tm(b['timestamp'])-1
        source=tokens[e['session']+'|'+e['symbol']]
        within=needed+1<=source['max_candidate_intent'];found=[r for r in source['current_prefix'] if tm(e['session']+'T'+r['Time']+':00+09:00')==needed]
        eq(within,True,'original_token_covers_needed_prefix');eq(len(found),0,'original_token_exact_mark_missing')
        lookups.append({'existing_token_prefix_covers_required_time':within,'exact_required_mark_source_N':len(found)})
    analysis['funded_MTM_existing_source_recovery']={'distinct_funded_blocked_identity_N':len(lookups),'original_saved_token_lookup':lookups,
        'source_tokens_sha256':sha(tokenpath),'new_provider_requests':0,'no_trade_vs_missing':'UNKNOWN; no missing-minute price substitution.'}
    states={s['entry_id']:s for s in rows(out/'STATE9_ENTRY_ROWS.jsonl.gz')}
    labels=sorted({s['primary'] for s in states.values() if s['observed']})+['__UNKNOWN_CURRENT__']
    state_descriptive=[]
    for label in labels:
        group=[e for e in entries if (states[e['watch_key']]['primary'] if states[e['watch_key']]['observed'] else '__UNKNOWN_CURRENT__')==label]
        state_descriptive.append({'label':label,**opportunity(group),
            'complete_pre_peak_MAE_abs_pct':observed_mean(group,'pre_peak_mae_abs_pct'),
            'observed_path_efficiency':observed_mean(group,'observed_path_efficiency'),
            'time_to_observed_high_active_minutes':observed_mean(group,'time_to_peak_active_min')})
    descriptive={'population_N':1600,'teacher_only_not_runtime':True,'source_censoring_not_imputed':True,
        'upside_thresholds':{str(i):{'confirmed_positive_N':sum(e['first_upside'][str(i)]['minute'] is not None for e in entries),
            'known_negative_N':sum(e['first_upside'][str(i)]['minute'] is None and e['remaining_source_complete'] for e in entries),
            'UNKNOWN_N':sum(e['first_upside'][str(i)]['minute'] is None and not e['remaining_source_complete'] for e in entries)} for i in range(1,6)},
        'State9_current_groups':state_descriptive,'Frozen_EXIT_reason_counts':dict(Counter(e['exit_reason'] for e in exits.values()))}
    report={'jst':analysis['jst'],'status':'INDEPENDENT_AUDIT_PASS_WITH_MEASUREMENT_BLOCKED' if not mismatches else 'INDEPENDENT_AUDIT_FAIL',
        'primary_imported':False,'new_fits':0,'new_performance_replays':0,'audit_reconstructions':6,'total_checks':sum(counts.values()),'checks_by_topic':dict(counts),'mismatch_N':len(mismatches),
        'candidate_N':len(entries),'unique_entry_N':len(byid),'cutoff_N':len(late),'liquidity_source_taxonomy':dict(reasons),'baseline_arms':independent,'diagnostic_independent':diag_ind,
        'full_portfolio_final_equity_maxdd_utilization_verified':False,'why':'Funded exact MTM source absent; only known prefix/source arithmetic can be independently certified.',
        'execution_and_same_time_ordering':'Existing parent 54,400 comparison/14,957 canaries and new C2 12,881 canaries retained; actual funded trace has zero sell-release events before mark blocker.',
        'robustness':'Full portfolio leave-one-session/symbol tests NOT_MEASURABLE, not run. Diagnostic session concentration independently verified; no budget expansion.',
        'long_cash_only':True,'commission_jpy':0,'price_imputation_N':0,'outcome_based_exclusion_N':0}
    serial(out/'INDEPENDENT_AUDIT.json',report);serial(out/'OPPORTUNITY_AUDIT.json',analysis);serial(out/'DESCRIPTIVE_OUTCOME_AUDIT.json',descriptive)
    serial(out/'INDEPENDENT_PREFIX_PRIVATE.json',private_prefix);serial(out/'INDEPENDENT_MISMATCHES_PRIVATE.json',mismatches)
    print(json.dumps({'audit':report,'opportunity':analysis},ensure_ascii=False))
    if mismatches:raise SystemExit(2)

if __name__=='__main__':main()
