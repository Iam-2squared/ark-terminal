"""Decode existing immutable J-Quants page envelopes; no network or imputation.

The archived format is a list of responseText/responseSha256 envelopes, not
already-decoded rows. Verify the exact page bytes before parsing responseText.
This proves archive/content identity, NOT historical receipt-time admissibility.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any

class RawPageError(ValueError):
    """Fail-closed error without echoing raw payloads or credentials."""


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise RawPageError('DUPLICATE_JSON_KEY')
        obj[key] = value
    return obj


def _load(text: str | bytes) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(RawPageError('NONFINITE_JSON')))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RawPageError('INVALID_JSON') from exc


def decode_pages(data: bytes, expected_date: str, kind: str,
                 expected_file_sha256: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return original row dictionaries after file/page/date/identity checks.

    Only the existing page-list format is accepted. Unknown formats fail closed
    instead of returning an apparently valid empty recovery. Code remains exact
    (including the fifth digit); all factor fields and nulls are preserved.
    """
    if kind not in ('daily', 'minute'):
        raise RawPageError('INVALID_KIND')
    file_hash = hashlib.sha256(data).hexdigest()
    if expected_file_sha256 is not None and file_hash != expected_file_sha256:
        raise RawPageError('RAW_FILE_SHA256_MISMATCH')
    pages = _load(data)
    if not isinstance(pages, list):
        raise RawPageError('EXPECTED_PAGE_ENVELOPE_LIST')
    rows: list[dict[str, Any]] = []
    hashes: list[str] = []
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get('responseText'), str):
            raise RawPageError('MISSING_RESPONSE_TEXT')
        text = page['responseText']
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if digest != page.get('responseSha256'):
            raise RawPageError('PAGE_SHA256_MISMATCH')
        body = _load(text)
        if not isinstance(body, dict) or not isinstance(body.get('data'), list):
            raise RawPageError('MISSING_DATA_ROW_LIST')
        for row in body['data']:
            if not isinstance(row, dict):
                raise RawPageError('ROW_NOT_OBJECT')
            if row.get('Date') != expected_date:
                raise RawPageError('RAW_DATE_MISMATCH')
            if not isinstance(row.get('Code'), str) or not row['Code']:
                raise RawPageError('RAW_CODE_MISSING')
            # Null OHLC is retained as evidence; no valid-price filter here.
            if not all(k in row for k in ('O', 'H', 'L', 'C')):
                raise RawPageError('RAW_OHLC_FIELDS_MISSING')
            if kind == 'minute' and not isinstance(row.get('Time'), str):
                raise RawPageError('RAW_MINUTE_TIME_MISSING')
            rows.append(row)
        hashes.append(digest)
    aggregate = hashlib.sha256(json.dumps(hashes, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return rows, {'format': 'JQUANTS_IMMUTABLE_RESPONSE_TEXT_PAGES',
                  'rawPagesSHA256': file_hash, 'responsePageN': len(pages),
                  'responseRowN': len(rows), 'responseAggregateSHA256': aggregate,
                  'individualResponseHashesVerified': True,
                  'receivedAtProven': False}
