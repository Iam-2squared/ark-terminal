"""Bounded current-access probe: metadata only, never market payloads or URLs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ENDPOINTS = ("/equities/bars/minute", "/equities/bars/daily", "/equities/master")
DATE = "2025-08-01"  # Existing intradayDevelopment; not commonHoldout.
MAX_BODY_BYTES = 5 * 1024 * 1024
REQUEST_INTERVAL = 2.6


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def summarize(status: int, body: bytes) -> dict:
    # Error text may include provider-specific details. It is never emitted.
    result = {"http_status": status, "response_bytes": len(body),
              "response_sha256": hashlib.sha256(body).hexdigest(),
              "listing_schema_valid": False, "file_count": None,
              "listed_size_bytes": None, "current_access": "UNCONFIRMED"}
    if status != 200:
        result["current_access"] = "REJECTED_OR_UNAVAILABLE"
        return result
    try:
        data = json.loads(body)
    except (UnicodeError, ValueError):
        return result
    files = data.get("data") if isinstance(data, dict) else None
    if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
        return result
    # Do not export arbitrary JSON fields, keys, signed URLs, or response text.
    valid = all(isinstance(f.get("Key"), str) and f["Key"] and
                isinstance(f.get("Size"), int) and not isinstance(f["Size"], bool)
                and f["Size"] >= 0 for f in files)
    if not valid:
        return result
    result.update(listing_schema_valid=True, file_count=len(files),
                  listed_size_bytes=sum(f["Size"] for f in files),
                  current_access="METADATA_ACCESS_CONFIRMED" if files else "EMPTY_AMBIGUOUS")
    return result


def probe(key: str, opener=None, pause=time.sleep, clock=time.monotonic) -> dict:
    now = datetime.now(timezone.utc)
    report = {"schema": "ARK_JQUANTS_BOUNDED_CURRENT_ACCESS_V1",
              "utc": now.isoformat(), "jst": now.astimezone(timezone(timedelta(hours=9))).isoformat(),
              "request_date": DATE, "max_provider_requests": len(ENDPOINTS),
              "provider_requests": 0, "raw_downloads": 0, "model_fits": 0,
              "capital_replays": 0, "protected_partitions_opened": 0,
              "contract_changes": 0, "credential_present": bool(key), "results": [],
              "future_entitlement_end": None, "retention_right_verified": False,
              "status": "NO_CREDENTIAL" if not key else "COMPLETED_METADATA_PROBE"}
    if not key:
        return report
    opener = opener or urllib.request.build_opener(NoRedirect())
    last_start = None
    for endpoint in ENDPOINTS:
        if last_start is not None:
            pause(max(0.0, REQUEST_INTERVAL - (clock() - last_start)))
        last_start = clock()
        query = urllib.parse.urlencode({"endpoint": endpoint, "from": DATE, "to": DATE})
        req = urllib.request.Request("https://api.jquants.com/v2/bulk/list?" + query,
                                     headers={"x-api-key": key, "Accept": "application/json"})
        report["provider_requests"] += 1
        result = {"endpoint": endpoint}
        try:
            with opener.open(req, timeout=35) as response:
                body = response.read(MAX_BODY_BYTES + 1)
                if len(body) > MAX_BODY_BYTES:
                    result.update(http_status=response.status, current_access="OVERSIZE_NOT_PARSED")
                else:
                    result.update(summarize(response.status, body))
        except urllib.error.HTTPError as exc:
            result.update(http_status=exc.code, current_access="REJECTED_OR_UNAVAILABLE")
            exc.close()
        except (urllib.error.URLError, OSError, TimeoutError):
            result.update(http_status=None, current_access="TRANSPORT_UNCONFIRMED")
        report["results"].append(result)
        if result.get("http_status") in (401, 403, 429) or result.get("http_status") is None:
            report["status"] = "STOPPED_NO_RETRY"
            break
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe(os.environ.get("JQUANTS_API_KEY", ""))
    # Exclusive create: never overwrite a previous observation.
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
