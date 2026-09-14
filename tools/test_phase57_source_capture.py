import unittest
from types import SimpleNamespace
from phase57_source_capture import read_snapshot, packet_from_rows, validate_config, FIELDS, SAFETY

CONFIG={'schemaId':'ARK_SOURCE_CAPTURE_CONFIG_V1','mode':'SOURCE_SEMANTICS_ONLY','workbookPath':'C:\\Ark\\Source.xlsx','workbookVersion':'ARK_SOURCE_V1','sourceIdentity':'MSII_LOCAL_DIAGNOSTIC','sheet':'ARK_CHART_5M','range':'A2:O20','versionCell':'B1','fields':FIELDS,'safety':SAFETY}
ROW=[0,0,'1000.T','1000','2026-09-14','09:00:00',100,101,99,100,1,'2026-09-14T00:05:00Z',100,99,101]
class Sheets:
    def __init__(self, names): self.names=names; self.Count=len(names); self.formula='=RssMarket("1000","現在値")'
    def __call__(self,key):
        name=self.names[key-1] if isinstance(key,int) else key
        return SimpleNamespace(Name=name,UsedRange=SimpleNamespace(Count=15,Formula=((self.formula,),)),Range=lambda address:SimpleNamespace(Value2='ARK_SOURCE_V1' if address=='B1' else (tuple(ROW),)))
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
        self.assertFalse(p['connected']);self.assertEqual(p['mode'],'SOURCE_SEMANTICS_ONLY');self.assertNotIn('finalized',p['rows'][0])
    def test_partial_and_cell_errors(self):
        with self.assertRaises(ValueError):packet_from_rows([[1]],CONFIG,'1','2026-09-14T00:05:01Z')
        row=ROW.copy();row[6]='#N/A';p=packet_from_rows([row],CONFIG,'1','2026-09-14T00:05:01Z',True)
        self.assertEqual(p['rows'][0]['cellErrors'],['open']);self.assertTrue(p['partialRead'])
    def test_modes_and_fieldmap_rejected(self):
        for mutation in [{'mode':'REALTIME_SHADOW'},{'fields':['close']},{'range':'A:O'},{'safety':{}}]:
            with self.assertRaises(ValueError):validate_config({**CONFIG,**mutation})
if __name__=='__main__':unittest.main()
