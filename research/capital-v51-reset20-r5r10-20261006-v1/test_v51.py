import unittest,copy,inspect
from reset20 import *
from test_reset20 import candidate,book,market,DAY,TABLE,win,CAL
from v51_allocation import allocation as v51alloc
from allocation import allocation as baseline
from io_utils import *

COUNT={'pure_allocation_calls':0,'synthetic_day_calls':0}
def allocate(cs,eq='1000000',exposure='0',cash='1000000',bands=[]):
    COUNT['pure_allocation_calls']+=1
    return v51alloc(cs,D(eq),D(exposure),D(cash),bands)
def replay(cs,books):
    COUNT['synthetic_day_calls']+=1
    return engine(v51alloc)(3,DAY,cs,books,D('1000000'),True,'TEST_V51',tables=TABLE)
def row(key,pp,score=2.1,minute=570,price='100',symbol=None):
    c=candidate(key,minute,price,symbol);c['lot_priority_pP']=pp;c['capital_score']=c['ML']=score
    c['rank']=c['capacity_band']='S' if score>=2 else 'A' if score>=1.5 else 'B'
    return c

class CandidateTests(unittest.TestCase):
    def test_integer_priority_channel(self):
        cs=[row('donor',.1,score=2.5),row('receiver',.8,score=1.6)]
        a=allocate(cs);b=baseline(cs,D('1000000'),D(0),D('1000000'),[])
        self.assertGreater(a[1]['quantity'],b[1]['quantity']);self.assertLess(a[0]['quantity'],b[0]['quantity']);self.assertEqual(sum(x['debit'] for x in a)+a[0]['budget_unspent'],a[0]['batch_budget'])
    def test_inherited_caps_target_cash(self):
        cs=[row('a',.9),row('b',.8,score=1.6),row('c',.7,score=1.2)]
        a=allocate(cs);self.assertTrue(all(x['quantity']%100==0 and x['debit']<=x['equity_cap'] for x in a));self.assertLessEqual(sum(x['debit'] for x in a),D('1000000'));self.assertEqual(a[0]['target_utilization'],D('.79'))
    def test_missing_nonfinite_abstain(self):
        for pp in [None,float('nan'),float('inf')]:
            cs=[row('x',pp)];self.assertEqual(allocate(cs),baseline(cs,D('1000000'),D(0),D('1000000'),[]))
    def test_ties_native_order_and_determinism(self):
        cs=[row('z',.5,score=2.1),row('a',.5,score=2.5)]
        self.assertEqual(allocate(cs),allocate(copy.deepcopy(cs)))
        a=allocate(cs,cash='10005',exposure='0');self.assertEqual(a[0]['quantity'],0);self.assertEqual(a[1]['quantity'],100)
    def test_low_cash_and_expensive_lot(self):
        self.assertEqual(allocate([row('x',.9,price='20000')])[0]['quantity'],0)
        self.assertEqual(allocate([row('x',.9)],cash='10')[0]['quantity'],0)
    def test_labels_never_influence_quantity(self):
        cs=[row('a',.1),row('b',.9)];alt=copy.deepcopy(cs)
        for r in alt:r.update(R5=True,R10=True,U5=True,U10=True,future_profit=10**9,future_arrival=[1],future_exit_available=False)
        self.assertEqual(allocate(cs),allocate(alt))
    def test_future_suffix_prefix(self):
        cs=[row('a',.1),row('b',.9)];bs={r['entry_id']:book(r) for r in cs};alt=copy.deepcopy(bs)
        for key,b in alt.items():
            b['market'][-1]=market(600,'90');b['frozen_exit']['sell_price_decimal']=str(D('90')*D('.9995'))
        a=replay(cs,bs);b=replay(cs,alt);self.assertEqual(a[1],b[1]);self.assertEqual(a[3][:600-540],b[3][:600-540])
    def test_future_arrival_prefix(self):
        c=row('now',.5);f=row('future',.99,minute=700);bs={'now':book(c),'future':book(f,release=750)}
        a=replay([c],{'now':bs['now']});b=replay([c,f],bs)
        self.assertEqual(a[1][0],b[1][0]);self.assertEqual(a[3][:700-540],b[3][:700-540])
    def test_max3_same_symbol_and_unsettled(self):
        cs=[row(str(i),.1*i) for i in range(4)];bs={r['entry_id']:book(r) for r in cs};a=replay(cs,bs)
        self.assertEqual(a[1][-1]['reason'],'MAX_POSITION_CAP');self.assertLessEqual(a[0]['max_concurrent'],3)
        c=row('same1',.5,symbol='SYMBOL');c2=row('same2',.8,minute=580,symbol='SYMBOL');b=replay([c,c2],{'same1':book(c)});self.assertEqual(b[1][1]['reason'],'SYMBOL_ALREADY_OPEN')
        a=replay([c],{'same1':book(c,missing=True)});self.assertIsNone(a[0]['ending_cash'])
    def test_sell_release_cost_and_mtm_cash(self):
        c=row('a',.9);b=book(c,exit_price='100');b['market'].append(market(575,'500'))
        a=replay([c],{'a':b});q=a[1][0]['quantity'];self.assertEqual(D(a[2][0]['pnl']),D('100')*(D('.9995')-D('1.0005'))*q);self.assertEqual(a[3][580-540]['cash'],a[3][570-540]['cash'])
    def test_no_evaluation_imports(self):
        text=inspect.getsource(v51alloc)
        for name in ['R5','R10','U5','U10','book','future','label','mP','q2','q3']:self.assertNotIn(name,text)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CandidateTests))
    save(OUT/'V51_CANARIES.json',{'exact_jst':now(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful(),'counts':COUNT,'policy_candidates_tested':1})
    raise SystemExit(0 if result.wasSuccessful() else 1)
