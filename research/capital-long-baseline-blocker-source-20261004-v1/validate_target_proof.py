"""Independent local audit of returned source proof and immutable parent excerpt."""
import argparse
import datetime
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import zipfile


def digest(b):
    return hashlib.sha256(b).hexdigest()


def read_zip(path, name, pin):
    raw = Path(path).read_bytes()
    assert digest(raw) == pin, "ARTIFACT_ZIP_HASH"
    with zipfile.ZipFile(path) as z:
        assert z.namelist() == [name], "ARTIFACT_MEMBERS"
        return z.read(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt-zip", required=True)
    ap.add_argument("--private-zip", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--parent-source", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    scope_bytes = Path(a.scope).read_bytes()
    scope = json.loads(scope_bytes)
    receipt_bytes = read_zip(a.receipt_zip, "SOURCE_PROBE_RECEIPT.json",
        "7c37cb5d571cf660cb11c8846ea7d3b1fb27031337a1ff6433c130b8fd26eda9")
    private_bytes = read_zip(a.private_zip, "TARGET_SOURCE_PROOF_PRIVATE.json",
        "40f9d8ff72d5764d2debc09dd63efba513761ce89d7302d1295411088507ef33")
    receipt, private = json.loads(receipt_bytes), json.loads(private_bytes)
    assert digest(scope_bytes) == receipt["scope_sha256"]
    assert digest(private_bytes) == receipt["private_proof_sha256"]
    assert receipt["archive_sha256"] == scope["encrypted_archive_sha256"]
    assert receipt["wrapper_sha256"] == scope["wrapper_sha256"]
    assert digest(private["date"].encode()) == scope["target_date_sha256"]
    assert digest(private["code"].encode()) == scope["target_code_sha256"]
    aa, bb = private["start_minute"], private["end_minute"]
    begin, end = f"{aa//60:02d}:{aa%60:02d}", f"{bb//60:02d}:{bb%60:02d}"
    assert digest(f'{private["date"]}|{private["code"]}|{begin}|{end}'.encode()) == scope["target_scope_sha256"]
    pages = private["page_receipts"]
    assert [p["page"] for p in pages] == list(range(1, len(pages)+1))
    assert pages[0]["request_cursor_sha256"] is None
    assert pages[-1]["response_cursor_sha256"] is None
    assert [p["response_cursor_sha256"] for p in pages[:-1]] == [
        p["request_cursor_sha256"] for p in pages[1:]]
    assert all(p["response_cursor_sha256"] for p in pages[:-1])
    assert sum(p["rows"] for p in pages) == receipt["all_date_rows"]
    assert len(pages) == receipt["pages"]
    assert len(private["window_rows"]) == receipt["target_window_rows"] == 0
    assert receipt["independent_mismatch"] == 0
    assert receipt["classification"] == "PROVIDER_CONFIRMED_NO_TRADE_TSE_LIT"
    parent_bytes = Path(a.parent_source).read_bytes()
    assert digest(parent_bytes) == "e1503a9947d79acfc39d57be324250027964efeac98f04af67ad8b09e9d240ac"
    parent = json.loads(gzip.decompress(parent_bytes))[private["date"]+"|"+private["code"]]
    check_count = 0
    for neighbor in (private["last_row_before_window"], private["first_row_after_window"]):
        matches = [r for r in parent["current_prefix"] if r["Time"] == neighbor["Time"]]
        assert len(matches) == 1
        old = matches[0]
        for f in ("O", "H", "L", "C", "Vo", "Va"):
            assert Decimal(str(old[f])) == Decimal(str(neighbor[f]))
            check_count += 1
        assert old["_source"]["response_SHA256"] == neighbor["_source"]["response_sha256"]
        assert old["_source"]["wrapper_SHA256"] == neighbor["_source"]["wrapper_sha256"]
        check_count += 2
    result = {"jst": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        "status": "INDEPENDENT_RETURNED_PROOF_AND_PARENT_LINEAGE_PASS",
        "artifact_zip_hash_checks": 2, "scope_private_parent_payload_hash_checks": 3,
        "provider_page_chain_edges_checked": len(pages)-1, "provider_pages": len(pages),
        "all_date_rows_verified_by_page_sum": sum(p["rows"] for p in pages),
        "original_vs_saved_neighbor_numeric_and_lineage_comparisons": check_count,
        "mismatch": 0, "source_window_rows": 0,
        "no_capture_or_adapter_gap_found": True,
        "classification": receipt["classification"],
        "private_proof_sha256": digest(private_bytes),
        "probe_receipt_sha256": digest(receipt_bytes),
        "current_mtm_contract_changed": False, "baseline_replays": 0,
        "provider_requests": 0, "new_market_data": 0, "safety": scope["safety"]}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "INDEPENDENT_SOURCE_AUDIT.json").write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")
    (out / "SOURCE_PROBE_RECEIPT.json").write_bytes(receipt_bytes)
    (out / "TARGET_SOURCE_PROOF_PRIVATE.json").write_bytes(private_bytes)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
