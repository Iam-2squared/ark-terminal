"""Synthetic JPX month-end workbook reference tests, completely offline."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import no11_jpx_monthly_equity_reference as jpx


def xml_text(s):
    return escape(str(s), {'"':'&quot;'})


def write_fake_xlsx(file, items, *, date=jpx.DATE, inject_macro=False):
    rows=[jpx.HEADERS]
    for code,category in items:
        rows.append((date,code,"合成テスト銘柄",category,
                     "3650","電気機器","11","電機・精密","7","TOPIX Small 2"))
    # Exercise native OOXML inline strings without involving openpyxl/Excel.
    body=['<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for n,row in enumerate(rows,1):
        body.append(f'<row r="{n}">')
        for col,txt in enumerate(row):
            letter=chr(65+col)
            body.append(f'<c r="{letter}{n}" t="inlineStr"><is><t>{xml_text(txt)}</t></is></c>')
        body.append('</row>')
    body.append('</sheetData></worksheet>')
    with ZipFile(file,"w",compression=ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml",
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')
        z.writestr("xl/worksheets/sheet1.xml","".join(body))
        z.writestr("[Content_Types].xml",
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        if inject_macro:
            z.writestr("xl/vbaProject.bin",b"test")
    return file


def write_audit(file,excluded,unresolved,provisional):
    obj={
        "schemaId":jpx.AUDIT,
        "status":"PROVISIONAL_REVIEW_REQUIRED_NOT_A_TRADING_PLAN",
        "sessionDate":jpx.SESSION, "previousSession":"2026-10-29",
        "originalG1PassCount":78, "provisionalSelectedCount":47,
        "permitsBuy":False, "actualCommonEquityIndependentlyReviewed":False,
        "executableChartPlanProduced":False,"orderTransmission":False,
        "knownExcludedFromG1":excluded,
        "unknownEligibilitySymbols":unresolved,
        "provisionalSelectedAfterKnownExclusions":provisional,
    }
    file.write_text(json.dumps(obj,ensure_ascii=False)+"\n",encoding="utf-8")
    return file


class JPXMonthlyReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="no11-monthend-")
        self.folder=Path(self.temp.name)
        self.audit=self.folder/"equity-audit.json"
        self.workbook=self.folder/"data_j.xlsx"
        self.excluded=sorted(jpx.EXPECTED_EXCLUDED)
        self.unresolved=[f"{9000+i}.T" for i in range(73)]
        self.provisional=self.unresolved[:47]
        write_audit(self.audit,self.excluded,self.unresolved,self.provisional)
        present=list(self.excluded)+self.unresolved[0:1]+self.unresolved[2:]
        filler=[f"{5000+i}" for i in range(3100)]
        items=[(code[:-2],"ETF・ETN" if code in self.excluded or code==self.unresolved[0]
                else "プライム（内国株式）") for code in present]
        items.extend((code,"スタンダード（内国株式）") for code in filler)
        write_fake_xlsx(self.workbook,items)

    def tearDown(self):
        self.temp.cleanup()

    def test_only_historical_category_reference_no_live_certification(self):
        result,receipt=jpx.verify(self.audit,self.workbook,self.folder)
        self.assertEqual(result["g1ExaminedCount"],78)
        self.assertEqual(result["jpxMonthEndDate"],"2026-09-30")
        self.assertEqual(result["categories"],{
            "DOMESTIC_EQUITY_MONTH_END_REFERENCE":71,
            "NON_EQUITY_MONTH_END_REFERENCE":6,
            "ABSENT_IN_MONTH_END_REFERENCE":1
        })
        self.assertFalse(result["ordinarySharesOnSessionCertified"])
        self.assertFalse(result["corporateActionsOnSessionCleared"])
        self.assertFalse(result["priceBasisVerified"])
        self.assertFalse(result["chart50ExecutablePlanCreated"])
        self.assertFalse(result["allowTrading"])
        self.assertFalse(result["orderTransmission"])
        self.assertEqual(sum(r["inProvisionalChart"] for r in result["rows"]),47)
        self.assertEqual(receipt.read_bytes(),
                         (json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n").encode())
        second,other=jpx.verify(self.audit,self.workbook,self.folder)
        self.assertEqual(result,second)
        self.assertEqual(receipt,other)

    def test_month_end_date_and_zip_macro_guard_fail_closed(self):
        files,_=jpx.from_zip(self.workbook)
        self.assertGreater(len(files),3000)
        new=self.folder/"wrong-month.xlsx"
        with ZipFile(self.workbook) as z, ZipFile(new,"w") as out:
            for item in z.infolist():
                data=z.read(item.filename)
                if item.filename=="xl/worksheets/sheet1.xml":
                    data=data.replace(b"20260930",b"20260831")
                out.writestr(item.filename,data)
        with self.assertRaisesRegex(ValueError,"MONTH_END_DATE_NOT_20260930"):
            jpx.verify(self.audit,new,self.folder)
        bad=self.folder/"macro.xlsx"
        with ZipFile(self.workbook) as z, ZipFile(bad,"w") as out:
            for item in z.infolist():
                out.writestr(item.filename,z.read(item.filename))
            out.writestr("xl/vbaProject.bin",b"test")
        with self.assertRaisesRegex(ValueError,"XLSX_EXTERNAL_OR_MACRO"):
            jpx.verify(self.audit,bad,self.folder)

    def test_audit_admission_fail_closed_and_original_source_unchanged(self):
        before=hashlib.sha256(self.audit.read_bytes()).hexdigest()
        obj=json.loads(self.audit.read_text())
        obj["actualCommonEquityIndependentlyReviewed"]=True
        self.audit.write_text(json.dumps(obj)+"\n")
        with self.assertRaisesRegex(ValueError,"G1_AUDIT_CONTRACT"):
            jpx.verify(self.audit,self.workbook,self.folder)
        self.assertNotEqual(before,hashlib.sha256(self.audit.read_bytes()).hexdigest())

    def test_no_rss_excel_order_or_network_calls(self):
        source=(TOOLS/"no11_jpx_monthly_equity_reference.py").read_text()
        for forbidden in ("RssStockOrder(","Workbooks.Add","Invoke-WebRequest",
                          "urllib.request","requests.get","fetch(","subprocess.run"):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
