"""Package only target proof and this append-only cycle; no broad market export."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--proof", required=True)
    p.add_argument("--docs", required=True)
    p.add_argument("--code", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--closure-head", required=True)
    a = p.parse_args()
    proof_dir = Path(a.proof)
    private = json.loads((proof_dir / "TARGET_SOURCE_PROOF_PRIVATE.json").read_bytes())
    receipt = json.loads((proof_dir / "SOURCE_PROBE_RECEIPT.json").read_bytes())
    assert sha((proof_dir / "TARGET_SOURCE_PROOF_PRIVATE.json").read_bytes()) == receipt["private_proof_sha256"]
    assert receipt["target_window_rows"] == 0
    assert receipt["classification"] == "PROVIDER_CONFIRMED_NO_TRADE_TSE_LIT"
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    assert not out.exists(), "APPEND_ONLY_PACKAGE_ALREADY_EXISTS"
    members = {}
    for base, label in [(Path(a.docs), "public_cycle"), (Path(a.code), "source_probe_code")]:
        for f in sorted(base.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                members[label + "/" + str(f.relative_to(base))] = f.read_bytes()
    for name in ("TARGET_SOURCE_PROOF_PRIVATE.json", "SOURCE_PROBE_RECEIPT.json", "INDEPENDENT_SOURCE_AUDIT.json"):
        members["PRIVATE_SOURCE/" + name] = (proof_dir / name).read_bytes()
    before = private["last_row_before_window"]
    after = private["first_row_after_window"]
    aa, bb = private["start_minute"], private["end_minute"]
    note = (
        "# Private single-window source finding\n\n"
        f"Target: {private['date']} / Code {private['code']} / "
        f"[{aa//60:02d}:{aa%60:02d},{bb//60:02d}:{bb%60:02d})\n"
        f"Original provider pages: {receipt['pages']}; window rows: 0.\n"
        f"Prior traded minute: {before['Time']}, raw Close {before['C']}; "
        f"next minute: {after['Time']}, raw Close {after['C']}.\n"
        "Next minute is outside valuation window and is not used for MTM.\n"
        "Prior Close is evidence only; no last-traded-price contract has been implemented.\n"
        "Historical actual arrival UNKNOWN. No all-venue/no-halt certificate.\n"
        f"Source result Git closure head: {a.closure_head}\n"
        "No provider request, new data, fit, replay, order or MTM change.\n"
        "Existing parent evidence remains immutable.\n"
    )
    members["PRIVATE_TARGET_NOTE.md"] = note.encode()
    manifest = {"jst": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        "status": "PRIVATE_SINGLE_TARGET_SOURCE_PROOF", "closure_head": a.closure_head,
        "classification": receipt["classification"],
        "source_member_bodies_opened": 1, "source_rows_in_window": 0,
        "private_target_proof_sha256": receipt["private_proof_sha256"],
        "members": [{"path": k, "bytes": len(v), "sha256": sha(v)} for k, v in sorted(members.items())]}
    members["MANIFEST_PRIVATE.json"] = (json.dumps(manifest, sort_keys=True, indent=2)+"\n").encode()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, content in sorted(members.items()):
            z.writestr(name, content)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == set(members)
        for name, b in members.items():
            assert z.read(name) == b
    print(json.dumps({"path": str(out.resolve()), "bytes": out.stat().st_size,
        "sha256": sha(out.read_bytes()), "members": len(members), "closure_head": a.closure_head}))


if __name__ == "__main__":
    main()
