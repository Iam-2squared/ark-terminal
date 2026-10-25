"""Received-data Shadow with native Capital/EXIT and optional account observation.

Real account rows only restrict synthetic entries. Real cash, positions and
executions are never copied into the synthetic portfolio or submitted anywhere.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import re

import no11_h235_asof_forward_shadow as h
import no11_h235_capital_v5_shadow as cap
import no11_rss_state9_p1_runner as received
from no11_shadow_portfolio import ShadowPortfolio, config_check, UPDATE, ACTIVE
from no11_account_observation import AccountObservation


def need(ok, code):
    if not ok:
        raise ValueError('NO11_EXECUTION_SHADOW_' + code)


def settings(path, session):
    p = Path(path).absolute()
    need(p != h.ROOT and h.ROOT not in p.parents, 'PRIVATE_CONFIG_REQUIRED')
    config, _ = received.read_json(p, 100000)
    config_check(config, session)
    arrival = cap.original_arrival_tables(config['originalArrivalTable'])
    return config, arrival


class ExecutionShadow:
    def __init__(self, root, config, arrival, runtime, previous, prior, *, funding=None):
        self.root, self.session = Path(root).absolute(), config['sessionDate']
        self.runtime, self.previous, self.prior = runtime, previous, prior
        kwargs = {} if funding is None else {'funding': funding}
        self.portfolio = ShadowPortfolio(self.root / ('portfolio-shadow-' + self.session + '.sqlite'),
                                         config, arrival, **kwargs)
        self.streams, self.input_hashes = {}, {}
        self.feed_pin = h.digest(previous)
        self.blocked = {}
        self.account = AccountObservation(self.root, self.session)

    def close(self):
        self.portfolio.close()

    def _quotes(self, feed, now):
        need(feed.get('receipt', {}).get('sessionDate') == self.session
             and feed.get('receipt', {}).get('orderTransmission') is False
             and feed.get('receipt', {}).get('proxyReceipt', {}).get('nativeExactMinuteVaCertified') is False
             and type(feed.get('rows')) is list, 'RECEIVED_FEED_REQUIRED')
        quotes, seen = {}, set()
        for r in feed['rows']:
            need(r.get('Date') == self.session and r.get('vaProvenance') == received.VA_SOURCE,
                 'SOURCE_IDENTITY')
            received.validate_prices(r)
            known = h.timestamp(r['knownAtJst'], self.session)
            end = h.timestamp(received.stamp(self.session, received.minute(r['Time']) + 1), self.session)
            need(end <= known <= now, 'FUTURE_OR_UNCLOSED_QUOTE')
            key = (r['Code'], r['Time'])
            need(key not in seen, 'DUPLICATE_QUOTE')
            seen.add(key)
            if (now - end).total_seconds() > 90:
                continue
            old = quotes.get(r['Code'])
            if old is None or r['Time'] > old['Time']:
                quotes[r['Code']] = r
        return quotes

    def _verify_held_prefix(self, feed):
        current = {(r['Code'], r['Time']): h.digest(r) for r in feed['rows']}
        for code, accepted in self.input_hashes.items():
            for minute, fingerprint in accepted.items():
                need((code, minute) in current, 'HELD_SOURCE_REMOVED')
                need(current[(code, minute)] == fingerprint, 'HELD_SOURCE_CHANGED')

    def _simulated_updates(self, quotes, at):
        initial = self.portfolio.state()
        ordered = sorted(initial['orders'].values(), key=lambda o: (o['side'] != 'SELL', o['createdAt'], o['orderId']))
        for old in ordered:
            current = self.portfolio.state()
            order = current['orders'][old['orderId']]
            if order['status'] not in ACTIVE or order['status'] == 'UNKNOWN':
                continue
            quote = quotes.get(order['symbol'])
            status, quantity, value = None, order['filled'], Decimal(order['value'])
            created = h.timestamp(order['createdAt'], self.session)
            if order['status'] == 'CANCEL_REQUESTED' or order['side'] == 'BUY' and current['sellFillLatch']:
                status = 'CANCELLED'  # local simulator only, not a brokerage ack
            elif (quote is not None
                  and h.timestamp(quote['knownAtJst'], self.session) > created
                  and h.timestamp(received.stamp(self.session, received.minute(quote['Time']) + 1), self.session) > created):
                remain = order['quantity'] - order['filled']
                effective = Decimal(str(quote['C'])) * Decimal('1.0005' if order['side'] == 'BUY' else '0.9995')
                if order['side'] == 'BUY' and effective > Decimal(order['unitReserve']):
                    status = 'CANCELLED'
                else:
                    quantity, value, status = order['quantity'], value + effective * remain, 'FILLED'
            if status is None:
                continue
            event = {'schemaId': UPDATE, 'eventId': h.digest([order['orderId'], quote, status, quantity, str(value)]),
                     'orderId': order['orderId'], 'symbol': order['symbol'], 'side': order['side'],
                     'knownAtJst': at, 'cumulativeQuantity': quantity, 'cumulativeValueJpy': str(value),
                     'status': status, 'syntheticOnly': True}
            self.portfolio.update(event, at)

    def _position_traces(self, feed):
        state = self.portfolio.state()
        owned = {p['symbol'] for p in state['positions'].values()}
        traces = {}
        for code in owned:
            if code not in self.streams:
                context = self.previous['symbols'].get(code)
                try:
                    self.streams[code] = received.ObservedStateStream(
                        self.runtime, self.session, code, context, self.prior)
                    self.input_hashes[code] = {}
                except (ValueError, KeyError, TypeError):
                    self.blocked[code] = 'HELD_SYMBOL_PREVIOUS_CONTEXT_UNAVAILABLE'
                    continue
            stream = self.streams[code]
            accepted = self.input_hashes[code]
            rows = sorted((r for r in feed['rows'] if r['Code'] == code), key=lambda r:r['Time'])
            seen = set()
            for row in rows:
                key, digest = row['Time'], h.digest(row)
                seen.add(key)
                if key in accepted:
                    need(accepted[key] == digest, 'HELD_SOURCE_CHANGED')
                    continue
                stream.push(row)
                accepted[key] = digest
            need(set(accepted) <= seen, 'HELD_SOURCE_REMOVED')
            traces[code] = stream.trace
        return traces

    def _account_guard(self, at):
        if not self.account.enabled:
            return True, set()
        report = self.account.observe()
        excluded = set(report['excludedSymbols'])
        allowed = report['newShadowEntriesAllowed'] is True
        if allowed:
            # The sidecar may finish a newer capture while inference is running.
            # It must not retroactively authorize the earlier decision instant.
            try:
                source = datetime.fromisoformat(report['sourceAt'])
                decision = h.timestamp(at, self.session)
                allowed = source <= decision and 0 <= (decision - source).total_seconds() <= 30
            except (ValueError, TypeError, KeyError):
                allowed = False
        for order in self.portfolio.state()['orders'].values():
            if (order['side'] == 'BUY' and order['status'] in {'INTENT', 'ACKNOWLEDGED', 'PARTIAL'}
                    and (not allowed or order['symbol'] in excluded)):
                self.portfolio.cancel(order['orderId'], at)
        return allowed, excluded

    def advance(self, feed, inference, at):
        now = h.timestamp(at, self.session)
        need(h.digest(self.previous) == self.feed_pin, 'PREVIOUS_SOURCE_CHANGED')
        digest = inference.get('h235PrivateResultSha256')
        need(type(digest) is str and re.fullmatch(r'[a-f0-9]{64}', digest), 'H235_RESULT_REQUIRED')
        file = self.root / ('h235-asof-' + digest[:16] + '.json')
        batch, actual = received.read_json(file, 25000000)
        need(actual == digest, 'H235_RESULT_HASH_CHANGED')
        quotes = self._quotes(feed, now)
        self._verify_held_prefix(feed)
        if h.minute(now) >= 920:
            self.heartbeat(at)
        allowed, excluded = self._account_guard(at)
        self._simulated_updates(quotes, at)
        self.portfolio.mark(quotes, at)
        traces = self._position_traces(feed)
        self.portfolio.evaluate_exits(traces, at)
        if allowed:
            eligible = dict(batch, results=[r for r in batch['results'] if r['symbol'] not in excluded])
            self.portfolio.fund(eligible, at)
        return self.summary()

    def heartbeat(self, at):
        now = h.timestamp(at, self.session)
        if h.minute(now) >= 920:
            for order in self.portfolio.state()['orders'].values():
                if order['side'] == 'BUY' and order['status'] in {'INTENT', 'ACKNOWLEDGED', 'PARTIAL'}:
                    self.portfolio.cancel(order['orderId'], at)
            self.portfolio.evaluate_exits({}, at)
        return self.summary()

    def summary(self):
        result = self.portfolio.summary()
        result.update(accountReadOnlyConfigured=self.account.enabled,
                      accountObservation=self.account.report,
                      realAccountExecutionConnected=False,
                      originalState9ForHeldSymbols=True,
                      heldStateUnavailableCount=len(self.blocked),
                      fillPolicy='NEXT_FRESH_RECEIVED_CLOSE_SIMULATION',
                      observedPriceIsBrokerFill=False,
                      originalHistoricalExecutionParity=False,
                      originalExitCodePins=__import__('no11_original_exit_shadow').PINS)
        return result
