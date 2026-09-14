import copy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from phase57_setup_rss_source import config_for, setup
from phase57_source_capture import read_snapshot, packet_from_rows
from phase57_rss_raw import layout, formulas, normalize, date_cell, time_cell, number_cell, scan_range

class Cell:
    def __init__(self,value=None,formula=None): self.Value2=value; self.Formula=formula
class Sheet:
    def __init__(self,name): self.Name=name; self.cells={}
    def Range(self,key): return self.cells.setdefault(key,Cell())
    @property
    def UsedRange(self): return SimpleNamespace(Count=100,Row=1,Rows=SimpleNamespace(Count=3002),Formula=tuple((c.Formula,) for c in self.cells.values()),Formula2=tuple((getattr(c,'Formula2',c.Formula.replace('=','=@',1) if c.Formula else c.Formula),) for c in self.cells.values()))
class Sheets:
    def __init__(self): self.items=[Sheet('ARK_CONFIG'),Sheet('ARK_CHART_5M')]
    @property
    def Count(self): return len(self.items)
    def __call__(self,key):
        return self.items[key-1] if isinstance(key,int) else next(s for s in self.items if s.Name==key)
    def Add(self,After):
        sheet=Sheet('new');self.items.append(sheet);return sheet
class Book:
    def __init__(self,path):
        self.FullName=path;self.Worksheets=Sheets();self.HasVBProject=False;self.Date1904=False;self.ReadOnly=False
        self.Connections=SimpleNamespace(Count=0);self.Names=SimpleNamespace(Count=0)
        self.Worksheets('ARK_CONFIG').Range('B1').Value2='ARK_SOURCE_V1';self.saved=False
    def LinkSources(self,_):return None
    def SaveCopyAs(self,path):Path(path).write_bytes(b'original-fixture-backup')
    def Save(self):self.saved=True

def populated(book,config):
    # Mock RSS output after Excel's direct function calls. No model/outcomes used.
    for slot in config['slots']:
        book.Worksheets('ARK_RAW_CHART').Range(scan_range(slot)).Value2=(('2026/09/14','09:00',100,101,99,100,20),)
        book.Worksheets('ARK_RAW_MARKET').Range(slot['market']).Value2=(('2026/09/14','09:05:01',100,99,101),)

class Tests(unittest.TestCase):
    def make(self,tmp):
        c=config_for(Path(tmp)/'Source.xlsx',['7203.T','6758.T'])
        b=Book(c['workbookPath'])
        # New ranges in Excel are rectangular blank matrices; mock that behavior.
        old=b.Worksheets.Add
        def add(After):
            s=old(After)
            for slot in c['slots']:
                s.Range(scan_range(slot)).Value2=((None,)*7,)
                s.Range(slot['market']).Value2=((None,)*5,)
            return s
        b.Worksheets.Add=add
        return b,c
    def test_setup_capture_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp)
            self.assertEqual(setup(b,c,Path(tmp)/'backup.xlsx'),'RAW_LAYOUT_CREATED')
            self.assertTrue(b.saved);self.assertTrue((Path(tmp)/'backup.xlsx').exists())
            populated(b,c);before,after=read_snapshot(b,c)
            self.assertEqual(before,after)
            rows=normalize(after,c['slots'],'2026-09-14')
            self.assertEqual(rows[0],[0,0,'7203.T','7203.T','2026-09-14','09:00:00',100,101,99,100,20,'2026-09-14T09:05:01+09:00',100,99,101])
            packet=packet_from_rows(rows,c,'1','2026-09-14T00:05:02Z')
            source=Path(tmp)/'capture.jsonl';source.write_text(json.dumps(packet)+'\n')
            diagnostic=Path(tmp)/'diagnostic'
            run=subprocess.run(['node','scripts/phase57-source-diagnostic.mjs',str(source),str(diagnostic)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads((diagnostic/'summary.json').read_text())
            self.assertEqual(report['events'],[])
            self.assertEqual(report['connectionState'],'REAL_SOURCE_CONNECTED_OBSERVED')
            self.assertIn('UNVERIFIED',json.dumps(report));self.assertIn('"strategyCalculated": false',json.dumps(report))
            b.saved=False
            self.assertEqual(setup(b,c,Path(tmp)/'unused.xlsx'),'EXISTING_LAYOUT_VERIFIED')
            self.assertTrue(b.saved)
            self.assertFalse((Path(tmp)/'unused.xlsx').exists())
    def test_changed_formula_header_and_mapping_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp);setup(b,c,Path(tmp)/'backup.xlsx');populated(b,c)
            cell=b.Worksheets('ARK_RAW_CHART').Range(c['slots'][0]['formulaCell'])
            for formula in ['=RssChart(A2:G2,"1111.T","5M",120)','=RssChart(ARK_CONFIG!A1,"7203.T","5M",120)','=RssStockOrder(1,TRUE)']:
                cell.Formula=formula
                with self.assertRaises(ValueError):read_snapshot(b,c)
            cell.Formula=c['slots'][0]['chartFormula']
            b.Worksheets('ARK_RAW_CHART').Range(c['slots'][0]['header']).Value2=(('bad',)*7,)
            with self.assertRaises(ValueError):read_snapshot(b,c)
    def test_existing_order_workbook_never_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp);b.Worksheets.items.append(Sheet('ARK_ORDER'))
            with self.assertRaises(ValueError):setup(b,c,Path(tmp)/'backup.xlsx')
            self.assertFalse((Path(tmp)/'backup.xlsx').exists());self.assertFalse(b.saved)
    def test_serials_strict_parse_errors_and_prior_day(self):
        self.assertEqual(date_cell(46279),'2026-09-14')
        self.assertEqual(time_cell(9/24),'09:00:00')
        for bad in [True,float('nan'),'1,000','-','','9'*400]:
            with self.assertRaises(ValueError):number_cell(bad)
        slots=layout(['7203.T'])
        raw=[dict(market=[['2026/09/14','09:01:01',100,99,101]],chart=[['2026/09/13','09:00',100,101,99,100,5],['2026/09/14','09:00','#N/A',101,99,100,5]])]
        before=copy.deepcopy(raw);rows=normalize(raw,slots,'2026-09-14')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0][6],'#INVALID_NUMERIC');self.assertEqual(raw,before)
    def test_partial_raw_and_date_system_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp);b.Date1904=True
            with self.assertRaises(ValueError):setup(b,c,Path(tmp)/'backup.xlsx')
        with self.assertRaises(ValueError):normalize([dict(market=[[1]],chart=[])],layout(['7203.T']),'2026-09-14')
    def test_compatibility_names_exact_allowlist(self):
        from phase57_source_capture import audit_names
        benign=dict(Name='_xlfn.SINGLE',Visible=False,RefersTo='=#NAME?')
        for mutation,allowed in [({},True),({'Visible':True},False),({'RefersTo':'=1'},False),
            ({'Name':'other'},False),({'Name':'Sheet1!_xlfn.SINGLE'},False),({'RefersTo':'=#NAME? '},False)]:
            names=SimpleNamespace(Count=1,Item=lambda i:SimpleNamespace(**{**benign,**mutation}))
            if allowed: audit_names(names)
            else:
                with self.assertRaises(ValueError): audit_names(names)
        with self.assertRaises(ValueError): audit_names(SimpleNamespace(Count=2))
    def test_formula_and_formula2_contract(self):
        from phase57_source_capture import audit_formula_pair
        for formula in ['=RssChart(A2:G2,"7203.T","5M",120)','=RssMarket("7203.T","現在値")']:
            audit_formula_pair(formula,formula)
            audit_formula_pair(formula,'=@'+formula[1:])
        for bad in ['=IF(TRUE,RssMarket("7203.T","現在値"),0)','=Other()','=RssStockOrder(1,TRUE)',
                    '=RssMarket(Sheet1!A1,"現在値")','=RssMarket([other.xlsx]A1,"現在値")']:
            with self.assertRaises(ValueError):audit_formula_pair(bad,'=@'+bad[1:])
        with self.assertRaises(ValueError):audit_formula_pair('=RssMarket("7203.T","現在値")','=@RssMarket("1111.T","現在値")')
    def test_failed_first_setup_can_resume_with_compat_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp);setup(b,c,Path(tmp)/'backup.xlsx');populated(b,c)
            b.saved=False
            b.Names=SimpleNamespace(Count=1,Item=lambda i:SimpleNamespace(Name='_xlfn.SINGLE',Visible=False,RefersTo='=#NAME?'))
            self.assertEqual(setup(b,c,Path(tmp)/'retry.xlsx'),'EXISTING_LAYOUT_VERIFIED')
            self.assertTrue(b.saved)
            b.saved=False
            b.Worksheets('ARK_RAW_MARKET').Range('A1:E1').Value2=(('wrong',)*5,)
            with self.assertRaises(ValueError): setup(b,c,Path(tmp)/'bad.xlsx')
            self.assertFalse(b.saved)
    def test_extra_raw_formula_not_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp);setup(b,c,Path(tmp)/'backup.xlsx');populated(b,c);b.saved=False
            b.Worksheets('ARK_RAW_MARKET').Range('A99').Formula='=RssMarket("1111.T","現在値")'
            with self.assertRaises(ValueError):setup(b,c,Path(tmp)/'retry.xlsx')
            self.assertFalse(b.saved)
    def test_partial_layout_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp);b.Worksheets.items.append(Sheet('ARK_RAW_CHART'))
            with self.assertRaises(ValueError):setup(b,c,Path(tmp)/'backup.xlsx')
            self.assertFalse(b.saved)
    def test_bounded_latest_window_sizes_blanks_and_lunch(self):
        from datetime import datetime,timedelta
        from phase57_rss_raw import select_latest,check_latest_parity
        slots=layout(['7203.T'])
        for count in [1,119,120,136,3000]:
            rows=[]
            for i in range(count):
                t=datetime(2026,9,1,9)+timedelta(minutes=i*5)
                rows.append([t.strftime('%Y/%m/%d'),t.strftime('%H:%M'),100,101,99,100,i])
            session=rows[-1][0].replace('/','-')
            raw=[{'chart':rows,'market':[[session,'14:16',100,99,101]]}]
            chosen,meta=select_latest(raw,slots,120,session)
            self.assertEqual(len(chosen[0]['chart']),min(count,120))
            self.assertEqual(chosen[0]['chart'][-1],rows[-1]);self.assertEqual(meta[0]['rawLastExcelRow'],count+2)
            normalized=normalize(chosen,slots,session);self.assertTrue(check_latest_parity(meta,normalized))
            self.assertEqual(meta[0]['normalizationParity'],'PASS')
            self.assertFalse(check_latest_parity(meta,normalized[:-1]))
        rows=[['2026/09/14','11:25',100,101,99,100,1],[None]*7,['2026/09/14','12:30',100,101,99,100,2],['']*7]
        chosen,meta=select_latest([{'chart':rows}],slots,120,'2026-09-14')
        self.assertEqual([r[1] for r in chosen[0]['chart']],['11:25','12:30'])
        self.assertEqual(meta[0]['rawValidRowCount'],2);self.assertEqual(meta[0]['rawLastExcelRow'],5)
    def test_scan_overflow_invalid_and_reversed_rows_fail(self):
        from phase57_rss_raw import select_latest
        slots=layout(['7203.T'])
        for rows in [[[None]*7]*3001,[['2026/09/14','14:15','#N/A',101,99,100,1]],
          [['2026/09/14','14:15',100,101,99,100,1],['2026/09/14','14:10',100,101,99,100,1]]]:
            with self.assertRaises(ValueError):select_latest([{'chart':rows}],slots,120,'2026-09-14')
    def test_capture_reads_beyond_initial_120_rows(self):
        from phase57_rss_raw import select_latest,check_latest_parity
        with tempfile.TemporaryDirectory() as tmp:
            b,c=self.make(tmp);setup(b,c,Path(tmp)/'backup.xlsx');populated(b,c)
            rows=[['2026/09/14','13:00',100,101,99,100,1] for _ in range(135)]
            rows.append(['2026/09/14','14:15',100,101,99,100,2])
            b.Worksheets('ARK_RAW_CHART').Range(scan_range(c['slots'][0])).Value2=tuple(map(tuple,rows))
            _,raw=read_snapshot(b,c)
            chosen,meta=select_latest(raw,c['slots'],120,'2026-09-14')
            normal=normalize(chosen,c['slots'],'2026-09-14')
            self.assertTrue(check_latest_parity(meta,normal));self.assertEqual(meta[0]['rawLastExcelRow'],138)
            self.assertEqual(meta[0]['normalizedLatestSourceTime'],'14:15:00')
            self.assertEqual(len([r for r in normal if r[0]==0]),120)
            self.assertEqual([r[2] for r in normal if r[0]==1],['6758.T'])
    def test_legacy_config_uses_new_scan_and_future_new_config_is_explicit(self):
        from phase57_source_capture import validate_config
        config=config_for('Source.xlsx',['7203.T'])
        self.assertEqual(config['slots'][0]['chart'],'A3:G3002')
        config['slots'][0]['chart']='A3:G122';validate_config(config)
        self.assertEqual(scan_range(config['slots'][0]),'A3:G3002')
        config['slots'][0]['chart']='A3:G9999'
        with self.assertRaises(ValueError):validate_config(config)
    def test_config_bounds(self):
        for symbols in [[],['7203.T']*2,['7203.T"),Other(']]:
            with self.assertRaises(ValueError):layout(symbols)
        with self.assertRaises(ValueError):layout(['7203.T'],3001)

if __name__=='__main__':unittest.main()
