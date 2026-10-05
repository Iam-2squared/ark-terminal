import copy,unittest
from decimal import Decimal as D
from datetime import date,timedelta
from reset20 import *
from io_utils import *

DAY='2025-07-15'
CAL=[(date(2025,7,15)+timedelta(days=i)).isoformat() for i in range(20)]
def candidate(key='x',minute=570,price='100',symbol=None):
    return {'entry_id':key,'session':DAY,'symbol':symbol or key,'entry_minute':minute,'entry_timestamp':DAY+'T09:30:00+09:00','capital_score':2.1,'capacity_band':'S','rank':'S','admission':True,'ML':2.1,'m2':.8,'m3':.7,'m5':.6,'block':1,'raw_reference':price}
def market(minute,price,session=DAY):
    return {'session':session,'minute':minute,'O':price,'H':price,'L':price,'C':price,'Vo':'1000','Va':str(D(price)*1000),'lineage':{'synthetic':True}}
def book(c,exit_price='110',release=601,missing=False):
    rows_=[market(c['entry_minute'],c['raw_reference'])]
    if not missing:rows_.append(market(release-1,exit_price))
    x={'sell_status':'UNFILLED' if missing else 'FILLED','sell_source_assumed_available_at':DAY+f'T{release//60:02d}:{release%60:02d}:00+09:00','sell_minute':release-1,'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':str(D(exit_price)*D('.9995'))}
    return {'entry_id':c['entry_id'],'session':DAY,'market':rows_,'frozen_exit':x,'capture_complete':True,'entry_actual_source':rows_[0],'limit_up_authority':None}
TABLE={'1':{'minute_counts':{str(t):[0,0,0,0] for t in range(540,932)},'minute_bucket':{str(t):'synthetic' for t in range(540,932)},'training_session_N':20,'B_median':1.2,'B_p75':1.3}}
def win(sessions=CAL,covered=True):
    return {'window_id':'TEST','sessions':sessions,'calendar_contiguous':True,'coverage_complete':covered,'coverage_blocked_sessions':[]}

class ResetTests(unittest.TestCase):
    def test_true_zero_day_and_window_reset(self):
        a=run_window(win(),{}, {},TABLE);b=run_window(win(),{}, {},TABLE)
        self.assertEqual(a,b);self.assertEqual(a[0]['final_cash_for_primary'],'1000000');self.assertEqual(len(a[0]['daily_series']),20)
    def test_compounding_and_lot_rounding(self):
        c=candidate();b=book(c);days=defaultdict(list);books={}
        for day in CAL[:2]:
            cc=copy.deepcopy(c);bb=copy.deepcopy(b);cc['session']=day;cc['entry_id']=day;bb['entry_id']=day;bb['session']=day
            for row in bb['market']:row['session']=day
            books[day]=bb;days[day]=[cc]
        res,ds,ts,_,_=run_window(win(),days,books,TABLE)
        self.assertNotEqual(ds[0]['quantity'],ds[1]['quantity']);self.assertEqual(D(res['final_cash_for_primary']),D('1000000')+sum(D(t['credit'])-D(t['debit']) for t in ts));self.assertTrue(all(d['quantity']%100==0 for d in ds))
    def test_gap_rejected(self):
        self.assertTrue(validate_sessions(CAL,CAL));self.assertFalse(validate_sessions(CAL[:10]+CAL[11:]+['2030-01-01'],CAL))
        res,*_=run_window(win(covered=False),{}, {},TABLE);self.assertEqual(res['status'],'BLOCKED_COVERAGE');self.assertEqual(res['attempted_day_N'],0)
    def test_max3(self):
        cs=[candidate(str(i)) for i in range(4)];bs={c['entry_id']:book(c) for c in cs}
        d,ds,ts,fs,it=engine()(3,DAY,cs,bs,D('1000000'),True,'TEST',tables=TABLE)
        self.assertEqual(sum(x['quantity']>0 for x in ds),3);self.assertEqual(ds[-1]['reason'],'MAX_POSITION_CAP');self.assertLessEqual(max(f['concurrent'] for f in fs),3)
    def test_cash_insufficient(self):
        c=candidate(price='20000');d,ds,*_=engine()(3,DAY,[c],{},D('1000000'),True,'TEST',tables=TABLE)
        self.assertEqual(ds[0]['quantity'],0);self.assertEqual(d['ending_cash'],'1000000')
    def test_same_minute_sell_precedes_buy(self):
        a=candidate('a');b=candidate('b',minute=601,price='5000');bs={'a':book(a,exit_price='200',release=601),'b':book(b,release=650)}
        _,ds,*_=engine()(3,DAY,[a,b],bs,D('1000000'),True,'TEST',tables=TABLE)
        self.assertGreater(ds[1]['quantity'],0);self.assertEqual(ds[1]['cash_before'],str(D('1000000')-D(ds[0]['debit'])+D('200')*D('.9995')*ds[0]['quantity']))
    def test_cost_once(self):
        c=candidate();d,ds,ts,*_=engine()(3,DAY,[c],{'x':book(c,exit_price='100')},D('1000000'),True,'TEST',tables=TABLE)
        q=ds[0]['quantity'];self.assertEqual(D(ts[0]['pnl']),D('100')*(D('.9995')-D('1.0005'))*q)
    def test_unsettled_window_stops(self):
        c=candidate();r,ds,*_=run_window(win(),{DAY:[c]}, {'x':book(c,missing=True)},TABLE)
        self.assertIsNone(r['final_cash_for_primary']);self.assertEqual(r['attempted_day_N'],1);self.assertFalse(r['execution_complete'])
    def test_same_symbol(self):
        a=candidate('a',symbol='S');b=candidate('b',minute=580,symbol='S');d,ds,*_=engine()(3,DAY,[a,b],{'a':book(a)},D('1000000'),True,'TEST',tables=TABLE)
        self.assertEqual(ds[1]['reason'],'SYMBOL_ALREADY_OPEN')
    def test_mtm_no_cash_credit(self):
        c=candidate();b=book(c,exit_price='200',release=601);b['market'].append(market(575,'1000'));d,ds,ts,fs,it=engine()(3,DAY,[c],{'x':b},D('1000000'),True,'TEST',tables=TABLE)
        self.assertEqual(fs[580-540]['cash'],fs[570-540]['cash']);self.assertGreater(D(fs[580-540]['equity']),D(fs[570-540]['equity']))
    def test_future_prefix_invariant(self):
        c=candidate();a=book(c);b=book(c,exit_price='90');b['frozen_exit']['sell_source_assumed_available_at']=DAY+'T11:00:00+09:00';b['market']=[market(570,'100'),market(659,'90')];b['frozen_exit'].update(sell_minute=659,sell_price_decimal=str(D('90')*D('.9995')))
        x=engine()(3,DAY,[c],{'x':a},D('1000000'),True,'TEST',tables=TABLE);y=engine()(3,DAY,[c],{'x':b},D('1000000'),True,'TEST',tables=TABLE)
        self.assertEqual(x[1],y[1]);self.assertEqual(x[3][:600-540],y[3][:600-540])
    def test_nonempty_window_state_isolation(self):
        c=candidate();bs={'x':book(c)};before=copy.deepcopy(bs)
        a=run_window(win(),{DAY:[c]},bs,TABLE);b=run_window(win(),{DAY:[c]},bs,TABLE)
        self.assertEqual(a,b);self.assertEqual(bs,before)

def saved_first_day_check():
    s=rows(INPUTS/'candidate_stream');b={r['entry_id']:r for r in rows(INPUTS/'books')};day=min(r['session'] for r in s)
    d,ds,ts,cs,it=engine()(3,day,[r for r in s if r['session']==day],b,D('1000000'),True,v5.PROFILE,tables=read(INPUTS/'arrival'))
    expected=[r for r in rows(INPUTS/'native_decisions') if r['session']==day];et=[r for r in rows(INPUTS/'native_trades') if r['session']==day];ec=[r for r in rows(INPUTS/'native_curve') if r['session']==day]
    daily=next(x for x in read(INPUTS/'native_result')['daily_series'] if x['session']==day)
    checks={'decisions':ds==expected,'trades':ts==et,'curve':cs==ec,'daily':d==daily}
    save(OUT/'SAVED_FIRST_DAY_COMPATIBILITY.json',{'exact_jst':now(),'market_day_probe_N':1,'session':day,'checks':checks,'mismatch_N':sum(not x for x in checks.values())})
    assert all(checks.values()),checks

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ResetTests);result=unittest.TextTestRunner(verbosity=2).run(suite)
    save(OUT/'RESET20_SYNTHETIC_TESTS.json',{'exact_jst':now(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()})
    if not result.wasSuccessful():sys.exit(1)
    saved_first_day_check()
