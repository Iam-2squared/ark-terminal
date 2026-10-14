"""Private source-ingest canary, deliberately not a Selector measurement.

Uses the same source authority/hash/session gates as the native builder. Does
not build snapshots, fit, calibrate, rank or open a Report label descriptor.
"""
import argparse
import json
import time
from pathlib import Path

from preopen_io import private_path, write_json, utc_now, SAFE_FLAGS
from preopen_native_source import NativeStore
from preopen_selector import PreopenError, digest


def run_source_canary(request, output):
    root=Path(request["privateRoot"]).resolve()
    output=private_path(output,root)
    if output.exists():
        raise PreopenError("REFUSE_OVERWRITE_SOURCE_CANARY")
    start=time.perf_counter()
    store=NativeStore(output/"native_shards",private_root=root,request=request)
    try:
        receipts=[store.ingest(s) for s in request["sources"]]
        n=store.connection.execute("SELECT count(*) FROM records").fetchone()[0]
        result={"schema":"ARK_PREOPEN_REAL_SOURCE_CANARY_ONLY_V1",
                "completedAt":utc_now(),"requestHash":digest(request),
                "sourceReceipts":receipts,"admittedRecords":n,
                "elapsedSeconds":time.perf_counter()-start,
                "measurementScope":"SOURCE_INGEST_ONLY_NOT_NATIVE_SCALE",
                "featureRowsBuilt":0,"marketHeadFits":0,"marketCalibrationFits":0,
                "watchlistsGenerated":0,"reportLabelEvaluationOpened":False,
                "marketMeasurementComplete":False,"fullCandidateSourceCoverage":False,
                "classification":"PRIVATE",**SAFE_FLAGS}
        write_json(output/"SOURCE_CANARY_RECEIPT_PRIVATE.json",result)
        return result
    finally:
        store.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args();request=json.loads(Path(a.request).read_text())
    result=run_source_canary(request,Path(a.output))
    print(json.dumps({k:result[k] for k in ("measurementScope","admittedRecords",
        "featureRowsBuilt","marketHeadFits","marketMeasurementComplete")},sort_keys=True))


if __name__ == "__main__":
    main()
