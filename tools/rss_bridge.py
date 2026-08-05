from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pythoncom
import win32com.client

app = FastAPI(title="Ark Terminal RSS Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

SYMBOLS: dict[str, str] = {
    "4755.T": "A1",
    "9432.T": "A2",
    "7203.T": "A3",
    "9984.T": "A4",
}


def read_price_from_excel(cell: str) -> float:
    pythoncom.CoInitialize()
    try:
        excel = win32com.client.GetActiveObject("Excel.Application")
        workbook = excel.ActiveWorkbook
        if workbook is None:
            raise RuntimeError("Excelでブックが開かれていません。")

        sheet = workbook.Worksheets("Sheet1")
        value = sheet.Range(cell).Value

        if value is None:
            raise RuntimeError("価格を取得できません。")

        return float(value)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "ExcelまたはMARKETSPEED II RSSに接続できません。"
        ) from exc
    finally:
        pythoncom.CoUninitialize()


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "mode": "read_only",
        "order_creation": False,
        "order_transmission": False,
    }


@app.get("/price/{symbol}")
def get_price(symbol: str) -> dict[str, object]:
    normalized = symbol.upper()

    if normalized not in SYMBOLS:
        raise HTTPException(status_code=404, detail="未登録の銘柄です。")

    try:
        value = read_price_from_excel(SYMBOLS[normalized])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "symbol": normalized,
        "price": value,
        "source": "MARKETSPEED II RSS",
        "read_only": True,
        "order_transmission": False,
    }
