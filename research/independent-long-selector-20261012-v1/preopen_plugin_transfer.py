"""Materialize exact original bytes returned by the sanctioned GitHub plugin.

Private only. This is not a downloader or a binary workaround. It accepts
UTF-8 text or the plugin's supported small-file base64 response only when the
decoded original bytes match a pinned storage receipt. Release downloads and
empty large-file responses are not supported or promoted to success.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path

from preopen_io import private_path, sha_file, write_json, SAFE_FLAGS, utc_now
from preopen_selector import PreopenError
from preopen_reuse_authorization import REPOSITORIES

MAX_PLUGIN_BASE64_ORIGINAL_BYTES = 1024 * 1024


def materialize_text_original(envelope, output, private_root):
    # Keep the existing public function name for UTF-8 caller compatibility.
    identity=envelope["sourceIdentity"]
    encoding=envelope.get("encoding")
    if (identity.get("repository") not in REPOSITORIES
            or not identity.get("objectKey") or not identity.get("sourceCommit")
            or not identity.get("storagePath") or encoding not in ("utf-8", "base64")
            or not isinstance(envelope.get("sourceText"),str)):
        raise PreopenError("PLUGIN_ORIGINAL_TEXT_IDENTITY_INCOMPLETE")
    if encoding == "utf-8":
        payload=envelope["sourceText"].encode("utf-8")
        method="GITHUB_PLUGIN_UTF8_TEXT_EXACT_BYTE_READBACK"
    else:
        expected_bytes=identity.get("bytes")
        encoded=envelope["sourceText"]
        if (type(expected_bytes) is not int or not 0 < expected_bytes <= MAX_PLUGIN_BASE64_ORIGINAL_BYTES
                or len(encoded) > 2 * MAX_PLUGIN_BASE64_ORIGINAL_BYTES):
            raise PreopenError("PLUGIN_BASE64_SMALL_ORIGINAL_BUDGET")
        # GitHub wraps base64 using ASCII whitespace; this is transport encoding,
        # not the original gzip/CSV bytes. Reject everything else strictly.
        compact=encoded.translate(str.maketrans("", "", " \t\r\n"))
        if not compact:
            raise PreopenError("PLUGIN_BASE64_EMPTY_PAYLOAD_NOT_AN_ORIGINAL")
        try:
            payload=base64.b64decode(compact.encode("ascii"), validate=True)
        except (ValueError, binascii.Error):
            raise PreopenError("PLUGIN_BASE64_INVALID_ENCODING") from None
        if len(payload) > MAX_PLUGIN_BASE64_ORIGINAL_BYTES:
            raise PreopenError("PLUGIN_BASE64_SMALL_ORIGINAL_BUDGET")
        method="GITHUB_PLUGIN_BASE64_EXACT_BYTE_READBACK"
    actual=hashlib.sha256(payload).hexdigest()
    if actual != identity.get("sha256") or len(payload) != identity.get("bytes"):
        raise PreopenError("PLUGIN_ORIGINAL_BYTES_OR_SHA256_MISMATCH")
    output=private_path(output,private_root)
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if output.exists():
        if sha_file(output) != (actual,len(payload)):
            raise PreopenError("REFUSE_OVERWRITE_DIFFERENT_PRIVATE_ORIGINAL")
    else:
        with output.open("xb") as stream:
            stream.write(payload)
        output.chmod(0o600)
    if sha_file(output) != (actual,len(payload)):
        raise PreopenError("MATERIALIZED_PLUGIN_ORIGINAL_READBACK_MISMATCH")
    return {"schema":"ARK_PRIVATE_PLUGIN_TEXT_ORIGINAL_RECEIPT_V1",
            "sourceIdentity":identity,"privatePath":str(output),
            "sha256":actual,"bytes":len(payload),"unmodified":True,
            "retrievalMethod":method,"transportEncoding":encoding,
            "numericPriceRowsParsed":0,"createdAt":utc_now(),
            "classification":"PRIVATE_ORIGINAL",**SAFE_FLAGS}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--envelope",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--receipt",required=True)
    p.add_argument("--private-root",required=True)
    a=p.parse_args()
    envelope=json.loads(private_path(a.envelope,a.private_root).read_text())
    result=materialize_text_original(envelope,a.output,a.private_root)
    write_json(private_path(a.receipt,a.private_root),result)
    print(json.dumps({"status":"PRIVATE_ORIGINAL_SHA256_VERIFIED",
                      "bytes":result["bytes"],"sha256":result["sha256"],
                      "priceRowsParsed":0,"transmitted":False}))


if __name__ == "__main__":
    main()
