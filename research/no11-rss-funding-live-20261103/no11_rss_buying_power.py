"""Explicit RSS funding policy. No transport, bank lookup or portfolio adoption.

The user selects RSS buying power as available funding. This is an input policy,
not certification of a vendor refresh. Keep those two facts distinct. Initial
funding is pinned once per existing session/run; a restart cannot mint cash.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

import no11_broker_execution_ledger as ledger

POLICY = 'RSS_BUYING_POWER'
AUTO = 'AUTO_RSS_BUYING_POWER'
SCHEMA = 'ARK_NO11_RSS_OPENING_FUNDING_V1'
BASIS = 'USER_SELECTED_RSS_BUYING_POWER_NOT_VENDOR_REFRESH_CERTIFIED'


def need(ok, reason):
    if not ok:
        raise ValueError('NO11_RSS_FUNDING_' + reason)


def selected(config):
    policy = config.get('fundingPolicy')
    need(policy is None or policy == POLICY, 'UNKNOWN_POLICY')
    return policy == POLICY


def validate(config):
    """Use only on the separately approved normal LIVE route."""
    need(selected(config), 'EXPLICIT_POLICY_REQUIRED')
    book, transport, terms = (config.get(k, {}) for k in ('ledger', 'transport', 'orderTerms'))
    day = config.get('sessionDate')
    need(config.get('evidenceMode') == 'BROKER_OBSERVATION'
         and transport.get('mode') == 'LIVE'
         and transport.get('orderTransmission') is True
         and config.get('orderTransmission') is True
         and config.get('productionReady') is False
         and transport.get('operatorEnabled') is True
         and transport.get('approvedForSession') is True
         and transport.get('sessionDate') == day, 'LIVE_SESSION_APPROVAL_REQUIRED')
    need(book.get('allocatedCashJpy') == AUTO and book.get('account') == '一般'
         and book.get('sessionDate') == day
         and book.get('evidenceMode') == 'BROKER_OBSERVATION'
         and type(book.get('maxSymbols')) is int and book['maxSymbols'] == 3
         and type(book.get('lotSize')) is int and book['lotSize'] == 100,
         'NORMAL_GENERAL_MAX3_100_REQUIRED')
    need(config.get('feeCourse') == 'ZERO' and terms.get('sor') is True
         and type(terms.get('accountType')) is int and terms['accountType'] == 1
         and terms.get('accountTypeVerified') is True
         and terms.get('orderType') == 'MARKET' and terms.get('timeInForce') == 'DAY'
         and terms.get('limitPrice') is None, 'GENERAL_ZERO_SOR_TERMS_REQUIRED')
    need(not config.get('securitiesCashEvidenceFile') and not config.get('buyingPowerEvidenceFile'),
         'MIXED_FUNDING_POLICY')


def amount_text(value):
    need(type(value) in (int, float, str), 'AMOUNT_TYPE')
    text = str(value)
    need(re.fullmatch(r'(?:0|[1-9][0-9]{0,14})(?:\.[0-9]{1,6})?', text) is not None,
         'AMOUNT_FORMAT')
    value = ledger.money(text)
    return ledger.decimal_text(value)


def verify_normalized(source, session, at):
    need(type(source) is dict and source.get('schemaId') == 'ARK_NO11_BROKER_SNAPSHOT_V1'
         and source.get('sessionDate') == session
         and source.get('accountSnapshotCompared') is True
         and source.get('productionReady') is False and source.get('orderTransmission') is False,
         'NORMALIZED_SOURCE_REQUIRED')
    body = dict(source)
    digest = body.pop('snapshotSha256', None)
    need(type(digest) is str and hashlib.sha256(ledger.ordered_json_bytes(body)).hexdigest() == digest,
         'NORMALIZED_SOURCE_HASH')
    age = ledger.instant(at, session) - ledger.instant(source['captureCompletedAt'], session)
    need(0 <= age <= 30 * ledger.TICKS_PER_SECOND, 'OBSERVATION_STALE_OR_FUTURE')
    return amount_text(source.get('buyingPower'))


def observer_path(config):
    explicit = config.get('accountObservationFile')
    inherited = os.environ.get('ARK_NO11_ACCOUNT_OBSERVATION_FILE')
    if explicit and inherited:
        need(os.path.normcase(os.path.abspath(explicit)) == os.path.normcase(os.path.abspath(inherited)),
             'OBSERVER_PATH_CONFLICT')
    path = explicit or inherited
    need(type(path) is str and Path(path).is_absolute(), 'OBSERVER_PATH_REQUIRED')
    return path


def normalize_envelope(envelope, session, at, bridge):
    need(type(envelope) is dict and envelope.get('schemaId') == 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1'
         and envelope.get('status') == 'OBSERVED' and envelope.get('readOnly') is True
         and envelope.get('orderTransmission') is False and envelope.get('productionReady') is False
         and type(envelope.get('snapshot')) is dict, 'OBSERVER_ENVELOPE_REQUIRED')
    source = bridge({'action': 'normalize', 'input': {
        'brokerObservation': envelope.get('brokerObservation'), 'sessionDate': session,
        'throughJst': at, 'previous': None, 'accountSnapshot': envelope['snapshot']}})
    verify_normalized(source, session, at)
    return source


def resolve_opening(root, config, database, at, read_private, bridge, write_exclusive):
    """Resolve once, then re-use the persisted starting allocation on recovery.

    Existing databases without their funding receipt are never reinitialized.
    Existing files are checked before use, and the ledger binds this receipt's
    bytes to controller.identity. Only cash is initialized, never a position.
    """
    validate(config)
    day = config['sessionDate']
    path = Path(root) / ('rss-opening-funding-' + day + '.json')
    config_sha = ledger.digest(config)
    if path.exists():
        proof, proof_sha = read_private(path, 100_000)
        need(type(proof) is dict and proof.get('schemaId') == SCHEMA
             and proof.get('sessionDate') == day and proof.get('account') == '一般'
             and proof.get('configSha256') == config_sha and proof.get('basis') == BASIS
             and proof.get('productionReady') is False and proof.get('orderTransmission') is False,
             'RECOVERY_IDENTITY_CHANGED')
        body = dict(proof)
        saved = body.pop('receiptSha256', None)
        need(saved == ledger.digest(body), 'RECOVERY_RECEIPT_CHANGED')
        need(ledger.instant(proof['capturedAtJst'], day) <= ledger.instant(at, day), 'RECOVERY_CLOCK_REVERSED')
        amount = amount_text(proof['allocatedCashJpy'])
    else:
        need(not Path(database).exists(), 'EXISTING_LEDGER_MISSING_RECEIPT')
        envelope, source_sha = read_private(observer_path(config))
        source = normalize_envelope(envelope, day, at, bridge)
        amount = verify_normalized(source, day, at)
        excluded = set(config['ledger'].get('externalSymbols', []))
        for row in source['positions']:
            raw = row.get('symbol')
            need(type(raw) is str and re.fullmatch(r'[0-9A-Z]{4}(?:\.T)?', raw) is not None,
                 'POSITION_SYMBOL')
            excluded.add(raw if raw.endswith('.T') else raw + '.T')
        proof = {'schemaId': SCHEMA, 'sessionDate': day, 'account': '一般',
                 'configSha256': config_sha, 'basis': BASIS,
                 'allocatedCashJpy': amount, 'capturedAtJst': source['captureCompletedAt'],
                 'observerSha256': source_sha, 'normalizedSha256': source['snapshotSha256'],
                 'externalSymbols': sorted(excluded),
                 'vendorRefreshCertified': False, 'productionReady': False, 'orderTransmission': False}
        proof['receiptSha256'] = ledger.digest(proof)
        write_exclusive(path, proof)
        _, proof_sha = read_private(path, 100_000)
    external = proof.get('externalSymbols')
    ledger.BrokerExecutionLedger._symbols(external)
    need(set(config['ledger'].get('externalSymbols', [])) <= set(external), 'EXTERNAL_EXCLUSION_REMOVED')
    result = deepcopy(config['ledger'])
    result['allocatedCashJpy'] = amount
    result['externalSymbols'] = list(external)
    return result, proof, proof_sha


def current_usable(service, at):
    """Current locally observed RSS value, not a claim of vendor freshness."""
    try:
        validate(service.config)
        if not service._source_current(at):
            return False
        verify_normalized(service.source, service.session, at)
        return True
    except (ValueError, TypeError, KeyError):
        return False
