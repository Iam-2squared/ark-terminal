#!/usr/bin/env python3
"""Read-only JPX *month-end* product-class reference for No.1.1 G1 candidates.

Accepts a locally downloaded, genuine-format JPX data_j.xlsx (no openpyxl or
Excel required). Completes only historical month-end product classification
reference, NEVER independent same-day commonEquity/corporate-action/price-basis
certification or an executable Chart50 plan.

JPX lists month-end listed issues; this is NOT an as-of-session master.
Source publication: https://www.jpx.co.jp/markets/statistics-equities/misc/01.html
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

SCHEMA = "ARK_NO11_JPX_MONTH_END_EQUITY_REFERENCE_V1"
AUDIT = "ARK_NO11_PROVISIONAL_EQUITY_TYPE_PRESCREEN_V1"
REPORT = "NO11_JPX_EQUITY_REFERENCE_"
DATE = "20260930"  # Latest September month-end evidence for 2026-10-30.
SESSION = "2026-10-30"
EXPECTED_EXCLUDED = frozenset({"1671.T","1690.T","1699.T","2014.T","2038.T"})
HEADERS = ("日付","コード","銘柄名","市場・商品区分","33業種コード",
           "33業種区分","17業種コード","17業種区分","規模コード","規模区分")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CELL = re.compile(r"^([A-Z]{1,3})([0-9]{1,7})$")
SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")


def need(ok, reason):
    if not ok:
        raise ValueError(REPORT + reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_json(p, limit=500_000):
    path=Path(p).resolve(strict=True)
    need(path.is_file() and not path.is_symlink() and
         0 < path.stat().st_size <= limit, "JSON_PATH_OR_SIZE")
    raw=path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), digest(raw)


def utf8_cell(c, shared):
    t=c.get("t","")
    if t=="s":
        element=c.find(NS+"v")
        need(element is not None and element.text is not None, "SHARED_INDEX")
        idx=int(element.text)
        need(0 <= idx < len(shared), "SHARED_INDEX_RANGE")
        return shared[idx]
    if t=="inlineStr":
        return "".join((t.text or "") for t in c.iter(NS+"t"))
    need(t in ("","n","str"), "CELL_KIND_UNEXPECTED")
    v=c.find(NS+"v")
    return (v.text if v is not None and v.text is not None else "")


def from_zip(p):
    file=Path(p).resolve(strict=True)
    need(file.is_file() and not file.is_symlink() and file.suffix.lower()==".xlsx" and
         0 < file.stat().st_size <= 15_000_000, "XLSX_PATH_OR_SIZE")
    raw=file.read_bytes()
    need(raw[:4]==b"PK\x03\x04", "XLSX_NOT_ZIP")
    with ZipFile(file,"r") as z:
        infos=z.infolist()
        need(3 <= len(infos) <= 300 and
             sum(i.file_size for i in infos) <= 50_000_000 and
             all(i.file_size <= 20_000_000 for i in infos), "XLSX_ZIP_LIMITS")
        names={i.filename for i in infos}
        need(all(not n.startswith("/") and ".." not in n.split("/")
                 and "\\" not in n for n in names), "XLSX_UNSAFE_ENTRY")
        need(not any("vba" in n.lower() or "externallinks/" in n.lower()
                     or "embeddings/" in n.lower() for n in names), "XLSX_EXTERNAL_OR_MACRO")
        need("xl/worksheets/sheet1.xml" in names and
             "xl/workbook.xml" in names, "XLSX_MAIN_SHEET_MISSING")
        shared=[]
        if "xl/sharedStrings.xml" in names:
            tree=ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared=["".join((t.text or "") for t in si.iter(NS+"t"))
                    for si in tree.findall(NS+"si")]
            need(len(shared) <= 100_000, "SHARED_STRINGS_LIMIT")
        sheet=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows=[]
    sheet_data=sheet.find(NS+"sheetData")
    need(sheet_data is not None, "XLSX_ROWS_MISSING")
    for r in sheet_data.findall(NS+"row"):
        if len(rows) >= 7000:
            raise ValueError(REPORT + "TOO_MANY_ROWS")
        cells={}
        for c in r.findall(NS+"c"):
            ref=c.get("r","")
            match=CELL.fullmatch(ref)
            need(match is not None, "XLSX_CELL_ADDRESS")
            letters=match.group(1)
            column=0
            for ch in letters:
                column=column*26+(ord(ch)-64)
            need(column<=50, "XLSX_COLUMN_LIMIT")
            if column <= 10:
                need(column not in cells, "XLSX_DUPLICATE_CELL")
                cells[column]=utf8_cell(c,shared)
        if cells:
            rows.append([cells.get(i,"") for i in range(1,11)])
    need(len(rows)>=1000, "XLSX_TOO_FEW_LISTINGS")
    header_i=next((i for i,row in enumerate(rows[:10])
                   if tuple(row)==HEADERS), None)
    need(header_i is not None, "XLSX_JPX_HEADER_MISMATCH")
    securities={}
    date_seen=set()
    for row in rows[header_i+1:]:
        raw_date,code,name,category,s33,sector,s17,sector17,scale,scale_name=row
        if not code and not raw_date:
            continue
        need(raw_date==DATE, "MONTH_END_DATE_NOT_20260930")
        date_seen.add(raw_date)
        need(re.fullmatch(r"[0-9A-Z]{4,5}",code) is not None
             and len(name)>0 and len(category)>0,"SECURITY_ROW_INVALID")
        # JPX has five-character special share-class codes. They are never
        # automatically collapsed into four-character ordinary equity codes.
        if len(code)!=4:
            continue
        symbol=code+".T"
        need(symbol not in securities,"SECURITY_DUPLICATE_CODE")
        normalized=unicodedata.normalize("NFKC",category).replace(" ","")
        domestic=normalized in (
            "プライム(内国株式)", "スタンダード(内国株式)", "グロース(内国株式)")
        segment=({"プライム(内国株式)":"PRIME",
                  "スタンダード(内国株式)":"STANDARD",
                  "グロース(内国株式)":"GROWTH"}).get(normalized)
        securities[symbol]={
            "listedNameAtMonthEnd":name, "jpxMonthEndCategory":category,
            "jpxMonthEndDomesticEquityCategory":domestic,
            "jpxMonthEndSegment":segment,
            "jpxMonthEndSector33":sector if domestic else None,
        }
    need(date_seen=={DATE} and len(securities)>3000,
         "XLSX_SOURCE_DATE_OR_LISTING_COUNT")
    return securities,digest(raw),len(securities)


def verify(audit_file,jpx_file,output_root):
    a,audit_sha=load_json(audit_file)
    need(type(a) is dict and a.get("schemaId")==AUDIT and
         a.get("status")=="PROVISIONAL_REVIEW_REQUIRED_NOT_A_TRADING_PLAN" and
         a.get("sessionDate")==SESSION and a.get("previousSession")=="2026-10-29" and
         a.get("originalG1PassCount")==78 and
         a.get("provisionalSelectedCount")==47 and
         a.get("permitsBuy") is False and
         a.get("actualCommonEquityIndependentlyReviewed") is False and
         a.get("executableChartPlanProduced") is False and
         a.get("orderTransmission") is False, "G1_AUDIT_CONTRACT")
    excluded=a.get("knownExcludedFromG1")
    unresolved=a.get("unknownEligibilitySymbols")
    need(type(excluded) is list and set(excluded)==EXPECTED_EXCLUDED and
         len(excluded)==5 and type(unresolved) is list and len(unresolved)==73 and
         len(set(unresolved))==73 and
         all(type(c) is str and SYMBOL.fullmatch(c) for c in unresolved) and
         not set(unresolved).intersection(excluded), "G1_SCOPE")
    selected=a.get("provisionalSelectedAfterKnownExclusions")
    need(type(selected) is list and len(selected)==47 and
         len(set(selected))==47 and set(selected).issubset(set(unresolved)),
         "PROVISIONAL_SELECTED_SCOPE")
    stock,jpx_sha,listed=from_zip(jpx_file)
    rows=[]
    categories={"DOMESTIC_EQUITY_MONTH_END_REFERENCE":0,
                "NON_EQUITY_MONTH_END_REFERENCE":0,
                "ABSENT_IN_MONTH_END_REFERENCE":0}
    for symbol in [*excluded,*unresolved]:
        ref=stock.get(symbol)
        if ref is None:
            status="ABSENT_IN_MONTH_END_REFERENCE"
        elif ref["jpxMonthEndDomesticEquityCategory"]:
            status="DOMESTIC_EQUITY_MONTH_END_REFERENCE"
        else:
            status="NON_EQUITY_MONTH_END_REFERENCE"
        categories[status]+=1
        if symbol in excluded:
            need(status!="DOMESTIC_EQUITY_MONTH_END_REFERENCE",
                 "KNOWN_ETF_ETN_CONFLICT_WITH_JPX")
        rows.append({"symbol":symbol,"baselineStatus":status,
                    "originalJpxRecord":ref,
                    "inProvisionalChart":symbol in selected,
                    "independentSameDayCommonEquityReviewed":False,
                    "independentCorporateActionsCleared":False,
                    "independentPriceBasisVerified":False,
                    "notAnOrderAuthorization":True})
    report={"schemaId":SCHEMA,"sessionDate":SESSION,
            "jpxMonthEndDate":"2026-09-30",
            "jpxWorkbookSha256":jpx_sha,
            "sourceJpxPage":"https://www.jpx.co.jp/markets/statistics-equities/misc/01.html",
            "sourceAuditSha256":audit_sha,"jpxRowsRead":listed,
            "g1ExaminedCount":len(rows),"categories":categories,"rows":rows,
            "ordinarySharesOnSessionCertified":False,
            "corporateActionsOnSessionCleared":False,
            "priceBasisVerified":False,"datedMasterCreated":False,
            "chart50ExecutablePlanCreated":False,"allowTrading":False,
            "productionReady":False,"orderTransmission":False}
    output=Path(output_root).resolve(strict=True)
    need(output.is_dir() and not output.is_symlink(),
         "PRIVATE_OUTPUT_ROOT_MISSING")
    raw=(json.dumps(report,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
    target=output/("jpx-monthly-equity-reference-"+digest(raw)+".json")
    need(not target.is_symlink(),"OUTPUT_SYMLINK")
    if target.exists():
        need(target.read_bytes()==raw,"PREVIOUS_OUTPUT_CHANGED")
    else:
        with target.open("xb") as f:
            f.write(raw)
    return report,target


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("audit","jpx-xlsx","output"):
        p.add_argument("--"+field,required=True,type=Path)
    args=p.parse_args(argv)
    result,receipt=verify(args.audit,args.jpx_xlsx,args.output)
    print("NO11_JPX_MONTH_END_REFERENCE=PASS_SOURCE_ONLY")
    print("NO11_JPX_MONTH_END_DATE="+result["jpxMonthEndDate"])
    print("NO11_JPX_G1_EXAMINED="+str(result["g1ExaminedCount"]))
    for k,n in result["categories"].items():
        print("NO11_JPX_"+k+"="+str(n))
    print("NO11_JPX_MONTH_END_RECEIPT="+str(receipt))
    print("NO11_JPX_SAME_DAY_EQUITY_REVIEW=NOT_CERTIFIED")
    print("NO11_JPX_PRICE_BASIS_REVIEW=NOT_CERTIFIED")
    print("EXCEL_TOUCHED=False")
    print("ORDER_TRANSMISSION=False")


if __name__=="__main__":
    try:
        main()
    except (ValueError,OSError,TypeError,KeyError,IndexError,BadZipFile,ET.ParseError) as e:
        msg=str(e)
        safe=msg if re.fullmatch(r"NO11_JPX_EQUITY_REFERENCE_[A-Z0-9_]+",msg) else REPORT+"SOURCE_OR_FORMAT_INVALID"
        print("NO11_JPX_MONTH_END_REFERENCE=BLOCKED|"+safe)
        print("EXCEL_TOUCHED=False")
        print("ORDER_TRANSMISSION=False")
        sys.exit(2)
