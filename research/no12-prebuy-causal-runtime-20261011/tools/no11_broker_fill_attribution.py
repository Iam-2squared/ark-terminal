"""Attribute recorded RSS executions without guessing a parent order.

RSS executions have no order number. Quantity is bound independently through
the persisted RSS ID -> broker order number. Prices are applied only when all
feasible quantity assignments in the observed group give the SAME gross value.
Execution rows may split across orders; treating a row as an indivisible fill
would manufacture uniqueness. No broker I/O, cash mutation, or authorization.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import heapq
import json
import re

from no11_broker_execution_ledger import ordered_json_bytes, money as ledger_money

SNAPSHOT = 'ARK_NO11_BROKER_SNAPSHOT_V1'
RECEIPT = 'ARK_NO11_BROKER_ORDER_RECEIPT_V1'
HEX = re.compile(r'[a-f0-9]{64}')
NS_SECOND = 1_000_000_000
JST = timezone(timedelta(hours=9))


def need(ok, code):
    if not ok:
        raise ValueError('NO11_BROKER_ATTR_' + code)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def instant(value, session=None):
    need(type(value) is str, 'CLOCK')
    m = re.fullmatch(r'(20\d\d)-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,7}))?\+09:00', value)
    need(m is not None, 'CLOCK')
    try:
        t = datetime(*map(int, m.groups()[:6]), tzinfo=JST)
    except ValueError:
        raise ValueError('NO11_BROKER_ATTR_CLOCK') from None
    need(session is None or t.date().isoformat() == session, 'SESSION_CLOCK')
    seconds = int(t.timestamp())
    return seconds * NS_SECOND + int((m[7] or '').ljust(9, '0') or '0')


def vendor_time(value, session):
    need(type(value) is str, 'VENDOR_TIME')
    m = re.fullmatch(r'(20\d\d)[/-](\d{1,2})[/-](\d{1,2})[ T](\d{2}):(\d{2}):(\d{2})(?:\+09:00)?', value)
    need(m is not None, 'VENDOR_TIME')
    result = '%s-%02d-%02dT%s:%s:%s+09:00' % (m[1], int(m[2]), int(m[3]), m[4], m[5], m[6])
    instant(result, session)
    return result


def price_ticks(value):
    need(type(value) in (str, int, float), 'PRICE')
    text = str(value)
    need(re.fullmatch(r'(?:0|[1-9]\d{0,12})(?:\.\d{1,6})?', text) is not None, 'PRICE')
    try:
        n = Decimal(text)
    except InvalidOperation:
        raise ValueError('NO11_BROKER_ATTR_PRICE') from None
    need(n.is_finite() and n > 0, 'PRICE')
    return int(n * 1_000_000)


def decimal_text(ticks):
    # Transport costs are exact integers. Decimal's ambient context must not
    # round a large, but otherwise valid, group sum before it reaches the ledger.
    whole, fraction = divmod(ticks, 1_000_000)
    tail = f'{fraction:06d}'.rstrip('0')
    return str(whole) + ('.' + tail if tail else '')


def symbol(value):
    need(type(value) is str and re.fullmatch(r'[0-9A-Z]{4}(?:\.T)?', value), 'SYMBOL')
    return value if value.endswith('.T') else value + '.T'


def side(value):
    values = {'買付': 'BUY', '買': 'BUY', '売付': 'SELL', '売': 'SELL', 'BUY': 'BUY', 'SELL': 'SELL'}
    need(type(value) is str and value in values, 'SIDE')
    return values[value]


def quantity(value, positive=False):
    need(type(value) is int and int(positive) <= value <= 1_000_000_000, 'QUANTITY')
    return value


def order_phase(row):
    q, filled = quantity(row.get('quantity'), True), quantity(row.get('filledQty'))
    need(filled <= q, 'FILLED_EXCEEDS_ORDER')
    raw = row.get('status')
    need(type(raw) is str and bool(raw), 'ORDER_STATUS')
    raw = raw.replace('(', '（').replace(')', '）')
    if raw == '約定':
        need(filled == q, 'FALSE_FULL_FILL')
        return 'FILLED'
    for prefix, result in [('取消済', 'CANCELLED'), ('出来ず', 'EXPIRED'), ('取消中', 'CANCEL_PENDING')]:
        if raw in (prefix + '（出来有）', prefix + '（出来無）'):
            need(0 < filled < q if raw.endswith('（出来有）') else filled == 0, 'FALSE_PARTIAL_FILL')
            return result
    if raw == '出来有':
        need(0 < filled < q, 'FALSE_PARTIAL_FILL')
        return 'PARTIAL'
    if raw in ('執行待ち', '執行中', '訂正済'):
        return 'PARTIAL' if filled else 'ACKNOWLEDGED'
    return 'UNKNOWN'


def _execution_fingerprint(row, session):
    return digest([symbol(row.get('symbol')), row.get('account'), side(row.get('side')),
                   row.get('market'), vendor_time(row.get('executionDate'), session),
                   quantity(row.get('quantity'), True), price_ticks(row.get('price'))])


def _min_cost(executions, orders, target, charge_target):
    """Integer min-cost transport; each share may be allocated independently."""
    n, m = len(executions), len(orders)
    sink, size = n + m + 1, n + m + 2
    graph = [[] for _ in range(size)]

    def edge(a, b, cap, cost):
        graph[a].append([b, len(graph[b]), cap, cost])
        graph[b].append([a, len(graph[a]) - 1, 0, -cost])

    for i, row in enumerate(executions):
        edge(0, 1 + i, row['quantity'], 0)
        for j, order in enumerate(orders):
            if row['timeNs'] < order['acceptedNs']:
                continue
            cost = row['priceTicks'] if ((j == target) == charge_target) else 0
            edge(1 + i, 1 + n + j, row['quantity'], cost)
    for j, order in enumerate(orders):
        edge(1 + n + j, sink, order['filledQty'], 0)
    wanted = sum(r['quantity'] for r in executions)
    if wanted != sum(o['filledQty'] for o in orders):
        return None
    sent = total = 0
    potentials = [0] * size
    while sent < wanted:
        dist, previous = [None] * size, [None] * size
        dist[0] = 0
        heap = [(0, 0)]
        while heap:
            d, u = heapq.heappop(heap)
            if dist[u] != d:
                continue
            for k, (v, _, capacity, cost) in enumerate(graph[u]):
                if capacity <= 0:
                    continue
                nd = d + cost + potentials[u] - potentials[v]
                if dist[v] is None or nd < dist[v]:
                    dist[v], previous[v] = nd, (u, k)
                    heapq.heappush(heap, (nd, v))
        if dist[sink] is None:
            return None
        for v, d in enumerate(dist):
            if d is not None:
                potentials[v] += d
        amount, v, path_cost = wanted - sent, sink, 0
        while v:
            u, k = previous[v]
            amount = min(amount, graph[u][k][2])
            path_cost += graph[u][k][3]
            v = u
        v = sink
        while v:
            u, k = previous[v]
            e = graph[u][k]
            e[2] -= amount
            graph[v][e[1]][2] += amount
            v = u
        sent += amount
        total += amount * path_cost
    return total


def inspect_source(snapshot, session, through, previous=None):
    """Persistable source multiset. A revised row is never a second new fill."""
    need(type(snapshot) is dict and snapshot.get('schemaId') == SNAPSHOT
         and snapshot.get('orderTransmission') is False, 'SNAPSHOT')
    need(snapshot.get('sessionDate') == session and snapshot.get('readOnly') is True
         and snapshot.get('productionReady') is False and snapshot.get('sameSnapshotVerified') is True
         and snapshot.get('verificationBasis') == 'DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED'
         and snapshot.get('cashScope') == 'ALL_CHANNELS_ALL_STATUSES_CASH_ONLY'
         and snapshot.get('completeTables') is True and snapshot.get('rowsTruncated') is False
         and snapshot.get('actualFeedTimestampCertified') is False
         and snapshot.get('buyingPowerFreshnessCertified') is False, 'NORMALIZED_READONLY_SOURCE_REQUIRED')
    end = instant(snapshot.get('captureCompletedAt'), session)
    start = instant(snapshot.get('capturedAt'), session)
    now = instant(through, session)
    need(start <= end <= now and end - start < 25 * NS_SECOND
         and now - end <= 30 * NS_SECOND, 'STALE_OR_FUTURE_SNAPSHOT')
    key = snapshot.get('sessionKey') or snapshot.get('excelSession', {}).get('sessionKey')
    need(type(key) is str and HEX.fullmatch(key), 'EXCEL_SESSION')
    checksum = snapshot.get('snapshotSha256')
    need(type(checksum) is str and HEX.fullmatch(checksum), 'SNAPSHOT_HASH')
    body = {k: v for k, v in snapshot.items() if k != 'snapshotSha256'}
    need(checksum == hashlib.sha256(ordered_json_bytes(body)).hexdigest(), 'SNAPSHOT_HASH_CHANGED')
    for name in ('idRows', 'orders', 'executions', 'positions'):
        need(type(snapshot.get(name)) is list and len(snapshot[name]) <= 5000, 'SOURCE_ROWS')
    ids = [r.get('orderNumber') for r in snapshot['orders']]
    need(all(type(v) is str and re.fullmatch(r'[1-9][0-9]{0,31}', v) for v in ids)
         and len(ids) == len(set(ids)), 'ORDER_NUMBERS')
    rows = Counter()
    for row in snapshot['executions']:
        stamp = vendor_time(row.get('executionDate'), session)
        need(instant(stamp, session) <= end, 'FUTURE_EXECUTION')
        need(row.get('trade') == '現物', 'EXECUTION_NOT_CASH')
        need(type(row.get('account')) is str and bool(row['account']), 'ACCOUNT')
        rows[_execution_fingerprint(row, session)] += 1
    issues = []
    if previous is not None:
        need(type(previous) is dict and previous.get('schemaId') == 'ARK_NO11_BROKER_SOURCE_STATE_V1'
             and previous.get('sessionDate') == session, 'PREVIOUS_SOURCE')
        body = {k: v for k, v in previous.items() if k != 'stateSha256'}
        need(previous.get('stateSha256') == digest(body), 'PREVIOUS_SOURCE_HASH')
        need(end >= instant(previous['captureCompletedAt'], session), 'SOURCE_CLOCK_REVERSED')
        if end == instant(previous['captureCompletedAt'], session):
            need(checksum == previous['snapshotSha256'], 'SAME_TIME_SOURCE_CHANGED')
        issues.extend(previous['latchedIssues'])
        if any(rows.get(k, 0) < n for k, n in previous['executionRows'].items()):
            issues.append('EXECUTION_ROWS_REMOVED_OR_REVISED')
        rows |= Counter(previous['executionRows'])
    state = {'schemaId': 'ARK_NO11_BROKER_SOURCE_STATE_V1', 'sessionDate': session,
             'sessionKey': key, 'captureCompletedAt': snapshot['captureCompletedAt'],
             'snapshotSha256': checksum, 'executionRows': dict(rows),
             'latchedIssues': sorted(set(issues)), 'orderTransmission': False}
    return {**state, 'stateSha256': digest(state)}


def attribute_order(origin, snapshot, *, session, through, source_state=None, fees=None,
                    evidence_mode='BROKER_OBSERVATION'):
    """Return quantity evidence even when price attribution is ambiguous.

    A verified persistent broker number survives an Excel restart. An unbound
    RSS ID does not. No symbol-only binding and no guessed fill timestamps.
    """
    need(evidence_mode in ('OFFLINE_REPLAY', 'BROKER_OBSERVATION'), 'EVIDENCE_MODE')
    state = inspect_source(snapshot, session, through, source_state)
    need(type(origin) is dict and origin.get('sessionDate', session) == session, 'ORIGIN')
    for name in ('intentId', 'rssSessionKey'):
        need(type(origin.get(name)) is str and HEX.fullmatch(origin[name]), 'ORIGIN_IDENTITY')
    rid = origin.get('rssOrderId')
    need(type(rid) is int and 1 <= rid <= 2147483647, 'RSS_ID')
    created = instant(origin.get('createdAtJst'), session)
    need(created <= instant(through, session), 'FUTURE_ORIGIN')
    number = origin.get('brokerOrderNumber')
    binding_from_current_id = False
    if origin['rssSessionKey'] == state['sessionKey']:
        matches = [r for r in snapshot['idRows'] if r.get('rssOrderId') == rid]
        need(len(matches) <= 1, 'DUPLICATE_RSS_ID')
        if matches:
            row = matches[0]
            need(row.get('functionName') in ('RssStockOrder', 'RssStockOrder_V', 'RssStockOrder_v')
                 and row.get('orderDate') == session, 'RSS_ID_IDENTITY')
            stamped = session + 'T' + str(row.get('orderTime')) + '+09:00'
            time = instant(stamped, session)
            need(created // NS_SECOND * NS_SECOND <= time <= instant(snapshot['captureCompletedAt'], session),
                 'RSS_ID_CLOCK')
            current = row.get('orderNumber')
            need(type(current) is str and re.fullmatch(r'[1-9][0-9]{0,31}', current), 'ORDER_NUMBER_UNAVAILABLE')
            need(number is None or number == current, 'BROKER_NUMBER_CHANGED')
            need(sum(r.get('orderNumber') == current and r.get('functionName') == row['functionName']
                     for r in snapshot['idRows']) == 1, 'BROKER_NUMBER_MULTIPLE_IDS')
            number, binding_from_current_id = current, True
    need(number is not None and (binding_from_current_id or origin.get('brokerBindingVerified') is True),
         'ORIGIN_NOT_BOUND_RECONCILIATION_REQUIRED')
    rows = [r for r in snapshot['orders'] if r.get('orderNumber') == number]
    need(len(rows) == 1, 'ORDER_DISAPPEARED_UNRESOLVED')
    row = rows[0]
    target_symbol, target_side = symbol(origin.get('symbol')), side(origin.get('side'))
    need(row.get('trade') == '現物' and symbol(row.get('symbol')) == target_symbol
         and side(row.get('side')) == target_side and row.get('account') == origin.get('account')
         and row.get('quantity') == origin.get('quantity'), 'ORDER_IDENTITY_CHANGED')
    phase = order_phase(row)
    qty = row['filledQty']
    prior_qty = origin.get('cumulativeQuantity', 0)
    need(type(prior_qty) is int and qty >= prior_qty, 'CUMULATIVE_FILL_REVERSED')
    issues = list(state['latchedIssues'])
    matching = [r for r in snapshot['orders'] if r.get('trade') == '現物'
                and symbol(r.get('symbol')) == target_symbol and r.get('account') == origin['account']
                and side(r.get('side')) == target_side]
    executions = [r for r in snapshot['executions'] if symbol(r.get('symbol')) == target_symbol
                  and r.get('account') == origin['account'] and side(r.get('side')) == target_side]
    gross = '0' if qty == 0 else None
    first_fill = None
    assigned_orders, assigned_rows = [], []
    if qty:
        for order in matching:
            order_phase(order)
            if order['filledQty'] == 0:
                continue
            observed_at = (order.get('orderReceivedAt') or order.get('acceptedAtJst')
                           or order.get('orderDateTime') or order.get('receivedAt'))
            if observed_at is None:
                # Only the target has an independently persisted local origin.
                if order['orderNumber'] == number:
                    accepted_ns = created // NS_SECOND * NS_SECOND
                else:
                    issues.append('OTHER_ORDER_TIME_UNAVAILABLE')
                    continue
            else:
                try:
                    accepted_ns = instant(vendor_time(observed_at, session), session)
                except ValueError:
                    issues.append('ORDER_TIME_INVALID')
                    continue
                if order['orderNumber'] == number and accepted_ns < created // NS_SECOND * NS_SECOND:
                    issues.append('TARGET_ORDER_TIME_PRECEDES_ORIGIN')
            assigned_orders.append(dict(order, acceptedNs=accepted_ns))
        for execution in executions:
            stamp = vendor_time(execution['executionDate'], session)
            market = execution.get('market')
            if market not in ('東証', '東京', 'T', '東証プライム', '東証スタンダード', '東証グロース'):
                issues.append('EXECUTION_MARKET_UNRESOLVED')
            assigned_rows.append(dict(execution, timeNs=instant(stamp, session),
                                      executionStamp=stamp, priceTicks=price_ticks(execution['price'])))
        target = next((i for i, o in enumerate(assigned_orders) if o['orderNumber'] == number), None)
        if len(assigned_orders) > 300 or len(assigned_rows) > 300:
            # A large unrelated account must not hide the target's confirmed
            # quantity. Bound the expensive allocation proof, not ownership.
            issues.append('PRICE_ATTRIBUTION_CAPACITY')
        if not issues and target is not None:
            lower = _min_cost(assigned_rows, assigned_orders, target, True)
            other = _min_cost(assigned_rows, assigned_orders, target, False)
            total = sum(r['priceTicks'] * r['quantity'] for r in assigned_rows)
            upper = None if other is None else total - other
            if lower is None or upper is None:
                issues.append('ORDER_EXECUTION_QUANTITY_OR_TIME_MISMATCH')
            elif lower != upper:
                issues.append('AMBIGUOUS_ORDER_EXECUTION_PRICE')
            else:
                gross = decimal_text(lower)
                # The exact first execution time is certified only in a
                # singleton group. Identical total cost need not fix its time.
                if len(assigned_orders) == 1:
                    first_fill = min(r['executionStamp'] for r in assigned_rows)
        elif target is None:
            issues.append('TARGET_FILL_SOURCE_UNAVAILABLE')
    # A contradictory monetary observation must not discard independently
    # bound positive shares. The ledger still rejects direct money reversal;
    # this adapter withholds only the contradictory amount from that receipt.
    prior_gross = ledger_money(origin.get('knownGrossJpy', '0'))
    prior_priced_qty = origin.get('grossVerifiedThroughQuantity', 0)
    need(type(prior_priced_qty) is int and 0 <= prior_priced_qty <= prior_qty, 'PRIOR_PRICED_QUANTITY')
    if gross is not None:
        try:
            current_gross = ledger_money(gross)
            if current_gross < prior_gross or (qty > prior_priced_qty and current_gross <= prior_gross):
                issues.append('CUMULATIVE_CONSIDERATION_CONFLICT')
                gross = None
        except ValueError:
            issues.append('CONSIDERATION_OUT_OF_RANGE')
            gross = None
    fees_value, tax_value = None, None
    receipt_known = snapshot['captureCompletedAt']
    usable_fees = None
    supplied_fee_hash = None
    if fees is not None:
        try:
            # json.loads accepts nonstandard NaN/Infinity by default. Such a
            # charge record is unusable, but must not prevent quantity capture.
            supplied_fee_hash = digest(fees)
            need(type(fees) is dict and fees.get('brokerOrderNumber') == number
                 and fees.get('sessionDate') == session
                 and type(fees.get('sourceSha256')) is str and HEX.fullmatch(fees['sourceSha256']), 'FEE_EVIDENCE')
            need(type(fees.get('cumulativeQuantity')) is int and fees['cumulativeQuantity'] == qty,
                 'FEE_CUMULATIVE_QUANTITY')
            fee_time = instant(fees.get('knownAtJst'), session)
            need(fee_time <= instant(through, session), 'FEE_FROM_FUTURE')
            # A fee receipt bound to a previous cumulative quantity cannot
            # cover a later fill. Also reject evidence predating any execution
            # which could belong to this order. Reusing evidence at unchanged
            # quantity remains valid when the underlying fill rows are stable.
            last_possible_fill = max((r['timeNs'] for r in assigned_rows), default=created // NS_SECOND * NS_SECOND)
            if qty:
                old_quantity_known = origin.get('quantityKnownAtJst') if prior_qty == qty else None
                last_possible_fill = max(last_possible_fill,
                    instant(old_quantity_known or snapshot['captureCompletedAt'], session))
                # New matching rows were not known at the earlier charge
                # attestation, even when their vendor time is in the past.
                prior_rows = (source_state or {}).get('executionRows', {})
                current_rows = Counter(_execution_fingerprint(r, session) for r in executions)
                if any(n > prior_rows.get(key, 0) for key, n in current_rows.items()):
                    last_possible_fill = max(last_possible_fill, instant(snapshot['captureCompletedAt'], session))
            need(fee_time >= last_possible_fill, 'FEE_PREDATES_FILL')
            for key in ('cumulativeFeesJpy', 'cumulativeTaxesJpy'):
                value = fees.get(key)
                need(type(value) in (str, int) and re.fullmatch(r'(?:0|[1-9]\d{0,14})(?:\.\d{1,6})?', str(value)),
                     'FEE_AMOUNT')
                ledger_money(value)
            fees_value, tax_value = str(fees['cumulativeFeesJpy']), str(fees['cumulativeTaxesJpy'])
            usable_fees = deepcopy(fees)
            if fee_time > instant(receipt_known, session):
                receipt_known = fees['knownAtJst']
        except (ValueError, TypeError, KeyError):
            # Bad/missing charge evidence cannot erase independently observed
            # positive shares; retain quantity and leave money charges unknown.
            issues.append('FEE_EVIDENCE_UNUSABLE')
    for key, value in [('cumulativeFeesJpy', fees_value), ('cumulativeTaxesJpy', tax_value)]:
        if value is not None and ledger_money(value) < ledger_money(origin.get(key, '0')):
            issues.append('CUMULATIVE_CHARGES_CONFLICT')
            if key == 'cumulativeFeesJpy':
                fees_value = None
            else:
                tax_value = None
    prior_fill = origin.get('filledAtJst') if origin.get('fillTimeVerified') is True else None
    if prior_fill is not None:
        need(created // NS_SECOND * NS_SECOND <= instant(prior_fill, session) <= instant(through, session),
             'PRIOR_FILL_TIME')
    fill_conflict = origin.get('fillTimeConflict') is True
    if first_fill is not None and prior_fill is not None and instant(first_fill, session) != instant(prior_fill, session):
        fill_conflict = True
    if fill_conflict:
        issues.append('FIRST_FILL_TIME_CONFLICT')
    verified_fill = None if fill_conflict else (prior_fill or first_fill)
    immutable_origin = {key: origin.get(key) for key in ('sessionDate', 'intentId', 'rssSessionKey',
        'rssOrderId', 'createdAtJst', 'symbol', 'side', 'account', 'quantity')}
    immutable_origin['sessionDate'] = session
    evidence = {'origin': immutable_origin, 'sourceSnapshotSha256': state['snapshotSha256'],
                'brokerOrderNumber': number, 'quantity': qty, 'gross': gross,
                'blockers': sorted(set(issues)), 'fees': usable_fees,
                'suppliedFeeEvidenceSha256': supplied_fee_hash,
                'filledAtJst': verified_fill, 'fillTimeConflict': fill_conflict,
                'attributionPolicy': 'ALL_FEASIBLE_SHARE_ASSIGNMENTS_HAVE_EQUAL_GROSS_V1'}
    evidence_hash = digest(evidence)
    receipt = {'schemaId': RECEIPT, 'sessionDate': session,
        'eventId': digest([origin['intentId'], evidence_hash, phase]),
        'intentId': origin['intentId'], 'rssSessionKey': origin['rssSessionKey'], 'rssOrderId': rid,
        'symbol': target_symbol, 'side': target_side, 'account': origin['account'],
        'brokerOrderNumber': number, 'knownAtJst': receipt_known,
        'cumulativeQuantity': qty, 'cumulativeGrossJpy': gross,
        'cumulativeFeesJpy': fees_value, 'cumulativeTaxesJpy': tax_value,
        'status': phase, 'filledAtJst': verified_fill, 'fillTimeVerified': verified_fill is not None,
        'fillTimeConflict': fill_conflict, 'quantityKnownAtJst': snapshot['captureCompletedAt'],
        'quantityAttributionVerified': True, 'attributionVerified': gross is not None,
        'evidenceMode': evidence_mode, 'sourceSnapshotSha256': state['snapshotSha256'],
        'allocationEvidenceSha256': evidence_hash}
    return {'receipt': receipt, 'sourceState': state, 'blockers': sorted(set(issues)),
            'status': 'OBSERVED_UNIQUE_PRICE' if gross is not None else 'QUANTITY_ONLY_PRICE_UNRESOLVED',
            'brokerBindingVerified': True, 'bindingFromCurrentId': binding_from_current_id,
            'brokerFeedAtomicityCertified': False, 'orderTransmission': False,
            'allocationEvidence': deepcopy(evidence)}
