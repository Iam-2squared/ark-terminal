"""Focused research-contract canaries; no fit, sweep, broker or provider calls."""
from copy import deepcopy
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
from checkpoint import ROOT,OUT,save,sha
from features import project
from contracts import liquidity,last_actual_mark,eod_source,eod_intent,rank
from model import predict_saved
from prepare import PRIVATE,rows
from replay import day_replay,run_profile

def main():
    stream=rows(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')
    pointer=json.load(open(PRIVATE/'FINAL_SOURCE_POINTER.json'))
    books={r['entry_id']:r for r in rows(PRIVATE/pointer['market_book'])}
    entries={r['watch_key']:r for r in rows(ROOT.parent/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
    results=[]
    def record(n,name,ok,detail=None):
        results.append({'id':n,'name':name,'pass':bool(ok),'detail':detail})
        assert ok,name
    # One chronologically earliest candidate per OOF session, chosen without labels.
    sample=[]
    for day in sorted({r['session'] for r in stream}):sample.append(next(r for r in stream if r['session']==day))
    invariant=[True]*4
    for r in sample:
        e=entries[r['entry_id']]
        trace=rows(ROOT.parent/f"work_inputs/exit_v2/FULL_TRACE/{r['session']}_{r['symbol']}.jsonl.gz")
        model=json.load(open(PRIVATE/'models'/f"BLOCK_{r['block']:02d}.json"))
        base=project(e,trace)
        modified=deepcopy(e)
        for k in ('remaining_upside_pct','session_end_mfe_pct','peak_bar_close','upside_retention_pct'):modified[k]=1e99
        f=project(modified,trace)
        invariant[0]&=f==base and predict_saved([f],model)[0]==predict_saved([base],model)[0]
        modified=deepcopy(e)
        for k in ('pre_peak_mae_abs_pct','session_end_mae_pct','observed_pre_peak_mae_abs_pct'):modified[k]=1e99
        invariant[1]&=project(modified,trace)==base
        suffix={'bar_end_minute':e['fill_minute']+1,'state':{'primary':'FORBIDDEN_FUTURE'},'path':{'Primary_or_null':'FORBIDDEN_FUTURE'}}
        invariant[2]&=project(e,trace+[suffix])==base
        suffix={'bar_end_minute':e['fill_minute']+999,'state':{},'path':{'future_path_suffix':['SHARP_RISE']*999}}
        invariant[3]&=project(e,trace+[suffix])==base
    for i,name in enumerate(('future_High_runtime_score_invariant','future_Low_runtime_score_invariant','future_State_suffix_invariant','future_Path_suffix_invariant'),1):
        record(i,name,invariant[i-1],{'session_cases':len(sample)})
    first_day=min(r['session'] for r in stream)
    first=[r for r in stream if r['session']==first_day]
    baseline=day_replay(3,first_day,first,books,Decimal(1000000))
    changed=deepcopy(books)
    for r in first:
        b=changed[r['entry_id']]
        b['market']=[m for m in b['market'] if m['minute']<920]
    absence=day_replay(3,first_day,first,changed,Decimal(1000000))
    record(5,'future_EOD_source_absence_cannot_change_BUY',absence[1]==baseline[1])
    changed=deepcopy(books)
    for r in first:
        changed[r['entry_id']]['limit_up_authority']={'status':'LIMIT_UP_CONFIRMED','session':first_day,
            'authoritative_price_limit_source':'CANARY_AUTHORITY','causal_exchange_status':True,'known_minute':919,'observed_minute':919}
    limit=day_replay(3,first_day,first,changed,Decimal(1000000))
    record(6,'future_limit_up_status_cannot_change_BUY',limit[1]==baseline[1])
    source={}
    for name in ('bigwinner_source','bigwinner_supplement'):
        for r in json.load(gzip.open(ROOT.parent/f'work_inputs/{name}/SAVED_SOURCE_PRIVATE.json.gz','rt')):source[r['session'],r['symbol']]=r
    scope=json.load(open(Path(__file__).parent/'SOURCE_RECOVERY_SCOPE.json'))
    calendar=sorted(set(scope['required_prior_dates']+scope['entry_cohort_dates']))
    causal=stream[0];orig=liquidity(causal['session'],causal['symbol'],causal['raw_reference'],calendar,source)
    altered=deepcopy(source)
    for (day,sym),h in altered.items():
        if sym==causal['symbol'] and day>=causal['session']:
            if h.get('daily'):h['daily']['Va']='9999999999999999999';h['daily']['Vo']='9999999999999999999'
            h['active_windows']=list(range(65))
    record(7,'Liquidity_only_completed_prior_sessions',all(d<causal['session'] for d in orig['support_dates']) and len(orig['lookback_dates'])<=20)
    record(8,'current_future_volume_cannot_change_Liquidity',liquidity(causal['session'],causal['symbol'],causal['raw_reference'],calendar,altered)==orig)
    # Deterministic synthetic event fixtures, independent of market/portfolio results.
    day='2025-06-27';lineage={'wrapper_sha256':'CANARY_WRAPPER','response_sha256':'CANARY_RESPONSE'}
    def bar(m,p=100,session=day):return {'session':session,'minute':m,'O':str(p),'H':str(p),'L':str(p),'C':str(p),'Vo':'1000','Va':str(p*1000),'lineage':lineage}
    def candidate(i,t=600,rk='S'):
        return {'entry_id':f'CANARY_{i}','session':day,'symbol':f'C{i:04d}','entry_minute':t,'entry_timestamp':day+f'T{t//60:02d}:{t%60:02d}:00+09:00',
            'p_bigwinner5':.5,'rank':rk,'raw_reference':'100','liquidity':{'eligible':True,'capacity':'1000000','reason':'LIQUIDITY_ELIGIBLE'}}
    def book(c,market):return {'session':day,'symbol':c['symbol'],'capture_complete':True,'market':market,
        'entry_actual_source':market[0],'frozen_exit':{'sell_status':'UNRESOLVED'},'limit_up_authority':None}
    c=candidate(0,920);b={c['entry_id']:book(c,[bar(920),bar(930)])}
    late=day_replay(3,day,[c],b,1000000)
    record(9,'Entry_at_1520_funding_zero',late[1][0]['quantity']==0 and late[1][0]['reason']=='CAPITAL_EOD_ENTRY_CUTOFF')
    c=candidate(0,rk='C');b={c['entry_id']:book(c,[bar(600),bar(920,110)])}
    cr=day_replay(3,day,[c],b,1000000)
    record(10,'C_rank_funding_zero',cr[1][0]['quantity']==0 and cr[1][0]['reason']=='BELOW_BIGWINNER_BASE_RATE')
    fixture=[candidate(i) for i in range(10)]
    fixture_book={c['entry_id']:book(c,[bar(600),bar(920,110)]) for c in fixture}
    batch={n:day_replay(n,day,fixture,fixture_book,1000000) for n in (3,4,5)}
    record(11,'MAX3_4_5_never_exceeded',all(max(s['concurrent'] for s in v[3])==n for n,v in batch.items()))
    record(12,'100_share_lot',all(d['quantity']%100==0 for v in batch.values() for d in v[1]))
    record(13,'cash_never_negative',all(Decimal(s['cash'])>=0 for v in batch.values() for s in v[3]))
    record(14,'LONG_cash_only',all(i['side']=='SELL' and i['quantity']>0 for v in batch.values() for i in v[4]))
    safety=json.load(open(OUT/'DESIGN_PRECOMMIT.json'))['safety']
    record(15,'margin_short_leverage_orders_zero',all(v is False for v in safety.values()) and json.load(open(OUT/'DESIGN_PRECOMMIT.json'))['accounting']['cash_only'])
    mark_rows=[bar(600,105),bar(610,999),bar(602,777,'2025-06-26')]
    record(16,'last_actual_mark_same_session_past_only',last_actual_mark(mark_rows,600,605,100,day)==(Decimal(105),601))
    one=candidate(99);ob={one['entry_id']:book(one,[bar(600,105)])}
    nofill=day_replay(3,day,[one],ob,1000000)
    record(17,'MTM_mark_cannot_be_execution_fill',not nofill[2] and nofill[0]['ending_cash'] is None)
    record(18,'no_trade_cannot_release_cash',len({s['cash'] for s in nofill[3] if s['minute']>=600})==1)
    ob={one['entry_id']:book(one,[bar(600),bar(920,110)])}
    sold=day_replay(3,day,[one],ob,1000000)
    cash_at={s['minute']:Decimal(s['cash']) for s in sold[3]}
    record(19,'EOD_fill_then_cash_release',cash_at[920]==cash_at[919] and cash_at[921]>cash_at[920] and sold[2][0]['release_minute']==921)
    ob[one['entry_id']]['limit_up_authority']={'status':'LIMIT_UP_CONFIRMED','session':day,
        'authoritative_price_limit_source':'CANARY_AUTHORITY','causal_exchange_status':True,'known_minute':700,'observed_minute':700}
    lu=day_replay(3,day,[one],ob,1000000)
    pos={'quantity':100,'side':'LONG','intent_issued':True}
    record(20,'limit_up_1520_intent_no_duplicate',len(lu[4])==len(lu[2])==1 and lu[4][0]['minute']==920 and lu[4][0]['sor'] is True and eod_intent(pos) is None)
    deterministic=True
    for n in (3,4,5):
        result,ds,ts,cs,it=run_profile(n,stream,books)
        result['score_stream_sha256']=sha(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')
        deterministic&=result==json.load(open(PRIVATE/f'MAX{n}_RESULT.json'))
        deterministic&=ds==rows(PRIVATE/f'MAX{n}_DECISIONS.jsonl.gz') and ts==rows(PRIVATE/f'MAX{n}_TRADES.jsonl.gz')
        deterministic&=cs==rows(PRIVATE/f'MAX{n}_CURVE.jsonl.gz') and it==rows(PRIVATE/f'MAX{n}_INTENTS.jsonl.gz')
    record(21,'deterministic_saved_score_rerun',deterministic,{'new_fits':0,'profiles':3})
    independent=json.load(open(OUT/'INDEPENDENT_AUDIT.json'))
    record(22,'Primary_Independent_mismatch_zero',independent['mismatch_N']==0)
    # Additional boundary checks implement user contracts without threshold search.
    record(23,'rank_lift_exact_boundaries',all(rank(p,.0625)[0]==r for p,r in ((.125,'S'),(.09375,'A'),(.0625,'B'),(.0624,'C'))))
    report={'status':'PASS','tests_N':len(results),'passed_N':sum(r['pass'] for r in results),'fail_N':0,
        'tests':results,'fits_added':0,'hyperparameter_sweep':0,'threshold_sweep':0,'orders':0,'productionReady':False}
    save(OUT/'FOCUSED_TEST_RESULTS.json',report)
    print(json.dumps({'status':'PASS','tests_N':len(results),'failed':0}))

if __name__=='__main__':main()
