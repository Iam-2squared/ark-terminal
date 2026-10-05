"""Reconstruct saved windows from raw source prices and quantities independently.
No imports of the V5 execution/allocation/summary functions.
"""
from decimal import Decimal as D
from datetime import datetime
from collections import defaultdict
from io_utils import *

def minute(timestamp):
    d=datetime.fromisoformat(timestamp);return d.hour*60+d.minute
def valid(row,auction=False):
    try:
        v=[D(row[k]) for k in ['O','H','L','C','Vo','Va']];o,h,l,c,_,_=v
        return bool(row.get('lineage')) and all(x.is_finite() and x>0 for x in v) and l<=min(o,c)<=max(o,c)<=h and (not auction or o==h==l==c)
    except (KeyError,ValueError,TypeError):return False
def sell_source(b,kind):
    market=b['market'];day=b['session']
    if kind=='FROZEN_EXIT_V3':
        x=b['frozen_exit'];assert x['sell_status']=='FILLED'
        source=next(r for r in market if r['session']==day and r['minute']==x['sell_minute']);assert valid(source)
        price=D(source['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else source['C']);release=minute(x['sell_source_assumed_available_at']);assert release<=920
    else:
        regular=sorted([r for r in market if r['session']==day and 920<=r['minute']<925 and valid(r)],key=lambda r:r['minute'])
        auctions=[r for r in market if r['session']==day and r['minute']==930 and valid(r,True)]
        source=regular[0] if regular else auctions[0];price=D(source['O'] if regular else source['C']);release=source['minute']+1
        assert kind==('EOD_REGULAR' if regular else 'EOD_EXACT_1530_AUCTION')
    return source,price*D('0.9995'),release

def audit_window(w,dest,stream,books,labels):
    if not w['coverage_complete']:return {'window_id':w['window_id'],'status':'NOT_APPLICABLE_BLOCKED_COVERAGE','mismatch_N':0}
    ds=rows(dest/'DECISIONS.jsonl.gz');ts=rows(dest/'TRADES.jsonl.gz');fs=rows(dest/'CURVE.jsonl.gz');mismatch=[];count=defaultdict(int)
    def check(ok,kind):
        count[kind]+=1
        if not ok:mismatch.append(kind)
    buys=defaultdict(list);sells=defaultdict(list);frames={(f['session'],f['minute']):f for f in fs}
    for d in ds:
        if d['quantity']>0:buys[(d['session'],d['minute'])].append(d)
    for t in ts:sells[(t['session'],t['release_minute'])].append(t)
    cash=D('1000000');positions={};daily=[];buyn=0;selln=0;fees=D(0)
    for day_record in w['daily_series']:
        day=day_record['session'];check(D(day_record['starting_cash'])==cash,'day_initial_carry')
        for t in range(540,932):
            for key,p in positions.items():
                while p['index']<len(p['updates']) and p['updates'][p['index']][0]<=t:
                    p['known'],p['mark']=p['updates'][p['index']];p['index']+=1
            for tr in sorted(sells[(day,t)],key=lambda x:x['entry_id']):
                key=tr['entry_id'];b=books[key];source,eff,release=sell_source(b,tr['exit_kind'])
                check(key in positions,'SELL_existing_position')
                p=positions.pop(key);credit=eff*tr['quantity'];debit=p['debit']
                check(tr['quantity']==p['quantity'],'SELL_quantity');check(release==t and source['minute']==tr['source_minute'],'SELL_time_source')
                check(eff==D(tr['sell_effective']),'SELL_effective_cost_once');check(credit==D(tr['credit']) and debit==D(tr['debit']) and credit-debit==D(tr['pnl']),'trade_money')
                check(source['lineage']==tr['lineage'],'SELL_lineage');cash+=credit;selln+=1
                fees+=credit/D('.9995')-credit
                l=labels[key]
                if l['known']:check(credit*D(l['buy_debit'])==debit*D(l['sell_credit']),'standalone_vs_actual_quantity_return')
            for d in buys[(day,t)]:
                r=stream[d['entry_id']];b=books[d['entry_id']];source=b['entry_actual_source'];raw=D(source['O']);qty=d['quantity'];eff=raw*D('1.0005');debit=qty*eff
                check(source['session']==day and source['minute']==t and valid(source),'BUY_raw_source');check(raw==D(r['raw_reference']),'BUY_raw_binding')
                check(qty%100==0 and qty>=100,'BUY_integer_lots');check(d['entry_id'] not in positions and all(p['symbol']!=r['symbol'] for p in positions.values()),'same_symbol')
                check(D(d['cash_before'])==cash,'BUY_cash_before');check(debit==D(d['debit']) and debit<=cash,'BUY_money_nonnegative')
                check(t<920,'Entry_cutoff');cash-=debit;fees+=debit-raw*qty;buyn+=1
                updates=sorted((x['minute']+1,D(x['C'])) for x in b['market'] if x['session']==day and x['minute']>=t and valid(x))
                positions[d['entry_id']]={'symbol':r['symbol'],'quantity':qty,'debit':debit,'mark':raw,'known':t,'updates':updates,'index':0}
                check(len(positions)<=3,'MAX3')
            frame=frames.get((day,t))
            if frame:
                exposure=sum((p['mark']*p['quantity'] for p in positions.values()),D(0));equity=cash+exposure
                check(D(frame['cash'])==cash,'frame_cash');check(D(frame['equity'])==equity and D(frame['exposure'])==exposure,'MTM_raw_causal_marks');check(frame['concurrent']==len(positions),'frame_positions');check(frame['known_marks']=={k:p['known'] for k,p in positions.items()},'frame_asof')
        if day_record['status']=='COMPLETE':check(not positions,'EOD_flat');check(D(day_record['ending_cash'])==cash,'day_final_cash')
        daily.append({'session':day,'reconstructed_cash':str(cash),'open_N':len(positions)})
    if w['status']=='COMPLETE':check(str(cash)==w['final_cash_for_primary'],'window_final_cash');check(not positions and buyn==selln,'all_obligations_settled')
    else:check(w['final_cash_for_primary'] is None,'blocked_primary_null')
    return {'window_id':w['window_id'],'status':'PASS' if not mismatch else 'FAIL','check_counts':dict(count),'mismatch_N':len(mismatch),'mismatches':mismatch[:30],'BUY_N':buyn,'SELL_N':selln,'cost_jpy':str(fees),'final_cash':str(cash) if w['status']=='COMPLETE' else None,'execution_complete':w['status']=='COMPLETE','daily':daily}

def main():
    import sys
    profiles=sys.argv[1:] or ['V5_RESET20'];books={r['entry_id']:r for r in rows(INPUTS/'books')};stream={r['entry_id']:r for r in rows(INPUTS/'candidate_stream')};labels={r['entry_id']:r for r in rows(PRIVATE/'evaluation-only/R_LABELS.jsonl.gz')}
    saved=read(OUT/'INDEPENDENT_ACCOUNTING_AUDIT.json') if (OUT/'INDEPENDENT_ACCOUNTING_AUDIT.json').exists() else {'profiles':[]}
    output=[x for x in saved['profiles'] if x['profile'] not in profiles]
    for profile in profiles:
        result=read(OUT/(profile+'_RESULT.json'));audits=[audit_window(w,PRIVATE/'runs'/profile/w['window_id'],stream,books,labels) for w in result['windows']]
        output.append({'profile':profile,'window_audit_N':len(audits),'covered_window_audit_N':sum(a['status']!='NOT_APPLICABLE_BLOCKED_COVERAGE' for a in audits),'mismatch_N':sum(a['mismatch_N'] for a in audits),'audits':audits})
    obj={'schema':'ARK_RAW_SOURCE_ACCOUNTING_AUDIT_V1','exact_jst':now(),'method':'Reconstruct BUY/SELL/cash/positions and every MTM frame from raw source O/C, 1.0005/0.9995 and saved integer quantities; independent of replay/execution/allocation functions','profiles':output,'pass':all(x['mismatch_N']==0 for x in output),'price_provider_requests':0,'market_replays':0}
    save(OUT/'INDEPENDENT_ACCOUNTING_AUDIT.json',obj);print({'pass':obj['pass'],'profiles':[{k:v for k,v in x.items() if k!='audits'} for x in output]});assert obj['pass']

if __name__=='__main__':main()
