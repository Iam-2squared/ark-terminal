"""Connect the existing received-data service to a durable synthetic portfolio.

Fresh RSS prices may drive explicitly simulated fills, never actual brokerage.
State9 for held symbols is the existing original ObservedStateStream, consumed
incrementally; original Structural v3 is called by the durable portfolio.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
from pathlib import Path

import no11_h235_asof_forward_shadow as h
import no11_h235_capital_v5_shadow as cap
import no11_rss_state9_p1_runner as received
from no11_shadow_portfolio import ShadowPortfolio, config_check, UPDATE, ACTIVE


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

    def _simulated_updates(self, quotes, at):
        initial = self.portfolio.state()
        # Match SELL before BUY, including the first partial SELL halt rule.
        ordered = sorted(initial['orders'].values(), key=lambda o: (o['side'] != 'SELL', o['createdAt'], o['orderId']))
        for old in ordered:
            current = self.portfolio.state()
            order = current['orders'][old['orderId']]
            if order['status'] not in ACTIVE or order['status'] == 'UNKNOWN':
                continue
            quote = quotes.get(order['symbol'])
            status, quantity, value = None, order['filled'], Decimal(order['value'])
            if order['status'] == 'CANCEL_REQUESTED' or order['side'] == 'BUY' and current['sellFillLatch']:
                # This is ONLY the local simulator acknowledging its own cancel.
                status = 'CANCELLED'
            elif quote is not None and h.timestamp(quote['knownAtJst'], self.session) > h.timestamp(order['createdAt'], self.session):
                remain = order['quantity'] - order['filled']
                effective = Decimal(str(quote['C'])) * Decimal('1.0005' if order['side'] == 'BUY' else '0.9995')
                if order['side'] == 'BUY' and effective > Decimal(order['unitReserve']):
                    status = 'CANCELLED'  # never manufacture an affordable fill
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

    def advance(self, feed, inference, at):
        now = h.timestamp(at, self.session)
        need(h.digest(self.previous) == self.feed_pin, 'PREVIOUS_SOURCE_CHANGED')
        quotes = self._quotes(feed, now)
        self._simulated_updates(quotes, at)
        self.portfolio.mark(quotes, at)
        traces = self._position_traces(feed)
        self.portfolio.evaluate_exits(traces, at)
        digest = inference.get('h235PrivateResultSha256')
        need(type(digest) is str and len(digest) == 64, 'H235_RESULT_REQUIRED')
        file = self.root / ('h235-asof-' + digest[:16] + '.json')
        batch, actual = received.read_json(file, 25000000)
        need(actual == digest, 'H235_RESULT_HASH_CHANGED')
        self.portfolio.fund(batch, at)
        return self.summary()

    def heartbeat(self, at):
        now = h.timestamp(at, self.session)
        if h.minute(now) >= 920:
            # Wall-clock EOD does not depend on another price receipt arriving.
            self.portfolio.evaluate_exits({}, at)
        return self.summary()

    def summary(self):
        result = self.portfolio.summary()
        result.update(originalState9ForHeldSymbols=True,
                      heldStateUnavailableCount=len(self.blocked),
                      fillPolicy='NEXT_FRESH_RECEIVED_CLOSE_SIMULATION',
                      observedPriceIsBrokerFill=False,
                      originalHistoricalExecutionParity=False,
                      originalExitCodePins=__import__('no11_original_exit_shadow').PINS)
        return result
