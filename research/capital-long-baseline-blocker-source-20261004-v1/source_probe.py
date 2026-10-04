"""One hash-pinned existing provider wrapper. No API calls, no market study."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def clock(t):
    h, m = map(int, t.split(":"))
    assert 0 <= h < 24 and 0 <= m < 60
    return h * 60 + m


def interval(day, code, pin):
    for end in range(5, 1440, 5):
        start_s = f"{(end-5)//60:02d}:{(end-5)%60:02d}"
        end_s = f"{end//60:02d}:{end%60:02d}"
        if sha(f"{day}|{code}|{start_s}|{end_s}") == pin:
            return end - 5, end
    raise AssertionError("TARGET_WINDOW_SCOPE_HASH")


def primary(wrapper, scope, day):
    assert sha(day) == scope["target_date_sha256"]
    expected_cursor = None
    keys, target, page_receipts = set(), [], []
    codes = set()
    assert isinstance(wrapper, list) and wrapper
    for index, page in enumerate(wrapper, 1):
        assert page["page"] == index, "PAGE_ORDINAL"
        req = page["request"]
        assert req["endpoint"] == "/v2/equities/bars/minute", "ENDPOINT"
        query = req["params"]
        assert set(query) <= {"date", "pagination_key"}, "NARROWED_SCOPE"
        assert query["date"] == day
        assert query.get("pagination_key") == expected_cursor, "CURSOR_CHAIN"
        text = page["responseText"]
        assert sha(text) == page["responseSha256"], "RESPONSE_HASH"
        body = json.loads(text)
        assert isinstance(body["data"], list)
        for row in body["data"]:
            assert row["Date"] == day, "CROSS_DATE"
            key = (row["Date"], str(row["Code"]), row["Time"])
            assert key not in keys, "DUPLICATE_ROW"
            keys.add(key)
            if sha(str(row["Code"])) == scope["target_code_sha256"]:
                codes.add(str(row["Code"]))
                target.append({**row, "_source": {
                    "response_sha256": page["responseSha256"],
                    "wrapper_sha256": scope["wrapper_sha256"]}})
        acquired = page["acquiredAt"]
        assert datetime.datetime.fromisoformat(acquired).tzinfo is not None
        nxt = body.get("pagination_key") or None
        if index < len(wrapper):
            assert nxt is not None, "EARLY_TERMINAL"
        else:
            assert nxt is None, "INCOMPLETE_PAGINATION"
        page_receipts.append({"page": index, "response_sha256": page["responseSha256"],
            "rows": len(body["data"]), "acquired_at": acquired,
            "request_cursor_sha256": sha(expected_cursor) if expected_cursor else None,
            "response_cursor_sha256": sha(nxt) if nxt else None})
        expected_cursor = nxt
    assert len(codes) == 1, "TARGET_SYMBOL_NOT_REPRESENTED"
    code = next(iter(codes))
    start, end = interval(day, code, scope["target_scope_sha256"])
    rows = sorted(target, key=lambda r: clock(r["Time"]))
    window = [r for r in rows if start <= clock(r["Time"]) < end]
    before = [r for r in rows if clock(r["Time"]) < start]
    after = [r for r in rows if clock(r["Time"]) >= end]
    result = {"classification": "ORIGINAL_VALID_ROWS_RECOVERED" if window else
        "PROVIDER_CONFIRMED_NO_TRADE_TSE_LIT", "pages": len(wrapper),
        "all_date_rows": len(keys), "target_symbol_rows": len(rows),
        "target_window_rows": len(window), "request_scope_complete": True,
        "terminal_pagination_proven": True, "source_row_order_not_relied_on": True}
    private = {"date": day, "code": code, "start_minute": start, "end_minute": end,
        "window_rows": window, "last_row_before_window": before[-1] if before else None,
        "first_row_after_window": after[0] if after else None, "page_receipts": page_receipts,
        "historical_actual_known_at": "UNKNOWN", "bar_end_availability": "EXISTING_RESEARCH_ASSUMPTION"}
    return result, private


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archives", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    scope = json.loads(Path(args.scope).read_bytes())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    archives = list(Path(args.archives).rglob("*.tar.gz.enc"))
    selected = [p for p in archives if file_sha(p) == scope["encrypted_archive_sha256"]]
    assert len(selected) == 1, "PINNED_ARCHIVE_NOT_UNIQUE"
    archive = selected[0]
    proc = subprocess.Popen(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter",
        "200000", "-pass", "env:JQUANTS_API_KEY", "-in", str(archive)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    opened = 0
    raw, day = None, None
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|gz") as tar:
            for member in tar:
                dates = re.findall(r"(?<![0-9])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9])", member.name)
                matches = [d for d in dates if sha(d) == scope["target_date_sha256"]]
                if not member.isfile() or not matches or Path(member.name).name != "minute-pages.json":
                    continue
                opened += 1
                assert opened == 1, "EXTRA_MEMBER_BODY"
                day = matches[0]
                raw = tar.extractfile(member).read()
                assert sha(raw) == scope["wrapper_sha256"], "WRAPPER_HASH"
        assert proc.wait() == 0, "DECRYPT_FAILED"
    finally:
        if proc.poll() is None:
            proc.terminate()
        proc.stdout.close()
    assert opened == 1 and raw is not None
    from independent_probe import independent
    p, private = primary(json.loads(raw), scope, day)
    independent_result = independent(raw, scope, day)
    fields = ("classification", "pages", "all_date_rows", "target_symbol_rows",
              "target_window_rows", "request_scope_complete", "terminal_pagination_proven")
    mismatches = [f for f in fields if p[f] != independent_result[f]]
    assert not mismatches, "INDEPENDENT_MISMATCH"
    private["original_response_sha_present"] = scope["parent_response_sha256"] in {
        x["response_sha256"] for x in private["page_receipts"]}
    assert private["original_response_sha_present"], "PARENT_RESPONSE_LINEAGE"
    private_bytes = (json.dumps(private, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (out / "TARGET_SOURCE_PROOF_PRIVATE.json").write_bytes(private_bytes)
    result = {**p, "jst": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        "status": p["classification"], "scope_sha256": file_sha(Path(args.scope)),
        "archive_sha256": scope["encrypted_archive_sha256"], "wrapper_sha256": sha(raw),
        "source_archive_run": scope["raw_artifact"]["run_id"], "source_artifact_id": scope["raw_artifact"]["artifact_id"],
        "original_capture_script_sha256": scope["original_capture"]["sha256"],
        "independent_fields_compared": len(fields), "independent_mismatch": len(mismatches),
        "member_bodies_opened": opened, "other_or_protected_member_bodies_opened": 0,
        "private_proof_sha256": sha(private_bytes), "private_proof_bytes": len(private_bytes),
        "provider_requests": 0, "new_market_data": 0, "replays": 0, "fits": 0,
        "HTTP_evidence": "SUCCESSFUL_ORIGINAL_CAPTURE_PATH; numerical HTTP status not separately stored",
        "real_time_arrival_certification": False, "price_imputation": 0,
        "mtm_contract_changed": False, "frozen_entry_exit_changed": False,
        "safety": scope["safety"]}
    (out / "SOURCE_PROBE_RECEIPT.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "pages", "target_window_rows", "independent_mismatch",
          "member_bodies_opened", "provider_requests", "private_proof_sha256")}), flush=True)


if __name__ == "__main__":
    main()
