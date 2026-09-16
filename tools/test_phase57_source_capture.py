import unittest
from unittest.mock import patch
from types import SimpleNamespace
from phase57_source_capture import read_snapshot, packet_from_rows, validate_config, FIELDS, SAFETY

CONFIG={'schemaId':'ARK_SOURCE_CAPTURE_CONFIG_V1','mode':'SOURCE_SEMANTICS_ONLY','workbookPath':'C:\\Ark\\Source.xlsx','workbookVersion':'ARK_SOURCE_V1','sourceIdentity':'MSII_LOCAL_DIAGNOSTIC','sheet':'ARK_CHART_5M','range':'A2:O20','versionCell':'B1','fields':FIELDS,'safety':SAFETY}
ROW=[0,0,'1000.T','1000','2026-09-14','09:00:00',100,101,99,100,1,'2026-09-14T00:05:00Z',100,99,101]
class Sheets:
    def __init__(self, names): self.names=names; self.Count=len(names); self.formula='=RssMarket("1000","現在値")'
    def __call__(self,key):
        name=self.names[key-1] if isinstance(key,int) else key
        return SimpleNamespace(Name=name,UsedRange=SimpleNamespace(Count=15,Formula=((self.formula,),),Formula2=((self.formula.replace('=','=@',1),),)),Range=lambda address:SimpleNamespace(Value2='ARK_SOURCE_V1' if address=='B1' else (tuple(ROW),)))
def workbook():
    return SimpleNamespace(Worksheets=Sheets(['ARK_CONFIG','ARK_CHART_5M']),FullName=CONFIG['workbookPath'],HasVBProject=False,Connections=SimpleNamespace(Count=0),Names=SimpleNamespace(Count=0),LinkSources=lambda _:None)
class Tests(unittest.TestCase):
    def test_config_and_read(self):
        validate_config(CONFIG);a,b=read_snapshot(workbook(),CONFIG);self.assertEqual(a,b)
    def test_orders_and_wrong_workbook(self):
        for change in [lambda w:setattr(w,'Worksheets',Sheets(['ARK_ORDER'])),lambda w:setattr(w,'FullName','wrong.xlsx'),lambda w:setattr(w,'HasVBProject',True)]:
            w=workbook();change(w)
            with self.assertRaises(ValueError):read_snapshot(w,CONFIG)
    def test_nested_or_order_formulas_rejected(self):
        for formula in ['=RssStockOrder(1,TRUE)', '=IF(TRUE,RssMarket("1000","現在値"),0)', '=OtherUdf()']:
            w=workbook();w.Worksheets.formula=formula
            with self.assertRaises(ValueError):read_snapshot(w,CONFIG)
    def test_source_packet_never_claims_connection_or_finality(self):
        p=packet_from_rows([ROW],CONFIG,'1','2026-09-14T00:05:01Z')
        self.assertIsNone(p['connected']);self.assertEqual(p['mode'],'SOURCE_SEMANTICS_ONLY');self.assertNotIn('finalized',p['rows'][0])
    def test_partial_and_cell_errors(self):
        with self.assertRaises(ValueError):packet_from_rows([[1]],CONFIG,'1','2026-09-14T00:05:01Z')
        row=ROW.copy();row[6]='#N/A';p=packet_from_rows([row],CONFIG,'1','2026-09-14T00:05:01Z',True)
        self.assertEqual(p['rows'][0]['cellErrors'],['open']);self.assertTrue(p['partialRead'])
    def test_modes_and_fieldmap_rejected(self):
        for mutation in [{'mode':'REALTIME_SHADOW'},{'fields':['close']},{'range':'A:O'},{'safety':{}}]:
            with self.assertRaises(ValueError):validate_config({**CONFIG,**mutation})
    def test_retry_match_and_exhaustion_preserve_reads(self):
        from phase57_source_capture import read_consistent_snapshot
        def fake(pairs):
            it=iter(pairs)
            def read(*args,**kwargs):
                a,b=next(it);kwargs['on_read']('A',a);kwargs['on_read']('B',b);return a,b
            return read
        for pairs,matched in [([([1],[2]),([3],[3])],True),([([1],[2])]*3,False)]:
            log=[]
            with patch('phase57_source_capture.read_snapshot',side_effect=fake(pairs)):
                a,b,ok=read_consistent_snapshot(None,CONFIG,log.append,sleep=lambda _:None)
            self.assertEqual(ok,matched);self.assertEqual(len([x for x in log if 'snapshot' in x]),len(pairs)*2)
            self.assertFalse(log[-1]['atomicityProven'])
    def test_retry_transient_exception_and_safety_failure(self):
        from phase57_source_capture import read_consistent_snapshot
        log=[]
        with patch('phase57_source_capture.read_snapshot',side_effect=[RuntimeError('Excel busy'),([1],[1])]) as read:
            self.assertTrue(read_consistent_snapshot(None,CONFIG,log.append,sleep=lambda _:None)[2]);self.assertEqual(read.call_count,2)
        self.assertEqual(log[0]['error'],'Excel busy')
        with patch('phase57_source_capture.read_snapshot',side_effect=ValueError('WRONG_WORKBOOK')) as read:
            with self.assertRaises(ValueError):read_consistent_snapshot(None,CONFIG,log.append,sleep=lambda _:None)
            self.assertEqual(read.call_count,1)
        with patch('phase57_source_capture.read_snapshot',side_effect=RuntimeError('Excel busy')) as read:
            with self.assertRaisesRegex(RuntimeError,'RETRIES_EXHAUSTED'):read_consistent_snapshot(None,CONFIG,log.append,sleep=lambda _:None)
            self.assertEqual(read.call_count,3)
    def test_a_preserved_if_b_raises(self):
        from phase57_source_capture import read_consistent_snapshot
        def fail(*args,**kwargs):kwargs['on_read']('A',[123]);raise RuntimeError('B failed')
        log=[]
        with patch('phase57_source_capture.read_snapshot',side_effect=fail):
            with self.assertRaises(RuntimeError):read_consistent_snapshot(None,CONFIG,log.append,attempts=1,sleep=lambda _:None)
        self.assertEqual(log[0]['snapshot'],[123]);self.assertEqual(log[1]['error'],'B failed')
if __name__=='__main__':unittest.main()
