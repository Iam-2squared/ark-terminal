#!/usr/bin/env python3
"""Local operational defaults, distinct from model parameters and permission.

ZERO requires SOR for BUY and SELL; LIMIT/SOR-off is not silently substituted.
Installer/profile updates NEVER carry an old approval into a new session.
No position adoption: existing manual holdings are not Ark EXIT inventory.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

SCHEMA = 'ARK_NO11_WEEKLY_SOR_OPERATION_PROFILE_V1'
POLICY = {
    'schemaId': SCHEMA, 'account': '一般', 'accountType': 1,
    'feeCourse': 'ZERO', 'orderType': 'MARKET', 'timeInForce': 'DAY',
    'sor': True, 'cashOnly': True, 'allowMargin': False,
    'allowBankTransfers': False, 'maxPositions': 3, 'lotShares': 100,
    'securityMasterRefresh': 'ONCE_PER_TRADING_WEEK',
    'dailySecurityChecks': 'AUTOMATIC', 'unknownSymbolAction': 'EXCLUDE_NEW_BUY_ONLY',
    'autoAdoptExternalHoldings': False,
    'sameDayApprovalRequired': True, 'automaticOrderAuthorization': False,
    'dialogSettingsManagedByBrokerUI': True,
    'productionReady': False, 'orderTransmission': False,
}


def need(value, code):
    if not value:
        raise ValueError('NO11_OPERATION_PROFILE_' + code)


def validate(value):
    need(type(value) is dict and all(value.get(k) == v and type(value.get(k)) is type(v)
         for k, v in POLICY.items()), 'POLICY_CHANGED')
    return deepcopy(value)


def stage_broker_configuration(template, profile):
    """Migrate only a stopped configuration into a DISABLED candidate copy."""
    validate(profile)
    need(type(template) is dict and template.get('schemaId') ==
         'ARK_NO11_BROKER_EXECUTION_CONFIG_V1', 'BROKER_TEMPLATE')
    need(template.get('orderTransmission') is False and
         template.get('transport', {}).get('mode') in ('DISABLED', 'OBSERVE_ONLY'),
         'ACTIVE_CONFIG_NOT_MUTABLE')
    candidate = deepcopy(template)
    candidate['feeCourse'] = 'ZERO'
    candidate['orderTerms'] = {'orderType': 'MARKET', 'limitPrice': None,
        'timeInForce': 'DAY', 'sor': True, 'accountType': 1, 'accountTypeVerified': True}
    book = candidate.get('ledger')
    need(type(book) is dict and book.get('maxSymbols') == 3 and book.get('lotSize') == 100,
         'ORIGINAL_CAPITAL_BOUNDARY')
    book['account'] = '一般'
    candidate['transport'] = {'mode': 'DISABLED', 'orderTransmission': False}
    candidate['orderTransmission'] = False
    candidate['productionReady'] = False
    return candidate


def audit_live_configuration(config, profile, session):
    """Pure validation. Passing this function is NOT an order permit."""
    validate(profile)
    need(config.get('sessionDate') == session, 'STALE_SESSION')
    terms, ledger = config.get('orderTerms', {}), config.get('ledger', {})
    need(terms.get('orderType') == 'MARKET' and terms.get('limitPrice') is None and
         terms.get('timeInForce') == 'DAY' and terms.get('sor') is True and
         terms.get('accountType') == 1 and terms.get('accountTypeVerified') is True,
         'GENERAL_MARKET_SOR_REQUIRED')
    need(config.get('feeCourse') == 'ZERO' and ledger.get('account') == '一般' and
         ledger.get('maxSymbols') == 3 and ledger.get('lotSize') == 100,
         'CASH_MAX3_GENERAL_REQUIRED')
    need(ledger.get('allocatedCashJpy') == 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY',
         'NO_GUESSED_OR_FIXED_OPENING_MONEY')
    need(type(config.get('securitiesCashEvidenceFile')) is str and
         type(config.get('buyingPowerEvidenceFile')) is str,
         'OPENING_SOURCE_AND_CURRENT_POWER_REQUIRED')
    # Existing config/transport validators still enforce every physical pin,
    # one-shot committed permit, expiry, reservation and exact command identity.
    return {'status': 'PROFILE_MATCH_ONLY_NOT_TRANSPORT_APPROVAL',
            'orderTransmission': False}


def validate_setup_declaration(value, profile):
    """One-time local checklist. No broker setting is modified or inferred."""
    validate(profile)
    need(type(value) is dict and value.get('schemaId') == 'ARK_NO11_BROKER_UI_SETUP_DECLARATION_V1',
         'SETUP_DECLARATION')
    need(value.get('bankLink') == 'NONE' and value.get('autoSweepEnabled') is False,
         'BANK_LINK_OR_SWEEP')
    need(value.get('rssOrderFeatureConfigured') is True and
         value.get('orderConfirmationDialogDisabled') is True and
         value.get('tradingWarningDialogDisabled') is True,
         'UNATTENDED_RSS_DIALOG_SETTINGS_UNCONFIRMED')
    limit, budget = value.get('rssPerOrderLimitJpy'), value.get('operatorBudgetCeilingJpy')
    need(type(limit) is int and type(budget) is int and 0 < limit <= budget < 1000000000,
         'EXPLICIT_BOUNDED_ORDER_LIMIT_REQUIRED')
    need(value.get('marginNewOrderLimitJpy') == 0,
         'MARGIN_LIMIT_MUST_REMAIN_ZERO')
    return {'basis': 'OPERATOR_DECLARATION_NOT_MACHINE_CERTIFICATION',
            'perOrderLimitJpy': limit, 'budgetCeilingJpy': budget,
            'orderTransmission': False}


def select_current_observation(records, now):
    """Newest captured event wins, including a newer BLOCKED observation.

    Callers must restrict records to the current observer run. Never recover
    permissions by searching older OBSERVED files or by filesystem mtime.
    """
    at = datetime.fromisoformat(now)
    need(at.utcoffset() == timedelta(hours=9), 'CURRENT_CLOCK')
    need(type(records) is list and records, 'OBSERVATION_MISSING')
    run_ids = {r.get('runId') for r in records}
    need(len(run_ids) == 1 and None not in run_ids, 'OBSERVER_RUN_AMBIGUOUS')
    need(all(type(r.get('sequence')) is int and r['sequence'] > 0 for r in records),
         'OBSERVER_SEQUENCE')
    record = max(records, key=lambda x: x['sequence'])
    need(sum(r['sequence'] == record['sequence'] for r in records) == 1, 'DUPLICATE_SEQUENCE')
    need(record.get('schemaId') == 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1' and
         record.get('status') == 'OBSERVED' and record.get('readOnly') is True and
         record.get('orderTransmission') is False, 'LATEST_OBSERVATION_BLOCKED')
    broker = record.get('brokerObservation', {})
    need(broker.get('status') == 'OBSERVED', 'BROKER_UNAVAILABLE')
    end = datetime.fromisoformat(broker['captureCompletedAt'])
    need(end.utcoffset() == timedelta(hours=9) and end.date() == at.date() and
         0 <= (at - end).total_seconds() <= 30, 'BROKER_OBSERVATION_STALE')
    return deepcopy(record)


def external_symbols(snapshot, ark_owned_symbols=()):
    """Separate already-observed manual holdings, never create SELL intents."""
    need(snapshot.get('status') == 'OBSERVED', 'BROKER_SOURCE_NOT_OBSERVED')
    symbols = set()
    for row in snapshot.get('positions', []):
        raw = row.get('symbol')
        need(type(raw) is str and re.fullmatch(r'[0-9A-Z]{4}(?:\.T)?', raw), 'POSITION_SYMBOL')
        symbols.add(raw if raw.endswith('.T') else raw + '.T')
    return sorted(symbols - set(ark_owned_symbols))


def write_default(path):
    target = Path(path)
    need(target.is_absolute() and target.parent.is_dir() and not target.is_symlink(), 'PROFILE_PATH')
    data = (json.dumps(POLICY, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if target.exists():
        validate(json.loads(target.read_text(encoding='utf-8-sig')))
    else:
        with target.open('xb') as f:
            f.write(data)
    return target
