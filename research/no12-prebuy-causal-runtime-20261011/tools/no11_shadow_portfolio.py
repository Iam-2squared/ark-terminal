"""Durable No.1.1 Shadow portfolio: native V5, native EXIT and simulated receipts.

No brokerage transport exists here. Intent, partial fill, cancellation request
and cancellation acknowledgement are different persisted events. An intent
never credits cash or releases a position. All money is explicitly synthetic.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import no11_h235_asof_forward_shadow as h
import no11_h235_capital_v5_shadow as capital
import no11_original_exit_shadow as exits

CONFIG = 'ARK_NO11_OBSERVED_SHADOW_ACCOUNT_V1'
UPDATE = 'ARK_NO11_SIMULATED_ORDER_UPDATE_V1'
ACTIVE = {'INTENT', 'ACKNOWLEDGED', 'PARTIAL', 'CANCEL_REQUESTED', 'UNKNOWN'}
TERMINAL = {'FILLED', 'CANCELLED', 'REJECTED'}
# A local request is not evidence that an uncertain order became understood.
CANCELLABLE = ACTIVE - {'UNKNOWN'}


def need(ok, reason):
    if not ok:
        raise ValueError('NO11_PORTFOLIO_' + reason)


def money(x):
    need(type(x) in (str, int, float) and len(str(x)) <= 64, 'MONEY_INVALID')
    try:
        n = Decimal(str(x))
    except InvalidOperation:
        raise ValueError('NO11_PORTFOLIO_MONEY_INVALID') from None
    need(n.is_finite() and 0 <= n <= Decimal('1000000000000'), 'MONEY_INVALID')
    return n


def config_check(config, session):
    need(type(config) is dict and set(config) == {
        'schemaId', 'sessionDate', 'initialCashJpy', 'externalSymbols',
        'originalArrivalTable', 'fillPolicy', 'syntheticAccountOnly',
        'productionReady', 'orderTransmission'}, 'CONFIG_FIELDS')
    need(config['schemaId'] == CONFIG and config['sessionDate'] == session
         and config['fillPolicy'] == 'NEXT_FRESH_RECEIVED_CLOSE_SIMULATION'
         and config['syntheticAccountOnly'] is True and config['productionReady'] is False
         and config['orderTransmission'] is False, 'CONFIG_NOT_SHADOW')
    money(config['initialCashJpy'])
    names = config['externalSymbols']
    need(type(names) is list and len(names) <= 500 and all(type(s) is str and h.SYMBOL.fullmatch(s) for s in names)
         and len(names) == len(set(names)), 'EXTERNAL_SYMBOLS_INVALID')
    h.policy(session)
    return config


class ShadowPortfolio:
    def __init__(self, database, config, arrival, *, funding=capital.fund_shadow):
        self.session = config['sessionDate']
        config_check(config, self.session)
        self.config, self.arrival, self.funding = deepcopy(config), deepcopy(arrival), funding
        path = Path(database).absolute()
        need(path != h.ROOT and h.ROOT not in path.parents and not path.is_symlink()
             and not any(p.is_symlink() for p in path.parents) and path.parent.is_dir(), 'PRIVATE_DATABASE_REQUIRED')
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS portfolio (singleton INTEGER PRIMARY KEY CHECK(singleton=1), body TEXT NOT NULL, sha TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL, previous_sha TEXT NOT NULL, event_sha TEXT NOT NULL, result TEXT NOT NULL)')
        self.pin = h.digest([config, arrival, exits.PINS])
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT body,sha FROM portfolio').fetchone()
            if row is None:
                need(self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 0, 'STATE_MISSING_WITH_EVENTS')
                state = {'session': self.session, 'pin': self.pin, 'cash': str(money(config['initialCashJpy'])),
                         'positions': {}, 'orders': {}, 'candidates': {}, 'sellFillLatch': False,
                         'reconciliationBlocked': False, 'clock': None, 'eventSeq': 0,
                         'eventHead': '0' * 64, 'productionReady': False, 'orderTransmission': False}
                self._save(state)
            else:
                state = self._read()
            previous, count = '0' * 64, 0
            for seq, eid, fingerprint, prev, sha, result in self.db.execute('SELECT * FROM events ORDER BY seq'):
                count += 1
                need(seq == count and prev == previous
                     and sha == h.digest([seq, eid, fingerprint, prev, result]), 'EVENT_CHAIN_CHANGED')
                previous = sha
            need(count == state['eventSeq'] and previous == state['eventHead'], 'STATE_EVENT_CHAIN_MISMATCH')
            self._invariants(state)
            self.db.commit()
        except BaseException:
            self.db.rollback()
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def _read(self):
        row = self.db.execute('SELECT body,sha FROM portfolio WHERE singleton=1').fetchone()
        need(row is not None, 'STATE_MISSING')
        state = json.loads(row[0])
        need(h.digest(state) == row[1] and state['pin'] == self.pin
             and state['session'] == self.session, 'STATE_CHANGED_OR_DIFFERENT_CONFIG')
        return state

    def state(self):
        return self._read()

    def _save(self, state):
        body = h.stable_bytes(state).decode()
        self.db.execute('INSERT OR REPLACE INTO portfolio VALUES (1,?,?)', (body, h.digest(state)))

    def _invariants(self, s):
        need(s['productionReady'] is False and s['orderTransmission'] is False, 'STATE_NOT_SHADOW')
        need(money(s['cash']) >= self._reserved(s), 'CASH_OVERRESERVED')
        occupied = {p['symbol'] for p in s['positions'].values() if p['quantity'] > 0}
        occupied.update(o['symbol'] for o in s['orders'].values() if o['side'] == 'BUY' and o['status'] in ACTIVE)
        need(len(occupied) <= 3 and not occupied.intersection(self.config['externalSymbols']), 'MAX3_OR_EXTERNAL_OWNERSHIP')
        for p in s['positions'].values():
            need(type(p['quantity']) is int and p['quantity'] > 0 and p['band'] in ('S', 'A', 'B'), 'POSITION_INVALID')
        for o in s['orders'].values():
            need(type(o['quantity']) is int and o['quantity'] > 0
                 and 0 <= o['filled'] <= o['quantity'], 'ORDER_QUANTITY_INVALID')
            need(o['status'] != 'UNKNOWN' or s['reconciliationBlocked'] is True,
                 'UNKNOWN_WITHOUT_RECONCILIATION_BLOCK')
            if o['side'] == 'SELL' and o['status'] in ACTIVE:
                need(o['entryId'] in s['positions'] and o['quantity'] - o['filled'] <= s['positions'][o['entryId']]['quantity'],
                     'SELL_EXCEEDS_OWNED_QUANTITY')

    def _reserved(self, s):
        return sum((money(o['unitReserve']) * (o['quantity'] - o['filled'])
                    for o in s['orders'].values() if o['side'] == 'BUY' and o['status'] in ACTIVE), Decimal(0))

    def _event(self, event_id, body, at, reducer):
        clock = h.timestamp(at, self.session)
        fingerprint = h.digest(body)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT fingerprint,result FROM events WHERE event_id=?', (event_id,)).fetchone()
            if old:
                need(old[0] == fingerprint, 'EVENT_ID_CONTENT_CHANGED')
                result = json.loads(old[1])
                self.db.commit()
                return dict(result, idempotentReplay=True)
            s = self._read()
            need(s['clock'] is None or h.timestamp(s['clock'], self.session) <= clock, 'PROCESS_CLOCK_REVERSED')
            need(s['eventSeq'] < 20000, 'EVENT_LIMIT')
            result = reducer(s)
            result.update(productionReady=False, orderTransmission=False, idempotentReplay=False)
            self._invariants(s)
            encoded = h.stable_bytes(result).decode()
            seq = s['eventSeq'] + 1
            sha = h.digest([seq, event_id, fingerprint, s['eventHead'], encoded])
            self.db.execute('INSERT INTO events VALUES (?,?,?,?,?,?)',
                            (seq, event_id, fingerprint, s['eventHead'], sha, encoded))
            s.update(clock=at, eventSeq=seq, eventHead=sha)
            self._save(s)
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def mark(self, quotes, at):
        now = h.timestamp(at, self.session)
        def apply(s):
            for entry, p in s['positions'].items():
                q = quotes.get(p['symbol'])
                if q is None:
                    continue
                known = h.timestamp(q['knownAtJst'], self.session)
                need(known <= now and money(q['C']) > 0, 'MARK_NOT_OBSERVED')
                if p.get('markKnownAt') is None or h.timestamp(p['markKnownAt'], self.session) < known:
                    p.update(mark=str(money(q['C'])), markKnownAt=q['knownAtJst'])
            return {'status': 'SHADOW_MARKS_UPDATED'}
        return self._event('MARK:' + h.digest(quotes), quotes, at, apply)

    def fund(self, batch, at):
        now = h.timestamp(at, self.session)
        def apply(s):
            fresh = []
            for r in batch['results']:
                identity, digest = r['candidateId'], h.digest(r)
                previous = s['candidates'].get(identity)
                need(previous is None or previous == digest, 'CANDIDATE_CHANGED')
                if previous is not None:
                    continue
                s['candidates'][identity] = digest
                decision = h.timestamp(r['decisionAtJst'], self.session)
                need(decision <= now, 'CANDIDATE_FROM_FUTURE')
                if h.minute(decision) == h.minute(now) and (now - decision).total_seconds() <= 90:
                    fresh.append(r)
            if not fresh:
                return {'status': 'NO_NEW_CURRENT_R0', 'buyIntents': 0}
            reason = ('AFTER_FIRST_SELL_FILL' if s['sellFillLatch'] else
                      'RECONCILIATION_REQUIRED' if s['reconciliationBlocked'] else
                      'PENDING_ORDER' if any(o['status'] in ACTIVE for o in s['orders'].values()) else
                      'EOD_CUTOFF' if h.minute(now) >= 920 else None)
            if reason:
                return {'status': reason, 'buyIntents': 0}
            exposure = Decimal(0)
            for p in s['positions'].values():
                if p.get('markKnownAt') is None or (now - h.timestamp(p['markKnownAt'], self.session)).total_seconds() > 120:
                    return {'status': 'POSITION_MARK_STALE', 'buyIntents': 0}
                exposure += money(p['mark']) * p['quantity']
            owned = {p['symbol'] for p in s['positions'].values()}
            fresh = [r for r in fresh if r['symbol'] not in owned and r['symbol'] not in self.config['externalSymbols']]
            reduced = dict(batch, results=fresh)
            scenario = {'schemaId': capital.SCENARIO, 'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',
                'sessionDate': self.session, 'decisionAtJst': at,
                'arkCapitalInputs': {'cash': s['cash'], 'equity': str(money(s['cash']) + exposure), 'exposure': str(exposure)},
                'externalSymbols': self.config['externalSymbols'], 'arkManagedSymbols': sorted(owned),
                'existingBands': [p['band'] for p in sorted(s['positions'].values(), key=lambda x:x['symbol'])],
                'afterFirstLegalSellFill': False, 'pendingBrokerOrders': False,
                'syntheticAccountOnly': True, 'productionReady': False, 'orderTransmission': False}
            funded = self.funding(reduced, scenario, self.arrival)['capital']
            by = {r['candidateId']: r for r in fresh}
            new = []
            for allocation in funded['allocations']:
                qty, eid = allocation['quantity'], allocation['entry_id']
                if qty == 0:
                    continue
                need(type(qty) is int and qty > 0 and qty % 100 == 0 and eid in by, 'CAPITAL_QUANTITY_INVALID')
                r = by[eid]
                unit = money(r['raw_reference']) * Decimal('1.0005')
                need(money(allocation['debitJpy']) == qty * unit, 'CAPITAL_DEBIT_MISMATCH')
                oid = h.digest([self.session, eid, 'BUY'])
                need(oid not in s['orders'], 'DUPLICATE_BUY_INTENT')
                s['orders'][oid] = {'orderId': oid, 'entryId': eid, 'symbol': r['symbol'], 'side': 'BUY',
                    'quantity': qty, 'band': allocation['band'], 'unitReserve': str(unit),
                    'filled': 0, 'value': '0', 'status': 'INTENT', 'createdAt': at, 'updatedAt': at,
                    'reason': 'ORIGINAL_CAPITAL_V5', 'simulatedOnly': True}
                new.append(oid)
            return {'status': 'ORIGINAL_V5_SHADOW_FUNDED', 'buyIntents': len(new), 'orderIds': new}
        return self._event('FUND:' + h.digest(batch), batch, at, apply)

    def evaluate_exits(self, traces, at):
        def apply(s):
            new = []
            for eid, p in s['positions'].items():
                pending = [o for o in s['orders'].values() if o['entryId'] == eid and o['side'] == 'SELL' and o['status'] in ACTIVE]
                if pending:
                    continue
                result = exits.decide_received_exit(session=self.session, entry_at=p['filledAt'],
                    trace=traces.get(p['symbol'], []), evaluated_at=at)
                intent = result['intent']
                if intent is None:
                    continue
                # Protect the confirmed partial position, but never overwrite
                # an UNKNOWN remainder with a simulator-acknowledgeable state.
                for order in s['orders'].values():
                    if order['entryId'] == eid and order['side'] == 'BUY' and order['status'] in CANCELLABLE:
                        order['status'] = 'CANCEL_REQUESTED'
                generation = sum(o['entryId'] == eid and o['side'] == 'SELL' for o in s['orders'].values())
                oid = h.digest([self.session, eid, 'SELL', generation])
                s['orders'][oid] = {'orderId': oid, 'entryId': eid, 'symbol': p['symbol'], 'side': 'SELL',
                    'quantity': p['quantity'], 'band': p['band'], 'unitReserve': '0',
                    'filled': 0, 'value': '0', 'status': 'INTENT', 'createdAt': at, 'updatedAt': at,
                    'reason': intent['reason'], 'sourceExitSha256': h.digest(result), 'simulatedOnly': True}
                new.append(oid)
            return {'status': 'ORIGINAL_EXIT_SHADOW', 'sellIntents': len(new), 'orderIds': new}
        identity = h.digest([at, traces, self.state()['positions']])
        return self._event('EXIT:' + identity, {'at': at, 'traces': traces}, at, apply)

    def cancel(self, order_id, at):
        def apply(s):
            need(order_id in s['orders'], 'ORDER_UNKNOWN')
            o = s['orders'][order_id]
            need(o['status'] in ACTIVE, 'ORDER_ALREADY_TERMINAL')
            need(o['status'] in CANCELLABLE, 'ORDER_RECONCILIATION_REQUIRED')
            o['status'] = 'CANCEL_REQUESTED'
            return {'status': 'CANCEL_REQUESTED_NO_RELEASE'}
        return self._event('CANCEL:' + order_id, {'orderId': order_id}, at, apply)

    def update(self, event, at):
        need(type(event) is dict and set(event) == {'schemaId', 'eventId', 'orderId', 'symbol', 'side',
            'knownAtJst', 'cumulativeQuantity', 'cumulativeValueJpy', 'status', 'syntheticOnly'}, 'UPDATE_FIELDS')
        need(event['schemaId'] == UPDATE and event['syntheticOnly'] is True
             and type(event['eventId']) is str and re.fullmatch(r'[a-f0-9]{64}', event['eventId']), 'SIMULATED_UPDATE_REQUIRED')
        known = h.timestamp(event['knownAtJst'], self.session)
        need(known <= h.timestamp(at, self.session), 'UPDATE_FROM_FUTURE')
        def apply(s):
            need(event['orderId'] in s['orders'], 'ORDER_UNKNOWN')
            o = s['orders'][event['orderId']]
            need(o['symbol'] == event['symbol'] and o['side'] == event['side'], 'ORDER_IDENTITY_MISMATCH')
            need(o['status'] in ACTIVE and h.timestamp(o['updatedAt'], self.session) <= known
                 and h.timestamp(o['createdAt'], self.session) <= known, 'TERMINAL_OR_REVERSED_UPDATE')
            quantity, value, status = event['cumulativeQuantity'], money(event['cumulativeValueJpy']), event['status']
            need(type(quantity) is int and o['filled'] <= quantity <= o['quantity'] and value >= money(o['value']), 'CUMULATIVE_COUNTER_REVERSED')
            need(status in {'ACKNOWLEDGED', 'PARTIAL', 'FILLED', 'CANCELLED', 'REJECTED', 'UNKNOWN'}, 'UPDATE_STATUS')
            need(status != 'FILLED' or quantity == o['quantity'], 'FALSE_FULL_FILL')
            need(status != 'PARTIAL' or 0 < quantity < o['quantity'], 'FALSE_PARTIAL_FILL')
            need(status not in {'ACKNOWLEDGED', 'REJECTED'} or quantity == 0, 'FALSE_UNFILLED_STATUS')
            dq, dv = quantity - o['filled'], value - money(o['value'])
            need((dq == 0) == (dv == 0), 'QUANTITY_VALUE_DELTA_MISMATCH')
            if dq:
                eid = o['entryId']
                if o['side'] == 'BUY':
                    need(dv <= money(o['unitReserve']) * dq and dv <= money(s['cash']), 'FILL_EXCEEDS_RESERVED_CASH')
                    p = s['positions'].get(eid)
                    if p is None:
                        p = {'symbol': o['symbol'], 'quantity': 0, 'band': o['band'],
                             'filledAt': event['knownAtJst'], 'cost': '0', 'mark': str(dv / dq), 'markKnownAt': event['knownAtJst']}
                        s['positions'][eid] = p
                    p['quantity'] += dq
                    p['cost'] = str(money(p['cost']) + dv)
                    s['cash'] = str(money(s['cash']) - dv)
                else:
                    need(eid in s['positions'] and dq <= s['positions'][eid]['quantity'], 'SELL_NOT_OWNED')
                    p = s['positions'][eid]
                    p['cost'] = str(money(p['cost']) * (p['quantity'] - dq) / p['quantity'])
                    p['quantity'] -= dq
                    if p['quantity'] == 0:
                        del s['positions'][eid]
                    s['cash'] = str(money(s['cash']) + dv)
                    s['sellFillLatch'] = True
                    for buy in s['orders'].values():
                        if buy['side'] == 'BUY' and buy['status'] in CANCELLABLE:
                            buy['status'] = 'CANCEL_REQUESTED'
            if status == 'UNKNOWN':
                s['reconciliationBlocked'] = True
            if o['status'] == 'CANCEL_REQUESTED' and status not in TERMINAL and status != 'UNKNOWN':
                status = 'CANCEL_REQUESTED'
            o.update(filled=quantity, value=str(value), status=status, updatedAt=event['knownAtJst'])
            return {'status': status, 'filledDelta': dq, 'sellFillLatch': s['sellFillLatch']}
        return self._event('UPDATE:' + event['eventId'], event, at, apply)

    def summary(self):
        s = self.state()
        return {'schemaId': 'ARK_NO11_DURABLE_SHADOW_PORTFOLIO_SUMMARY_V1',
                'cashJpy': s['cash'], 'reservedCashJpy': str(self._reserved(s)),
                'positionCount': len(s['positions']), 'pendingOrders': sum(o['status'] in ACTIVE for o in s['orders'].values()),
                'buyIntentCount': sum(o['side'] == 'BUY' for o in s['orders'].values()),
                'sellIntentCount': sum(o['side'] == 'SELL' for o in s['orders'].values()),
                'firstSellFillBuyHalt': s['sellFillLatch'], 'reconciliationBlocked': s['reconciliationBlocked'],
                'events': s['eventSeq'], 'eventHeadSha256': s['eventHead'], 'syntheticAccountOnly': True,
                'brokerTransmissions': 0, 'productionReady': False, 'orderTransmission': False}
