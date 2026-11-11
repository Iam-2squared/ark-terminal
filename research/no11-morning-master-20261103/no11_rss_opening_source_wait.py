"""Source transform; no restart, Excel or broker I/O.

Preserve the historical funding source and all existing session/claim records.
Only the first opening-observation read is replaced. Existing funding receipt
reuse, position exclusion, allocation and dispatch remain native and unchanged.
"""
from __future__ import annotations

import ast
import hashlib
import inspect

ORIGINAL_BLOB = '7cc22baf4628f8163964742fb3a6ac1d6832413b'


def read_opening_source(config, at, read_private, bridge, normalize, get_path, *,
                        clock=None, monotonic=None, sleep=None, diagnostic=None,
                        timeout_seconds=15.0, poll_seconds=0.25):
    """Read-only bounded wait; only explicitly transient reader failures retry.

    Never use the previous good sample, hide an identity error, reset a ledger,
    accept stale evidence, or retransmit an order. Successful input must pass
    the unchanged complete native normalizer. No funding write happens here.
    Injected clocks/readers are exclusively for deterministic offline tests.
    """
    from datetime import datetime, timedelta, timezone
    import math
    import re
    import sys
    import time

    def fail(code):
        raise ValueError('NO11_RSS_FUNDING_OPENING_' + code)

    def ticks(value):
        if not isinstance(value, str):
            fail('CLOCK_TYPE')
        match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})', value)
        if match is None:
            fail('CLOCK_FORMAT')
        whole = datetime.fromisoformat(match[1] + match[3].replace('Z', '+00:00'))
        delta = whole.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (delta.days * 86400 + delta.seconds) * 10_000_000 + int((match[2] or '').ljust(7, '0'))

    def session_clock(value):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if (parsed.utcoffset() != timedelta(hours=9)
                or parsed.date().isoformat() != config['sessionDate']
                or not '09:00:00' <= parsed.strftime('%H:%M:%S') < '15:20:00'):
            fail('ENTRY_WINDOW_CLOSED')
        if ticks(value) >= ticks(config['transport']['expiresAtJst']):
            fail('TRANSPORT_EXPIRED')
        return ticks(value)

    for value in (timeout_seconds, poll_seconds):
        if type(value) not in (int, float) or not math.isfinite(value):
            fail('WAIT_BOUNDS')
    if not (0 < poll_seconds <= timeout_seconds <= 60):
        fail('WAIT_BOUNDS')
    monotonic = monotonic or time.monotonic
    sleep = sleep or time.sleep
    clock = clock or (lambda: datetime.now(timezone(timedelta(hours=9))).isoformat())
    diagnostic = diagnostic or (lambda row: print(row, file=sys.stderr, flush=True))
    transient = frozenset({
        'NO11_BROKER_BROKER_TABLE_CHANGED_DURING_CAPTURE',
        'NO11_BROKER_ACCOUNT_CHANGED_DURING_CAPTURE',
        'NO11_BROKER_CAPTURE_DURATION',
    })
    source_path = get_path(config)
    start = monotonic()
    last_clock = session_clock(at)
    prior_run = None
    prior_sequence = None
    attempts = math.ceil(timeout_seconds / poll_seconds) + 1
    for attempt in range(attempts):
        if monotonic() - start >= timeout_seconds:
            fail('SOURCE_WAIT_TIMEOUT')
        envelope, source_sha = read_private(source_path)
        # The caller's initialization timestamp may predate this I/O. Use the
        # actual read/return clocks on the FIRST attempt as well as retries.
        checked_at = clock()
        checked_clock = session_clock(checked_at)
        if checked_clock < last_clock:
            fail('CLOCK_REVERSED')
        last_clock = checked_clock
        if monotonic() - start >= timeout_seconds:
            fail('SOURCE_WAIT_TIMEOUT')
        if prior_run is not None:
            if (type(envelope) is not dict or envelope.get('runId') != prior_run
                    or type(envelope.get('sequence')) is not int
                    or envelope['sequence'] < prior_sequence):
                fail('OBSERVER_CHANGED')
        try:
            source = normalize(envelope, config['sessionDate'], checked_at, bridge)
        except ValueError as error:
            if str(error) != 'NO11_BROKER_SOURCE_UNAVAILABLE':
                raise
            outer = envelope if type(envelope) is dict else {}
            raw = outer.get('brokerObservation')
            if not (outer.get('schemaId') == 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1'
                    and outer.get('status') == 'OBSERVED'
                    and outer.get('readOnly') is True
                    and outer.get('productionReady') is False
                    and outer.get('orderTransmission') is False
                    and type(raw) is dict
                    and raw.get('schemaId') == 'ARK_NO11_BROKER_OBSERVATION_V1'
                    and raw.get('status') == 'UNAVAILABLE'
                    and raw.get('readOnly') is True
                    and raw.get('productionReady') is False
                    and raw.get('orderTransmission') is False):
                fail('UNAVAILABLE_CONTRACT')
            reason = raw.get('reason')
            safe_reason = (reason if type(reason) is str and
                           re.fullmatch(r'(?:NO11_BROKER_[A-Z0-9_]+|BROKER_SOURCE_UNAVAILABLE)', reason)
                           else 'UNCLASSIFIED_REDACTED')
            diagnostic('NO11_RSS_OPENING_UNAVAILABLE_CAUSE=' + safe_reason)
            if reason not in transient:
                fail('UNAVAILABLE_NOT_RETRYABLE_' + safe_reason)
            run_id = outer.get('runId')
            sequence = outer.get('sequence')
            if (type(run_id) is not str or re.fullmatch(r'[a-f0-9]{32}', run_id) is None
                    or type(sequence) is not int or sequence < 1):
                fail('OBSERVER_IDENTITY_MISSING')
            prior_run, prior_sequence = run_id, sequence
            left = timeout_seconds - (monotonic() - start)
            if left <= 0:
                fail('SOURCE_WAIT_TIMEOUT')
            sleep(min(poll_seconds, left))
            continue
        if monotonic() - start >= timeout_seconds:
            fail('SOURCE_WAIT_TIMEOUT')
        returned_at = clock()
        if session_clock(returned_at) < last_clock:
            fail('CLOCK_REVERSED')
        if prior_sequence is not None and envelope['sequence'] <= prior_sequence:
            fail('OBSERVATION_NOT_ADVANCED')
        identity = source.get('excelSession', {})
        transport = config['transport']
        if (type(identity.get('processId')) is not int
                or identity['processId'] != transport.get('expectedExcelPid')
                or identity.get('sessionKey') != transport.get('rssSessionKey')
                or ticks(identity.get('startedAtUtc')) != ticks(transport.get('expectedExcelStartedAt'))):
            fail('EXCEL_SESSION_CHANGED')
        if type(source_sha) is not str or re.fullmatch(r'[a-f0-9]{64}', source_sha) is None:
            fail('OBSERVER_HASH_INVALID')
        # resolve_opening revalidates freshness with this post-normalization
        # timestamp before it can write the immutable opening-funding receipt.
        return envelope, source_sha, source, returned_at
    fail('SOURCE_WAIT_TIMEOUT')


def transform(raw: bytes) -> bytes:
    """Return derived bytes, preserving BOM/newlines. Never install here."""
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    encoded = text.encode('utf-8')
    actual = hashlib.sha1(b'blob ' + str(len(encoded)).encode() + b'\0' + encoded).hexdigest()
    if actual != ORIGINAL_BLOB:
        raise ValueError('NO11_RSS_OPENING_TRANSFORM_UNKNOWN_SOURCE')
    before = (
        '        envelope, source_sha = read_private(observer_path(config))\n'
        '        source = normalize_envelope(envelope, day, at, bridge)\n'
        '        amount = verify_normalized(source, day, at)\n')
    after = (
        '        envelope, source_sha, source, verified_at = read_opening_source(\n'
        '            config, at, read_private, bridge, normalize_envelope, observer_path)\n'
        '        amount = verify_normalized(source, day, verified_at)\n')
    anchor = 'def resolve_opening('
    if text.count(before) != 1 or text.count(anchor) != 1:
        raise ValueError('NO11_RSS_OPENING_TRANSFORM_CONTEXT_CHANGED')
    text = text.replace(before, after, 1)
    text = text.replace(anchor, inspect.getsource(read_opening_source) + '\n\n' + anchor, 1)
    ast.parse(text)
    return bom + text.replace('\n', newline).encode('utf-8')
