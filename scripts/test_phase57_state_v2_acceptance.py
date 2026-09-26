"""Frozen golden-vector tests; synthetic fixtures only, never market outcomes."""
from __future__ import annotations
import ast,copy,inspect,json,unittest
from pathlib import Path
from fractions import Fraction as F
from phase57_state_v2.common import r,axis,semantic_axes,observation,digest,PITReader,SAFETY,validate_tree,ROOT
from phase57_state_v2.now import now_state_reference_v2,validate_now
from phase57_state_v2.future import future_resolution_v2,validate_future
from phase57_state_v2.independent import verify_core
from phase57_state_v2.historical import prefix_at
DAY='2025-06-02';PREV='2025-05-30';ENDS=tuple(range(541,691))+tuple(range(751,926))
CAL=['2025-05-26','2025-05-27','2025-05-28','2025-05-29',PREV,DAY]
ID={'opportunityId':DAY+'|SYNTHETIC','sessionDate':DAY,'securityId':'SYNTHETIC','selectorAt':DAY+'T09:00:00+09:00','elapsedActiveMinutesFromSelector':5}

def bars(prices,start=541,spread=0,known=True):
    return tuple(r.Bar(start+i,p,F(p)+spread,F(p)-spread,p,100,F(p)*100,start+i if known else None) for i,p in enumerate(prices))

def context(previous=True,basis=True,flat=False,short=False):
    prev=bars([100]*30 if flat else [F(100)+F(i%5,4) for i in range(30)]) if previous else ()
    if short:prev=prev[:-1]
    session=r.Session(PREV,'SYNTHETIC','RAW' if basis else None,ENDS,prev) if prev else None
    scale=r.scale_from_previous(session,DAY,PREV,'SYNTHETIC','RAW') if session else {'status':'PREVIOUS_CONTEXT_UNAVAILABLE','scale':None,'blockN':0}
    return {'previous':prev,'previousDay':PREV,'previousBasis':'RAW' if basis else None,'basis':'RAW','previousContext':{'observedHigh':max(b.h for b in prev),'observedLow':min(b.l for b in prev)} if prev else None,'previousCoverage':F(len(prev),len(ENDS)),'scale':scale,'dailyRows':[],'dailyReasons':{},'calendar':CAL,'sourceHashes':{'todayMinute':'synthetic','previousMinute':'synthetic','dailyProjection':'synthetic'},'sourceVintageId':'SYNTHETIC_ONLY','quality':['SYNTHETIC_ONLY']}

def now(bs,t,ctx=None,ends=ENDS):
    return now_state_reference_v2(prefix=bs,ends=ends,asof=t,identity=ID,context=ctx or context())
def future(bs,t,ctx=None,ends=ENDS):
    cut=([e for e in ends if e>t][:10] or [t])[-1]
    return future_resolution_v2(bounded_bars=prefix_at(bs,cut),ends=ends,asof=t,identity=ID,context=ctx or context())

def core_fixture(n=0,active=None,phases=None,highs=(101,101),lows=(100,100)):
    ps=[]
    for i in range(n):
        kind='LOW' if i%2==0 else 'HIGH';price=lows[i//2%2] if kind=='LOW' else highs[i//2%2]
        ps.append({'kind':kind,'price':F(price),'id':str(i)})
    mech={'observation':{'status':'COMPLETE','reasons':[]},'descriptors':{'direction':'UP','returnPct':F(1)},'state':{'structure':{'kind':active} if active else None,'identificationStatus':'IDENTIFIED' if active else 'UNRESOLVED_STRUCTURE','phase':phases or [],'pivots':ps}}
    a=semantic_axes(mech,{'status':'AVAILABLE','scale':F(1)},{'missingFlags':[]})
    verify_core(a,mech,'AVAILABLE')
    return a

class GoldenVectors(unittest.TestCase):
    def test_GV01(self):
        z=now(bars([100,100,100,100,101]),545,context(short=True))
        self.assertEqual((z['direction']['status'],z['direction']['value']),('DEFINED','UP'))
        self.assertEqual(z['structure']['reasonCodes'],['SCALE_INSUFFICIENT_BLOCKS'])
    def test_GV02(self):
        z=now(bars([100]*4),545,context(short=True))
        self.assertEqual(z['structure']['primaryReason'],'OBS_CURRENT_BAR_NOT_OBSERVED')
        self.assertTrue({'OBS_CURRENT_BAR_NOT_OBSERVED','OBS_LATEST5_INCOMPLETE','SCALE_INSUFFICIENT_BLOCKS'}<=set(z['structure']['reasonCodes']))
    def test_GV03(self):
        z=core_fixture(n=2)['structure'];self.assertEqual(z['status'],'INSUFFICIENT');self.assertIsNone(z['value'])
    def test_GV04(self):self.assertEqual(core_fixture(n=4)['structure']['value'],'NONE')
    def test_GV05(self):self.assertEqual(core_fixture(n=1,active='RANGE_STRUCTURE')['structure']['status'],'DEFINED')
    def test_GV06(self):self.assertEqual(core_fixture()['phase']['value'],[])
    def test_GV07(self):
        z=now(bars([100]*10),550)
        self.assertEqual(z['events']['fixedLevel']['TODAY_PRIOR_HIGH']['value'],[])
        self.assertEqual(z['events']['persistence']['status'],'NOT_APPLICABLE')
        self.assertEqual(z['events']['persistence']['reasonCodes'],['NO_TRIGGER_EVENT'])
    def test_GV08(self):
        z=future(bars([100]*8,start=917),920)
        self.assertEqual(z['resolutionStatus'],'CENSORED')
        self.assertEqual(z['censorFlags'],['OBSERVATION_CENSORED_BEFORE_H','SESSION_CENSORED_BEFORE_H'])
    def test_GV09(self):
        bs=bars([100,101,100,102,101,103,102,104,103,105]);t=545
        z=future(bs,t);ps=z['stateAtTWitness']['pivots']
        self.assertTrue(any(p['effectiveAt']<=t<p['confirmedAt'] for p in ps))
        own=r.snapshot(prefix_at(bs,t),ENDS,t,F(1))['state']['pivots']
        self.assertTrue(all(p['confirmedAt']<=t for p in own))
    def test_GV10(self):
        z=future(bars([100,101,100,102,101,103,102,104,103,105]),545)
        self.assertTrue(all(p['effectiveAt']<=545 for p in z['stateAtTWitness']['pivots']))
    def test_GV11(self):
        a=bars([100]*20);b=a[:5]+bars([200]*15,546)
        self.assertEqual(digest(now(prefix_at(a,545),545)),digest(now(prefix_at(b,545),545)))
    def test_GV12(self):self.assertEqual(core_fixture(n=1,active='UP_STRUCTURE')['structure']['status'],'DEFINED')
    def test_GV13(self):
        z=now(bars([100]*2,689)+bars([100]*3,751),753)
        self.assertEqual(z['direction']['status'],'NOT_EVALUATED');self.assertIn('OBS_SESSION_BOUNDARY',z['direction']['reasonCodes'])
    def test_GV14(self):
        z=now(bars([100]*2),542)
        self.assertEqual(z['observationQuality']['density5'],1)
        self.assertIn('OBS_SHORT_SESSION_HISTORY',z['direction']['reasonCodes'])
    def test_GV15(self):
        z=future(bars([100]*10,916),920)
        self.assertEqual(z['censorFlags'],['SESSION_CENSORED_BEFORE_H'])
    def test_GV16(self):
        bs=bars([100]*5);z=now(bs[:2]+bs[3:],545)
        self.assertEqual(z['observationQuality']['latest5ObservedK'],4)
        self.assertTrue({'OBS_LATEST5_INCOMPLETE','OBS_MISSING_SCHEDULED_BAR'}<=set(z['direction']['reasonCodes']))
    def test_GV17(self):
        z=now(bars([100]*5),545,context(previous=False))
        self.assertEqual(z['direction']['status'],'DEFINED');self.assertEqual(z['structure']['reasonCodes'],['SCALE_PREVIOUS_CONTEXT_UNAVAILABLE'])
    def test_GV18(self):
        z=now(bars([100]*5),545,context(basis=False))
        self.assertEqual(z['structure']['reasonCodes'],['SCALE_PRICE_BASIS_UNVERIFIED']);self.assertIsNone(z['scale']['scaleValue'])
    def test_GV19(self):
        z=now(bars([100]*5),545,context(flat=True))
        self.assertEqual(z['structure']['reasonCodes'],['SCALE_ZERO']);self.assertIsNone(z['scale']['scaleValue'])
    def test_GV20(self):
        self.assertEqual(core_fixture(n=3)['structure']['status'],'INSUFFICIENT')
        self.assertEqual(core_fixture(n=4)['structure']['status'],'DEFINED')
    def test_GV21(self):self.assertEqual(core_fixture(n=4,lows=(100,99))['pivotSignature']['value']['highRelation'],'H_EQ')
    def test_GV22(self):
        z=core_fixture(n=4,active='DOWN_STRUCTURE',phases=['CORRECTION','RECOVERY'])
        self.assertEqual(z['phase']['status'],'DEFINED');self.assertEqual(z['phase']['value'],['CORRECTION','RECOVERY'])
    def test_GV23(self):
        z=core_fixture(n=4)['pivotSignature'];self.assertEqual(z['value']['highRelation'],'H_EQ');self.assertIsNone(z['evidence']['highDiffTicks'])
    def test_GV24(self):
        with self.assertRaisesRegex(ValueError,'FUTURE_SOURCE_READ'):now(bars([100]*6),545)
    def test_GV25(self):
        bs=bars([100]*5);late=r.Bar(545,100,100,100,100,100,10000,546)
        with self.assertRaisesRegex(ValueError,'KNOWN_AT_AFTER'):now(bs[:-1]+(late,),545)
    def test_GV26(self):
        bs=bars([100,101,100,102,101,103,102,104,103,105]);a=now(prefix_at(bs,545),545);h=digest(a);b=future(bs,545)
        self.assertEqual(h,digest(a));self.assertNotEqual(a['artifactKind'],b['artifactKind']);self.assertNotIn('adjudicatedStructureAtT',a);self.assertNotEqual(a['structure']['value'],b['adjudicatedStructureAtT']['value'])

class AdditionalAcceptanceTests(unittest.TestCase):
    def test_golden_coverage_exact_26(self):
        vectors=json.loads((ROOT/'docs/evidence/phase57-state-v2-hardening/GOLDEN_VECTORS_v2.json').read_text())['vectors']
        self.assertEqual(len(vectors),26)
        self.assertEqual({'test_'+v['id'][:4] for v in vectors},{x for x in dir(GoldenVectors) if x.startswith('test_')})
    def test_historical_known_at_not_inferred(self):
        z=now(bars([100]*5,known=False),545)
        self.assertEqual(z['causalMetadata']['availabilityEvidence'],'HISTORICAL_CLOSED_RECONSTRUCTION')
    def test_late_known_previous_rejected(self):
        ctx=context();ctx['dailyRows']=[{'date':PREV,'security':'SYNTHETIC','basis':'RAW','o':100,'h':100,'l':100,'c':100,'knownAt':DAY+'T10:00:00+09:00'}]
        with self.assertRaisesRegex(ValueError,'KNOWN_AT_AFTER'):now(bars([100]*5),545,ctx)
    def test_modules_are_isolated(self):
        p=ROOT/'scripts/phase57_state_v2/now.py';tree=ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and node.module!='__future__':self.assertNotIn('future',node.module or '')
            if isinstance(node,ast.Attribute):self.assertNotEqual(node.attr,'reference_at')
        self.assertNotIn('future',inspect.signature(now_state_reference_v2).parameters)
    def test_phase_not_masked_by_unrelated_direction_failure(self):
        bs=bars([100,101,100,102,101]);z=now(bs[:2]+bs[3:],545)
        self.assertEqual(z['direction']['status'],'NOT_EVALUATED');self.assertEqual(z['phase']['status'],'DEFINED')
    def test_invalid_axis_reason_value_fail_closed(self):
        for args in [('AMBIGUOUS',None,()),('DEFINED',None,()),('NOT_EVALUATED',None,()),('DEFINED','UP',('SCALE_ZERO',)),('NOT_EVALUATED',None,('GUESS',))]:
            with self.assertRaises(ValueError):axis(*args)
    def test_invalid_direction_value_rejected(self):
        z=now(bars([100]*5),545);z['direction']['value']='SIDEWAYS'
        with self.assertRaises(ValueError):validate_now(z)
    def test_illegal_future_enum_rejected(self):
        z=future(bars([100]*20),545);z['resolutionStatus']='RESOLVED'
        with self.assertRaises(ValueError):validate_future(z)
    def test_primary_reason_independent_input_order(self):
        a=axis('NOT_EVALUATED',reasons=['SCALE_ZERO','OBS_CURRENT_BAR_NOT_OBSERVED']);b=axis('NOT_EVALUATED',reasons=['OBS_CURRENT_BAR_NOT_OBSERVED','SCALE_ZERO']);self.assertEqual(a,b)
    def test_retrospective_effective_timeline_reason_without_new_pivot(self):
        from run_phase57_state_v2 import reasons_for
        old={'structure':None,'phase':['RESTRUCTURING'],'lateConfirmedPivotN':0}
        now={'structure':{'status':'DEFINED','value':'NONE'},'phase':{'status':'DEFINED','value':[]}}
        bridge={'structure':None,'phase':['RESTRUCTURING']}
        self.assertIn('RETROSPECTIVE_EFFECTIVE_TIME_REPLAY',reasons_for(old,now,bridge))
    def test_all_safety_false(self):self.assertEqual(9,len(SAFETY));self.assertTrue(all(v is False for v in SAFETY.values()))

if __name__=='__main__':unittest.main(verbosity=2)
