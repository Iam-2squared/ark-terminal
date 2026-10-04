"""Independent raw bytes / page-chain audit; does not import primary probe."""
import hashlib
import json


def independent(raw, scope, day):
    assert hashlib.sha256(raw).hexdigest() == scope["wrapper_sha256"]
    pages = json.loads(raw)
    assert isinstance(pages, list) and pages
    queries, cursors, keys, rows = [], [], [], []
    for page in reversed(pages):
        assert hashlib.sha256(page["responseText"].encode()).hexdigest() == page["responseSha256"]
        request = page["request"]
        assert request["endpoint"] == "/v2/equities/bars/minute"
        q = request["params"]
        assert set(q) <= {"date", "pagination_key"} and q["date"] == day
        body = json.loads(page["responseText"])
        assert isinstance(body["data"], list)
        keys.append(page["page"])
        queries.append(q.get("pagination_key"))
        cursors.append(body.get("pagination_key") or None)
        rows.extend(body["data"])
    keys.reverse()
    queries.reverse()
    cursors.reverse()
    assert keys == list(range(1, len(pages)+1))
    assert queries[0] is None and cursors[-1] is None
    assert queries[1:] == cursors[:-1]
    assert all(cursors[i] is not None for i in range(len(cursors)-1))
    assert len(set(c for c in cursors if c)) == len(cursors)-1
    assert all(r["Date"] == day for r in rows)
    triples = sorted((r["Date"], str(r["Code"]), r["Time"]) for r in rows)
    assert len(triples) == len(set(triples))
    symbol_rows = [r for r in rows if hashlib.sha256(str(r["Code"]).encode()).hexdigest() == scope["target_code_sha256"]]
    symbols = {str(r["Code"]) for r in symbol_rows}
    assert len(symbols) == 1
    symbol = next(iter(symbols))
    intervals = []
    for h in range(24):
        for m in range(0, 60, 5):
            start = h*60+m
            if start+5 >= 1440:
                continue
            s = f"{start//60:02d}:{start%60:02d}"
            e = f"{(start+5)//60:02d}:{(start+5)%60:02d}"
            if hashlib.sha256(f"{day}|{symbol}|{s}|{e}".encode()).hexdigest() == scope["target_scope_sha256"]:
                intervals.append((start, start+5))
    assert len(intervals) == 1
    a, b = intervals[0]
    n = 0
    for row in symbol_rows:
        parts = row["Time"].split(":")
        t = int(parts[0])*60+int(parts[1])
        n += int(a <= t < b)
    return {"classification": "ORIGINAL_VALID_ROWS_RECOVERED" if n else "PROVIDER_CONFIRMED_NO_TRADE_TSE_LIT",
        "pages": len(pages), "all_date_rows": len(triples), "target_symbol_rows": len(symbol_rows),
        "target_window_rows": n, "request_scope_complete": True, "terminal_pagination_proven": True}
