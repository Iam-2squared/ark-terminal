"""Durable broker-observation accounting, with no broker or Excel I/O.

This ledger is deliberately separate from ``ShadowPortfolio``.  Its balance is
an explicitly allocated Ark amount plus attributed broker cash flows; broker
buying power is only an additional admission bound.  A committed dispatch
permit is a once-only transport record, not evidence of acceptance or a fill.

All externally supplied money is decimal text.  Unknown prices, charges and
submission outcomes retain their reservations and stop new buys, while known
Ark-owned quantities remain available to the original EXIT coordinator.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3


ROOT = Path(__file__).resolve().parents[3]
CONFIG_SCHEMA = 'ARK_NO11_BROKER_EXECUTION_LEDGER_CONFIG_V1'
INTENT_SCHEMA = 'ARK_NO11_BROKER_ORDER_INTENT_V1'
ACCOUNT_SCHEMA = 'ARK_NO11_BROKER_ACCOUNT_BOUND_V1'
RECEIPT_SCHEMA = 'ARK_NO11_BROKER_ORDER_RECEIPT_V1'
COMMAND_SCHEMA = 'ARK_NO11_BROKER_TRANSPORT_COMMAND_V1'
PERMIT_SCHEMA = 'ARK_NO11_BROKER_DISPATCH_PERMIT_V1'
SNAPSHOT_SCHEMA = 'ARK_NO11_BROKER_EXECUTION_LEDGER_SNAPSHOT_V1'
MODES = {'OFFLINE_REPLAY', 'BROKER_OBSERVATION'}
COMMAND_MODES = {'OFFLINE_REPLAY': 'SYNTHETIC_OFFLINE_ONLY',
                 'BROKER_OBSERVATION': 'LIVE_OBSERVED'}
ACCOUNTS = ('特定', '一般', 'NISA（NISA成長投資枠）', '旧NISA')
TERMINAL = {'FILLED', 'CANCELLED', 'EXPIRED', 'REJECTED', 'LOCAL_WITHDRAWN'}
RECEIPT_PHASES = {'ACKNOWLEDGED', 'PARTIAL', 'FILLED', 'CANCEL_PENDING',
                  'CANCELLED', 'EXPIRED', 'REJECTED', 'UNKNOWN'}
SHA = re.compile(r'^[a-f0-9]{64}$')
SYMBOL = re.compile(r'^[0-9A-Z]{4}\.T$')
ZERO = '0' * 64
TICKS_PER_SECOND = 10_000_000  # Preserve all seven PowerShell DateTime digits.


def need(ok, code):
    if not ok:
        raise ValueError('NO11_BROKER_LEDGER_' + code)


def _number(value):
    """JSON number formatting shared with the JS command/permit digest."""
    if type(value) is int:
        need(abs(value) <= 9_007_199_254_740_991, 'JSON_INTEGER_RANGE')
        return str(value)
    need(type(value) is float and math.isfinite(value), 'JSON_NUMBER')
    if value == 0:
        return '0'
    text = repr(value).lower()
    if 1e-6 <= abs(value) < 1e21:
        text = format(Decimal(text), 'f')
        return text.rstrip('0').rstrip('.') if '.' in text else text
    mantissa, exponent = text.split('e') if 'e' in text else (text, '0')
    if mantissa.endswith('.0'):
        mantissa = mantissa[:-2]
    exp = int(exponent)
    return mantissa + 'e' + ('+' if exp >= 0 else '-') + str(abs(exp))


def canonical_bytes(value, *, sort_keys=True):
    def encode(v):
        if v is None:
            return 'null'
        if v is True:
            return 'true'
        if v is False:
            return 'false'
        if type(v) in (int, float):
            return _number(v)
        if type(v) is str:
            return json.dumps(v, ensure_ascii=False)
        if type(v) is list:
            return '[' + ','.join(encode(x) for x in v) + ']'
        need(type(v) is dict and all(type(k) is str for k in v), 'JSON_VALUE')
        keys = sorted(v) if sort_keys else v
        return '{' + ','.join(encode(k) + ':' + encode(v[k]) for k in keys) + '}'
    return encode(value).encode('utf-8')


def ordered_json_bytes(value):
    """Match JSON.stringify member order for the existing broker normalizer."""
    return canonical_bytes(value, sort_keys=False)


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def clone(value):
    data = canonical_bytes(value)
    need(len(data) <= 25_000_000, 'PAYLOAD_SIZE')
    return json.loads(data)


def money(value, *, signed=False):
    need(type(value) in (str, int), 'MONEY_DECIMAL_TEXT_REQUIRED')
    text = str(value)
    pattern = r'-?(?:0|[1-9]\d{0,20})(?:\.\d{1,6})?' if signed else r'(?:0|[1-9]\d{0,14})(?:\.\d{1,6})?'
    need(re.fullmatch(pattern, text) is not None, 'MONEY_FORMAT')
    try:
        result = Decimal(text)
    except InvalidOperation:
        raise ValueError('NO11_BROKER_LEDGER_MONEY_FORMAT') from None
    maximum = Decimal('100000000000000000000') if signed else Decimal('100000000000000')
    need(result.is_finite() and abs(result) <= maximum, 'MONEY_RANGE')
    return result


def decimal_text(value):
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def instant(value, session=None):
    need(type(value) is str, 'CLOCK')
    match = re.fullmatch(r'(20\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.(\d{1,7}))?\+09:00', value)
    need(match is not None, 'CLOCK')
    try:
        year, month, day, hour, minute, second = map(int, match.groups()[:6])
        dt = datetime(year, month, day, hour, minute, second)
    except ValueError:
        raise ValueError('NO11_BROKER_LEDGER_CLOCK') from None
    need(session is None or value[:10] == session, 'SESSION_CLOCK')
    seconds = (dt.toordinal() * 86400 + hour * 3600 + minute * 60 + second)
    return seconds * TICKS_PER_SECOND + int((match.group(7) or '').ljust(7, '0'))


def _text(value, name, limit=256):
    need(type(value) is str and 0 < len(value) <= limit and
         value == value.strip() and not any(ord(c) < 32 for c in value), name)
    return value


def _sha(value, name):
    need(type(value) is str and SHA.fullmatch(value) is not None, name)
    return value


def _integer(value, name, minimum=0, maximum=1_000_000_000):
    need(type(value) is int and minimum <= value <= maximum, name)
    return value


class BrokerExecutionLedger:
    """One trading session, one explicit Ark allocation, one account type."""

    def __init__(self, database, config):
        need(type(config) is dict and config.get('schemaId') == CONFIG_SCHEMA, 'CONFIG_SCHEMA')
        self.config = clone(config)
        self.session = config.get('sessionDate')
        need(type(self.session) is str and re.fullmatch(r'20\d\d-\d\d-\d\d', self.session), 'SESSION')
        try:
            date.fromisoformat(self.session)
        except ValueError:
            raise ValueError('NO11_BROKER_LEDGER_SESSION') from None
        self.account = config.get('account')
        need(self.account in ACCOUNTS, 'ACCOUNT')
        self.mode = config.get('evidenceMode')
        need(type(self.mode) is str and self.mode in MODES, 'EVIDENCE_MODE')
        allocation = money(config.get('allocatedCashJpy'))
        external = config.get('externalSymbols', [])
        self._symbols(external)
        need(config.get('maxSymbols', 3) == 3 and config.get('lotSize', 100) == 100,
             'ORIGINAL_MAX3_AND_LOT_REQUIRED')
        need(config.get('orderTransmission', False) is False and
             config.get('productionReady', False) is False, 'LEDGER_HAS_NO_TRANSPORT')
        path = Path(database).absolute()
        need(path != ROOT and ROOT not in path.parents and path.parent.is_dir()
             and not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
             'PRIVATE_DATABASE_REQUIRED')
        need(not path.exists() or path.is_file(), 'PRIVATE_DATABASE_REQUIRED')
        self.pin = digest(self.config)
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS broker_state (singleton INTEGER PRIMARY KEY CHECK(singleton=1), body TEXT NOT NULL, sha TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS broker_events (seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, fingerprint TEXT NOT NULL, previous_sha TEXT NOT NULL, event_sha TEXT NOT NULL, result TEXT NOT NULL)')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT body FROM broker_state WHERE singleton=1').fetchone()
            if row is None:
                need(self.db.execute('SELECT COUNT(*) FROM broker_events').fetchone()[0] == 0,
                     'STATE_MISSING_WITH_EVENTS')
                state = {'sessionDate': self.session, 'account': self.account, 'pin': self.pin,
                         'evidenceMode': self.mode, 'allocatedCashJpy': decimal_text(allocation),
                         'cashJpy': decimal_text(allocation), 'orders': {}, 'positions': {},
                         'commands': {}, 'rssIds': {}, 'brokerOrders': {}, 'sourceCheckpoints': {},
                         'accountObservation': None, 'firstSellFillBuyHalt': False,
                         'firstSellFillObservedAtJst': None, 'clock': None,
                         'eventSeq': 0, 'eventHeadSha256': ZERO}
                self._save(state)
            state = self._read()
            previous, count = ZERO, 0
            for seq, eid, payload, fp, prev, sha, result in self.db.execute('SELECT * FROM broker_events ORDER BY seq'):
                count += 1
                need(seq == count and prev == previous and digest(json.loads(payload)) == fp
                     and sha == digest([seq, eid, fp, prev, result]), 'EVENT_CHAIN_CHANGED')
                previous = sha
            need(count == state['eventSeq'] and previous == state['eventHeadSha256'],
                 'STATE_EVENT_CHAIN_MISMATCH')
            self._invariants(state)
            self.db.commit()
        except BaseException:
            self.db.rollback()
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @staticmethod
    def _symbols(values):
        need(type(values) is list and len(values) <= 5000 and
             all(type(x) is str and SYMBOL.fullmatch(x) for x in values) and
             len(values) == len(set(values)), 'EXTERNAL_SYMBOLS')

    def _read(self):
        row = self.db.execute('SELECT body,sha FROM broker_state WHERE singleton=1').fetchone()
        need(row is not None, 'STATE_MISSING')
        state = json.loads(row[0])
        need(digest(state) == row[1] and state['pin'] == self.pin and
             state['sessionDate'] == self.session and state['account'] == self.account and
             state['evidenceMode'] == self.mode, 'STATE_CHANGED_OR_DIFFERENT_CONFIG')
        return state

    def _save(self, state):
        encoded = canonical_bytes(state).decode('utf-8')
        self.db.execute('INSERT OR REPLACE INTO broker_state VALUES (1,?,?)', (encoded, digest(state)))

    def _event(self, event_id, payload, at, reducer, *, once=False):
        clock, body = instant(at, self.session), clone(payload)
        fingerprint = digest(body)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT fingerprint,result FROM broker_events WHERE event_id=?',
                                  (event_id,)).fetchone()
            if old:
                need(old[0] == fingerprint, 'EVENT_ID_CONTENT_CHANGED')
                need(not once, 'DISPATCH_ALREADY_STARTED')
                result = json.loads(old[1])
                self.db.commit()
                return dict(result, idempotentReplay=True)
            state = self._read()
            need(state['clock'] is None or instant(state['clock'], self.session) <= clock,
                 'PROCESS_CLOCK_REVERSED')
            need(state['eventSeq'] < 50000, 'EVENT_LIMIT')
            result = reducer(state)
            result.update(orderTransmission=False, brokerIoPerformed=False, idempotentReplay=False)
            self._invariants(state)
            encoded = canonical_bytes(result).decode('utf-8')
            seq = state['eventSeq'] + 1
            sha = digest([seq, event_id, fingerprint, state['eventHeadSha256'], encoded])
            self.db.execute('INSERT INTO broker_events VALUES (?,?,?,?,?,?,?)',
                            (seq, event_id, canonical_bytes(body).decode('utf-8'), fingerprint,
                             state['eventHeadSha256'], sha, encoded))
            state.update(clock=at, eventSeq=seq, eventHeadSha256=sha)
            self._save(state)
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def _evidence(self, event):
        need(event.get('evidenceMode') == self.mode, 'EVIDENCE_MODE_MISMATCH')
        _sha(event.get('sourceSnapshotSha256'), 'SOURCE_SNAPSHOT_HASH')

    def _invariants(self, state):
        money(state['cashJpy'], signed=True)
        occupied = {p['symbol'] for p in state['positions'].values() if p['quantity'] > 0}
        for oid, order in state['orders'].items():
            need(oid == order['intentId'] and 0 <= order['cumulativeQuantity'] <= order['quantity'],
                 'ORDER_QUANTITY_INVARIANT')
            need(0 <= order['grossVerifiedThroughQuantity'] <= order['cumulativeQuantity'],
                 'PRICED_QUANTITY_INVARIANT')
            if order['side'] == 'BUY' and order['phase'] not in TERMINAL:
                occupied.add(order['symbol'])
            _sha(order['sourceDecisionSha256'], 'ORDER_SOURCE_HASH')
        # Late attributed fills can exceed the intended exposure.  Record them
        # and block new buys instead of rolling back a confirmed broker fill.
        for entry, position in state['positions'].items():
            need(position['entryId'] == entry and position['quantity'] >= 0 and
                 position['quantity'] == position['boughtQuantity'] - position['soldQuantity'],
                 'POSITION_QUANTITY_INVARIANT')
            pending = sum(o['quantity'] - o['cumulativeQuantity'] for o in state['orders'].values()
                          if o['entryId'] == entry and o['side'] == 'SELL' and o['phase'] not in TERMINAL)
            need(pending <= position['quantity'], 'SELL_RESERVATION_EXCEEDS_OWNED')
        for key, command_id in state['rssIds'].items():
            command = state['commands'][command_id]['command']
            need(key == self._rss_key(command['rssSessionKey'], command['rssOrderId']), 'RSS_RESERVATION_INVARIANT')

    @staticmethod
    def _rss_key(session_key, order_id):
        return json.dumps([session_key, order_id], separators=(',', ':'), ensure_ascii=False)

    @staticmethod
    def _active(order):
        return order['phase'] not in TERMINAL

    @staticmethod
    def _charges_known(order):
        q = order['cumulativeQuantity']
        return q == 0 or (order['feesVerifiedThroughQuantity'] >= q and
                          order['taxesVerifiedThroughQuantity'] >= q)

    def _order_reserve(self, order):
        remaining = order['quantity'] - order['cumulativeQuantity'] if self._active(order) else 0
        unpriced = order['cumulativeQuantity'] - order['grossVerifiedThroughQuantity']
        pending = money(order['reservePriceJpy']) * (remaining + unpriced) if order['side'] == 'BUY' else Decimal(0)
        unpaid_allowance = max(Decimal(0), money(order['reserveChargesJpy']) -
                               money(order['cumulativeFeesJpy']) - money(order['cumulativeTaxesJpy']))
        if self._active(order) or not self._charges_known(order):
            pending += unpaid_allowance
        return pending

    def _view(self, state, at):
        now = instant(at, self.session) if at is not None else None
        reservations = {oid: self._order_reserve(o) for oid, o in state['orders'].items()}
        reserved = sum(reservations.values(), Decimal(0))
        cash = money(state['cashJpy'], signed=True)
        observation = state['accountObservation']
        blockers = []
        if state['firstSellFillBuyHalt']:
            blockers.append('AFTER_FIRST_SELL_FILL')
        unknown = [o['intentId'] for o in state['orders'].values() if o['phase'] == 'UNKNOWN']
        if unknown:
            blockers.append('ORDER_RECONCILIATION_REQUIRED')
        unpriced = [o['intentId'] for o in state['orders'].values()
                    if o['grossVerifiedThroughQuantity'] < o['cumulativeQuantity']]
        if unpriced:
            blockers.append('ATTRIBUTABLE_EXECUTION_AMOUNT_REQUIRED')
        unknown_charges = [o['intentId'] for o in state['orders'].values() if not self._charges_known(o)]
        if unknown_charges:
            blockers.append('FEES_OR_TAXES_UNRECONCILED')
        if any(o.get('fillTimeConflict') for o in state['orders'].values()):
            blockers.append('FILL_TIME_RECONCILIATION_REQUIRED')
        unresolved = [c['command']['commandId'] for c in state['commands'].values()
                      if c['state'] in {'IN_FLIGHT', 'RETURNED', 'UNKNOWN'} and not c['brokerObserved']]
        if unresolved:
            blockers.append('DISPATCH_RECONCILIATION_REQUIRED')
        fresh = (observation is not None and observation['buyingPowerJpy'] is not None and now is not None
                 and 0 <= now - instant(observation['knownAtJst'], self.session) <= 30 * TICKS_PER_SECOND)
        if not fresh:
            blockers.append('FRESH_BUYING_POWER_REQUIRED')
        buying_power = money(observation['buyingPowerJpy']) if observation and observation['buyingPowerJpy'] is not None else Decimal(0)
        # Unless an observation explicitly proves reservation reflection,
        # subtract every local buy reservation from its buying-power bound.
        reflected = observation.get('reflectedOrders', {}) if observation else {}
        bp_unreflected = Decimal(0)
        for oid, order in state['orders'].items():
            if order['side'] != 'BUY':
                continue
            proof = reflected.get(order['brokerOrderNumber'])
            covered = (proof is not None and proof['cumulativeQuantity'] == order['cumulativeQuantity'] and
                       proof['reservedCashJpy'] == decimal_text(reservations[oid]))
            if not covered:
                bp_unreflected += reservations[oid]
            if observation and instant(order['knownAtJst'], self.session) > instant(observation['knownAtJst'], self.session):
                # A receipt newer than the bound may have spent cash not yet
                # reflected by it.  Require a fresh bound before further buys.
                if order['cumulativeQuantity']:
                    blockers.append('BUYING_POWER_PREDATES_FILL')
        available_cash = max(Decimal(0), cash - reserved)
        available_bp = max(Decimal(0), buying_power - bp_unreflected)
        shortfall = cash < reserved or cash < 0
        if shortfall:
            blockers.append('ACCOUNT_SHORTFALL')
        if any(o['reservationOverrun'] for o in state['orders'].values()):
            blockers.append('EXECUTION_RESERVATION_OVERRUN')
        occupied = {p['symbol'] for p in state['positions'].values() if p['quantity'] > 0}
        occupied.update(o['symbol'] for o in state['orders'].values() if o['side'] == 'BUY' and self._active(o))
        if len(occupied) > 3:
            blockers.append('CONFIRMED_EXPOSURE_EXCEEDS_MAX3')
        return {'reservedCashJpy': decimal_text(reserved), 'availableCashJpy': decimal_text(available_cash),
                'brokerBuyingPowerJpy': observation['buyingPowerJpy'] if observation else None,
                'unreflectedBuyingPowerReservationJpy': decimal_text(bp_unreflected),
                'availableBuyJpy': decimal_text(min(available_cash, available_bp)) if not blockers else '0',
                'accountShortfall': shortfall, 'newBuysAllowed': not blockers,
                'blockers': sorted(set(blockers)), 'unknownOrders': unknown,
                'unpricedOrders': unpriced, 'unknownChargeOrders': unknown_charges,
                'unresolvedCommands': unresolved, 'occupiedSymbols': sorted(occupied),
                'buyingPowerIsCash': False}

    def observe_account(self, event, at):
        need(type(event) is dict and event.get('schemaId') == ACCOUNT_SCHEMA, 'ACCOUNT_SCHEMA')
        self._evidence(event)
        eid = _sha(event.get('eventId'), 'EVENT_ID')
        need(event.get('sessionDate') == self.session and event.get('account') == self.account, 'ACCOUNT_IDENTITY')
        known = instant(event.get('knownAtJst'), self.session)
        need(known <= instant(at, self.session), 'ACCOUNT_FROM_FUTURE')
        value = event.get('buyingPowerJpy')
        if value is not None:
            value = decimal_text(money(value))
        self._symbols(event.get('externalSymbols'))
        reflected = {}
        for row in event.get('reflectedOrders', []):
            number = _text(row.get('brokerOrderNumber'), 'BROKER_ORDER_NUMBER', 32)
            need(re.fullmatch(r'[0-9]{1,32}', number) and number not in reflected, 'REFLECTION_ORDER')
            reflected[number] = {'cumulativeQuantity': _integer(row.get('cumulativeQuantity'), 'REFLECTION_QUANTITY'),
                                 'reservedCashJpy': decimal_text(money(row.get('reservedCashJpy')))}
        def apply(state):
            old = state['accountObservation']
            need(old is None or instant(old['knownAtJst'], self.session) <= known, 'ACCOUNT_CLOCK_REVERSED')
            if old is not None and instant(old['knownAtJst'], self.session) == known:
                need(old['sourceSnapshotSha256'] == event['sourceSnapshotSha256'], 'ACCOUNT_SAME_CLOCK_SOURCE_CHANGED')
            state['accountObservation'] = {'knownAtJst': event['knownAtJst'], 'buyingPowerJpy': value,
                'externalSymbols': sorted(event['externalSymbols']), 'reflectedOrders': reflected,
                'sourceSnapshotSha256': event['sourceSnapshotSha256'], 'evidenceMode': self.mode}
            return {'status': 'BUYING_POWER_BOUND_OBSERVED', 'buyingPowerIsCash': False}
        return self._event('ACCOUNT:' + eid, event, at, apply)

    def _intent(self, intent, at):
        need(type(intent) is dict and intent.get('schemaId') == INTENT_SCHEMA, 'INTENT_SCHEMA')
        obj = clone(intent)
        _sha(obj.get('intentId'), 'INTENT_ID')
        _text(obj.get('entryId'), 'ENTRY_ID')
        _sha(obj.get('sourceDecisionSha256'), 'SOURCE_DECISION_HASH')
        need(obj.get('sessionDate') == self.session and obj.get('account') == self.account, 'INTENT_SESSION_OR_ACCOUNT')
        need(type(obj.get('symbol')) is str and SYMBOL.fullmatch(obj['symbol']), 'INTENT_SYMBOL')
        need(obj.get('side') in {'BUY', 'SELL'}, 'INTENT_SIDE')
        q = _integer(obj.get('quantity'), 'INTENT_QUANTITY', 100)
        need(q % 100 == 0, 'LOT_100_REQUIRED')
        need(instant(obj.get('createdAtJst'), self.session) <= instant(at, self.session), 'INTENT_FROM_FUTURE')
        need(obj.get('sourceKind') == ('ORIGINAL_CAPITAL_V5' if obj['side'] == 'BUY' else 'ORIGINAL_EXIT'),
             'ORIGINAL_SOURCE_KIND')
        need(obj.get('band') in {'S', 'A', 'B'}, 'ORIGINAL_BAND_REQUIRED')
        price = money(obj.get('reservePriceJpy', '0'))
        need(obj['side'] != 'BUY' or price > 0, 'BUY_RESERVE_PRICE')
        obj['reservePriceJpy'] = decimal_text(price)
        obj['reserveChargesJpy'] = decimal_text(money(obj.get('reserveChargesJpy', '0')))
        return obj

    def _command(self, command, order, kind, at):
        need(type(command) is dict and command.get('schemaId') == COMMAND_SCHEMA, 'COMMAND_SCHEMA')
        obj = clone(command)
        given = obj.pop('commandSha256', None)
        need(_sha(given, 'COMMAND_HASH') == digest(obj), 'COMMAND_HASH_CHANGED')
        obj['commandSha256'] = given
        _sha(obj.get('commandId'), 'COMMAND_ID')
        _text(obj.get('rssSessionKey'), 'RSS_SESSION_KEY')
        _integer(obj.get('rssOrderId'), 'RSS_ID', 1, 2147483647)
        need(obj.get('kind') == kind and obj.get('sessionDate') == self.session and
             obj.get('evidenceMode') == COMMAND_MODES[self.mode], 'COMMAND_MODE_OR_SESSION')
        for key in ('intentId', 'symbol', 'side', 'quantity', 'account'):
            need(obj.get(key) == order[key], 'COMMAND_IDENTITY_' + key.upper())
        created = instant(obj.get('createdAtJst'), self.session)
        need(instant(order['createdAtJst'], self.session) <= created <= instant(at, self.session), 'COMMAND_CLOCK')
        need(obj.get('functionName') == ('RssStockOrder' if kind == 'ORDER' else 'RssCancelOrder'), 'COMMAND_FUNCTION')
        args = obj.get('arguments')
        need(type(args) is list and len(args) == (20 if kind == 'ORDER' else 3) and
             all(type(x) is str for x in args) and args[0] == str(obj['rssOrderId']) and args[1] == '0',
             'COMMAND_ARGUMENTS')
        if kind == 'ORDER':
            need(obj.get('targetOrderNumber') is None, 'ORDER_TARGET_MUST_BE_NULL')
            terms = obj.get('orderTerms')
            need(type(terms) is dict and terms.get('timeInForce') == 'DAY' and
                 type(terms.get('sor')) is bool and terms.get('accountTypeVerified') is True,
                 'ORDER_TERMS')
            account_type = _integer(terms.get('accountType'), 'ACCOUNT_TYPE', 0, 3)
            need(ACCOUNTS[account_type] == self.account and terms.get('orderType') in {'MARKET', 'LIMIT'},
                 'ORDER_TERMS')
            if terms['orderType'] == 'MARKET':
                need(terms.get('limitPrice') is None, 'MARKET_LIMIT_PRICE')
                limit = ''
            else:
                price = terms.get('limitPrice')
                need(type(price) in (str, int, float) and type(price) is not bool, 'LIMIT_PRICE')
                limit = _number(price) if type(price) in (int, float) else price
                need(money(limit) > 0, 'LIMIT_PRICE')
            expected = [str(obj['rssOrderId']), '0', order['symbol'], '3' if order['side'] == 'BUY' else '1',
                        '0', '1' if terms['sor'] else '0', str(order['quantity']),
                        '0' if terms['orderType'] == 'MARKET' else '1', limit, '1', '', str(account_type),
                        '', '', '', '', '0', '', '', '']
            need(args == expected, 'COMMAND_ARGUMENT_IDENTITY')
        else:
            number = obj.get('targetOrderNumber')
            need(number == order.get('brokerOrderNumber') and type(number) is str and
                 re.fullmatch(r'[1-9]\d{0,14}', number) and int(number) <= 9_007_199_254_740_991,
                 'CANCEL_TARGET')
            need(obj.get('orderTerms') is None and args == [str(obj['rssOrderId']), '0', number], 'CANCEL_ARGUMENTS')
        return obj

    def _reserve_command(self, state, command, at):
        cid = command['commandId']
        need(cid not in state['commands'], 'COMMAND_ID_ALREADY_USED')
        key = self._rss_key(command['rssSessionKey'], command['rssOrderId'])
        need(key not in state['rssIds'], 'RSS_ID_ALREADY_RESERVED')
        state['rssIds'][key] = cid
        state['commands'][cid] = {'command': command, 'state': 'PREPARED', 'preparedAtJst': at,
                                 'begunAtJst': None, 'permit': None, 'brokerObserved': False,
                                 'transportResults': []}

    def prepare_order(self, intent, command, at):
        original = self._intent(intent, at)
        compiled = self._command(command, original, 'ORDER', at)
        def apply(state):
            oid, entry = original['intentId'], original['entryId']
            need(oid not in state['orders'], 'INTENT_ALREADY_RESERVED')
            if original['side'] == 'BUY':
                view = self._view(state, at)
                need(view['newBuysAllowed'], 'NEW_BUY_BLOCKED:' + ','.join(view['blockers']))
                excluded = set(self.config.get('externalSymbols', []))
                excluded.update(state['accountObservation']['externalSymbols'])
                need(original['symbol'] not in excluded, 'EXTERNAL_SYMBOL_PROTECTED')
                need(original['symbol'] not in view['occupiedSymbols'] and entry not in state['positions'] and
                     not any(o['side'] == 'BUY' and o['entryId'] == entry for o in state['orders'].values()),
                     'ENTRY_OR_SYMBOL_ALREADY_OWNED')
                need(len(view['occupiedSymbols']) < 3, 'MAX3_SLOTS')
                reserve = money(original['reservePriceJpy']) * original['quantity'] + money(original['reserveChargesJpy'])
                need(reserve <= money(view['availableBuyJpy']), 'ALLOCATION_OR_BUYING_POWER_BOUND')
            else:
                need(entry in state['positions'], 'SELL_NOT_ARK_OWNED')
                position = state['positions'][entry]
                need(position['symbol'] == original['symbol'] and position['account'] == original['account'] and
                     position['band'] == original['band'], 'SELL_POSITION_IDENTITY')
                reserved = sum(o['quantity'] - o['cumulativeQuantity'] for o in state['orders'].values()
                               if o['side'] == 'SELL' and o['entryId'] == entry and self._active(o))
                need(original['quantity'] <= position['quantity'] - reserved, 'SELL_EXCEEDS_UNRESERVED_OWNED')
            order = dict(original, commandId=compiled['commandId'], rssSessionKey=compiled['rssSessionKey'],
                         rssOrderId=compiled['rssOrderId'], brokerOrderNumber=None, phase='PREPARED',
                         observedPhase=None, cumulativeQuantity=0, knownGrossJpy='0', grossVerifiedThroughQuantity=0,
                         cumulativeFeesJpy='0', cumulativeTaxesJpy='0', feesVerifiedThroughQuantity=0,
                         taxesVerifiedThroughQuantity=0, knownAtJst=at, quantityKnownAtJst=at,
                         filledAtJst=None, fillTimeVerified=False, fillTimeConflict=False,
                         brokerBindingVerified=False,
                         cancelRequested=False, cancelNeeded=False, reservationOverrun=False,
                         terminalRevisionObserved=False, lastReceiptSha256=None)
            state['orders'][oid] = order
            self._reserve_command(state, compiled, at)
            return {'status': 'ORDER_PREPARED_AND_RESERVED', 'intentId': oid, 'commandId': compiled['commandId']}
        return self._event('PREPARE:' + compiled['commandId'], {'intent': original, 'command': compiled}, at, apply)

    def begin_dispatch(self, command_id, at):
        _sha(command_id, 'COMMAND_ID')
        def apply(state):
            need(command_id in state['commands'], 'COMMAND_UNKNOWN')
            record = state['commands'][command_id]
            need(record['state'] == 'PREPARED' and record['begunAtJst'] is None, 'DISPATCH_ALREADY_STARTED')
            command = record['command']
            order = state['orders'][command['intentId']]
            need(self._active(order), 'ORDER_ALREADY_TERMINAL')
            if command['kind'] == 'ORDER':
                need(order['phase'] == 'PREPARED', 'ORDER_NOT_PREPARED')
                if order['side'] == 'BUY':
                    view = self._view(state, at)
                    # Other commands from this already-reserved batch may be
                    # awaiting broker observation.  They cannot be prepared a
                    # second time, but do not invalidate the batch reservation.
                    blockers = [x for x in view['blockers'] if x != 'DISPATCH_RECONCILIATION_REQUIRED']
                    need(not blockers and money(view['reservedCashJpy']) <= money(state['cashJpy'], signed=True),
                         'RESERVED_BUY_BLOCKED:' + ','.join(blockers))
                    need(money(view['unreflectedBuyingPowerReservationJpy']) <=
                         money(view['brokerBuyingPowerJpy']), 'BUYING_POWER_BOUND_CHANGED')
                    excluded = set(self.config.get('externalSymbols', []))
                    excluded.update(state['accountObservation']['externalSymbols'])
                    need(order['symbol'] not in excluded, 'EXTERNAL_SYMBOL_PROTECTED')
                order['phase'] = 'IN_FLIGHT'
            else:
                need(order['brokerOrderNumber'] == command['targetOrderNumber'] and
                     order['observedPhase'] in {'ACKNOWLEDGED', 'PARTIAL'} and
                     order['cumulativeQuantity'] < order['quantity'], 'CANCEL_TARGET_NOT_ACTIVE')
            core = {'schemaId': PERMIT_SCHEMA, 'commandId': command_id,
                    'commandSha256': command['commandSha256'], 'kind': command['kind'],
                    'sessionDate': self.session, 'rssSessionKey': command['rssSessionKey'],
                    'rssOrderId': command['rssOrderId'], 'intentId': command['intentId'],
                    'targetOrderNumber': command['targetOrderNumber'],
                    'preparedAtJst': record['preparedAtJst'], 'begunAtJst': at, 'state': 'IN_FLIGHT_COMMITTED'}
            permit = dict(core, permitSha256=digest(core))
            record.update(state='IN_FLIGHT', begunAtJst=at, permit=permit)
            return {'status': 'DISPATCH_BEGUN_ONCE', 'commandId': command_id, 'dispatchPermit': permit}
        return self._event('BEGIN:' + command_id, {'commandId': command_id}, at, apply, once=True)

    def record_transport_result(self, command_id, result, at):
        _sha(command_id, 'COMMAND_ID')
        need(type(result) is dict and result.get('commandId') == command_id, 'TRANSPORT_RESULT_IDENTITY')
        eid = _sha(result.get('eventId'), 'EVENT_ID')
        _sha(result.get('transportReceiptSha256'), 'TRANSPORT_RECEIPT_HASH')
        known = instant(result.get('knownAtJst'), self.session)
        need(known <= instant(at, self.session) and result.get('outcome') in {'RETURNED', 'UNKNOWN', 'NOT_SENT'},
             'TRANSPORT_RESULT')
        need(type(result.get('definitelyNotInvoked')) is bool, 'TRANSPORT_INVOCATION_EVIDENCE')
        need(result['outcome'] != 'NOT_SENT' or result['definitelyNotInvoked'] is True,
             'NO_INVOKE_PROOF_REQUIRED')
        need(result['outcome'] == 'NOT_SENT' or result['definitelyNotInvoked'] is False,
             'TRANSPORT_INVOCATION_CONTRADICTION')
        def apply(state):
            need(command_id in state['commands'], 'COMMAND_UNKNOWN')
            record = state['commands'][command_id]
            need(record['begunAtJst'] is not None and known >= instant(record['begunAtJst'], self.session),
                 'TRANSPORT_RESULT_BEFORE_BEGIN')
            need(record['state'] != 'NOT_SENT', 'TRANSPORT_RESULT_AFTER_NOT_SENT')
            if record['transportResults']:
                need(known >= instant(record['transportResults'][-1]['knownAtJst'], self.session),
                     'TRANSPORT_RESULT_CLOCK_REVERSED')
            order = state['orders'][record['command']['intentId']]
            if result['outcome'] == 'NOT_SENT':
                need(not record['brokerObserved'] and not record['transportResults'], 'NO_INVOKE_PROOF_CONTRADICTS_HISTORY')
                record['state'] = 'NOT_SENT'
                if record['command']['kind'] == 'ORDER':
                    need(order['cumulativeQuantity'] == 0 and order['brokerOrderNumber'] is None,
                         'NO_INVOKE_PROOF_CONTRADICTS_ORDER')
                    order['phase'] = 'LOCAL_WITHDRAWN'
                else:
                    order['cancelRequested'] = False
                    order['phase'] = order['observedPhase']
            else:
                record['state'] = result['outcome']
                if result['outcome'] == 'UNKNOWN' and not record['brokerObserved']:
                    order['phase'] = 'UNKNOWN'
            record['transportResults'].append(clone(result))
            return {'status': 'TRANSPORT_RESULT_RECORDED_NOT_BROKER_ACK', 'commandId': command_id,
                    'orderPhase': order['phase'], 'orderCanBeResent': False}
        return self._event('TRANSPORT:' + eid, result, at, apply)

    def request_cancel(self, intent_id, command, at):
        _sha(intent_id, 'INTENT_ID')
        # Validation is repeated under the transaction using the current order.
        need(type(command) is dict, 'COMMAND_SCHEMA')
        cid = _sha(command.get('commandId'), 'COMMAND_ID')
        def apply(state):
            need(intent_id in state['orders'], 'ORDER_UNKNOWN')
            order = state['orders'][intent_id]
            compiled = self._command(command, order, 'CANCEL', at)
            need(self._active(order) and order['phase'] != 'UNKNOWN' and
                 order['observedPhase'] in {'ACKNOWLEDGED', 'PARTIAL'} and
                 order['cumulativeQuantity'] < order['quantity'], 'CANCEL_REQUIRES_KNOWN_ACTIVE_ORDER')
            existing = [c for c in state['commands'].values() if c['command']['kind'] == 'CANCEL'
                        and c['command']['intentId'] == intent_id and c['state'] not in {'NOT_SENT', 'OBSOLETE'}]
            need(not existing, 'CANCEL_ALREADY_REQUESTED')
            self._reserve_command(state, compiled, at)
            order.update(cancelRequested=True, phase='CANCEL_REQUESTED')
            return {'status': 'CANCEL_PREPARED_NO_RELEASE', 'intentId': intent_id, 'commandId': cid}
        return self._event('CANCEL:' + cid, {'intentId': intent_id, 'command': command}, at, apply)

    def withdraw_prepared(self, intent_id, at):
        """Withdraw a never-dispatched local intent; never fabricate broker ACK."""
        def apply(state):
            need(intent_id in state['orders'], 'ORDER_UNKNOWN')
            order = state['orders'][intent_id]
            record = state['commands'][order['commandId']]
            need(record['state'] == 'PREPARED' and record['begunAtJst'] is None and
                 order['phase'] == 'PREPARED', 'LOCAL_WITHDRAW_REQUIRES_NEVER_DISPATCHED')
            record['state'] = 'NOT_SENT'
            order['phase'] = 'LOCAL_WITHDRAWN'
            return {'status': 'LOCAL_INTENT_WITHDRAWN_NOT_BROKER_CANCEL', 'intentId': intent_id}
        return self._event('WITHDRAW:' + intent_id, {'intentId': intent_id}, at, apply)

    def abandon_prepared(self, command_id, at):
        """Recover only a command whose dispatch was provably never begun.

        Its RSS ID stays consumed forever in this namespace.  This is a local
        withdrawal, never a simulated broker cancellation or acknowledgement.
        """
        _sha(command_id, 'COMMAND_ID')
        def apply(state):
            need(command_id in state['commands'], 'COMMAND_UNKNOWN')
            record = state['commands'][command_id]
            need(record['state'] == 'PREPARED' and record['begunAtJst'] is None,
                 'ABANDON_REQUIRES_NEVER_DISPATCHED')
            order = state['orders'][record['command']['intentId']]
            if record['command']['kind'] == 'ORDER':
                need(order['phase'] == 'PREPARED' and order['cumulativeQuantity'] == 0 and
                     order['brokerOrderNumber'] is None, 'ABANDON_ORDER_ALREADY_OBSERVED')
                order['phase'] = 'LOCAL_WITHDRAWN'
            else:
                order['cancelRequested'] = False
                if order['phase'] not in TERMINAL:
                    need(order['observedPhase'] in RECEIPT_PHASES, 'ABANDON_CANCEL_OBSERVATION_MISSING')
                    order['phase'] = order['observedPhase']
            record['state'] = 'NOT_SENT'
            return {'status': 'NEVER_BEGUN_COMMAND_ABANDONED', 'commandId': command_id,
                    'kind': record['command']['kind'], 'rssIdRemainsReserved': True,
                    'brokerCancellationAcknowledged': False}
        return self._event('ABANDON:' + command_id, {'commandId': command_id}, at, apply)

    def apply_receipt(self, receipt, at):
        need(type(receipt) is dict and receipt.get('schemaId') == RECEIPT_SCHEMA, 'RECEIPT_SCHEMA')
        self._evidence(receipt)
        eid = _sha(receipt.get('eventId'), 'EVENT_ID')
        oid = _sha(receipt.get('intentId'), 'INTENT_ID')
        _sha(receipt.get('allocationEvidenceSha256'), 'ALLOCATION_EVIDENCE_HASH')
        need(receipt.get('quantityAttributionVerified') is True, 'QUANTITY_ATTRIBUTION_REQUIRED')
        need(receipt.get('sessionDate') == self.session, 'RECEIPT_SESSION')
        known = instant(receipt.get('knownAtJst'), self.session)
        need(known <= instant(at, self.session), 'RECEIPT_FROM_FUTURE')
        quantity = _integer(receipt.get('cumulativeQuantity'), 'RECEIPT_QUANTITY')
        phase = receipt.get('status')
        need(type(phase) is str and phase in RECEIPT_PHASES, 'RECEIPT_STATUS')
        gross = money(receipt['cumulativeGrossJpy']) if receipt.get('cumulativeGrossJpy') is not None else None
        if gross is not None and quantity > 0:
            need(receipt.get('attributionVerified') is True and gross > 0, 'EXECUTION_AMOUNT_ATTRIBUTION_REQUIRED')
        else:
            need(type(receipt.get('attributionVerified')) is bool, 'ATTRIBUTION_FLAG')
        need(quantity > 0 or gross in (None, Decimal(0)), 'GROSS_WITHOUT_FILL')
        fees = money(receipt['cumulativeFeesJpy']) if receipt.get('cumulativeFeesJpy') is not None else None
        taxes = money(receipt['cumulativeTaxesJpy']) if receipt.get('cumulativeTaxesJpy') is not None else None
        first_fill = receipt.get('filledAtJst')
        if first_fill is not None:
            need(quantity > 0 and receipt.get('fillTimeVerified') is True and
                 instant(first_fill, self.session) <= known, 'FILL_TIME_NOT_VERIFIED')
        else:
            need(receipt.get('fillTimeVerified', False) is False, 'FILL_TIME_FLAG')
        time_conflict = receipt.get('fillTimeConflict', False)
        need(type(time_conflict) is bool and (not time_conflict or first_fill is None), 'FILL_TIME_CONFLICT_FLAG')
        quantity_known = instant(receipt.get('quantityKnownAtJst', receipt['knownAtJst']), self.session)
        need(quantity_known <= known, 'QUANTITY_FROM_FUTURE')
        number = receipt.get('brokerOrderNumber')
        need(type(number) is str and re.fullmatch(r'[0-9]{1,32}', number) and int(number) > 0, 'BROKER_ORDER_NUMBER')
        def apply(state):
            need(oid in state['orders'], 'ORDER_UNKNOWN')
            order = state['orders'][oid]
            record = state['commands'][order['commandId']]
            need(record['begunAtJst'] is not None and record['state'] != 'NOT_SENT', 'RECEIPT_WITHOUT_DISPATCH_BEGIN')
            for key in ('rssSessionKey', 'rssOrderId', 'symbol', 'side', 'account'):
                need(receipt.get(key) == order[key], 'RECEIPT_IDENTITY_' + key.upper())
            need(known >= instant(order['knownAtJst'], self.session) and
                 known >= instant(record['begunAtJst'], self.session), 'RECEIPT_CLOCK_REVERSED')
            need(quantity_known >= instant(record['begunAtJst'], self.session), 'QUANTITY_BEFORE_DISPATCH')
            need(order['brokerOrderNumber'] in (None, number), 'BROKER_ORDER_NUMBER_CHANGED')
            owner = state['brokerOrders'].get(number)
            need(owner in (None, oid), 'BROKER_ORDER_ASSIGNED_TWICE')
            need(order['cumulativeQuantity'] <= quantity <= order['quantity'], 'CUMULATIVE_QUANTITY_REVERSED_OR_OVERFILL')
            old_gross = money(order['knownGrossJpy'])
            old_fees, old_taxes = money(order['cumulativeFeesJpy']), money(order['cumulativeTaxesJpy'])
            need(gross is None or gross >= old_gross, 'CUMULATIVE_GROSS_REVERSED')
            need(gross is None or quantity <= order['grossVerifiedThroughQuantity'] or gross > old_gross,
                 'NEW_PRICED_QUANTITY_WITHOUT_CONSIDERATION')
            need(fees is None or fees >= old_fees, 'CUMULATIVE_FEES_REVERSED')
            need(taxes is None or taxes >= old_taxes, 'CUMULATIVE_TAXES_REVERSED')
            need(phase != 'FILLED' or quantity == order['quantity'], 'FALSE_FULL_FILL')
            need(phase != 'PARTIAL' or 0 < quantity < order['quantity'], 'FALSE_PARTIAL_FILL')
            need(phase not in {'ACKNOWLEDGED', 'REJECTED'} or quantity == 0, 'FALSE_UNFILLED_STATUS')
            if order['phase'] in TERMINAL:
                need(phase == order['observedPhase'] or phase == 'FILLED' and quantity == order['quantity'],
                     'TERMINAL_ORDER_REOPENED')
                if quantity > order['cumulativeQuantity']:
                    order['terminalRevisionObserved'] = True
            if first_fill is not None:
                floor_origin = instant(order['createdAtJst'], self.session) // TICKS_PER_SECOND * TICKS_PER_SECOND
                need(instant(first_fill, self.session) >= floor_origin, 'FILL_BEFORE_ORIGIN')
                need(order['filledAtJst'] is None or instant(order['filledAtJst'], self.session) ==
                     instant(first_fill, self.session), 'FIRST_FILL_TIME_CHANGED')
            dq = quantity - order['cumulativeQuantity']
            dg = Decimal(0) if gross is None else gross - old_gross
            df = Decimal(0) if fees is None else fees - old_fees
            dt = Decimal(0) if taxes is None else taxes - old_taxes
            if order['side'] == 'BUY':
                cash_delta = -dg - df - dt
                if quantity > 0:
                    position = state['positions'].get(order['entryId'])
                    if position is None:
                        position = {'entryId': order['entryId'], 'symbol': order['symbol'], 'account': self.account,
                                    'band': order['band'], 'quantity': 0, 'boughtQuantity': 0, 'soldQuantity': 0,
                                    'buyIntentId': oid, 'filledAtJst': None, 'fillTimeVerified': False,
                                    'fillTimeConflict': False}
                        state['positions'][order['entryId']] = position
                    need(position['buyIntentId'] == oid, 'BUY_ENTRY_ID_REUSED')
                    position['quantity'] += dq
                    position['boughtQuantity'] += dq
                    if first_fill is not None:
                        position.update(filledAtJst=first_fill, fillTimeVerified=True)
                    if time_conflict or order['fillTimeConflict']:
                        position.update(fillTimeConflict=True, fillTimeVerified=False)
            else:
                cash_delta = dg - df - dt
                if dq:
                    need(order['entryId'] in state['positions'], 'SELL_NOT_ARK_OWNED')
                    position = state['positions'][order['entryId']]
                    need(dq <= position['quantity'], 'SELL_EXCEEDS_OWNED')
                    position['quantity'] -= dq
                    position['soldQuantity'] += dq
                    state['firstSellFillBuyHalt'] = True
                    if state['firstSellFillObservedAtJst'] is None:
                        state['firstSellFillObservedAtJst'] = receipt['knownAtJst']
                    for buy in state['orders'].values():
                        if buy['side'] == 'BUY' and self._active(buy):
                            buy['cancelNeeded'] = True  # request only; no fake ACK
            state['cashJpy'] = decimal_text(money(state['cashJpy'], signed=True) + cash_delta)
            order['cumulativeQuantity'] = quantity
            if dq:
                order['quantityKnownAtJst'] = receipt.get('quantityKnownAtJst', receipt['knownAtJst'])
            if gross is not None:
                order['knownGrossJpy'] = decimal_text(gross)
                order['grossVerifiedThroughQuantity'] = quantity
            if fees is not None:
                order['cumulativeFeesJpy'] = decimal_text(fees)
                order['feesVerifiedThroughQuantity'] = quantity
            if taxes is not None:
                order['cumulativeTaxesJpy'] = decimal_text(taxes)
                order['taxesVerifiedThroughQuantity'] = quantity
            if first_fill is not None:
                order['filledAtJst'] = first_fill
                order['fillTimeVerified'] = True
            if time_conflict or order['fillTimeConflict']:
                order.update(fillTimeConflict=True, fillTimeVerified=False)
            if order['side'] == 'BUY' and gross is not None:
                actual = gross + money(order['cumulativeFeesJpy']) + money(order['cumulativeTaxesJpy'])
                ceiling = money(order['reservePriceJpy']) * quantity + money(order['reserveChargesJpy'])
                if actual > ceiling:
                    order['reservationOverrun'] = True
            order.update(brokerOrderNumber=number, brokerBindingVerified=True,
                         knownAtJst=receipt['knownAtJst'], observedPhase=phase,
                         lastReceiptSha256=digest(receipt))
            if phase == 'UNKNOWN' or phase in TERMINAL:
                order['phase'] = phase
            else:
                order['phase'] = 'CANCEL_REQUESTED' if order['cancelRequested'] and phase != 'CANCEL_PENDING' else phase
            state['brokerOrders'][number] = oid
            record['brokerObserved'] = phase != 'UNKNOWN'
            for cancel in state['commands'].values():
                if cancel['command']['kind'] == 'CANCEL' and cancel['command']['intentId'] == oid:
                    if phase in {'CANCEL_PENDING', 'CANCELLED', 'EXPIRED', 'FILLED'}:
                        cancel['brokerObserved'] = True
                    if phase in TERMINAL and cancel['state'] == 'PREPARED':
                        cancel['state'] = 'OBSOLETE'
            return {'status': 'BROKER_OBSERVATION_APPLIED', 'intentId': oid, 'phase': order['phase'],
                    'filledQuantityDelta': dq, 'knownCashDeltaJpy': decimal_text(cash_delta),
                    'firstSellFillBuyHalt': state['firstSellFillBuyHalt'], 'orderCanBeResent': False}
        return self._event('RECEIPT:' + eid, receipt, at, apply)

    def checkpoint_source(self, name, value, at, expected_sha256=None):
        _text(name, 'CHECKPOINT_NAME', 128)
        obj, sha = clone(value), digest(value)
        if expected_sha256 is not None:
            _sha(expected_sha256, 'CHECKPOINT_EXPECTED_HASH')
        def apply(state):
            old = state['sourceCheckpoints'].get(name)
            if expected_sha256 is not None:
                need(old is not None and old['sha256'] == expected_sha256, 'CHECKPOINT_COMPARE_AND_SWAP')
            state['sourceCheckpoints'][name] = {'value': obj, 'sha256': sha, 'knownAtJst': at}
            return {'status': 'SOURCE_CHECKPOINT_SAVED', 'name': name, 'sha256': sha}
        return self._event('CHECKPOINT:' + digest([name, sha, expected_sha256]),
                           {'name': name, 'value': obj, 'expectedSha256': expected_sha256}, at, apply)

    def source_checkpoint(self, name):
        _text(name, 'CHECKPOINT_NAME', 128)
        old = self._read()['sourceCheckpoints'].get(name)
        return deepcopy(old['value']) if old is not None else None

    def snapshot(self, at=None):
        state = self._read()
        through = at if at is not None else state['clock']
        if through is not None:
            need(state['clock'] is None or instant(through, self.session) >= instant(state['clock'], self.session),
                 'SNAPSHOT_CLOCK_REVERSED')
        result = clone(state)
        result.pop('pin')
        result.pop('rssIds')
        result.pop('brokerOrders')
        result.update(self._view(state, through))
        for record in result['commands'].values():
            # Audit hashes remain inspectable, but a restart API does not hand
            # a caller an old permit which could be mistaken for a fresh one.
            saved = record.pop('permit')
            record['permitSha256'] = saved['permitSha256'] if saved is not None else None
        for oid, order in result['orders'].items():
            order['cumulativeGrossJpy'] = order['knownGrossJpy'] if order['grossVerifiedThroughQuantity'] == order['cumulativeQuantity'] else None
            order['reservedCashJpy'] = decimal_text(self._order_reserve(state['orders'][oid]))
            order['feesAndTaxesKnown'] = self._charges_known(order)
            order['orderCanBeResent'] = False
        for position in result['positions'].values():
            buy = state['orders'][position['buyIntentId']]
            total = money(buy['knownGrossJpy']) + money(buy['cumulativeFeesJpy']) + money(buy['cumulativeTaxesJpy'])
            remaining_cost = total * position['quantity'] / position['boughtQuantity'] if position['boughtQuantity'] else Decimal(0)
            position['knownCostJpy'] = decimal_text(remaining_cost.quantize(Decimal('0.000001')))
            position['costComplete'] = (buy['grossVerifiedThroughQuantity'] == buy['cumulativeQuantity'] and self._charges_known(buy))
            position['firstReportedFillAtJst'] = position['filledAtJst']
            if not position['fillTimeVerified']:
                position['filledAtJst'] = None
        result.update(schemaId=SNAPSHOT_SCHEMA, evaluatedAtJst=through,
                      positionCount=sum(p['quantity'] > 0 for p in state['positions'].values()),
                      dispatchStarted=any(c['begunAtJst'] is not None for c in state['commands'].values()),
                      observedOrderEvidencePresent=any(c['brokerObserved'] for c in state['commands'].values()),
                      actualTransportRequested=self.mode == 'BROKER_OBSERVATION' and any(c['begunAtJst'] is not None for c in state['commands'].values()),
                      actualTransportObserved=self.mode == 'BROKER_OBSERVATION' and any(c['brokerObserved'] for c in state['commands'].values()),
                      brokerIoPerformed=False, orderTransmission=False, productionReady=False,
                      realFillsAppliedToShadow=False)
        return result
