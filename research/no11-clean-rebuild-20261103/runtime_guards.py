"""New source-only guards; no broker I/O, cash adoption or model changes.

Only the coordinator owns observation and transport. Ownership conflicts are
latched in its existing durable checkpoint; personal shares are never adopted.
"""
from __future__ import annotations


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError('NO11_CLEAN_' + reason)


def validate_fee_course(config: dict) -> None:
    """Validate explicit fee profile without changing existing permissions."""
    course = config.get('feeCourse')
    if course is None:
        return
    require(type(course) is str and course in ('ZERO', 'OTHER'), 'FEE_COURSE_UNKNOWN')
    require(course != 'ZERO' or config.get('orderTerms', {}).get('sor') is True,
            'ZERO_REQUIRES_SOR')


def latch_ownership_conflict(service, symbol: str, at: str) -> None:
    """Preserve observed ownership uncertainty even if quantity later returns.

This does not invent a manual fill or its price. The existing checkpoint is
reused rather than creating a second ownership ledger or clearing old flags.
"""
    writer = getattr(service.book, 'checkpoint_source', None)
    halt = getattr(service, 'halt_entry', None)
    require(callable(writer) and callable(halt), 'EXIT_DURABLE_LATCH_UNAVAILABLE')
    old = service.book.source_checkpoint('broker.externalSymbols') or []
    require(type(old) is list and all(type(x) is str for x in old), 'EXIT_EXTERNAL_CHECKPOINT')
    current = sorted(set(old) | {symbol})
    if current != old:
        writer('broker.externalSymbols', current, at)
    halt('NO11_CLEAN_OWNERSHIP_MISMATCH', at)


def recheck_exit(service, command: dict, at: str) -> str:
    """Validate a prepared SELL before IN_FLIGHT and irreversible transport.

A local observer read is not an atomic broker lock. Unobserved manual trades
cannot be detected and already-sent orders are not cancelled by this guard.
"""
    if command.get('kind') != 'ORDER' or command.get('side') != 'SELL':
        return at
    if service.config.get('evidenceMode') == 'BROKER_OBSERVATION':
        require(service.observe_file(at) is True, 'EXIT_OBSERVATION_FAILED')
        newer = service.clock()
        from no11_broker_execution_ledger import instant
        require(instant(newer, service.session) >= instant(at, service.session),
                'EXIT_CLOCK_REVERSED')
        at = newer
    require(service._source_current(at), 'EXIT_CURRENT_SOURCE_REQUIRED')
    state = service.book.snapshot(at)
    order = state.get('orders', {}).get(command.get('intentId'))
    require(type(order) is dict and order.get('commandId') == command.get('commandId')
            and all(order.get(k) == command.get(k)
                    for k in ('symbol', 'side', 'quantity', 'account')),
            'EXIT_RECORDED_ORDER_REQUIRED')
    quantity = order.get('quantity')
    position = state.get('positions', {}).get(order.get('entryId'))
    require(type(position) is dict and type(quantity) is int and quantity > 0
            and type(position.get('quantity')) is int
            and quantity <= position['quantity']
            and position.get('symbol') == order.get('symbol')
            and position.get('account') == order.get('account'),
            'EXIT_REMAINING_OWNERSHIP_REQUIRED')
    from no11_broker_fill_attribution import symbol
    holdings = [p for p in service.source['positions']
                if symbol(p['symbol']) == order['symbol'] and p['account'] == order['account']]
    owned = [p for p in state['positions'].values()
             if p.get('symbol') == order['symbol'] and p.get('account') == order['account']]
    require(all(type(p.get('quantity')) is int and p['quantity'] >= 0 for p in owned),
            'EXIT_OWNED_QUANTITY_INVALID')
    total = sum(p['quantity'] for p in owned)
    if len(holdings) != 1 or holdings[0]['quantity'] != total:
        # Latch before _sell_safe: that existing guard could reject a zero
        # holding first, losing the evidence of a later same-symbol rebuy.
        latch_ownership_conflict(service, order['symbol'], at)
        raise ValueError('NO11_CLEAN_EXIT_MIXED_OR_CHANGED_HOLDING')
    service._sell_safe(order, at)
    return at
