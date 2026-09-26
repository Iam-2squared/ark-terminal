"""Synthetic integrity tests only; not market evidence or later-step research."""
import copy, json, subprocess, tempfile, unittest
from pathlib import Path
import numpy as np
from scripts import phase57_future_path_deep_audit as d


def bars(prices,start=600):
    result=[];old=prices[0]
    for i,p in enumerate(prices):
        result.append([start+i,old,max(old,p)+.01,min(old,p)-.01,p,10.,1000.]);old=p
    return np.array(result,float)

class DeepAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.F=d.frozen()

    def test_original_no_dominant(self):
        z=self.F.classify('2025-06-02',600,100.,bars([100.]*40),True)
        self.assertEqual(z['reason'],'NO_DOMINANT_PATH');self.assertFalse(any(z['predicate'].values()))

    def test_original_direct(self):
        z=self.F.classify('2025-06-02',600,100.,bars(np.linspace(100,104,40)),True)
        self.assertTrue(z['predicate'][d.PATHS[0]])

    def test_recovery_and_clause_parity(self):
        a=bars(np.r_[np.linspace(100,98,15),np.linspace(98,103,25)])
        z=self.F.classify('2025-06-02',600,100.,a,True)
        atoms,w,_=d.clauses('2025-06-02',a,100.,self.F)
        self.assertTrue(z['predicate'][d.PATHS[1]]);self.assertTrue(atoms['RECOVERY/pairAndTerminal'])
        self.assertLess(w['recovery']['lowMinute'],w['recovery']['highMinute'])

    def test_consolidation_clause_parity(self):
        a=bars([100.]*12+[101.]+list(np.linspace(101,103,27)))
        a[12,2]=101.3;a[12,3]=99.99
        z=self.F.classify('2025-06-02',600,100.,a,True)
        _,w,_=d.clauses('2025-06-02',a,100.,self.F)
        self.assertTrue(z['predicate'][d.PATHS[2]]);self.assertIsNotNone(w['consolidation'])

    def test_chop_override_preserves_overlap(self):
        a=bars([100.]+[98.,102.]*20+[100.])
        z=self.F.classify('2025-06-02',600,100.,a,True)
        self.assertEqual(z['path'],d.PATHS[3]);self.assertGreater(sum(z['predicate'].values()),1)
        self.assertEqual(len(d.reversals_with_witness(a,self.F)),z['reversals'])

    def test_same_bar_order_is_unknown(self):
        a=bars([100.]*40);a[0,2]=101.1;a[0,3]=99.4
        z=self.F.classify('2025-06-02',600,100.,a,True)
        self.assertTrue(z['sameBarOrderUnknown']);self.assertFalse(z['predicate'][d.PATHS[0]])

    def test_empty_and_twenty_row_boundary(self):
        day='2025-06-02'
        self.assertEqual(self.F.classify(day,600,100.,np.empty((0,7)),True)['reason'],'MISSING_PATH_DATA')
        self.assertEqual(self.F.classify(day,600,100.,bars([100.]*19),True)['reason'],'INSUFFICIENT_OBSERVATION')
        self.assertEqual(self.F.classify(day,600,100.,bars([100.]*20),True)['reason'],'NO_DOMINANT_PATH')

    def test_remaining_thirty_boundary(self):
        self.assertEqual(self.F.classify('2025-06-02',895,100.,bars([100.]*30,895),True)['reason'],'NO_DOMINANT_PATH')
        self.assertEqual(self.F.classify('2025-06-02',896,100.,bars([100.]*29,896),True)['reason'],'INSUFFICIENT_OBSERVATION')

    def test_gate_overlap_not_lost(self):
        z=d.observation('2025-06-02',915,bars([100.]*5,915),False,self.F)
        self.assertEqual(len(z['gateFailures']),3);self.assertEqual(z['primaryReason'],'REMAINING_LT30')

    def test_lunch_not_missing(self):
        day='2025-06-02';minutes=self.F.e.minutes(day)
        a=np.array([[m,100,100.1,99.9,100,1,100] for m in minutes if m>=680],float)
        z=d.observation(day,680,a,True,self.F)
        self.assertEqual(z['missingRegular'],0);self.assertTrue(z['crossesLunch'])
        a=a[a[:,0]!=751];z=d.observation(day,680,a,True,self.F)
        self.assertEqual(z['missingMinutes'],[751]);self.assertEqual(z['sourceCause'],'UNRESOLVED_SOURCE_CAUSE')

    def test_reversal_reset_at_lunch_and_missing(self):
        a=bars([100,101,100,101,100,101],680);a[3:,0]+=60
        ev=d.reversals_with_witness(a,self.F)
        self.assertEqual(len(ev),self.F.reversal_count(a))
        for e in ev:self.assertLess(e['minute']-e['pivotMinute'],60)

    def test_auction_endpoint_exclusion(self):
        a=bars([100,101],690);b=self.F.c.future_rows('2025-06-02',a,690)
        self.assertNotIn(690,b[:,0]);a=bars([100,101],900)
        self.assertIn(900,self.F.c.future_rows('2025-06-02',a,900)[:,0])

    def test_deterministic_representatives(self):
        rows=[]
        for i,x in enumerate([.3,.1,.2,.1]):
            rows.append({'opportunity':str(i),'original':{'path':d.PATHS[-1],'reason':'NO_DOMINANT_PATH'},'predicateSignature':'NONE','metrics':{'efficiency':x,'remainingActive':100,'terminalReturnPct':0}})
        self.assertEqual(d.representatives(rows),d.representatives(list(reversed(rows))))
        self.assertIn('1',d.representatives(rows));self.assertNotIn('3',d.representatives(rows))

    def test_deterministic_gzip_and_nan_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.json.gz';b=Path(td)/'b.json.gz'
            d.write(a,{'z':2,'a':[1,2]});d.write(b,{'a':[1,2],'z':2})
            self.assertEqual(a.read_bytes(),b.read_bytes())
            with self.assertRaises(ValueError):d.write(a,{'bad':float('nan')})

    def test_ast_extraction_never_runs_module_top_level(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'trap.py';p.write_text('raise RuntimeError("forbidden")\n\ndef allowed(x):\n return x+1\n\ndef state():\n raise RuntimeError("forbidden")\n')
            ns={};f=d.extract(p,('allowed',),ns)
            self.assertEqual(f.allowed(2),3);self.assertNotIn('state',ns)

    def test_source_pin_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'data.txt';p.write_text('original\n')
            def git(*args):return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()
            git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid');git('add','.');git('commit','-m','fixture')
            ref=git('rev-parse','HEAD');self.assertEqual(d.pin('data.txt',ref,root)['sha256'],d.sha(p))
            p.write_text('corrupted\n')
            with self.assertRaisesRegex(ValueError,'SOURCE_CHANGED'):d.pin('data.txt',ref,root)

if __name__=='__main__':unittest.main()
