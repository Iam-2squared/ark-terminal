"""Generated-fixture worker. Cannot install an owner channel or market rights."""
from __future__ import annotations
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ark_selector_v2.artifact_io import sha_file
from ark_selector_v2.monthly_fixture import isolated_channel
from ark_selector_v2.exact_math import V2Error
import v2_cli


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True); parser.add_argument("--config-pin", required=True)
    parser.add_argument("--stage", required=True, choices=["census", "train", "calibrate", "predict", "evaluate", "restore-verify"])
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    path = Path(args.config)
    if sha_file(path)[0] != args.config_pin: raise V2Error("TEST_SUPERVISOR_CONFIG_PIN_DRIFT")
    authority = isolated_channel(json.loads(path.read_text()))
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        code = v2_cli.main([args.stage, "--request", args.request], authority=authority)
    print(json.dumps({"isolated_worker_pid": os.getpid(), "result": json.loads(capture.getvalue())}, allow_nan=False))
    return code


if __name__ == "__main__": raise SystemExit(main())
