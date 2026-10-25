"""Received No.1.1 decisions -> durable observed orders -> one-shot transport.

The ordinary bootstrap always supplies ``--broker-execution-readonly``. This
coordinator therefore observes or produces drafts unless a separate explicit
session-bound LIVE configuration is supplied to the direct service entry.
No real configuration or broker call is made by the offline test suite.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import no11_broker_execution_ledger as ledger
import no11_broker_fill_attribution as attribution
import no11_broker_decision_bridge as decisions
import no11_h235_asof_forward_shadow as h
import no11_h235_capital_v5_shadow as capital
import no11_rss_state9_p1_runner as received
from no11_observed_execution_shadow import ExecutionShadow

CONFIG = 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1'
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError)


def need(ok, code):
    if not ok:
        raise ValueError('NO11_BROKER_SERVICE_' + code)


def now_jst():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='milliseconds')


def safe_reason(error):
    text = str(error)
    return text if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', text) else 'NO11_BROKER_SERVICE_INPUT_OR_RUNTIME_FAILURE'


def private_path(value, *, directory=False, exists=True):
    need(isinstance(value, (str, Path)) and bool(str(value)), 'PRIVATE_PATH')
    path = Path(value)
    need(path.is_absolute(), 'ABSOLUTE_PRIVATE_PATH')
    path = path.absolute()
    need(path != ROOT and ROOT not in path.parents and not path.is_symlink()
         and not any(p.is_symlink() for p in path.parents), 'PRIVATE_PATH')
    if exists:
        need(path.is_dir() if directory else path.is_file(), 'PRIVATE_SOURCE_MISSING')
    else:
        need(path.parent.is_dir() and not path.exists(), 'PRIVATE_OUTPUT_EXISTS')
    return path


def read_private(value, limit=25_000_000):
    path = private_path(value)
    need(0 < path.stat().st_size <= limit, 'PRIVATE_SOURCE_SIZE')
    data = path.read_bytes()
    return json.loads(data.decode('utf-8-sig')), hashlib.sha256(data).hexdigest()


def exclusive_json(path, value):
    path = Path(path)
    data = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if path.exists():
        private_path(path)
        need(path.read_bytes() == data, 'PRIVATE_EVIDENCE_CHANGED')
    else:
        private_path(path, exists=False)
        with path.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    return path


def node_bridge(request):
    result = subprocess.run(['node', str(HERE / 'no11_broker_bridge.mjs')],
        input=json.dumps(request, ensure_ascii=False, separators=(',', ':'), allow_nan=False),
        capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
    if result.returncode:
        raise ValueError(safe_reason(result.stderr.strip()))
    return json.loads(result.stdout)


def validate_config(config, session, *, read_only=False):
    need(type(config) is dict and config.get('schemaId') == CONFIG and
         config.get('sessionDate') == session, 'CONFIG')
    ledger.instant(session + 'T00:00:00+09:00', session)
    need(config.get('evidenceMode') in ledger.MODES, 'EVIDENCE_MODE')
    book, transport = config.get('ledger'), config.get('transport')
    need(type(book) is dict and book.get('schemaId') == ledger.CONFIG_SCHEMA
         and book.get('sessionDate') == session and book.get('evidenceMode') == config['evidenceMode'], 'LEDGER_CONFIG')
    need(type(transport) is dict and transport.get('mode') in ('DISABLED', 'OBSERVE_ONLY', 'LIVE'), 'TRANSPORT_CONFIG')
    live = transport['mode'] == 'LIVE'
    need(config.get('productionReady') is False and config.get('orderTransmission') is live,
         'CONFIG_TRANSMISSION_FLAG')
    need(not read_only or not live, 'READONLY_LAUNCHER_CANNOT_TRANSMIT')
    need(not live or config['evidenceMode'] == 'BROKER_OBSERVATION', 'LIVE_REQUIRES_OBSERVED_EVIDENCE')
    need(not live or (transport.get('orderTransmission') is True and transport.get('operatorEnabled') is True
         and transport.get('approvedForSession') is True and transport.get('sessionDate') == session), 'LIVE_OPERATOR_CONFIGURATION')
    need(live or transport.get('orderTransmission', False) is False, 'DISABLED_TRANSMISSION')
    terms = config.get('orderTerms')
    need(type(terms) is dict and set(terms) == {'orderType', 'limitPrice', 'timeInForce', 'sor', 'accountType', 'accountTypeVerified'}
         and terms['orderType'] == 'MARKET' and terms['limitPrice'] is None
         and terms['timeInForce'] == 'DAY' and type(terms['sor']) is bool
         and type(terms['accountType']) is int and 0 <= terms['accountType'] < len(ledger.ACCOUNTS)
         and ledger.ACCOUNTS[terms['accountType']] == book.get('account')
         and terms['accountTypeVerified'] is True, 'ORIGINAL_ORDER_TERMS')
    ledger.money(config.get('reserveChargesJpy', '0'))
    return deepcopy(config)


def settings(path, session, *, read_only=False):
    config, _ = read_private(path, 100_000)
    config = validate_config(config, session, read_only=read_only)
    for name in ('accountObservationFile', 'feesEvidenceFile', 'buyingPowerEvidenceFile'):
        if config.get(name):
            # The observer's atomic output may not exist before startup.
            p = Path(config[name])
            if name == 'accountObservationFile' and not p.exists():
                private_path(p, exists=False)
            else:
                private_path(p)
    arrival = capital.original_arrival_tables(config['originalArrivalTable'])
    return config, arrival


class BrokerExecution:
    """A dedicated real-observation ledger, never a synthetic portfolio."""

    def __init__(self, root, config, arrival, runtime, previous, prior, *,
                 bridge=node_bridge, replay_dispatch=None, clock=now_jst):
        self.root = private_path(root, directory=True)
        self.session = config['sessionDate']
        self.config = validate_config(config, self.session)
        self.arrival, self.runtime, self.previous, self.prior = arrival, runtime, previous, prior
        self.bridge, self.clock, self.replay_dispatch = bridge, clock, replay_dispatch
        need(replay_dispatch is None or (callable(replay_dispatch)
             and config['evidenceMode'] == 'OFFLINE_REPLAY' and config['transport']['mode'] != 'LIVE'),
             'REPLAY_SINK_ONLY_FOR_OFFLINE_EVIDENCE')
        self.book = ledger.BrokerExecutionLedger(self.root / ('broker-execution-' + self.session + '.sqlite'), config['ledger'])
        try:
            identity = {'configSha256': ledger.digest(config), 'previousContextSha256': h.digest(previous)}
            old = self.book.source_checkpoint('controller.identity')
            need(old is None or old == identity, 'RECOVERY_CONFIG_OR_PREVIOUS_CHANGED')
            if old is None:
                self.book.checkpoint_source('controller.identity', identity, self.clock())
            self.source = None
            stored = self.book.source_checkpoint('broker.normalized')
            if stored is not None:
                # Keep JS member ordering: the normalizer's hash is JSON.stringify,
                # whereas ledger events deliberately use canonical sorted keys.
                self.source = json.loads(stored['json'])
            for cid, command in self.book.snapshot(self.clock())['commands'].items():
                if command['state'] == 'PREPARED':
                    self.book.abandon_prepared(cid, self.clock())
        except BaseException:
            self.book.close()
            raise
        self.streams, self.stream_seen = {}, {}
        self.source_error = 'NO11_BROKER_SERVICE_SOURCE_NOT_OBSERVED'
        self.last_raw_hash = None
        self.last_decision = None
        self.last_exit = None
        self.drafts = []

    def close(self):
        self.book.close()

    @property
    def entry_halted(self):
        return bool(self.book.source_checkpoint('controller.entryHalt'))

    def halt_entry(self, reason, at):
        code = safe_reason(reason)
        reasons = self.book.source_checkpoint('controller.entryHalt') or []
        if code not in reasons:
            self.book.checkpoint_source('controller.entryHalt', sorted(reasons + [code]), at)

    def _source_current(self, at):
        if self.source is None or self.source_error is not None:
            return False
        age = ledger.instant(at, self.session) - ledger.instant(self.source['captureCompletedAt'], self.session)
        return 0 <= age <= 30 * ledger.TICKS_PER_SECOND

    def _fees(self):
        path = self.config.get('feesEvidenceFile')
        if path is None:
            return {}
        value, _ = read_private(path, 1_000_000)
        need(value.get('schemaId') == 'ARK_NO11_BROKER_CHARGE_EVIDENCE_V1'
             and value.get('sessionDate') == self.session and type(value.get('orders')) is list
             and len(value['orders']) <= 1000, 'CHARGE_EVIDENCE')
        result = {}
        for row in value['orders']:
            number = row.get('brokerOrderNumber')
            need(type(number) is str and number not in result, 'CHARGE_EVIDENCE_DUPLICATE')
            result[number] = row
        return result

    def _buying_power_verified(self, at):
        if not self._source_current(at):
            return False
        if self.config['evidenceMode'] == 'OFFLINE_REPLAY':
            return True
        filename = self.config.get('buyingPowerEvidenceFile')
        if filename is None:
            return False
        try:
            proof, _ = read_private(filename, 100_000)
            need(proof.get('schemaId') == 'ARK_NO11_MSII_BUYING_POWER_REFRESH_V1'
                 and proof.get('sessionDate') == self.session
                 and proof.get('rssSessionKey') == self.source['sessionKey']
                 and proof.get('refreshObserved') is True
                 and proof.get('sourceKind') == 'MSII_ACCOUNT_TAB_REFRESH_OBSERVED'
                 and isinstance(proof.get('sourceSha256'), str)
                 and re.fullmatch(r'[a-f0-9]{64}', proof['sourceSha256']), 'BUYING_POWER_REFRESH_EVIDENCE')
            refreshed = ledger.instant(proof['refreshedAtJst'], self.session)
            capture = ledger.instant(self.source['capturedAt'], self.session)
            need(0 <= ledger.instant(at, self.session) - refreshed <= 30 * ledger.TICKS_PER_SECOND
                 and refreshed <= capture and ledger.money(proof['observedBuyingPowerJpy']) == Decimal(str(self.source['buyingPower'])),
                 'BUYING_POWER_REFRESH_CLOCK_OR_AMOUNT')
            return True
        except ERRORS:
            return False

    def observe_envelope(self, envelope, at):
        """Read-only normalization and reconciliation; no dispatch from here."""
        need(type(envelope) is dict and envelope.get('schemaId') == 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1'
             and envelope.get('status') == 'OBSERVED' and envelope.get('readOnly') is True
             and envelope.get('productionReady') is False and envelope.get('orderTransmission') is False
             and type(envelope.get('snapshot')) is dict, 'ACCOUNT_ENVELOPE')
        normalized = self.bridge({'action': 'normalize', 'input': {
            'brokerObservation': envelope.get('brokerObservation'), 'sessionDate': self.session,
            'throughJst': at, 'previous': self.source, 'accountSnapshot': envelope.get('snapshot')}})
        source_state = self.book.source_checkpoint('broker.executionRows')
        new_state = attribution.inspect_source(normalized, self.session, at, source_state)
        snapshot = self.book.snapshot(at)
        fee_failure = None
        try:
            fee_rows = self._fees()
        except ERRORS as error:
            # A charge-file problem cannot erase a separately proven fill.
            fee_rows, fee_failure = {}, safe_reason(error)
        semantics = self.book.source_checkpoint('broker.receiptSemantics') or {}
        updated = dict(semantics)
        unresolved = {}
        if fee_failure:
            unresolved['charges'] = [fee_failure]
        for oid, order in snapshot['orders'].items():
            command = snapshot['commands'][order['commandId']]
            if command['begunAtJst'] is None or command['state'] == 'NOT_SENT':
                continue
            origin = {k: order.get(k) for k in ('intentId', 'sessionDate', 'rssSessionKey', 'rssOrderId',
                'createdAtJst', 'symbol', 'side', 'account', 'quantity', 'cumulativeQuantity',
                'brokerOrderNumber', 'brokerBindingVerified', 'filledAtJst', 'fillTimeVerified',
                'fillTimeConflict', 'quantityKnownAtJst', 'knownGrossJpy', 'grossVerifiedThroughQuantity',
                'cumulativeFeesJpy', 'cumulativeTaxesJpy', 'feesVerifiedThroughQuantity', 'taxesVerifiedThroughQuantity')}
            try:
                # ID binding precedes fee lookup when the first broker number
                # has not yet been persisted by the ledger.
                first = attribution.attribute_order(origin, normalized, session=self.session, through=at,
                    source_state=source_state, evidence_mode=self.config['evidenceMode'])
                charge = fee_rows.get(first['receipt']['brokerOrderNumber'])
                evidence = first if charge is None else attribution.attribute_order(origin, normalized,
                    session=self.session, through=at, source_state=source_state,
                    evidence_mode=self.config['evidenceMode'], fees=charge)
                receipt = evidence['receipt']
                stable = {k: v for k, v in receipt.items()
                          if k not in ('eventId', 'knownAtJst', 'quantityKnownAtJst',
                                       'sourceSnapshotSha256', 'allocationEvidenceSha256')}
                signature = ledger.digest(stable)
                if evidence['blockers']:
                    unresolved[oid] = evidence['blockers']
            except ERRORS as error:
                unresolved[oid] = [safe_reason(error)]
                continue
            # Ledger integrity/state errors are fatal. They must not be
            # converted to an ordinary unavailable broker row and ignored.
            if updated.get(oid) != signature:
                self.book.apply_receipt(receipt, at)
                updated[oid] = signature
        if updated != semantics:
            self.book.checkpoint_source('broker.receiptSemantics', updated, at)
        # External ownership is never inferred to be Ark's. A known local
        # origin + broker number is the only way a row leaves this exclusion.
        current = self.book.snapshot(at)
        owned_numbers = {o['brokerOrderNumber'] for o in current['orders'].values() if o['brokerOrderNumber'] is not None}
        own_symbols = {p['symbol'] for p in current['positions'].values() if p['quantity'] > 0}
        awaiting_binding = {o['symbol'] for o in current['orders'].values()
                            if o['brokerOrderNumber'] is None and o['phase'] not in ledger.TERMINAL
                            and current['commands'][o['commandId']]['begunAtJst'] is not None}
        external = set(self.config['ledger'].get('externalSymbols', []))
        external.update(attribution.symbol(p['symbol']) for p in normalized['positions']
                        if attribution.symbol(p['symbol']) not in own_symbols | awaiting_binding)
        external.update(attribution.symbol(o['symbol']) for o in normalized['orders']
                        if o['orderNumber'] not in owned_numbers and attribution.symbol(o['symbol']) not in awaiting_binding)
        prior_external = self.book.source_checkpoint('broker.externalSymbols') or []
        external.update(prior_external)
        # Never clear a personal exclusion just because a row disappears.
        if sorted(external) != prior_external:
            self.book.checkpoint_source('broker.externalSymbols', sorted(external), at)
        event = {'schemaId': ledger.ACCOUNT_SCHEMA,
            'sessionDate': self.session, 'account': self.config['ledger']['account'],
            'knownAtJst': normalized['captureCompletedAt'], 'buyingPowerJpy': str(normalized['buyingPower']),
            'externalSymbols': sorted(external), 'evidenceMode': self.config['evidenceMode'],
            'sourceSnapshotSha256': normalized['snapshotSha256']}
        event['eventId'] = ledger.digest(event)
        self.book.observe_account(event, at)
        self.book.checkpoint_source('broker.executionRows', new_state, at)
        self.book.checkpoint_source('broker.normalized', {'json': json.dumps(normalized, ensure_ascii=False,
            separators=(',', ':'), allow_nan=False)}, at)
        self.book.checkpoint_source('broker.unresolved', unresolved, at)
        self.source, self.source_error = normalized, None
        if new_state['latchedIssues']:
            self.halt_entry('NO11_BROKER_SERVICE_EXECUTION_SOURCE_REVISED', at)
        if own_symbols.intersection(external):
            self.halt_entry('NO11_BROKER_SERVICE_PERSONAL_OWNERSHIP_CONFLICT', at)
        return self.summary(at)

    def observe_file(self, at):
        filename = self.config.get('accountObservationFile') or os.environ.get('ARK_NO11_ACCOUNT_OBSERVATION_FILE')
        if not filename:
            self.source_error = 'NO11_BROKER_SERVICE_SOURCE_NOT_CONFIGURED'
            return False
        try:
            envelope, sha = read_private(filename)
            if sha != self.last_raw_hash:
                self.observe_envelope(envelope, at)
                self.last_raw_hash = sha
            elif self.source is not None:
                self.source_error = None
            need(self._source_current(at), 'SOURCE_STALE')
            return True
        except ERRORS as error:
            if str(error).startswith('NO11_BROKER_LEDGER_'):
                raise
            self.source_error = safe_reason(error)
            return False

    def _fresh_id(self, at, assigned=()):
        need(self._source_current(at), 'CURRENT_ID_NAMESPACE_REQUIRED')
        used = {r['rssOrderId'] for r in self.source['idRows']}
        used.update(c['command']['rssOrderId'] for c in self.book.snapshot(at)['commands'].values()
                    if c['command']['rssSessionKey'] == self.source['sessionKey'])
        used.update(assigned)
        value = max(used, default=0) + 1
        need(value <= 2147483647, 'RSS_IDS_EXHAUSTED')
        return value

    def _command(self, intent, at, *, kind='ORDER', assigned=()):
        rid = self._fresh_id(at, assigned)
        original = {k: intent[k] for k in ('intentId', 'symbol', 'side', 'quantity', 'account')}
        original.update(kind=kind, sessionDate=self.session, rssSessionKey=self.source['sessionKey'], rssOrderId=rid,
            commandId=ledger.digest([self.session, self.source['sessionKey'], rid, intent['intentId'], kind]),
            createdAtJst=at, evidenceMode=ledger.COMMAND_MODES[self.config['evidenceMode']],
            orderTerms=self.config['orderTerms'] if kind == 'ORDER' else None,
            targetOrderNumber=intent.get('brokerOrderNumber') if kind == 'CANCEL' else None)
        return self.bridge({'action': 'compile', 'input': original})

    def _send_enabled(self):
        return self.config['transport']['mode'] == 'LIVE' or self.replay_dispatch is not None

    def _validate_physical_config(self, command, at):
        if self.config['transport']['mode'] == 'LIVE':
            need(self.source is not None and self.source['excelSession']['processId'] == self.config['transport']['expectedExcelPid'],
                 'EXCEL_PROCESS_CHANGED')
        return self.bridge({'action': 'validate-config', 'config': self.config['transport'],
                            'command': command, 'now': at})

    def _transport(self, packet):
        if self.replay_dispatch is not None:
            return self.replay_dispatch(deepcopy(packet))
        need(self.config['transport']['mode'] == 'LIVE', 'TRANSPORT_DISABLED')
        command = packet['command']
        request = exclusive_json(self.root / (command['commandId'] + '.dispatch-request.json'), packet)
        result = self.root / (command['commandId'] + '.dispatch-result.json')
        need(not result.exists(), 'TRANSPORT_RESULT_ALREADY_PRESENT')
        completed = subprocess.run(['node', str(HERE / 'no11_msii_transport.mjs'), '--request', str(request),
            '--result', str(result)], capture_output=True, text=True, encoding='utf-8', timeout=45, check=False)
        need(completed.returncode == 0 and result.exists(), 'TRANSPORT_REPLY_UNAVAILABLE')
        output, _ = read_private(result, 1_000_000)
        return output

    def _dispatch(self, command, at):
        # IN_FLIGHT is committed before invoking any process/sink. Neither a
        # restart nor a missing result can issue this command a second time.
        permit = self.book.begin_dispatch(command['commandId'], at)['dispatchPermit']
        packet = {'command': command, 'config': self.config['transport'], 'permit': permit}
        try:
            raw = self._transport(packet)
            need(type(raw) is dict and raw.get('schemaId') == 'ARK_NO11_MSII_TRANSPORT_RESULT_V1'
                 and raw.get('commandId') == command['commandId'] and raw.get('commandSha256') == command['commandSha256']
                 and raw.get('rssOrderId') == command['rssOrderId'] and raw.get('status') in ('NOT_SENT', 'UNKNOWN', 'SENT_AWAITING_RECONCILIATION')
                 and type(raw.get('dispatchAttempted')) is bool, 'TRANSPORT_RESULT_IDENTITY')
            need(raw['status'] != 'NOT_SENT' or raw['dispatchAttempted'] is False, 'TRANSPORT_FALSE_NOT_SENT')
            need(raw['status'] != 'SENT_AWAITING_RECONCILIATION' or raw['dispatchAttempted'] is True, 'TRANSPORT_FALSE_SENT')
            outcome = {'NOT_SENT': 'NOT_SENT', 'UNKNOWN': 'UNKNOWN', 'SENT_AWAITING_RECONCILIATION': 'RETURNED'}[raw['status']]
            not_invoked = outcome == 'NOT_SENT'
        except ERRORS as error:
            raw = {'commandId': command['commandId'], 'status': 'UNKNOWN', 'reason': safe_reason(error)}
            outcome, not_invoked = 'UNKNOWN', False
        known = self.clock()
        need(ledger.instant(known, self.session) >= ledger.instant(at, self.session), 'DISPATCH_CLOCK_REVERSED')
        sha = ledger.digest(raw)
        record = {'eventId': ledger.digest([command['commandId'], sha, known]), 'commandId': command['commandId'],
            'transportReceiptSha256': sha, 'knownAtJst': known, 'outcome': outcome, 'definitelyNotInvoked': not_invoked}
        self.book.record_transport_result(command['commandId'], record, known)
        exclusive_json(self.root / (command['commandId'] + '.transport-evidence.json'), raw)
        return raw

    def _sell_safe(self, intent, at):
        need(self._source_current(at), 'CURRENT_HOLDINGS_REQUIRED')
        external = set(self.book.source_checkpoint('broker.externalSymbols') or [])
        need(intent['symbol'] not in external, 'PERSONAL_POSITION_CONFLICT')
        owned = self.book.snapshot(at)
        broker_rows = [p for p in self.source['positions'] if attribution.symbol(p['symbol']) == intent['symbol']
                       and p['account'] == intent['account']]
        need(len(broker_rows) == 1 and broker_rows[0]['quantity'] >= intent['quantity'], 'BROKER_HOLDINGS_NOT_CONFIRMED')
        ours = {o['brokerOrderNumber'] for o in owned['orders'].values() if o['brokerOrderNumber'] is not None}
        for row in self.source['orders']:
            if row['orderNumber'] not in ours and attribution.symbol(row['symbol']) == intent['symbol'] and row['account'] == intent['account']:
                need(attribution.side(row['side']) != 'SELL' or attribution.order_phase(row) in ledger.TERMINAL,
                     'EXTERNAL_SELL_RESERVATION')

    def submit_intents(self, intents, at):
        """Validate/compile the whole batch before any irreversible boundary."""
        need(type(intents) is list and len(intents) <= 3, 'INTENT_BATCH')
        self.drafts = []
        if not intents:
            return []
        need(self._source_current(at), 'CURRENT_SOURCE_REQUIRED')
        need(not self.source.get('unsupportedMarkets'), 'UNSUPPORTED_MARKET_OBSERVATION')
        commands, assigned = [], []
        for intent in intents:
            if intent['side'] == 'BUY':
                need(not self.entry_halted and at[11:16] < '15:20' and self._buying_power_verified(at)
                     and not self.book.source_checkpoint('broker.unresolved')
                     and self.book.snapshot(at)['newBuysAllowed'], 'NEW_BUY_ADMISSION')
            else:
                self._sell_safe(intent, at)
            command = self._command(intent, at, assigned=assigned)
            self._validate_physical_config(command, at)
            commands.append(command)
            assigned.append(command['rssOrderId'])
        self.drafts = deepcopy(commands)
        if not self._send_enabled():
            return [{'status': 'OBSERVE_ONLY_DRAFT', 'commandId': c['commandId'], 'orderTransmission': False} for c in commands]
        prepared = []
        try:
            for intent, command in zip(intents, commands):
                self.book.prepare_order(intent, command, at)
                prepared.append(intent['intentId'])
        except ERRORS:
            for oid in prepared:
                self.book.withdraw_prepared(oid, at)
            raise
        results = []
        for command in commands:
            current = self.clock()
            try:
                self._validate_physical_config(command, current)
                if command['side'] == 'BUY':
                    need(not self.entry_halted and self._buying_power_verified(current), 'NEW_BUY_ADMISSION')
                result = self._dispatch(command, current)
                results.append(result)
                if result.get('status') != 'SENT_AWAITING_RECONCILIATION':
                    break
            except ERRORS as error:
                self.halt_entry(safe_reason(error), self.clock())
                break
        # Never leave an unsent tail that could be dispatched on restart.
        state = self.book.snapshot(self.clock())
        for oid in prepared:
            if state['orders'][oid]['phase'] == 'PREPARED':
                self.book.withdraw_prepared(oid, self.clock())
        return results

    def cancel_buys(self, at):
        state = self.book.snapshot(at)
        for order in state['orders'].values():
            at = self.clock()
            if order['side'] != 'BUY' or order['phase'] in ledger.TERMINAL:
                continue
            if order['phase'] == 'PREPARED':
                self.book.withdraw_prepared(order['intentId'], at)
                continue
            if (not self._source_current(at) or order['brokerOrderNumber'] is None or order['cancelRequested']
                    or order['observedPhase'] not in ('ACKNOWLEDGED', 'PARTIAL')):
                continue
            command = self._command(order, at, kind='CANCEL')
            self._validate_physical_config(command, at)
            self.drafts.append(command)
            if self._send_enabled():
                self.book.request_cancel(order['intentId'], command, at)
                self._dispatch(command, self.clock())

    def _position_traces(self, feed, at):
        need(h.digest(self.previous) == self.book.source_checkpoint('controller.identity')['previousContextSha256'], 'PREVIOUS_SOURCE_CHANGED')
        quotes = ExecutionShadow._quotes(self, feed, h.timestamp(at, self.session))
        current = {(r['Code'], r['Time']): h.digest(r) for r in feed['rows']}
        accepted = self.book.source_checkpoint('market.heldPrefix') or {}
        for code, history in accepted.items():
            for minute, fingerprint in history.items():
                need(current.get((code, minute)) == fingerprint, 'HELD_SOURCE_CHANGED_OR_REMOVED')
        traces = {}
        positions = self.book.snapshot(at)['positions'].values()
        for position in positions:
            if position['quantity'] <= 0:
                continue
            code = position['symbol']
            if code not in self.streams:
                self.streams[code] = received.ObservedStateStream(self.runtime, self.session, code,
                    self.previous['symbols'].get(code), self.prior)
                self.stream_seen[code] = set()
            rows = sorted((r for r in feed['rows'] if r['Code'] == code), key=lambda r: r['Time'])
            for row in rows:
                if row['Time'] not in self.stream_seen[code]:
                    self.streams[code].push(row)
                    self.stream_seen[code].add(row['Time'])
                accepted.setdefault(code, {})[row['Time']] = h.digest(row)
            traces[code] = self.streams[code].trace
        self.book.checkpoint_source('market.heldPrefix', accepted, at)
        return quotes, traces

    def evaluate_exits(self, traces, at):
        state = self.book.snapshot(at)
        result = decisions.calculate_exits(list(state['positions'].values()), traces,
            session=self.session, at=at, order_history=state['orders'])
        self.last_exit = result
        if result['intents']:
            self.cancel_buys(at)
            self.submit_intents(result['intents'], self.clock())
        return result

    def _capital_input(self, quotes, at):
        state = self.book.snapshot(at)
        positions = [p for p in state['positions'].values() if p['quantity'] > 0]
        exposure, missing = Decimal(0), []
        for position in positions:
            row = quotes.get(position['symbol'])
            if row is None:
                missing.append(position['symbol'])
            else:
                exposure += Decimal(str(row['C'])) * position['quantity']
        external = set(self.book.source_checkpoint('broker.externalSymbols') or [])
        conflict = bool(external.intersection(p['symbol'] for p in positions))
        # A mark is necessary for the original equity allocation. Never use a
        # stale acquisition price as a current observed mark.
        need(not missing and not conflict, 'FRESH_OWNED_MARKS_OR_IDENTITY_REQUIRED')
        cash = Decimal(state['availableBuyJpy'])
        return {'schemaId': 'ARK_NO11_BROKER_CAPITAL_INPUT_V1', 'sessionDate': self.session,
            'decisionAtJst': at, 'account': self.config['ledger']['account'],
            'availableCashJpy': str(cash), 'exposureJpy': str(exposure), 'equityJpy': str(cash + exposure),
            'positions': positions, 'externalSymbols': sorted(external),
            'entryBlocked': self.entry_halted or not state['newBuysAllowed']
                or bool(self.book.source_checkpoint('broker.unresolved'))
                or not self._buying_power_verified(at) or at[11:16] >= '15:20',
            'pendingOrders': any(o['phase'] not in ledger.TERMINAL for o in state['orders'].values()),
            'reserveChargesJpy': self.config.get('reserveChargesJpy', '0')}

    def fund(self, batch, quotes, at):
        need(type(batch) is dict and type(batch.get('results')) is list, 'H235_BATCH')
        consumed = self.book.source_checkpoint('capital.consumed') or {}
        changed, fresh = dict(consumed), []
        for row in batch['results']:
            key, sha = row.get('candidateId'), h.digest(row)
            need(type(key) is str and bool(key), 'CANDIDATE_ID')
            need(key not in consumed or consumed[key] == sha, 'CANDIDATE_CHANGED')
            if key not in consumed:
                decision = h.timestamp(row.get('decisionAtJst'), self.session)
                now = h.timestamp(at, self.session)
                need(decision <= now, 'CANDIDATE_FROM_FUTURE')
                if h.minute(decision) == h.minute(now) and (now - decision).total_seconds() <= 90:
                    fresh.append(row)
                changed[key] = sha
        if not fresh:
            if changed != consumed:
                self.book.checkpoint_source('capital.consumed', changed, at)
            return None
        # Validate the complete fresh batch before consuming a candidate or
        # reserving funds. Already evaluated rows may never return as new BUY.
        result = decisions.calculate_capital(dict(batch, results=fresh), self._capital_input(quotes, at), self.arrival)
        self.book.checkpoint_source('capital.consumed', changed, at)
        self.last_decision = result
        self.submit_intents(result['intents'], self.clock())
        return result

    def heartbeat(self, at, *, observe=True):
        if observe:
            self.observe_file(at)
        state = self.book.snapshot(at)
        if self.entry_halted or state['firstSellFillBuyHalt'] or at[11:16] >= '15:20':
            try:
                self.cancel_buys(at)
            except ERRORS as error:
                self.halt_entry(safe_reason(error), self.clock())
        if at[11:16] >= '15:20':
            try:
                self.evaluate_exits({}, self.clock())
            except ERRORS as error:
                self.halt_entry(safe_reason(error), self.clock())
        return self.summary(self.clock())

    def advance(self, feed, inference, at):
        self.observe_file(at)
        quotes, traces = self._position_traces(feed, at)
        self.evaluate_exits(traces, at)
        if not self.entry_halted:
            sha = inference.get('h235PrivateResultSha256')
            need(type(sha) is str and re.fullmatch(r'[a-f0-9]{64}', sha), 'H235_RESULT_REQUIRED')
            batch, actual = read_private(self.root / ('h235-asof-' + sha[:16] + '.json'))
            need(actual == sha, 'H235_RESULT_CHANGED')
            self.fund(batch, quotes, self.clock())
        return self.summary(self.clock())

    def exit_only(self, feed, at):
        self.observe_file(at)
        _, traces = self._position_traces(feed, at)
        self.evaluate_exits(traces, at)
        return self.summary(self.clock())

    def summary(self, at=None):
        at = at or self.clock()
        state = self.book.snapshot(at)
        return {'schemaId': 'ARK_NO11_BROKER_EXECUTION_REPORT_V1', 'sessionDate': self.session,
            'evaluatedAtJst': at, 'mode': self.config['transport']['mode'], 'evidenceMode': self.config['evidenceMode'],
            'sourceCurrent': self._source_current(at), 'sourceFailure': self.source_error,
            'buyingPowerRefreshVerified': self._buying_power_verified(at),
            'entryPipelineHalted': self.entry_halted,
            'entryHaltReasons': self.book.source_checkpoint('controller.entryHalt') or [],
            'ledger': state, 'unresolvedOrders': self.book.source_checkpoint('broker.unresolved') or {},
            'capital': self.last_decision, 'exit': self.last_exit, 'drafts': self.drafts,
            'positionCount': state['positionCount'], 'realFillsAppliedToShadow': False,
            'brokerConnectionPhysicallyVerified': False, 'brokerFeedAtomicityCertified': False,
            'productionReady': False, 'orderTransmission': self.config['transport']['mode'] == 'LIVE'}
