#!/usr/bin/env python3
"""Mode A CLI. All external numeric/fit/label commands fail before raw open."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[key]="1"
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))  # V2 namespace only; no V1 module imports.
from ark_selector_v2.admission import metadata_audit,validate_approval,ApprovalPins,Mode
from ark_selector_v2.artifact_io import exclusive_json
from ark_selector_v2.exact_math import V2Error


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    meta=sub.add_parser("metadata-audit");meta.add_argument("--request",required=True);meta.add_argument("--output")
    synth=sub.add_parser("synthetic-test");synth.add_argument("--output",required=True)
    audit=sub.add_parser("public-audit");audit.add_argument("--base",default="4b02c4eb6fed0b75bfc7a6e8afc49d7868696159")
    for name in ("census","train","calibrate","predict","evaluate","restore-verify"):
        cmd=sub.add_parser(name)
        cmd.add_argument("--request",required=True,help="metadata-only execution request; cannot create owner authority")
    args=parser.parse_args(argv)
    try:
        if args.command=="synthetic-test":
            from ark_selector_v2.synthetic import run_synthetic
            result=run_synthetic(Path(args.output).resolve())
        elif args.command=="metadata-audit":
            result=metadata_audit(json.loads(Path(args.request).read_text(encoding="utf8")))
            if args.output:exclusive_json(Path(args.output),result)
        elif args.command=="public-audit":
            from protection_audit import audit_repo
            result=audit_repo(ROOT.parents[1],args.base)
        else:
            # No request/raw/model/label file is opened in Mode A, including a
            # request claiming approved=true. Pins require an owner-controlled
            # channel and exact role bindings, none of which exists this turn.
            raise V2Error("AWAITING_MARKET_APPROVAL:MODE_A_EXTERNAL_NUMERIC_COMMAND_DISABLED")
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,allow_nan=False))
        return 0
    except (V2Error,FileExistsError) as e:
        print(json.dumps({"status":"BLOCKED","reason":str(e),"market_numeric_reads":0,"market_fits":0,"executionAllowed":False},ensure_ascii=False))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
