"""JPX公式の東証上場銘柄一覧をDiscovery用JSONへ変換する。"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

import xlrd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "screener-universe.json"
OVERRIDES_PATH = ROOT / "data" / "screener-theme-overrides.json"
JPX_URL = os.environ.get(
    "JPX_UNIVERSE_URL",
    "https://www.jpx.co.jp/markets/statistics-equities/misc/"
    "tvdivq0000001vg2-att/data_j.xls",
)


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def text(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value or "").strip()


def normalize_code(value: Any) -> str:
    code = text(value).upper().replace(" ", "")

    if re.fullmatch(r"\d+\.0", code):
        code = code[:-2]

    return code


def normalize_market(value: Any) -> str | None:
    market = text(value)

    for label in ("プライム", "スタンダード", "グロース"):
        if label in market and "外国" not in market:
            return label

    return None


def header_index(headers: list[str], candidates: tuple[str, ...]) -> int:
    for candidate in candidates:
        for index, header in enumerate(headers):
            if candidate == header or candidate in header:
                return index

    raise ValueError(f"必要な列がありません: {', '.join(candidates)}")


def download_xls() -> bytes:
    request = urllib.request.Request(
        JPX_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ArkTerminal/3.0)",
            "Accept": "application/vnd.ms-excel,*/*",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def parse_universe(content: bytes) -> tuple[list[dict[str, Any]], str | None]:
    workbook = xlrd.open_workbook(file_contents=content)
    sheet = workbook.sheet_by_index(0)
    headers = [text(value) for value in sheet.row_values(0)]
    date_column = header_index(headers, ("日付", "基準日"))
    code_column = header_index(headers, ("コード",))
    name_column = header_index(headers, ("銘柄名", "会社名"))
    market_column = header_index(headers, ("市場・商品区分", "市場区分"))
    sector_column = header_index(headers, ("33業種区分", "業種区分"))
    overrides = load_json(OVERRIDES_PATH, {})
    current_payload = load_json(OUTPUT_PATH, {})
    current_entries = current_payload.get("entries", [])
    existing = {
        str(entry.get("code")): entry
        for entry in current_entries
        if entry.get("code")
    }
    entries: list[dict[str, Any]] = []
    source_date: str | None = None

    for row_index in range(1, sheet.nrows):
        row = sheet.row_values(row_index)
        code = normalize_code(row[code_column])
        market = normalize_market(row[market_column])

        if not market or not re.fullmatch(r"(?:\d{4}|\d{3}[A-Z])", code):
            continue

        name = text(row[name_column])
        sector = text(row[sector_column]) or "未分類"
        source_date = source_date or text(row[date_column]) or None
        previous = existing.get(code, {})
        themes = overrides.get(code, previous.get("themes", []))

        entries.append(
            {
                "code": code,
                "symbol": f"{code}.T",
                "name": name,
                "market": market,
                "sector": sector,
                "themes": list(dict.fromkeys(themes)),
                "lotSize": int(previous.get("lotSize") or 100),
                "marketCap": previous.get("marketCap"),
            }
        )

    entries.sort(key=lambda entry: entry["code"])

    if len(entries) < 3000:
        raise ValueError(
            f"JPX一覧の解析結果が{len(entries)}件しかないため、既存ファイルを保護しました。"
        )

    return entries, source_date


def main() -> None:
    entries, source_date = parse_universe(download_xls())
    payload = {
        "meta": {
            "mode": "jpx-official",
            "source": JPX_URL,
            "sourceDate": source_date,
            "updatedAt": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "count": len(entries),
            "scope": "東証プライム・スタンダード・グロースの内国上場銘柄",
            "lotSizeMethod": "既存上書き値または100株。正確な売買単位データ接続時に置換可能",
        },
        "entries": entries,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"JPX universe: {len(entries)} issues")


if __name__ == "__main__":
    main()
