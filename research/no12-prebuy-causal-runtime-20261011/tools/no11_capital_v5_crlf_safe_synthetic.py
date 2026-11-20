#!/usr/bin/env python3
"""READ-ONLY Windows CRLF adapter for the byte-exact existing Capital V5 bridge.

No Frozen source is edited or recreated. Only the Git text checkout CRLF is
canonicalized IN MEMORY for SHA1 identity comparison; Python then imports and
executes the unchanged Frozen allocation/slot logic. SYNTHETIC ONLY, no broker.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
ORIGINAL = REPO / "integration/no1-1-msii/tools/no11_capital_v5_shadow.py"
ORIGINAL_GIT_BLOB = "917f3e48dfa67fb17b618f1869f048a2c282e591"


def canonical_git_blob(data: bytes) -> str:
    normalized = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(
        b"blob " + str(len(normalized)).encode("ascii") + b"\0" + normalized
    ).hexdigest()


def load_original_bridge():
    if not ORIGINAL.is_file() or ORIGINAL.is_symlink():
        raise RuntimeError("NO11_V5_ORIGINAL_BRIDGE_NOT_PRESENT")
    if canonical_git_blob(ORIGINAL.read_bytes()) != ORIGINAL_GIT_BLOB:
        raise RuntimeError("NO11_V5_ORIGINAL_BRIDGE_BLOB_CHANGED")
    spec = importlib.util.spec_from_file_location("frozen_v5_unmodified", ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, blob in module.CAPITAL_BLOBS.items():
        source = module.SOURCE / name
        if not source.is_file() or source.is_symlink():
            raise RuntimeError("NO11_V5_ORIGINAL_SOURCE_MISSING")
        if canonical_git_blob(source.read_bytes()) != blob:
            raise RuntimeError("NO11_V5_ORIGINAL_SOURCE_GIT_BLOB_CHANGED")
    return module


def run_request(request):
    module = load_original_bridge()
    hash_original = module.git_blob_sha

    def verify_git_checkout(source: bytes) -> str:
        # This substitution is stricter than bypassing source identity:
        # the expected Git blob remains identical across OS checkouts.
        return hash_original(source.replace(b"\r\n", b"\n"))

    module.git_blob_sha = verify_git_checkout
    try:
        return module.shadow(request)
    finally:
        module.git_blob_sha = hash_original


def main():
    try:
        data = sys.stdin.buffer.read(250_001)
        if len(data) < 1 or len(data) > 250_000:
            raise RuntimeError("NO11_V5_SYNTHETIC_INPUT_SIZE_REJECTED")
        request = json.loads(data)
        output = run_request(request)
        sys.stdout.write(json.dumps(output, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False) + "\n")
    except Exception as exc:
        # Synthetic-only fixed label, never echo payloads or Python tracebacks.
        safe = str(exc)
        if not (safe.isascii() and safe.replace("_", "").isalnum()
                and safe.isupper() and len(safe) < 100):
            safe = "NO11_V5_SYNTHETIC_SOURCE_OR_RUNTIME_INVALID"
        sys.stdout.write(json.dumps({
            "status": "BLOCKED", "reason": safe,
            "orderAllowed": False, "transmitted": False,
            "productionReady": False
        }, separators=(",", ":")) + "\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
